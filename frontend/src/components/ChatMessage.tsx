/**
 * 聊天消息气泡组件
 *
 * 根据消息角色决定气泡的位置和样式：
 *   面试官：左对齐、白色背景、灰色边框
 *   候选人：右对齐、蓝色背景、白色文字
 *
 * 样式说明：
 *   max-w-[75%]：最大宽度 75%（防止消息太宽）
 *   rounded-2xl：大圆角（像微信/钉钉的气泡）
 *   whitespace-pre-wrap：保留换行符和空格（AI 回复中可能有换行）
 */
import type { InterviewMessage } from '../types'

export default function ChatMessage({ msg }: { msg: InterviewMessage }) {
  const isAI = msg.role === 'interviewer'

  return (
    <div className={`flex ${isAI ? 'justify-start' : 'justify-end'} mb-4`}>
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isAI
            ? 'bg-white border shadow-sm'
            : 'bg-blue-600 text-white'
        }`}
      >
        {/* 轮次和角色标签 */}
        <p className="text-xs font-medium mb-1 opacity-60">
          Round {msg.round} · {isAI ? '面试官' : '你'}
        </p>
        {/* 消息正文 */}
        <div className="whitespace-pre-wrap">{msg.content}</div>
      </div>
    </div>
  )
}