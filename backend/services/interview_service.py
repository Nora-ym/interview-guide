"""
面试服务
模拟面试的核心引擎，包括：

技能方向管理（加载 skills/ 目录下的定义文件）
创建面试会话
开始面试（AI 发出开场白 + 第一题）
处理用户回答 → AI 追问/下一题/结束评估
结束面试 → 生成评估报告
面试历史查询
出题策略：

每 3 轮做一次追问（深入挖掘）
其他轮次直接出下一道新题
通过系统提示词控制题目难度和方向
"""

import json
from datetime import datetime
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.interview import Interview, InterviewMessage
from backend.models.user import User
from backend.services.ai_service import chat, chat_structured
from backend.utils.pdf_generator import generate_interview_evaluation_pdf
from backend.services.storage_service import upload_file

# 技能方向注册表
SKILL_REGISTRY: dict[str, dict] = {}


def load_skills():
    """
    从 skills/ 目录加载所有技能方向定义
    每个 .md 文件格式：第一行是名称（# 开头），后面是描述
    """
    from pathlib import Path
    skills_dir = Path(__file__).parent.parent / "skills"
    if not skills_dir.exists():
        return
    for md_file in skills_dir.glob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        lines = content.strip().split("\n")
        name = lines[0].strip("# ").strip()
        description = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
        SKILL_REGISTRY[md_file.stem] = {
            "id": md_file.stem,
            "name": name,
            "description": description,
            "raw_content": content,
        }


load_skills()


def get_available_skills() -> list[dict]:
    """获取所有可用的技能方向"""
    return list(SKILL_REGISTRY.values())


async def create_interview(
    db: AsyncSession, user: User, skill_id: str,
    difficulty: str = "medium", interview_type: str = "text", max_rounds: int = 10,
) -> Interview:
    """创建面试会话（还没开始，只创建记录）"""
    skill = SKILL_REGISTRY.get(skill_id)
    if not skill:
        raise ValueError(f"不存在的技能方向: {skill_id}")
    interview = Interview(
        user_id=user.id, skill_id=skill_id, skill_name=skill["name"],
        difficulty=difficulty, interview_type=interview_type,
        status="in_progress", max_rounds=max_rounds, current_round=0,
    )
    db.add(interview)
    await db.flush()
    await db.refresh(interview)
    return interview


async def start_interview(db: AsyncSession, interview: Interview) -> str:
    """开始面试：AI 发出开场白 + 第一道题"""
    system_prompt = _build_system_prompt(interview)
    prompt = (
        f"技能方向：{interview.skill_name}\n"
        f"难度：{interview.difficulty}\n"
        f"最大轮数：{interview.max_rounds}\n\n"
        f"请先做简短自我介绍，然后直接给出第一道面试题。"
    )
    response = await chat(messages=[{"role": "user", "content": prompt}], system_prompt=system_prompt)
    msg = InterviewMessage(
        interview_id=interview.id, role="interviewer", content=response,
        message_type="text", round=1,
    )
    db.add(msg)
    interview.current_round = 1
    await db.flush()
    return response


async def submit_answer(db: AsyncSession, interview: Interview, answer: str) -> str:
    """
    用户提交回答 → AI 评估 + 追问 或 下一题 或 结束面试

    决策逻辑：
    1. 如果已达最大轮数 → 结束面试
    2. 如果 current_round 是 3 的倍数 → 追问
    3. 否则 → 出下一道新题
    """
    if interview.status != "in_progress":
        raise ValueError("面试已结束")
    if interview.current_round >= interview.max_rounds:
        return await finish_interview(db, interview)

    # 保存用户回答
    user_msg = InterviewMessage(
        interview_id=interview.id, role="candidate", content=answer,
        message_type="text", round=interview.current_round + 1,
    )
    db.add(user_msg)

    # 获取对话历史
    history = await _get_history(db, interview)
    system_prompt = _build_system_prompt(interview)

    # 决定操作：追问 or 出题
    is_follow_up = interview.current_round > 0 and interview.current_round % 3 == 0
    prompt = (
        f"用户回答了第 {interview.current_round} 题。"
        f"进度：{interview.current_round}/{interview.max_rounds}\n"
        f"操作：{'追问候选人的回答' if is_follow_up else '给出下一道面试题'}\n\n"
        f"不要给答案，保持专业氛围。"
    )
    response = await chat(messages=history + [{"role": "user", "content": prompt}],
                         system_prompt=system_prompt)

    ai_msg = InterviewMessage(
        interview_id=interview.id, role="interviewer", content=response,
        message_type="text", round=interview.current_round + 1,
    )
    db.add(ai_msg)
    interview.current_round += 1

    if interview.current_round >= interview.max_rounds:
        await db.flush()
        return await finish_interview(db, interview)
    await db.flush()
    return response


async def finish_interview(db: AsyncSession, interview: Interview) -> str:
    """结束面试并生成评估"""
    history = await _get_history(db, interview)
    system_prompt = (
        "你是资深面试官，面试结束，请全面评估。"
        "每个维度0-25分（技术深度/问题解决/沟通表达/项目经验），"
        "总分0-100，列优势不足和改进建议。"
    )
    eval_schema = {
        "dimension_scores": {
            "technical_depth": {"score": 0, "comment": ""},
            "problem_solving": {"score": 0, "comment": ""},
            "communication": {"score": 0, "comment": ""},
            "project_experience": {"score": 0, "comment": ""},
        },
        "total_score": 0,
        "strengths": [],
        "weaknesses": [],
        "improvement_suggestions": [],
        "summary": "",
    }
    evaluation = await chat_structured(
        messages=history + [{"role": "user", "content": "请对整场面试进行最终评估。"}],
        output_schema=eval_schema, temperature=0.3, system_prompt=system_prompt,
    )

    dim_scores = evaluation.get("dimension_scores", {})
    total = sum(d.get("score", 0) for d in dim_scores.values())
    evaluation["total_score"] = min(total, 100)

    interview.evaluation = evaluation
    interview.total_score = evaluation["total_score"]
    interview.status = "completed"

    # 生成 PDF 报告
    messages_data = [{"role": m.role, "content": m.content, "round": m.round}
                     for m in await _get_messages(db, interview)]
    pdf_bytes = generate_interview_evaluation_pdf(
        evaluation, interview.skill_name, interview.difficulty,
        interview.total_score, "", messages_data,
    )
    interview.report_url = upload_file(
        pdf_bytes, f"interview_report_{interview.id}.pdf",
        folder="reports", content_type="application/pdf",
    )
    interview.ended_at = datetime.now()

    conclusion = _format_conclusion(evaluation, dim_scores)
    end_msg = InterviewMessage(
        interview_id=interview.id, role="interviewer", content=conclusion,
        message_type="text", round=interview.current_round,
    )
    db.add(end_msg)
    await db.flush()
    return conclusion


def _format_conclusion(evaluation: dict, dim_scores: dict) -> str:
    """格式化面试结束的总结文字"""
    text = f"面试结束！\n\n总分：{evaluation['total_score']}/100\n\n| 维度 | 评分 |\n|------|------|"
    for dim, info in dim_scores.items():
        text += f"\n| {dim} | {info.get('score', 'N/A')}/25 |"
    for label, key in [("优势", "strengths"), ("改进建议", "improvement_suggestions")]:
        items = evaluation.get(key, [])
        if items:
            text += f"\n\n{label}：\n"
            for item in items:
                text += f"- {item}\n"
    text += f"\n{evaluation.get('summary', '')}\n\n评估报告 PDF 已生成。"
    return text


def _build_system_prompt(interview: Interview) -> str:
    """构建面试系统提示词"""
    skill = SKILL_REGISTRY.get(interview.skill_id, {})
    diff_map = {"easy": "初级", "medium": "中级", "hard": "高级"}
    return (
        f"你是资深技术面试官。技能方向：{interview.skill_name}，"
        f"难度：{diff_map.get(interview.difficulty, interview.difficulty)}。\n"
        f"考察要求：{skill.get('description', '')}\n"
        f"规则：每次只问一道题、不给答案、追问时先简评再追问、保持专业氛围。"
    )


async def _get_history(db: AsyncSession, interview: Interview) -> list[dict]:
    """获取对话历史（给大模型做上下文）"""
    msgs = await _get_messages(db, interview)
    return [{"role": m.role, "content": m.content} for m in msgs]


async def _get_messages(db: AsyncSession, interview: Interview) -> list[InterviewMessage]:
    """获取面试的所有消息（按时间排序）"""
    result = await db.execute(
        select(InterviewMessage)
        .where(InterviewMessage.interview_id == interview.id)
        .order_by(InterviewMessage.created_at)
    )
    return list(result.scalars().all())


async def get_user_interviews(
    db: AsyncSession, user_id: int, status: str | None = None,
    page: int = 1, page_size: int = 20,
) -> tuple[list[Interview], int]:
    """获取用户的面试列表（分页，可选状态筛选）"""
    conditions = [Interview.user_id == user_id]
    if status:
        conditions.append(Interview.status == status)
    query = select(Interview).where(and_(*conditions))
    count_query = select(func.count()).select_from(Interview).where(and_(*conditions))
    total = (await db.execute(count_query)).scalar()
    result = await db.execute(
        query.order_by(Interview.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    return list(result.scalars().all()), total or 0


async def get_interview_detail(
    db: AsyncSession, interview_id: int, user_id: int,
) -> Interview | None:
    """获取面试详情（含所有消息，验证归属权）"""
    result = await db.execute(
        select(Interview).where(Interview.id == interview_id, Interview.user_id == user_id)
    )
    return result.scalar_one_or_none()