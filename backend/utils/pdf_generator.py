"""
====================================================
PDF 报告生成器
====================================================
用 ReportLab 库生成 PDF 文档。

两种报告：
1. 简历分析报告（generate_resume_analysis_pdf）
   - 评分、优势、不足、建议、技能标签、总结
2. 面试评估报告（generate_interview_evaluation_pdf）
   - 维度得分表格、面试记录、总结

ReportLab 的基本概念：
    SimpleDocTemplate - PDF 文档模板（设置纸张大小、边距）
    Paragraph - 段落文本（支持简单样式）
    Table - 表格（支持行列合并、样式）
    Spacer - 空白间距
    HRFlowable - 水平分隔线
    story - 文档内容列表（按顺序排列的所有元素）
"""

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)

FONT = "Helvetica"  # 字体（中文需要换成实际中文字体路径，这里先用默认）


def _styles():
    """获取自定义排版样式"""
    s = getSampleStyleSheet()
    s.add_paragraphStyle(
        name="Title2",
        parent=s["Title"],
        fontSize=22,
        spaceAfter=20,
        fontName=FONT,
    )
    s.add_paragraphStyle(
        name="H22",
        parent=s["Heading2"],
        fontSize=14,
        spaceAfter=10,
        fontName=FONT,
    )
    s.add_paragraphStyle(
        name="Body2",
        parent=s["Normal"],
        fontSize=10,
        leading=16,  # 行高
        fontName=FONT,
    )
    return s


def generate_resume_analysis_pdf(
    analysis: dict, title: str, username: str,
) -> bytes:
    """
    生成简历分析 PDF 报告

    参数：
        analysis: AI 分析结果（来自 resume_service._call_ai_analysis）
        title: 简历标题
        username: 用户名

    返回：PDF 文件的二进制数据
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    st = _styles()

    # story 是一个列表，里面的元素会按顺序渲染到 PDF
    story = [
        Paragraph("Resume Analysis Report", st["Title2"]),
        Spacer(1, 10),
        Paragraph(
            f"Overall Score: {analysis.get('overall_score', 'N/A')}/100",
            st["H22"],
        ),
        Spacer(1, 10),
    ]

    # 遍历优势和不足
    for label, key in [("Strengths", "strengths"), ("Improvements", "weaknesses")]:
        items = analysis.get(key, [])
        if items:
            story.append(Paragraph(label, st["H22"]))
            for item in items:
                prefix = "+" if key == "strengths" else "-"
                story.append(Paragraph(f"  {prefix} {item}", st["Body2"]))
            story.append(Spacer(1, 10))

    # 技能标签
    tags = analysis.get("skill_tags", [])
    if tags:
        story.append(Paragraph("Skill Tags", st["H22"]))
        story.append(Paragraph(f"  {', '.join(tags)}", st["Body2"]))

    # 总体评价
    summary = analysis.get("summary", "")
    if summary:
        story += [
            HRFlowable(width="100%", thickness=1, color=colors.grey),
            Spacer(1, 10),
            Paragraph("Summary", st["H22"]),
            Paragraph(summary, st["Body2"]),
        ]

    doc.build(story)  # 把 story 渲染成 PDF，写入 buf
    buf.seek(0)
    return buf.getvalue()


def generate_interview_evaluation_pdf(
    evaluation: dict, skill_name: str, difficulty: str,
    total_score: float, username: str, messages: list[dict],
) -> bytes:
    """
    生成面试评估 PDF 报告

    参数：
        evaluation: 评估结果（来自 interview_service.finish_interview）
        skill_name: 技能方向名称
        difficulty: 难度
        total_score: 总分
        username: 用户名
        messages: 面试消息列表
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    st = _styles()
    story = [
        Paragraph("Interview Evaluation Report", st["Title2"]),
        Spacer(1, 10),
        Paragraph(f"Score: {total_score}/100", st["H22"]),
    ]

    # 维度得分表格
    dims = evaluation.get("dimension_scores", {})
    if dims:
        rows = [["Dimension", "Score"]]
        for dim_name, dim_info in dims.items():
            rows.append([dim_name, str(dim_info.get("score", 0))])
        t = Table(rows, colWidths=[8 * cm, 4 * cm])
        t.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), FONT),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story += [t, Spacer(1, 20)]

    # 总结
    summary = evaluation.get("summary", "")
    if summary:
        story.append(Paragraph(summary, st["Body2"]))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()
