/**
 * 面试卡片组件
 *
 * 用于面试列表页面，每一条面试记录显示为一个卡片。
 * 点击整个卡片跳转到面试详情/对话页面。
 *
 * 显示内容：
 *   - 技能方向名称
 *   - 状态标签（进行中=蓝色，已完成=绿色）
 *   - 难度、轮次、得分
 *   - 操作按钮：重新开始、删除
 */
import { useState } from 'react'
import type { Interview } from '../types'
import { Link } from 'react-router-dom'
import { RotateCcw, Trash2, ChevronRight } from 'lucide-react'
import api from '../api/client'

export default function InterviewCard({ interview, onDelete }: { interview: Interview; onDelete: (id: string) => void }) {
  // 状态映射：英文 → 中文
  const statusMap: Record<string, string> = {
    in_progress: '进行中',
    completed: '已完成',
    cancelled: '已取消',
  }

  const [loading, setLoading] = useState<string | null>(null)

  // 重新开始面试
  const handleRestart = async () => {
    setLoading('restart')
    try {
      const res = await api.post('/interviews', {
        skill_id: interview.skill_id,
        difficulty: interview.difficulty,
        interview_type: 'text',
      })
      window.location.href = `/interviews/${res.data.id}`
    } catch (error: any) {
      console.error('重做失败:', error)
      alert(`重做失败: ${error.response?.data?.detail || error.message || '未知错误'}`)
      setLoading(null)
    }
  }

  // 删除面试
  const handleDelete = async () => {
    if (confirm(`确定要删除 "${interview.skill_name}" 的面试记录吗？`)) {
      setLoading('delete')
      try {
        await api.delete(`/interviews/${interview.id}`)
        onDelete(String(interview.id))
      } catch (error: any) {
        console.error('删除失败:', error)
        alert(`删除失败: ${error.response?.data?.detail || error.message || '未知错误'}`)
      } finally {
        setLoading(null)
      }
    }
  }

  const isCompleted = interview.status === 'completed'

  return (
    <div className="border rounded-xl p-4 hover:shadow-md transition-all bg-white border-gray-100">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <Link
              to={`/interviews/${interview.id}`}
              className="font-medium text-gray-700 hover:text-blue-500 transition-colors flex items-center gap-2"
            >
              {interview.skill_name}
              <ChevronRight className="w-4 h-4 text-gray-400" />
            </Link>
            <span
              className={`text-xs px-2 py-1 rounded-full ${
                interview.status === 'completed'
                  ? 'bg-green-100 text-green-600'
                  : interview.status === 'cancelled'
                  ? 'bg-gray-100 text-gray-600'
                  : 'bg-blue-100 text-blue-600'
              }`}
            >
              {statusMap[interview.status] || interview.status}
            </span>
          </div>
          <div className="flex gap-4 text-xs text-gray-400">
            <span>难度: {interview.difficulty}</span>
            <span>轮次: {interview.current_round}/{interview.max_rounds}</span>
            {interview.total_score != null && (
              <span className="font-semibold text-blue-500">
                得分: {interview.total_score}
              </span>
            )}
          </div>
        </div>

        {/* 操作按钮 */}
        <div className="flex gap-2 ml-4">
          {/* 重新开始按钮（仅已完成的面试显示） */}
          {isCompleted && (
            <button
              onClick={handleRestart}
              disabled={loading === 'restart'}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium 
                         bg-gradient-to-r from-blue-100 to-sky-100 text-blue-600 border border-blue-200
                         hover:from-blue-200 hover:to-sky-200 disabled:opacity-50 transition-all"
              title="重新做一次"
            >
              <RotateCcw className={`w-3.5 h-3.5 ${loading === 'restart' ? 'animate-spin' : ''}`} />
              重练
            </button>
          )}

          {/* 删除按钮 */}
          <button
            onClick={handleDelete}
            disabled={loading === 'delete'}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium 
                       bg-gradient-to-r from-rose-100 to-pink-100 text-rose-600 border border-rose-200
                       hover:from-rose-200 hover:to-pink-200 disabled:opacity-50 transition-all"
            title="删除记录"
          >
            <Trash2 className="w-3.5 h-3.5" />
            删除
          </button>
        </div>
      </div>
    </div>
  )
}
