/**
 * 面试列表页
 *
 * 功能：
 *   1. 上半部分：技能方向选择网格（点击即创建面试并跳转到对话页）
 *   2. 下半部分：历史面试列表
 *
 * 点击技能方向时的流程：
 *   POST /interviews → 后端创建面试 + AI 出题 → 返回面试详情
 *   → 直接跳转到对话页 /interviews/{id}
 */
import { useState, useEffect } from 'react'
import api from '../api/client'
import InterviewCard from '../components/InterviewCard'
import type { Interview } from '../types'

export default function InterviewList() {
  const [interviews, setInterviews] = useState<Interview[]>([])
  const [skills, setSkills] = useState<any[]>([])

  useEffect(() => {
    // 并行请求：面试列表 + 技能方向
    api.get('/interviews').then((res: any) => setInterviews(res.data.items))
    api.get('/interviews/skills').then((res: any) => setSkills(res.data))
  }, [])

  // 点击技能方向 → 创建面试 → 跳转
  const handleCreate = async (skillId: string, difficulty: string) => {
    const res = await api.post('/interviews', {
      skill_id: skillId,
      difficulty,
      interview_type: 'text',
    })
    window.location.href = `/interviews/${res.data.id}`
  }

  return (
    <div>
      <h1 className="text-xl font-bold mb-4">模拟面试</h1>

      {/* 技能方向选择网格 */}
      <div className="bg-white border rounded-xl p-6 mb-6">
        <h2 className="font-semibold mb-3">开始新面试</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {skills.map((s: any) => (
            <button
              key={s.id}
              onClick={() => handleCreate(s.id, 'medium')}
              className="border rounded-lg p-3 text-left hover:border-blue-400 hover:bg-blue-50 transition-colors"
            >
              <p className="font-medium text-sm">{s.name}</p>
              <p className="text-xs text-gray-400 mt-1 truncate">
                {s.description}
              </p>
            </button>
          ))}
        </div>
      </div>

      {/* 历史面试列表 */}
      <h2 className="font-semibold mb-3">历史面试</h2>
      <div className="space-y-3">
        {interviews.map((i: Interview) => (
          <InterviewCard key={i.id} interview={i} />
        ))}
        {interviews.length === 0 && (
          <p className="text-gray-400 text-center py-8">暂无面试记录</p>
        )}
      </div>
    </div>
  )
}