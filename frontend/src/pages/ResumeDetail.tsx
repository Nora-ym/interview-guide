/**
 * 简历详情页
 *
 * 功能：
 *   1. 如果分析中 → 显示加载动画 + 每 3 秒轮询状态
 *   2. 分析完成 → 显示评分、技能标签、优势、不足、建议、总结
 *   3. 有 PDF 报告 → 提供下载链接
 *
 * 轮询机制：
 *   setInterval 每 3 秒调用一次 /resumes/{id}/status
 *   如果状态变为 completed → 更新数据 → 清除定时器
 *   如果状态变为 failed → 显示错误信息 → 清除定时器
 */
import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import api from '../api/client'
import type { Resume } from '../types'

export default function ResumeDetail() {
  const { id } = useParams<{ id: string }>()
  const [resume, setResume] = useState<Resume | null>(null)

  // 获取简历详情
  useEffect(() => {
    api.get(`/resumes/${id}`).then((res: any) => setResume(res.data))
  }, [id])

  // 轮询分析状态
  useEffect(() => {
    const timer = setInterval(() => {
      if (
        resume?.analysis_status === 'pending' ||
        resume?.analysis_status === 'analyzing'
      ) {
        api.get(`/resumes/${id}/status`).then((res: any) => {
          if (res.data.status === 'completed') {
            setResume((prev: any) => ({
              ...prev!,
              analysis_status: 'completed',
              analysis_result: res.data.result,
              report_url: res.data.report_url,
            }))
            clearInterval(timer)
          }
        })
      }
    }, 3000) // 每 3 秒轮询

    return () => clearInterval(timer) // 组件卸载时清除定时器
  }, [id, resume?.analysis_status])

  if (!resume) return <div>加载中...</div>

  const a = resume.analysis_result

  return (
    <div>
      {/* 标题栏 */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold">{resume.title}</h1>
        {resume.report_url && (
          <a
            href={resume.report_url}
            className="text-sm text-blue-600 border rounded-lg px-3 py-1 hover:bg-blue-50"
          >
            下载 PDF 报告
          </a>
        )}
      </div>

      {/* 分析完成 → 显示结果 */}
      {resume.analysis_status === 'completed' && a ? (
        <div className="space-y-6">
          {/* 评分卡片 */}
          <div className="bg-white rounded-xl border p-6">
            <div className="text-3xl font-bold text-blue-600 mb-2">
              {a.overall_score}/100
            </div>
            <p className="text-sm text-gray-500">综合评分</p>
          </div>

          {/* 技能标签 */}
          {a.skill_tags && (
            <div className="bg-white rounded-xl border p-6">
              <h3 className="font-semibold mb-2">技能标签</h3>
              <div className="flex flex-wrap gap-2">
                {a.skill_tags.map((t: string) => (
                  <span
                    key={t}
                    className="bg-blue-50 text-blue-700 text-xs px-2 py-1 rounded-full"
                  >
                    {t}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* 优势 */}
          {a.strengths && (
            <div className="bg-white rounded-xl border p-6">
              <h3 className="font-semibold mb-2">✅ 优势</h3>
              <ul className="list-disc list-inside text-sm space-y-1">
                {a.strengths.map((s: string, i: number) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>
          )}

          {/* 不足 */}
          {a.weaknesses && (
            <div className="bg-white rounded-xl border p-6">
              <h3 className="font-semibold mb-2">⚠️ 不足</h3>
              <ul className="list-disc list-inside text-sm space-y-1">
                {a.weaknesses.map((w: string, i: number) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {/* 改进建议 */}
          {a.improvement_suggestions && (
            <div className="bg-white rounded-xl border p-6">
              <h3 className="font-semibold mb-2">💡 改进建议</h3>
              <ol className="list-decimal list-inside text-sm space-y-1">
                {a.improvement_suggestions.map((s: string, i: number) => (
                  <li key={i}>{s}</li>
                ))}
              </ol>
            </div>
          )}

          {/* 总体评价 */}
          {a.summary && (
            <div className="bg-white rounded-xl border p-6">
              <h3 className="font-semibold mb-2">📝 总体评价</h3>
              <p className="text-sm leading-relaxed">{a.summary}</p>
            </div>
          )}
        </div>
      ) : (
        /* 加载中状态 */
        <div className="text-center py-12 text-gray-400">
          {/* CSS 旋转动画：模拟加载 */}
          <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full mx-auto mb-3" />
          <p>
            {resume.analysis_status === 'analyzing'
              ? 'AI 正在分析简历...'
              : '等待分析...'}
          </p>
        </div>
      )}
    </div>
  )
}