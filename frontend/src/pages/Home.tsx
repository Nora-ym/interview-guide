/**
 * 首页
 *
 * 展示 5 个功能模块的入口卡片，用户点击跳转到对应页面。
 * 每个卡片有图标、标题、描述，hover 时有阴影和放大效果。
 */
import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import {
  FileText,
  MessageSquare,
  Mic,
  BookOpen,
  Calendar,
} from 'lucide-react'

// 功能模块配置
const cards = [
  {
    to: '/resumes',
    icon: FileText,
    title: '简历管理',
    desc: '上传简历，AI 智能分析，生成评估报告',
  },
  {
    to: '/interviews',
    icon: MessageSquare,
    title: '模拟面试',
    desc: '文字模拟面试，AI 多轮出题与评估',
  },
  {
    to: '/voice-interview',
    icon: Mic,
    title: '语音面试',
    desc: '实时语音对话式面试',
  },
  {
    to: '/knowledge',
    icon: BookOpen,
    title: '知识库',
    desc: 'RAG 问答，构建私有知识库',
  },
  {
    to: '/schedules',
    icon: Calendar,
    title: '面试安排',
    desc: 'AI 解析邀请，日历管理',
  },
]

export default function Home() {
  const { user } = useAuth()

  return (
    <div>
      {/* 欢迎语 */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold">欢迎回来，{user?.username} 👋</h1>
        <p className="text-gray-500 mt-1">选择一个功能模块开始使用</p>
      </div>

      {/* 功能卡片网格：小屏1列，中屏2列，大屏3列 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {cards.map(({ to, icon: Icon, title, desc }) => (
          <Link
            key={to}
            to={to}
            className="border rounded-xl p-6 hover:shadow-lg hover:border-blue-300 transition-all group"
          >
            {/* 图标：hover 时放大 */}
            <Icon
              size={28}
              className="text-blue-600 mb-3 group-hover:scale-110 transition-transform"
            />
            <h2 className="font-semibold text-lg mb-1">{title}</h2>
            <p className="text-sm text-gray-500">{desc}</p>
          </Link>
        ))}
      </div>
    </div>
  )
}