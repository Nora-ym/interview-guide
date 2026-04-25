"""
初始数据库迁移：创建所有表
这是项目的第一个迁移版本，从零开始建表

执行命令：alembic upgrade head
回滚命令：alembic downgrade base
"""

revision = '001'           # 这个迁移版本的 ID
down_revision = None       # 上一个版本（第一个版本没有上游）
branch_labels = None
depends_on = None

# 需要用到的 SQLAlchemy 组件
from alembic import op          # Alembic 操作器（create_table, add_column 等）
import sqlalchemy as sa         # SQLAlchemy 核心库


def upgrade() -> None:
    """
    升级：创建所有表
    按照外键依赖顺序创建（被引用的表先创建）
    """

    # ============================================================
    # 1. 用户表（被所有表引用，必须第一个创建）
    # ============================================================
    op.create_table(
        'users',  # 表名
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),  # 主键，自增
        sa.Column('username', sa.String(64), unique=True, nullable=False, index=True),  # 用户名，唯一+索引
        sa.Column('email', sa.String(256), unique=True, nullable=False, index=True),    # 邮箱，唯一+索引
        sa.Column('hashed_password', sa.String(256), nullable=False),  # 加密后的密码
        sa.Column('avatar_url', sa.String(512), nullable=True),       # 头像 URL
        sa.Column('is_active', sa.Boolean(), server_default='1'),     # 是否激活，默认 true
        sa.Column('is_admin', sa.Boolean(), server_default='0'),      # 是否管理员，默认 false
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),  # 创建时间
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),  # 更新时间
        mysql_charset='utf8mb4',       # MySQL 字符集
        mysql_collate='utf8mb4_unicode_ci',  # MySQL 排序规则
    )

    # ============================================================
    # 2. 简历表（依赖 users 表）
    # ============================================================
    op.create_table(
        'resumes',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        # ↑ 外键：关联 users.id，CASCADE 表示用户删了简历也删
        sa.Column('title', sa.String(256), nullable=False),            # 简历标题
        sa.Column('file_url', sa.String(512), nullable=False),         # 文件存储路径
        sa.Column('file_type', sa.String(32), nullable=False),         # 文件类型：pdf/docx/txt
        sa.Column('file_size', sa.BigInteger(), nullable=False),       # 文件大小（字节）
        sa.Column('content_hash', sa.String(64), nullable=True),       # 文件内容哈希（用于去重）
        sa.Column('parsed_text', sa.Text(), nullable=True),            # 解析后的纯文本内容
        sa.Column('analysis_status', sa.String(32), server_default='pending', nullable=False),
        # ↑ 分析状态：pending=待分析, analyzing=分析中, completed=完成, failed=失败
        sa.Column('analysis_result', sa.JSON(), nullable=True),        # AI 分析结果（JSON 格式）
        sa.Column('report_url', sa.String(512), nullable=True),        # PDF 报告文件路径
        sa.Column('task_id', sa.String(128), nullable=True),           # Celery 异步任务 ID（用于查进度）
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        mysql_charset='utf8mb4', mysql_collate='utf8mb4_unicode_ci',
    )
    # 创建索引加速查询
    op.create_index('idx_resumes_user_id', 'resumes', ['user_id'])       # 按用户查简历
    op.create_index('idx_resumes_content_hash', 'resumes', ['content_hash'])  # 去重查询

    # ============================================================
    # 3. 面试会话表
    # ============================================================
    op.create_table(
        'interviews',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('skill_id', sa.String(64), nullable=False),       # 技能方向标识（如 java_backend）
        sa.Column('skill_name', sa.String(128), nullable=False),    # 技能方向显示名（如 "Java 后端"）
        sa.Column('difficulty', sa.String(16), server_default='medium'),  # 难度：easy/medium/hard
        sa.Column('interview_type', sa.String(16), server_default='text'),  # 类型：text=文字, voice=语音
        sa.Column('status', sa.String(32), server_default='in_progress'),  # 状态：in_progress/completed/cancelled
        sa.Column('current_round', sa.Integer(), server_default='0'),  # 当前轮次
        sa.Column('max_rounds', sa.Integer(), server_default='10'),    # 最大轮次
        sa.Column('total_score', sa.Float(), nullable=True),          # 总分（面试结束后填）
        sa.Column('evaluation', sa.JSON(), nullable=True),            # 评估结果（JSON）
        sa.Column('report_url', sa.String(512), nullable=True),       # PDF 报告路径
        sa.Column('started_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('ended_at', sa.DateTime(), nullable=True),          # 结束时间
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        mysql_charset='utf8mb4', mysql_collate='utf8mb4_unicode_ci',
    )
    op.create_index('idx_interviews_user_id', 'interviews', ['user_id'])
    op.create_index('idx_interviews_status', 'interviews', ['status'])

    # ============================================================
    # 4. 面试消息表（每轮对话中的一条消息）
    # ============================================================
    op.create_table(
        'interview_messages',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('interview_id', sa.Integer(), sa.ForeignKey('interviews.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(16), nullable=False),             # 角色：interviewer=面试官, candidate=候选人
        sa.Column('content', sa.Text(), nullable=False),              # 消息内容
        sa.Column('message_type', sa.String(16), server_default='text'),  # 类型：text=文字, audio=语音
        sa.Column('round', sa.Integer(), server_default='1'),         # 第几轮
        sa.Column('metadata', sa.JSON(), nullable=True),              # 额外信息（如语音消息的时长等）
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        mysql_charset='utf8mb4', mysql_collate='utf8mb4_unicode_ci',
    )
    op.create_index('idx_messages_interview_id', 'interview_messages', ['interview_id'])

    # ============================================================
    # 5. 知识库表
    # ============================================================
    op.create_table(
        'knowledge_bases',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(256), nullable=False),            # 知识库名称
        sa.Column('description', sa.Text(), nullable=True),           # 描述
        sa.Column('doc_count', sa.Integer(), server_default='0'),     # 文档数量
        sa.Column('chunk_count', sa.Integer(), server_default='0'),   # 分块数量
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        mysql_charset='utf8mb4', mysql_collate='utf8mb4_unicode_ci',
    )

    # ============================================================
    # 6. 知识库文档表（每个上传的文件）
    # ============================================================
    op.create_table(
        'knowledge_documents',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('knowledge_base_id', sa.Integer(), sa.ForeignKey('knowledge_bases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(256), nullable=False),
        sa.Column('file_url', sa.String(512), nullable=False),
        sa.Column('file_type', sa.String(32), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=True),      # 去重用
        sa.Column('process_status', sa.String(32), server_default='pending'),  # 处理状态
        sa.Column('chunk_count', sa.Integer(), server_default='0'),   # 分块数
        sa.Column('error_message', sa.Text(), nullable=True),         # 错误信息
        sa.Column('task_id', sa.String(128), nullable=True),          # Celery 任务 ID
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        mysql_charset='utf8mb4', mysql_collate='utf8mb4_unicode_ci',
    )

    # ============================================================
    # 7. 文档分块表
    # 注意：这里没有 embedding（向量）列！
    # 向量数据存在 ChromaDB 中，通过 chunk_{id} 的方式关联
    # ============================================================
    op.create_table(
        'document_chunks',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('document_id', sa.Integer(), sa.ForeignKey('knowledge_documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('knowledge_base_id', sa.Integer(), sa.ForeignKey('knowledge_bases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),      # 第几个分块（从 0 开始）
        sa.Column('content', sa.Text(), nullable=False),             # 分块文本内容
        sa.Column('token_count', sa.Integer(), nullable=True),       # token 数量（粗略估算）
        # ⚠️ 向量不存这里，存在 ChromaDB，通过 id 关联
        sa.Column('metadata', sa.JSON(), nullable=True),             # 元数据（来源文档名等）
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        mysql_charset='utf8mb4', mysql_collate='utf8mb4_unicode_ci',
    )
    op.create_index('idx_chunks_doc_id', 'document_chunks', ['document_id'])
    op.create_index('idx_chunks_kb_id', 'document_chunks', ['knowledge_base_id'])

    # ============================================================
    # 8. 面试安排表
    # ============================================================
    op.create_table(
        'interview_schedules',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('company', sa.String(256), nullable=True),          # 公司名称
        sa.Column('position', sa.String(256), nullable=True),         # 岗位名称
        sa.Column('interview_type', sa.String(64), nullable=True),    # 面试类型（技术面/HR面/终面）
        sa.Column('interview_time', sa.DateTime(), nullable=False),   # 面试时间
        sa.Column('duration_minutes', sa.Integer(), server_default='60'),  # 面试时长（分钟）
        sa.Column('meeting_platform', sa.String(64), nullable=True),  # 会议平台（飞书/腾讯会议/Zoom）
        sa.Column('meeting_link', sa.String(512), nullable=True),     # 会议链接
        sa.Column('meeting_id', sa.String(128), nullable=True),       # 会议号
        sa.Column('status', sa.String(32), server_default='upcoming'),  # 状态：upcoming/completed/cancelled
        sa.Column('location', sa.String(256), nullable=True),         # 面试地点（线下）
        sa.Column('interviewer_name', sa.String(128), nullable=True), # 面试官姓名
        sa.Column('notes', sa.Text(), nullable=True),                # 备注
        sa.Column('raw_text', sa.Text(), nullable=True),             # 原始邀请文本（保留原文）
        sa.Column('reminder_sent', sa.Boolean(), server_default='0'),  # 是否已发送提醒
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        mysql_charset='utf8mb4', mysql_collate='utf8mb4_unicode_ci',
    )
    op.create_index('idx_schedules_user_id', 'interview_schedules', ['user_id'])
    op.create_index('idx_schedules_time', 'interview_schedules', ['interview_time'])  # 按时间查


def downgrade() -> None:
    """
    回滚：删除所有表
    必须按创建的逆序删除（先删被引用的表）
    """
    op.drop_table('interview_schedules')   # 8
    op.drop_table('document_chunks')       # 7
    op.drop_table('knowledge_documents')   # 6
    op.drop_table('knowledge_bases')       # 5
    op.drop_table('interview_messages')    # 4
    op.drop_table('interviews')           # 3
    op.drop_table('resumes')              # 2
    op.drop_table('users')                # 1（最后删，因为其他表引用它）
