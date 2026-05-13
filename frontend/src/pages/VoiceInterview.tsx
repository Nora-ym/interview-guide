/**
 * 语音面试页
 *
 * 完整交互流程：
 *   1. 点击"开始面试" → 建立 WebSocket 连接 → 后端 AI 说开场白
 *   2. 点击"开始录音" → 调用浏览器麦克风 API 录音
 *   3. 点击"停止录音" → 停止录音
 *   4. 点击"发送回答" → 音频通过 WebSocket 发给后端 → ASR 识别 → AI 回复 → TTS 合成 → 音频推回 → 前端播放
 *   5. 重复 2-4 步
 *   6. 点击"结束面试" → 生成评估
 *
 * 技术要点：
 *   - navigator.mediaDevices.getUserMedia：浏览器录音 API
 *   - MediaRecorder：录音器，把音频流编码成文件
 *   - WebSocket：实时双向通信
 *   - Audio 对象：播放 TTS 返回的音频
 */
import { useState, useRef } from 'react'

export default function VoiceInterview() {
  const [started, setStarted] = useState(false)
  const [connected, setConnected] = useState(false)
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([])
  const [recording, setRecording] = useState(false)
  const [speaking, setSpeaking] = useState(false)
  const [interviewId, setInterviewId] = useState<number | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  // 创建面试 + 建立 WebSocket 连接
  const start = async () => {
    // 第一步：调用 API 创建面试
    const res = await fetch('/api/v1/interviews', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`,
      },
      body: JSON.stringify({
        skill_id: 'java_backend',
        difficulty: 'medium',
        interview_type: 'voice',
      }),
    })
    const data = await res.json()
    const id = data.data.id
    setInterviewId(id)

    // 第二步：建立 WebSocket 连接
    const token = localStorage.getItem('token')
    const ws = new WebSocket(
      `ws://localhost:8000/api/v1/voice-interviews/ws/${id}?token=${token}`
    )
    wsRef.current = ws

    ws.onopen = () => setConnected(true)

    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data)
      if (msg.type === 'ai_text') {
        // AI 的文字回复
        setMessages((prev) => [
          ...prev,
          { role: 'interviewer', content: msg.content },
        ])
      }
      if (msg.type === 'tts_audio') {
        // TTS 音频：解码 base64 → 创建 Blob → 播放
        setSpeaking(true)
        const audioBlob = new Blob(
          [Uint8Array.fromBase64(msg.audio)],
          { type: 'audio/mp3' }
        )
        const url = URL.createObjectURL(audioBlob)
        const audio = new Audio(url)
        audio.play()
        audio.onended = () => setSpeaking(false)
      }
      if (msg.type === 'tts_done') {
        setSpeaking(false)
      }
      if (msg.type === 'ended') {
        setMessages((prev) => [
          ...prev,
          { role: 'system', content: msg.conclusion || '面试已结束' },
        ])
      }
    }

    ws.onclose = () => setConnected(false)
  }

  // 开始录音
  const startRecording = async () => {
    try {
      // 请求麦克风权限
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      // 创建录音器
      mediaRecorderRef.current = new MediaRecorder(stream)
      chunksRef.current = []

      // 当有音频数据时，收集到 chunks 数组
      mediaRecorderRef.current.ondataavailable = (e) => {
        chunksRef.current.push(e.data)
      }
      mediaRecorderRef.current.start()
      setRecording(true)
    } catch (err) {
      alert('无法访问麦克风，请确保已授权')
    }
  }

  // 停止录音
  const stopRecording = () => {
    if (mediaRecorderRef.current && recording) {
      mediaRecorderRef.current.stop()
      setRecording(false)

      // 停止麦克风
      mediaRecorderRef.current.stream.getTracks().forEach((track) => track.stop())

      // 合并音频块
      const audioBlob = new Blob(chunksRef.current, { type: 'audio/wav' })

      if (wsRef.current?.readyState === WebSocket.OPEN) {
        // 把音频转成 base64 发给后端
        const reader = new FileReader()
        reader.onload = () => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(
              JSON.stringify({
                action: 'submit_answer',
                data: reader.result,
              })
            )
          }
        }
        reader.readAsDataURL(audioBlob)
      }
    }
  }

  // 结束面试
  const endInterview = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'end' }))
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">🎤 语音面试</h1>

      {/* 状态指示器 */}
      <div className="flex gap-4 mb-6">
        <span
          className={`inline-flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-full ${
            connected ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
          }`}
        >
          {connected ? '已连接' : '未连接'}
        </span>
        <span
          className={`text-sm px-3 py-1.5 rounded-full ${
            recording ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-500'
          }`}
        >
          {recording ? '🔴 录音中...' : '未录音'}
        </span>
        <span
          className={`text-sm px-3 py-1.5 rounded-full ${
            speaking ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-500'
          }`}
        >
          {speaking ? '🔊 播放中...' : '🔇 等待回答'}
        </span>
      </div>

      {/* 操作按钮区域 */}
      {!started ? (
        <button
          onClick={() => {
            setStarted(true)
            start()
          }}
          className="w-full bg-blue-600 text-white py-3 rounded-xl text-sm font-medium hover:bg-blue-700 mb-4"
        >
          开始面试
        </button>
      ) : (
        <div className="space-y-3">
          {!recording && !speaking && (
            <button
              onClick={startRecording}
              className="w-full bg-blue-600 text-white py-3 rounded-xl text-sm font-medium hover:bg-blue-700"
            >
              🎤 开始录音
            </button>
          )}
          {recording && (
            <button
              onClick={stopRecording}
              className="w-full bg-red-600 text-white py-3 rounded-xl text-sm font-medium hover:bg-red-700"
            >
              ⏹ 停止录音并发送
            </button>
          )}
          {speaking && (
            <div className="w-full bg-purple-50 text-purple-700 py-3 rounded-xl text-sm text-center">
              AI 正在回答中，请等待...
            </div>
          )}
          <button
            onClick={endInterview}
            className="w-full border border-gray-300 text-gray-600 py-3 rounded-xl text-sm hover:bg-gray-50"
          >
            结束面试
          </button>
        </div>
      )}

      {/* 对话记录 */}
      <div className="bg-white border rounded-xl p-4 overflow-y-auto mt-4" style={{ height: 400 }}>
        {messages.map((msg, i) => (
          <div key={i} className={`mb-3 ${msg.role === 'system' ? 'text-gray-400 italic' : ''}`}>
            <p className={`font-medium ${msg.role === 'interviewer' ? 'text-blue-600' : 'text-gray-700'}`}>
              {msg.role === 'interviewer' ? 'AI' : msg.role === 'system' ? '系统' : '你'}:
            </p>
            <p className="text-sm leading-relaxed">{msg.content}</p>
          </div>
        ))}
      </div>
    </div>
  )
}