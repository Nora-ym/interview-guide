"""
====================================================
面试服务（重写版）
====================================================

修复了以下问题：

【1. 评分失真 —— 最核心问题】
  原问题：
    ① _get_history() 把消息角色传成 "interviewer"/"candidate"，
      大模型只认识 "assistant"/"user"，导致整个对话上下文被大模型
      误解，评估时根本不知道谁问谁答，分数完全失去依据。
    ② finish_interview 直接把对话扔给大模型让它自己评，没有任何引导，
      大模型不知道哪些回答好哪些回答差，容易给出随机分数。
    ③ eval_schema 的 score 是字符串占位 "请给出0~25的整数"，
      AI 有时原样返回字符串，sum() 直接 TypeError；
      有时忽略实际对话内容，直接填一个感觉合理的默认值。
  修复：
    ① 修复角色映射：interviewer→assistant，candidate→user。
    ② 引入 _build_qa_summary()：评估前先提取并格式化每一轮的
      "题目 + 候选人回答"，让大模型有明确的打分依据。
    ③ 评估 prompt 明确要求大模型按题逐一分析质量，再汇总打分。
    ④ eval_schema score 字段用整数 0 占位，prompt 强调必须是整数；
      _normalize_evaluation() 做全面类型安全转换兜底。

【2. 出题逻辑】
  原问题：追问/出新题决策用自然语言塞进 prompt 末尾，AI 可能忽略；
          Redis 去重函数从未被调用，AI 会重复出题。
  修复：  _decide_action() 在 Python 层硬决策；
          独立 prompt 模板精确表达意图；
          每道题哈希后写 Redis，重复时自动重试换题。

【3. 最大轮数边界】
  原问题：current_round 语义混乱，submit_answer 有两处结束判断，
          第一处触发时用户消息未 flush，finish_interview 丢失最后一条回答。
  修复：  current_round 统一语义：= 已完整完成的问答轮数（0 表示还未有回答）；
          submit_answer 只有一处结束判断，用户消息先 flush 再判断。
"""

import hashlib
from datetime import datetime
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.interview import Interview, InterviewMessage
from backend.models.user import User
from backend.services.ai_service import chat, chat_structured
from backend.services.cache_service import add_asked_question, is_question_asked
from backend.utils.pdf_generator import generate_interview_evaluation_pdf
from backend.services.storage_service import upload_file


# ================================================================
# 技能方向注册表
# ================================================================

SKILL_REGISTRY: dict[str, dict] = {}


def load_skills():
    """
    从 skills/ 目录加载所有技能方向定义（*.md）。
    文件格式：第一行是 # 技能名称，其余行是考察要求描述。
    应用启动时由 main.py 的 lifespan 调用。
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
    """获取所有可用的技能方向（供 GET /interviews/skills 返回）"""
    return list(SKILL_REGISTRY.values())


# ================================================================
# 创建 & 开始面试
# ================================================================

async def create_interview(
    db: AsyncSession,
    user: User,
    skill_id: str,
    difficulty: str = "medium",
    interview_type: str = "text",
    max_rounds: int = 10,
) -> Interview:
    """
    创建面试会话记录（此时只建库记录，不与 AI 交互）。

    current_round 初始值为 0，语义：
        0 = 面试已建立，尚未有任何完整的问答轮次
    """
    skill = SKILL_REGISTRY.get(skill_id)
    if not skill:
        raise ValueError(f"不存在的技能方向: {skill_id}")

    interview = Interview(
        user_id=user.id,
        skill_id=skill_id,
        skill_name=skill["name"],
        difficulty=difficulty,
        interview_type=interview_type,
        status="in_progress",
        max_rounds=max_rounds,
        current_round=0,
    )
    db.add(interview)
    await db.flush()
    await db.refresh(interview)
    return interview


async def start_interview(db: AsyncSession, interview: Interview) -> str:
    """
    开始面试：AI 发出简短开场白并提出第 1 题。

    current_round 保持 0，代表"AI 已出题，用户尚未作答"。
    只有 submit_answer 收到第一次回答后，current_round 才会变为 1。
    """
    system_prompt = _build_system_prompt(interview)
    prompt = (
        f"现在开始对候选人进行【{interview.skill_name}】方向的"
        f"{_diff_label(interview.difficulty)}难度模拟面试，"
        f"共 {interview.max_rounds} 轮问答。\n\n"
        "请先用 1-2 句话做简短自我介绍，然后直接给出第 1 题。\n"
        "要求：只问一道题，不给答案，不做多余解释。"
    )

    response = await chat(
        messages=[{"role": "user", "content": prompt}],
        system_prompt=system_prompt,
        temperature=0.7,
    )

    _save_msg(db, interview, role="interviewer", content=response, round_num=1)
    await add_asked_question(interview.id, _hash_text(response))
    await db.flush()
    return response


# ================================================================
# 提交回答（核心流程）
# ================================================================

async def submit_answer(db: AsyncSession, interview: Interview, answer: str) -> str:
    """
    用户提交回答，处理流程：

    1. 状态校验
    2. 保存用户回答并立即 flush（确保 finish_interview 能读到）
    3. current_round += 1 并 flush
    4. 唯一一处结束判断：达到 max_rounds → 结束
    5. Python 层决策追问/出新题，生成 AI 回复，Redis 去重
    """
    if interview.status != "in_progress":
        raise ValueError("面试已结束")

    this_round = interview.current_round + 1

    # 步骤 2：保存用户回答，立即 flush
    _save_msg(db, interview, role="candidate", content=answer, round_num=this_round)
    await db.flush()

    # 步骤 3：更新轮数
    interview.current_round = this_round
    await db.flush()

    # 步骤 4：唯一的结束判断
    if interview.current_round >= interview.max_rounds:
        return await finish_interview(db, interview)

    # 步骤 5：决策 + 生成回复
    action = _decide_action(interview.current_round)
    next_round = interview.current_round + 1
    history = await _get_history(db, interview)
    system_prompt = _build_system_prompt(interview)

    if action == "follow_up":
        instruction = _build_follow_up_prompt(interview, this_round)
    else:
        instruction = _build_next_question_prompt(interview, this_round, next_round)

    response = await chat(
        messages=history + [{"role": "user", "content": instruction}],
        system_prompt=system_prompt,
        temperature=0.7,
    )

    # Redis 去重：重复时重试一次
    q_hash = _hash_text(response)
    if await is_question_asked(interview.id, q_hash):
        retry_instruction = (
            "这道题之前已经问过了，请换一道考察完全不同知识点的全新题目。"
            "格式不变：先用 1 句话点评候选人本题回答，再给出新题。"
        )
        response = await chat(
            messages=history + [{"role": "user", "content": retry_instruction}],
            system_prompt=system_prompt,
            temperature=0.9,
        )
        q_hash = _hash_text(response)

    await add_asked_question(interview.id, q_hash)
    _save_msg(db, interview, role="interviewer", content=response, round_num=next_round)
    await db.flush()
    return response


# ================================================================
# 结束面试 & 生成评估（评分核心修复区）
# ================================================================

async def finish_interview(db: AsyncSession, interview: Interview) -> str:
    """
    结束面试，生成结构化评估 + PDF 报告。

    评分修复要点：
    1. 先调用 _build_qa_summary() 把每一轮的"题目+候选人回答"提取出来，
       格式化成清单，作为大模型评分的显式依据
    2. 评估 prompt 要求大模型按题逐一分析，不允许跳过对话记录
    3. eval_schema score 字段用整数 0 占位，prompt 强调必须是整数
    4. _normalize_evaluation() 做全面类型安全转换兜底
    """
    all_messages = await _get_messages(db, interview)

    # ---- 核心修复：提取每轮 Q&A 作为显式打分依据 ----
    qa_summary = _build_qa_summary(all_messages)

    system_prompt = (
        f"你是一位经验丰富的【{interview.skill_name}】技术面试官，"
        f"刚刚完成了一场{_diff_label(interview.difficulty)}难度的模拟面试。\n"
        "你的任务是根据候选人在每道题上的实际回答内容，给出客观、准确的评估。\n\n"
        "评分标准：\n"
        "- 回答正确、完整、有深度：该题贡献高分\n"
        "- 回答部分正确或不够完整：该题贡献中等分\n"
        "- 回答错误、不知道、没有实质内容：该题贡献低分或零分\n"
        "- 评分必须严格基于候选人的实际回答，不能凭空给分"
    )

    # 构建评估请求，把 Q&A 摘要直接放进 prompt
    evaluation_request = (
        f"以下是本次面试的完整问答记录（共 {interview.current_round} 轮）：\n\n"
        f"{qa_summary}\n\n"
        "请根据以上每道题的候选人回答，进行综合评估。\n"
        "评估维度说明：\n"
        "- technical_depth（技术深度，0-25）：技术知识是否扎实、有深度\n"
        "- problem_solving（问题解决，0-25）：分析和解决问题的能力\n"
        "- communication（沟通表达，0-25）：回答是否清晰、有条理\n"
        "- project_experience（项目经验，0-25）：是否有结合实际经验\n\n"
        "重要约束：\n"
        "1. score 字段必须是整数，不能是字符串，不能带'分'字\n"
        "2. total_score = 四个维度 score 之和，范围 0-100\n"
        "3. 如果候选人多数回答'不知道'或回答错误，total_score 应在 0-40 之间\n"
        "4. 如果候选人回答基本正确，total_score 应在 60-80 之间\n"
        "5. 如果候选人回答优秀，total_score 应在 80-100 之间\n"
        "6. 评分必须与实际回答质量一致，不能给出与回答质量明显不符的分数"
    )

    eval_schema = {
        "dimension_scores": {
            "technical_depth": {"score": 0, "comment": "评价（1-2句）"},
            "problem_solving": {"score": 0, "comment": "评价（1-2句）"},
            "communication": {"score": 0, "comment": "评价（1-2句）"},
            "project_experience": {"score": 0, "comment": "评价（1-2句）"}
        },
        "total_score": 0,
        "strengths": ["优点1"],
        "weaknesses": ["不足1"],
        "improvement_suggestions": ["建议1"],
        "summary": "总体评价（2-3句）"
    }

    # 注意：这里不用 _get_history()，直接传包含 Q&A 摘要的独立请求
    # 避免对话历史角色混乱影响评估结果
    evaluation = await chat_structured(
        messages=[{"role": "user", "content": evaluation_request}],
        output_schema=eval_schema,
        temperature=0.2,   # 低温度，让评分更稳定、更贴近实际
        system_prompt=system_prompt,
    )

    # 类型安全标准化
    evaluation = _normalize_evaluation(evaluation)

    # 写入数据库
    interview.evaluation = evaluation
    interview.total_score = float(evaluation["total_score"])
    interview.status = "completed"
    interview.ended_at = datetime.now()

    # 生成 PDF 报告（失败不影响主流程）
    try:
        messages_data = [
            {"role": m.role, "content": m.content, "round": m.round}
            for m in all_messages
        ]
        pdf_bytes = generate_interview_evaluation_pdf(
            evaluation,
            interview.skill_name,
            interview.difficulty,
            interview.total_score,
            "",
            messages_data,
        )
        interview.report_url = upload_file(
            pdf_bytes,
            f"interview_report_{interview.id}.pdf",
            folder="reports",
            content_type="application/pdf",
        )
    except Exception:
        pass

    conclusion = _format_conclusion(evaluation)
    _save_msg(
        db, interview,
        role="interviewer",
        content=conclusion,
        round_num=interview.current_round,
    )
    await db.flush()
    return conclusion


def _build_qa_summary(messages: list[InterviewMessage]) -> str:
    """
    从消息列表中提取每一轮的"面试官提问 + 候选人回答"，
    格式化成清单文本，作为评分的显式依据。

    这是修复评分失真的核心函数：
    把对话历史从"一串消息"转化为"明确的题目-回答对"，
    让大模型在评估时有清晰的锚点，而不是从混乱的角色对话中猜测。

    输出格式示例：
        【第 1 题】
        面试官：请解释一下 HashMap 和 ConcurrentHashMap 的区别？
        候选人：HashMap 是线程不安全的，ConcurrentHashMap 通过分段锁...

        【第 2 题】
        面试官：请问什么是 JVM 的 GC Root？
        候选人：不知道，没了解过这个。
    """
    # 按轮次分组消息
    rounds: dict[int, dict[str, str]] = {}
    for msg in messages:
        r = msg.round
        if r not in rounds:
            rounds[r] = {}
        if msg.role == "interviewer":
            # 面试官消息可能包含点评+新题，只保留面试官内容
            rounds[r]["question"] = msg.content
        elif msg.role == "candidate":
            rounds[r]["answer"] = msg.content

    if not rounds:
        return "（本次面试没有问答记录）"

    lines = []
    for round_num in sorted(rounds.keys()):
        rd = rounds[round_num]
        question = rd.get("question", "（无题目记录）")
        answer = rd.get("answer", "（候选人未作答）")

        # 截断过长内容，防止 prompt 超长
        if len(question) > 300:
            question = question[:300] + "..."
        if len(answer) > 500:
            answer = answer[:500] + "..."

        lines.append(f"【第 {round_num} 题】")
        lines.append(f"面试官：{question}")
        lines.append(f"候选人：{answer}")
        lines.append("")  # 空行分隔

    return "\n".join(lines)


def _normalize_evaluation(evaluation: dict) -> dict:
    """
    标准化评估结果，防御 AI 输出以下异常：
    - score 是字符串（"20"、"20分"、"约20分"）
    - score 超出合法范围
    - 某个维度字段缺失
    - total_score 与各维度加总明显不一致

    total_score 策略：
        以维度加总为基准；若 AI 给的值与加总差距 ≤10，用 AI 值；
        差距 >10 说明 AI 算错了，以加总为准。
    """
    dim_scores = evaluation.get("dimension_scores", {})
    if not isinstance(dim_scores, dict):
        dim_scores = {}

    dim_total = 0
    for dim_key in ["technical_depth", "problem_solving", "communication", "project_experience"]:
        dim_val = dim_scores.get(dim_key)
        if not isinstance(dim_val, dict):
            dim_val = {"score": 0, "comment": ""}

        score = _safe_int(dim_val.get("score", 0), min_val=0, max_val=25)
        dim_val["score"] = score
        dim_total += score
        dim_scores[dim_key] = dim_val

    ai_total = _safe_int(
        evaluation.get("total_score", dim_total),
        min_val=0,
        max_val=100,
    )
    final_total = ai_total if abs(ai_total - dim_total) <= 10 else min(dim_total, 100)

    evaluation["dimension_scores"] = dim_scores
    evaluation["total_score"] = final_total

    for list_key in ["strengths", "weaknesses", "improvement_suggestions"]:
        if not isinstance(evaluation.get(list_key), list):
            evaluation[list_key] = []

    if not isinstance(evaluation.get("summary"), str):
        evaluation["summary"] = ""

    return evaluation


def _safe_int(value, min_val: int = 0, max_val: int = 100) -> int:
    """安全转换为整数，clip 到合法范围，失败返回 min_val"""
    try:
        cleaned = str(value).replace("分", "").replace("约", "").replace("~", "").strip()
        v = int(float(cleaned))
        return max(min_val, min(max_val, v))
    except (ValueError, TypeError, AttributeError):
        return min_val


# ================================================================
# 出题决策
# ================================================================

def _decide_action(completed_rounds: int) -> str:
    """
    根据已完成轮数在 Python 层决定下一步动作，不依赖 AI 自行理解。

    节奏：新题 → 新题 → 追问 → 新题 → 新题 → 追问 → ...
        completed_rounds % 3 == 2  →  追问（第 3、6、9... 轮后）
        其他                        →  出新题

    效果：追问比例约 1/3，不会连续追问，面试节奏均衡。
    """
    if completed_rounds > 0 and completed_rounds % 3 == 2:
        return "follow_up"
    return "new_question"


def _build_follow_up_prompt(interview: Interview, this_round: int) -> str:
    """追问 prompt：意图精确，不依赖 AI 自行理解"追问"二字"""
    return (
        f"候选人刚完成第 {this_round} 题的回答"
        f"（进度：{interview.current_round}/{interview.max_rounds} 轮）。\n\n"
        "请按格式回复：\n"
        "【点评】1 句话简短点评回答（不能给出答案或提示）\n"
        "【追问】针对回答中某个细节或薄弱点，提出一个更深入的追问\n\n"
        "要求：只追问一个问题，保持专业简洁。"
    )


def _build_next_question_prompt(
    interview: Interview, this_round: int, next_round: int
) -> str:
    """出新题 prompt：意图精确，不依赖 AI 自行理解"出新题"二字"""
    return (
        f"候选人刚完成第 {this_round} 题的回答"
        f"（进度：{interview.current_round}/{interview.max_rounds} 轮）。\n\n"
        "请按格式回复：\n"
        f"【点评】1 句话简短点评本题回答（不能给出答案或提示）\n"
        f"【第 {next_round} 题】给出一道全新的【{interview.skill_name}】面试题\n\n"
        "要求：\n"
        "- 新题必须考察与之前题目不同的知识点\n"
        "- 只问一道题，不做多余解释\n"
        "- 难度循序渐进"
    )


# ================================================================
# 通用辅助
# ================================================================

def _build_system_prompt(interview: Interview) -> str:
    """构建面试系统提示词"""
    skill = SKILL_REGISTRY.get(interview.skill_id, {})
    return (
        f"你是一位经验丰富的【{interview.skill_name}】技术面试官，"
        f"正在进行{_diff_label(interview.difficulty)}难度的模拟面试。\n"
        f"考察要求：{skill.get('description', '全面考察候选人的技术能力')}\n\n"
        "行为准则：\n"
        "1. 每次只提出一道题目或一个追问\n"
        "2. 绝对不主动给出答案或解题提示\n"
        "3. 追问时先简评（不超过 2 句），再提问\n"
        "4. 保持专业、客观、友好的面试官语气\n"
        "5. 题目难度循序渐进，由浅入深"
    )


def _diff_label(difficulty: str) -> str:
    return {"easy": "初级", "medium": "中级", "hard": "高级"}.get(difficulty, difficulty)


def _hash_text(text: str) -> str:
    """
    计算题目去重哈希。
    只取末尾 200 字符（跳过点评前缀，聚焦题目本身），
    避免点评不同但题目相同被误判为不重复。
    """
    core = text.strip()[-200:] if len(text) > 200 else text.strip()
    return hashlib.sha256(core.encode("utf-8")).hexdigest()[:16]


def _save_msg(
    db: AsyncSession,
    interview: Interview,
    role: str,
    content: str,
    round_num: int,
    message_type: str = "text",
) -> InterviewMessage:
    """保存一条面试消息（不 flush，由调用方决定时机）"""
    msg = InterviewMessage(
        interview_id=interview.id,
        role=role,
        content=content,
        message_type=message_type,
        round=round_num,
    )
    db.add(msg)
    return msg


def _format_conclusion(evaluation: dict) -> str:
    """格式化面试结束总结（Markdown，前端直接渲染）"""
    dim_labels = {
        "technical_depth": "技术深度",
        "problem_solving": "问题解决",
        "communication": "沟通表达",
        "project_experience": "项目经验",
    }
    total = evaluation.get("total_score", 0)
    dim_scores = evaluation.get("dimension_scores", {})

    lines = [
        "## 面试结束！以下是您的评估报告\n",
        f"**综合得分：{total} / 100**\n",
        "### 各维度得分",
    ]

    for dim_key, label in dim_labels.items():
        info = dim_scores.get(dim_key, {})
        if isinstance(info, dict):
            score = info.get("score", "N/A")
            comment = info.get("comment", "")
        else:
            score, comment = "N/A", ""
        lines.append(f"- **{label}**：{score}/25　{comment}")

    strengths = evaluation.get("strengths", [])
    if strengths:
        lines.append("\n### 优势")
        for s in strengths:
            lines.append(f"- {s}")

    weaknesses = evaluation.get("weaknesses", [])
    if weaknesses:
        lines.append("\n### 有待加强")
        for w in weaknesses:
            lines.append(f"- {w}")

    suggestions = evaluation.get("improvement_suggestions", [])
    if suggestions:
        lines.append("\n### 改进建议")
        for sg in suggestions:
            lines.append(f"- {sg}")

    summary = evaluation.get("summary", "")
    if summary:
        lines.append(f"\n### 总体评价\n{summary}")

    lines.append("\n\n📄 评估报告 PDF 已生成，可在面试记录页面下载。")
    return "\n".join(lines)


# ================================================================
# 历史消息查询（角色映射修复）
# ================================================================

async def _get_history(db: AsyncSession, interview: Interview) -> list[dict]:
    """
    获取对话历史，格式化为大模型所需的消息列表。

    角色映射（原代码的隐藏 bug）：
        原代码把 "interviewer"/"candidate" 直接传给大模型，
        但大模型只认识 "assistant"/"user"，导致上下文完全乱掉。
        修复：interviewer → assistant，candidate → user。
    """
    role_map = {"interviewer": "assistant", "candidate": "user"}
    msgs = await _get_messages(db, interview)
    return [
        {"role": role_map.get(m.role, "user"), "content": m.content}
        for m in msgs
    ]


async def _get_messages(db: AsyncSession, interview: Interview) -> list[InterviewMessage]:
    """获取面试所有消息，按创建时间正序"""
    result = await db.execute(
        select(InterviewMessage)
        .where(InterviewMessage.interview_id == interview.id)
        .order_by(InterviewMessage.created_at)
    )
    return list(result.scalars().all())


# ================================================================
# 公共查询接口
# ================================================================

async def get_user_interviews(
    db: AsyncSession,
    user_id: int,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Interview], int]:
    """获取用户的面试列表（分页，可按状态筛选）"""
    conditions = [Interview.user_id == user_id]
    if status:
        conditions.append(Interview.status == status)

    total = (await db.execute(
        select(func.count()).select_from(Interview).where(and_(*conditions))
    )).scalar() or 0

    result = await db.execute(
        select(Interview)
        .where(and_(*conditions))
        .order_by(Interview.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def get_interview_detail(
    db: AsyncSession,
    interview_id: int,
    user_id: int,
) -> Interview | None:
    """获取面试详情（含所有消息，同时验证所有权）"""        
    result = await db.execute(
        select(Interview).where(
            Interview.id == interview_id,
            Interview.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def delete_interview(
    db: AsyncSession,
    interview_id: int,
    user_id: int,
) -> bool:
    """删除面试记录（包括关联的消息）"""
    from sqlalchemy import delete
    
    # 直接删除面试记录（数据库外键约束会自动删除关联的消息）
    result = await db.execute(
        delete(Interview).where(
            Interview.id == interview_id,
            Interview.user_id == user_id
        )
    )
    await db.commit()
    
    return result.rowcount > 0