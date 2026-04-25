/**
 * WebSocket Hook
 *
 * WebSocket 是什么？
 *   全双工通信协议，客户端和服务器可以随时互相发消息。
 *   HTTP 是"请求-响应"模式（客户端问，服务器答）。
 *   WebSocket 是"持久连接"模式（建连后双方随时发消息）。
 *
 * 这里用于语音面试：
 *   前端录音 → WebSocket 发音频 → 后端 ASR 识别 → AI 回答 → TTS 合成 → WebSocket 推回音频
 *
 * 注意：
 *   WebSocket 不支持自定义 Header，所以 Token 通过 query 参数传递：
 *   ws://host/ws/123?token=xxx
 */
import { useState, useRef, useCallback, useEffect } from 'react'

export function useWebSocket(url: string) {
  const [messages, setMessages] = useState<any[]>([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  // 建立 WebSocket 连接
  const connect = useCallback(() => {
    const token = localStorage.getItem('token')
    const sep = url.includes('?') ? '&' : '?'
    const ws = new WebSocket(`${url}${sep}token=${token}`)

    ws.onopen = () => setConnected(true)
    ws.onclose = () => setConnected(false)
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        setMessages((prev) => [...prev, data])
      } catch {
        // 忽略解析失败的消息
      }
    }

    wsRef.current = ws
  }, [url])

  // 发送消息
  const send = useCallback((data: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  // 关闭连接
  const close = useCallback(() => {
    wsRef.current?.close()
  }, [])

  // 组件卸载时自动关闭连接（防止内存泄漏）
  useEffect(() => {
    return () => {
      wsRef.current?.close()
    }
  }, [])

  return { messages, connected, connect, send, close }
}
