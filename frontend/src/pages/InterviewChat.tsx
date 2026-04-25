/**
 * 面试对话页
 *
 * 核心交互流程：
 *   1. 进入页面 → 加载历史消息
 *   2. 底部消息区域自动滚到底部（新消息出现时）
 *   3. 输入框 + 发送按钮
 *   4. 发送后禁用按钮 → AI 回来后恢复
 *   5. 面试结束 → 显示评分雷达图 + 下载报告按钮
 *
 * 自动滚动实现：
 *   用 useRef 获取消息列表底部的空 div 元素
 *   每次消息变化时调用 scrollIntoView 滚动到底部
 */
import { useState, useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import api from '../api/client'
import ChatMessage from '../components/ChatMessage'
import RadarChart from '../components/RadarChart'
import type { Interview } from '../types'

export default function InterviewChat() {
  const { id } = useParams<{ id: string }>()
  const [interview, setInterview] = useState<Interview | null>(null)
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)  // 滚动锚点

  // 加载面试详情
  useEffect(() => {
    api.get(`/interviews/${id}`).then((res: any) => setInterview(res.data))
  }, [id])

  // 新消息时自动滚到底部
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [interview?.messages])

  // 发送回答
  const handleSend = async () => {
    if (!input.trim() || sending) return
    const text = input
    setInput('')
    setSending(true)

    try {
      const res = await api.post(`/interviews/${id}/answer`, {
        content: text,
      })

      // 乐观更新：不重新请求，直接在本地追加消息
      setInterview((prev: any) => ({
        ...prev!,
        status: res.data.status,
        current_round: res.data.current_round,
        messages: [
          ...prev!.messages,
          // 追加用户的回答
          {
            id: Date.now(),
            role: 'candidate',
            content: text,
            message_type: 'text',
            round: prev!.current_round + 1,
            created_at: new Date().toISOString(),
          },
          // 追加 AI 的回复
          {
            id: Date.now() + 1,
            role: 'interviewer',
            content: res.data.response,
            message_type: 'text',
            round: res.data.current_round,
            created_at: new Date().toISOString(),
          },
        ],
        total_score: res.data.is_finished
          ? (prev?.total_score || 0)
          : prev?.total_score,
        evaluation: res.data.is_finished
          ? (prev?.evaluation || {})
          : prev?.evaluation,
      }))
    } finally {
      setSending(false)
    }
  }

  // 手动结束面试
  const handleEnd = async () => {
    const res = await api.post(`/interviews/${id}/end`)
    setInterview((prev: any) => ({
      ...prev!,
      status: 'completed',
      evaluation: res.data.evaluation,
      total_score: res.data.total_score,
    }))
  }

  if (!interview) return <div>加载中...</div>

  const isFinished = interview.status === 'completed'
  const dims = interview.evaluation?.dimension_scores
  // 把后端的维度得分转成雷达图需要的格式
  const radarData = dims
    ? Object.entries(dims).map(([k, v]: any) => ({
        dimension: k,
        score: v.score,
      }))
    : []

  return (
    <div className="flex flex-col h-full">
      {/* 标题栏 */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-lg font-bold">
            {interview.skill_name} · {interview.difficulty}
          </h1>
          <p className="text-sm text-gray-500">
            Round {interview.current_round}/{interview.max_rounds}
          </p>
        </div>
        <div className="flex gap-2">
          {!isFinished && (
            <button
              onClick={handleEnd}
              className="text-sm border rounded-lg px-3 py-1 text-red-600 hover:bg-red-50"
            >
              结束面试
            </button>
          )}
          {interview.report_url && (
            <a
              href={interview.report_url}
              className="text-sm bg-blue-600 text-white rounded-lg px-3 py-1"
            >
              下载报告
            </a>
          )}
        </div>
      </div>

      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto border rounded-xl bg-white p-4 mb-4">
        {interview.messages.map((msg) => (
          <ChatMessage key={msg.id} msg={msg} />
        ))}
        {/* 滚动锚点 */}
        <div ref={bottomRef} />
      </div>

      {/* 雷达图（面试结束后显示） */}
      {isFinished && radarData.length > 0 && (
        <div className="bg-white border rounded-xl p-4 mb-4">
          <h3 className="font-semibold mb-2">
            评估结果: {interview.total_score}/100
          </h3>
          <RadarChart data={radarData} />
        </div>
      )}

      {/* 输入框 + 发送按钮（面试结束后隐藏） */}
      {!isFinished && (
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              // Enter 发送，Shift+Enter 换行
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSend()
              }
            }}
            placeholder="输入你的回答..."
            className="flex-1 border rounded-xl px-4 py-3 text-sm"
            disabled={sending}
          />
          <button
            onClick={handleSend}
            disabled={sending || !input.trim()}
            className="bg-blue-600 text-white rounded-xl px-6 py-3 text-sm font-medium disabled:opacity-50 hover:bg-blue-700"
          >
            {sending ? '思考中...' : '发送'}
          </button>
        </div>
      )}
    </div>
  )
}