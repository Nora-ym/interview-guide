/**
 * 面试安排管理页
 *
 * 功能：
 *   1. 顶部：日历视图（月视图展示所有面试安排）
 *   2. 中间：添加按钮（手动添加 / AI 解析文本添加）
 *   3. 下方：列表视图（查看所有安排的详细信息）
 *
 * 日历数据来源：
 *   GET /schedules/calendar?year=2025&month=1
 *   返回 react-big-calendar 需要的事件格式
 */
import { useState, useEffect } from 'react'
import api from '../api/client'
import ScheduleCalendar from '../components/ScheduleCalendar'
import type { Schedule } from '../types'

export default function SchedulePage() {
  const [schedules, setSchedules] = useState<Schedule[]>([])
  const [calendarEvents, setCalendarEvents] = useState<any[]>([])
  const [showAddForm, setShowAddForm] = useState(false)
  const [parseText, setParseText] = useState('')
  const [parsedResult, setParsedResult] = useState<any>(null)
  const [year, setYear] = useState(new Date().getFullYear())
  const [month, setMonth] = useState(new Date().getMonth() + 1)

  // 加载面试安排列表
  const fetchSchedules = async () => {
    const res = await api.get('/schedules')
    setSchedules(res.data.items)
  }

  // 加载日历数据
  const fetchCalendar = async () => {
    const res = await api.get(`/schedules/calendar?year=${year}&month=${month}`)
    setCalendarEvents(res.data)
  }

  useEffect(() => {
    fetchSchedules()
    fetchCalendar()
  }, [year, month])

  // AI 解析邀请文本
  const handleParse = async () => {
    if (!parseText.trim()) return
    const res = await api.post('/schedules/parse', { text: parseText })
    setParsedResult(res.data)
  }

  // 确认创建（用解析结果创建安排）
  const handleConfirmCreate = async () => {
    await api.post('/schedules/from-text', { text: parseText })
    setShowAddForm(false)
    setParseText('')
    setParsedResult(null)
    fetchSchedules()
    fetchCalendar()
  }

  // 状态显示映射
  const statusMap: Record<string, { label: string; color: string }> = {
    upcoming: { label: '待面试', color: 'bg-blue-100 text-blue-700' },
    completed: { label: '已完成', color: 'bg-green-100 text-green-700' },
    cancelled: { label: '已取消', color: 'bg-red-100 text-red-700' },
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-bold">📅 面试安排</h1>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="bg-blue-600 text-white rounded-lg px-4 py-2 text-sm hover:bg-blue-700"
        >
          + 添加安排
        </button>
      </div>

      {/* 添加安排面板 */}
      {showAddForm && (
        <div className="bg-white border rounded-xl p-6 mb-6">
          <h3 className="font-semibold mb-3">粘贴面试邀请文本，AI 自动解析</h3>
          <textarea
            value={parseText}
            onChange={(e) => setParseText(e.target.value)}
            placeholder="粘贴面试邀请邮件、短信等内容..."
            className="w-full border rounded-lg p-3 text-sm h-32 mb-3"
          />
          <div className="flex gap-2">
            <button
              onClick={handleParse}
              className="bg-blue-600 text-white rounded-lg px-4 py-2 text-sm hover:bg-blue-700"
            >
              AI 解析
            </button>
            {parsedResult && (
              <button
                onClick={handleConfirmCreate}
                className="bg-green-600 text-white rounded-lg px-4 py-2 text-sm hover:bg-green-700"
              >
                确认创建
              </button>
            )}
          </div>

          {/* 解析结果预览 */}
          {parsedResult && (
            <div className="mt-4 bg-gray-50 rounded-lg p-4">
              <h4 className="font-medium text-sm mb-2">解析结果：</h4>
              <div className="grid grid-cols-2 gap-2 text-sm">
                {parsedResult.company && (
                  <div><span className="text-gray-400">公司：</span>{parsedResult.company}</div>
                )}
                {parsedResult.position && (
                  <div><span className="text-gray-400">岗位：</span>{parsedResult.position}</div>
                )}
                {parsedResult.interview_time && (
                  <div><span className="text-gray-400">时间：</span>{parsedResult.interview_time}</div>
                )}
                {parsedResult.meeting_platform && (
                  <div><span className="text-gray-400">平台：</span>{parsedResult.meeting_platform}</div>
                )}
                {parsedResult.location && (
                  <div><span className="text-gray-400">地点：</span>{parsedResult.location}</div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* 日历视图 */}
      <div className="bg-white border rounded-xl p-4 mb-6">
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={() => {
              if (month === 1) { setYear(year - 1); setMonth(12) }
              else setMonth(month - 1)
            }}
            className="text-sm px-3 py-1 border rounded hover:bg-gray-50"
          >
            ← 上月
          </button>
          <span className="font-medium">{year}年{month}月</span>
          <button
            onClick={() => {
              if (month === 12) { setYear(year + 1); setMonth(1) }
              else setMonth(month + 1)
            }}
            className="text-sm px-3 py-1 border rounded hover:bg-gray-50"
          >
            下月 →
          </button>
        </div>
        <ScheduleCalendar events={calendarEvents} />
      </div>

      {/* 列表视图 */}
      <h2 className="font-semibold mb-3">安排列表</h2>
      <div className="space-y-3">
        {schedules.map((s) => (
          <div key={s.id} className="border rounded-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium">
                {s.company || '面试'} - {s.position || '未指定岗位'}
              </span>
              <span className={`text-xs px-2 py-1 rounded-full ${statusMap[s.status]?.color || ''}`}>
                {statusMap[s.status]?.label || s.status}
              </span>
            </div>
            <div className="flex flex-wrap gap-4 text-sm text-gray-500">
              <span>🕐 {new Date(s.interview_time).toLocaleString()}</span>
              {s.interview_type && <span>类型: {s.interview_type}</span>}
              {s.meeting_platform && <span>平台: {s.meeting_platform}</span>}
              {s.location && <span>地点: {s.location}</span>}
              {s.meeting_link && (
                <a href={s.meeting_link} target="_blank" className="text-blue-600">
                  加入会议
                </a>
              )}
            </div>
            {s.notes && (
              <p className="text-xs text-gray-400 mt-2">备注: {s.notes}</p>
            )}
          </div>
        ))}
        {schedules.length === 0 && (
          <p className="text-gray-400 text-center py-8">暂无面试安排</p>
        )}
      </div>
    </div>
  )
}