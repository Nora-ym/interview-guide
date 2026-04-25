"""
语音服务
封装语音识别（ASR）和语音合成（TTS）的调用。

ASR = 语音转文字（用户说话 → 文字）
TTS = 文字转语音（AI 回复 → 音频播放给用户）

使用阿里云 DashScope 的语音模型。
"""

import time
import dashscope
from dashscope.audio.asr import Recognition, RecognitionCallback
from dashscope.audio.tts import SpeechSynthesizer

from backend.config import get_settings

settings = get_settings()
dashscope.api_key = settings.dashscope_api_key


async def speech_to_text_sync(
    audio_data: bytes, format: str = "wav", sample_rate: int = 16000,
) -> str:
    """
    语音转文字
    参数：audio_data = 音频二进制数据（WAV 格式）
    返回：识别出的文字
    """
    result_text = ""

    class SyncCB(RecognitionCallback):
        def on_open(self):
            pass

        def on_close(self):
            pass

        def on_error(self, result):
            pass

        def on_event(self, result):
            nonlocal result_text
            sentence = result.get_sentence()
            if sentence and sentence.get("is_final", False):
                result_text = sentence.get("text", result_text)

    recognition = Recognition(
        model=settings.dashscope_asr_model,
        format=format, sample_rate=sample_rate, callback=SyncCB(),
    )
    recognition.send_audio(audio_data)
    time.sleep(0.5)
    return result_text


def text_to_speech_sync(text: str, voice: str | None = None) -> bytes:
    """
    文字转语音
    参数：text = 要转换的文字
    返回：音频二进制数据
    """
    voice = voice or settings.dashscope_tts_voice
    audio_data = bytearray()

    class CollectCB(object):
        def on_event(self, result):
            if hasattr(result, 'audio_frame') and result.audio_frame:
                audio_data.extend(result.audio_frame)

        def on_open(self):
            pass

        def on_close(self):
            pass

        def on_error(self, result):
            pass

    synthesizer = SpeechSynthesizer(
        model=settings.dashscope_tts_model, voice=voice, callback=CollectCB(),
    )
    synthesizer.call(text)
    return bytes(audio_data)