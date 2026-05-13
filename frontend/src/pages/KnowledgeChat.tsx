/**
 * 知识库 RAG 聊天页
 *
 * 用户输入问题 → SSE 流式返回 AI 回答（打字机效果）
 * 同时显示引用的文档来源
 *
 * 交互流程：
 *   1. 用户输入问题，点击"提问"
 *   2. 调用 useSSE 的 start() 发起 SSE 请求
 *   3. 先显示引用来源（哪些文档段落被检索到）
 *   4. 然后逐字显示 AI 回答（打字机效果）
 *   5. 回答完成后显示"已完成"
 */
import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {useSSE} from '../hooks/useSSE'

export default function KnowledgeChat() {
  const { id } = useParams<{ id: string }>()
  const [question, setQuestion] = useState('')

  // 初始化 SSE Hook（URL 包含知识库 ID 和问题参数）
  const url = `/knowledgebases/${id}/chat?question=${encodeURIComponent(question)}`
  const { content, sources, done, error, start } = useSSE(url)

  // 提交问题
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!question.trim()) return
    start()
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* 返回按钮 */}
      <Link
        to="/knowledge"
        className="text-sm text-blue-600 hover:underline mb-4 inline-block"
      >
        ← 返回知识库列表
      </Link>
      <h1 className="text-xl font-bold mb-4">RAG 问答</h1>

      {/* 输入框 */}
      <form onSubmit={handleSubmit} className="flex gap-2 mb-6">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="输入你的问题..."
          className="flex-1 border rounded-xl px-4 py-3 text-sm"
        />
        <button
          type="submit"
          className="bg-blue-600 text-white rounded-xl px-6 py-3 text-sm font-medium hover:bg-blue-700"
        >
          提问
        </button>
      </form>

      {/* 引用的文档来源 */}
      {sources.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 mb-4">
          <h3 className="font-semibold text-sm mb-2">📄 引用来源</h3>
          {sources.map((s: any, i: number) => (
            <div key={i} className="text-xs text-gray-600 mb-1">
              <span className="font-medium">{s.source}</span>
              <span className="ml-2 text-gray-400">相似度: {s.score}</span>
              <p className="mt-1 text-gray-500">{s.content}...</p>
            </div>
          ))}
        </div>
      )}

      {/* AI 回答（打字机效果） */}
      {content && (
        <div className="bg-white border rounded-xl p-6 mb-4">
          <h3 className="font-semibold text-sm mb-2">🤖 AI 回答</h3>
          <div className="text-sm leading-relaxed whitespace-pre-wrap">
            {content}
            {!done && <span className="animate-pulse">|</span>}
          </div>
        </div>
      )}

      {/* 错误提示 */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-600 text-sm">
          {error}
        </div>
      )}

      {/* 完成提示 */}
      {done && content && (
        <p className="text-gray-400 text-sm text-center">回答已完成</p>
      )}
    </div>
  )
}