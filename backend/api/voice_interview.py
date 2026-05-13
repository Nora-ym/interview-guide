"""
====================================================
语音面试 WebSocket 接口
====================================================
WebSocket 是全双工通信协议，适合实时交互场景。

语音面试流程：
    前端 ──录音音频──→ WebSocket ──→ 后端 ASR 识别 ──→ 文字
                                                              ↓
    前端 ←──TTS音频── WebSocket ←── AI 回复文字 ←── 面试引擎

连接地址：ws://localhost:8000/api/v1/voice-interviews/ws/{interview_id}?token=xxx
（token 通过 query 参数传递，因为 WebSocket 没有 Header）
"""

import json
import base64
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.database import AsyncSessionLocal
from backend.models.interview import Interview, InterviewMessage
from backend.services import interview_service, voice_service

router = APIRouter()


@router.websocket("/ws/{interview_id}")
async def voice_interview_ws(websocket: WebSocket, interview_id: int):
    """
    语音面试 WebSocket 端点

    连接时在 query 参数中带 token：
        ws://host/ws/123?token=eyJhbGciOiJIUzI1NiJ9...

    前端发送的消息格式（JSON）：
        {"action": "start"}          - 开始面试
        {"action": "audio", "data": "base64音频"}  - 发送音频数据
        {"action": "submit_answer"}  - 提交回答（触发 ASR）
        {"action": "end"}            - 结束面试

    后端发送的消息格式：
        {"type": "ai_text", "content": "..."}     - AI 的文字回复
        {"type": "tts_audio", "audio": "base64"}  - TTS 生成的音频
        {"type": "tts_done"}                     - TTS 播放完毕
        {"type": "asr_result", "text": "..."}     - ASR 识别结果
        {"type": "ended"}                         - 面试结束
    """
    from backend.utils.security import decode_jwt

    # 1. 验证 Token
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="缺少 token")
        return
    payload = decode_jwt(token)
    if not payload:
        await websocket.close(code=4001, reason="无效 token")
        return
    user_id = int(payload.get("sub", 0))

    # 2. 接受连接
    await websocket.accept()
    db = AsyncSessionLocal()
    audio_buffer = bytearray()  # 收集音频数据的缓冲区

    try:
        # 3. 验证面试归属权
        interview = await db.get(Interview, interview_id)
        if not interview or interview.user_id != user_id:
            await websocket.send_json({"type": "error", "message": "面试不存在"})
            return

        # 4. 如果还没开始，AI 发开场白
        if interview.current_round == 0:
            opening = await interview_service.start_interview(db, interview)
            await db.refresh(interview)
            await _speak(websocket, opening)

        # 5. 消息循环
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=3600)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "paused"})
                continue

            msg = json.loads(data)
            action = msg.get("action", "")

            if action == "audio":
                # 收集音频片段（前端可能分多次发送）
                audio_buffer.extend(base64.b64decode(msg.get("data", "")))

            elif action == "submit_answer":
                # 用户提交回答 → ASR 识别 → 面试引擎处理
                if audio_buffer:
                    audio_bytes = bytes(audio_buffer)
                    audio_buffer.clear()
                    text = await voice_service.speech_to_text_sync(audio_bytes)
                    if text.strip():
                        await websocket.send_json({"type": "asr_result", "text": text})
                        # 保存用户消息
                        user_msg = InterviewMessage(
                            interview_id=interview.id, role="candidate",
                            content=text, message_type="audio",
                            round=interview.current_round + 1,
                        )
                        db.add(user_msg)
                        await db.flush()
                        # 调用面试引擎
                        try:
                            response = await interview_service.submit_answer(
                                db, interview, text)
                        except ValueError:
                            response = await interview_service.finish_interview(
                                db, interview)
                        await db.refresh(interview)
                        await _speak(websocket, response)

            elif action == "end":
                # 手动结束面试
                conclusion = await interview_service.finish_interview(db, interview)
                await _speak(websocket, conclusion)
                await websocket.send_json({"type": "ended"})
                break

    except WebSocketDisconnect:
        pass
    finally:
        await db.close()


async def _speak(websocket: WebSocket, text: str):
    """发送文字 + TTS 音频给前端"""
    # 先发文字（前端可以立即显示）
    await websocket.send_json({"type": "ai_text", "content": text})
    # 再发音频（前端播放）
    try:
        audio_bytes = voice_service.text_to_speech_sync(text)
        await websocket.send_json({
            "type": "tts_audio",
            "audio": base64.b64encode(audio_bytes).decode(),
        })
        await websocket.send_json({"type": "tts_done"})
    except Exception as e:
        await websocket.send_json({"type": "tts_error", "message": str(e)})
