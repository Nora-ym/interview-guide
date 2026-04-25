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
 */
import type { Interview } from '../types'
import { Link } from 'react-router-dom'

export default function InterviewCard({ interview }: { interview: Interview }) {
  // 状态映射：英文 → 中文
  const statusMap: Record<string, string> = {
    in_progress: '进行中',
    completed: '已完成',
    cancelled: '已取消',
  }

  return (
    <Link
      to={`/interviews/${interview.id}`}
      className="block border rounded-xl p-4 hover:shadow-md transition-shadow"
    >
      <div className="flex items-center justify-between mb-2">
        <span className="font-medium">{interview.skill_name}</span>
        <span
          className={`text-xs px-2 py-1 rounded-full ${
            interview.status === 'completed'
              ? 'bg-green-100 text-green-700'
              : 'bg-blue-100 text-blue-700'
          }`}
        >
          {statusMap[interview.status] || interview.status}
        </span>
      </div>
      <div className="flex gap-4 text-xs text-gray-500">
        <span>难度: {interview.difficulty}</span>
        <span>轮次: {interview.current_round}/{interview.max_rounds}</span>
        {interview.total_score != null && (
          <span className="font-bold text-blue-600">
            得分: {interview.total_score}
          </span>
        )}
      </div>
    </Link>
  )
}