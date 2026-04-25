"""
====================================================
总路由注册
====================================================
把所有子路由模块（auth、resume、interview 等）统一注册到 api_router。
所有接口的前缀是 /api/v1，例如：
    /api/v1/auth/login
    /api/v1/resumes/upload
    /api/v1/interviews
"""

from fastapi import APIRouter
from backend.api import auth, resume, interview, voice_interview, knowledgebase, schedule

# 创建总路由，所有子路由都挂在这个下面
api_router = APIRouter(prefix="/api/v1")

# 注册各模块路由
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(resume.router, prefix="/resumes", tags=["简历管理"])
api_router.include_router(interview.router, prefix="/interviews", tags=["模拟面试"])
api_router.include_router(voice_interview.router, prefix="/voice-interviews", tags=["语音面试"])
api_router.include_router(knowledgebase.router, prefix="/knowledgebases", tags=["知识库"])
api_router.include_router(schedule.router, prefix="/schedules", tags=["面试安排"])
