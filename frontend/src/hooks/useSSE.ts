/**
 * SSE（Server-Sent Events）Hook
 *
 * SSE 是什么？
 *   服务器向客户端单向持续推送数据的协议。
 *   和 WebSocket 的区别：SSE 只能服务器→客户端，WebSocket 可以双向。
 *   SSE 更简单，适合"服务器推送、客户端只接收"的场景。
 *
 * 应用场景：
 *   知识库 RAG 问答的打字机效果。
 *   用户提问 → 服务器先找文档 → 然后 AI 一个字一个字地返回 → 前端逐字显示。
 *
 * 为什么不用 EventSource API？
 *   浏览器原生有 EventSource API，但它不支持自定义 Header。
 *   我们的接口需要传 Authorization Token，所以用 fetch + ReadableStream 手动解析。
 *
 * SSE 数据格式：
 *   每条消息以 "data: " 开头，以 "\n\n" 结尾。
 *   例：data: {"type": "token", "content": "你"}\n\n
 *       data: {"type": "token", "content": "好"}\n\n
 *       data: {"type": "done"}\n\n
 */
import { useState, useCallback } from 'react'

export function useSSE(url: string) {
  const [content, setContent] = useState('')       // 累积的文本内容
  const [sources, setSources] = useState<any[]>([]) // 引用的文档来源
  const [done, setDone] = useState(false)           // 是否结束
  const [error, setError] = useState('')            // 错误信息

  const start = useCallback(() => {
    // 重置状态
    setContent('')
    setSources([])
    setDone(false)
    setError('')

    const token = localStorage.getItem('token')
    const sep = url.includes('?') ? '&' : '?'

    // 用 fetch 发起请求（可以自定义 Header）
    fetch(`${url}${sep}_t=${Date.now()}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'text/event-stream',
      },
    }).then(async (res) => {
      // 获取响应体的读取流
      const reader = res.body?.getReader()
      const decoder = new TextDecoder()
      let buffer = ''  // 缓冲区（因为一次 read 可能只收到半个消息）

      while (reader) {
        const { done, value } = await reader.read()
        if (done) break

        // 把新的字节追加到缓冲区
        buffer += decoder.decode(value, { stream: true })

        // 按 \n 切分，处理完整的行
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''  // 最后一个可能不完整，留在缓冲区

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))  // 去掉 "data: " 前缀
              if (data.type === 'sources') {
                setSources(data.sources)
              } else if (data.type === 'token') {
                // 追加文本（不是替换！这样才能实现打字机效果）
                setContent((c) => c + data.content)
              } else if (data.type === 'done') {
                setDone(true)
              } else if (data.type === 'error') {
                setError(data.message)
              }
            } catch {
              // JSON 解析失败，忽略
            }
          }
        }
      }
      setDone(true)
    }).catch((e) => {
      setError(e.message)
    })
  }, [url])

  return { content, sources, done, error, start }
}
