/**
 * 首页 - 温暖版
 * 
 * 设计理念：
 * - 非常浅的蓝色背景
 * - 温暖的配色，去除冰冷感
 * - 圆润的卡片设计
 * - 亲切友好的欢迎语
 */
import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import {
  FileText,
  MessageSquare,
  Mic,
  BookOpen,
  Calendar,
  Sparkles,
  TrendingUp,
  Target,
  Award,
  Heart,
} from 'lucide-react'

// 功能模块配置
const cards = [
  {
    to: '/resumes',
    icon: FileText,
    title: '简历管理',
    desc: '上传简历，AI 帮你分析和优化',
    gradient: 'from-blue-100 to-sky-100',
    iconColor: 'text-blue-400',
  },
  {
    to: '/interviews',
    icon: MessageSquare,
    title: '模拟面试',
    desc: 'AI 多轮出题，模拟真实面试',
    gradient: 'from-purple-100 to-pink-100',
    iconColor: 'text-purple-400',
  },
  {
    to: '/voice-interview',
    icon: Mic,
    title: '语音面试',
    desc: '实时语音对话，沉浸式体验',
    gradient: 'from-emerald-100 to-teal-100',
    iconColor: 'text-emerald-400',
  },
  {
    to: '/knowledge',
    icon: BookOpen,
    title: '知识库',
    desc: '智能问答，构建你的知识体系',
    gradient: 'from-amber-100 to-orange-100',
    iconColor: 'text-amber-400',
  },
  {
    to: '/schedules',
    icon: Calendar,
    title: '面试安排',
    desc: '智能解析邀请，高效管理日程',
    gradient: 'from-cyan-100 to-blue-100',
    iconColor: 'text-cyan-400',
  },
]

// 统计数据
const stats = [
  { value: '3', label: '今日练习', icon: Target, color: 'text-blue-400' },
  { value: '15', label: '累计面试', icon: TrendingUp, color: 'text-emerald-400' },
  { value: '85%', label: '通过率', icon: Award, color: 'text-amber-400' },
]

// 改进的卡片组件
const FeatureCard = ({ to, icon: Icon, title, desc, gradient, iconColor }) => (
  <Link
    to={to}
    className="group relative overflow-hidden rounded-2xl p-6 bg-white border border-gray-100 
               shadow-sm hover:shadow-md hover:shadow-blue-50/50 hover:-translate-y-1 transition-all duration-300"
  >
    {/* 渐变背景层（hover 时显示） */}
    <div className={`absolute inset-0 bg-gradient-to-br ${gradient} opacity-0 group-hover:opacity-30 transition-opacity duration-300`} />
    
    {/* 图标容器 */}
    <div className={`relative w-12 h-12 rounded-xl bg-gradient-to-br ${gradient} 
                    flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300`}>
      <Icon className={`w-6 h-6 ${iconColor}`} />
    </div>
    
    <h3 className="relative font-semibold text-lg text-gray-700 mb-2 group-hover:text-blue-500 transition-colors">
      {title}
    </h3>
    <p className="relative text-sm text-gray-400 leading-relaxed">
      {desc}
    </p>
    
    {/* 装饰元素 - 小爱心 */}
    <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-50 transition-opacity">
      <Heart className="w-4 h-4 text-pink-300" />
    </div>
  </Link>
)

// 统计卡片组件
const StatCard = ({ value, label, icon: Icon, color }) => (
  <div className="bg-white rounded-xl p-5 border border-gray-100 shadow-sm hover:shadow-md transition-shadow duration-300">
    <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${color} bg-opacity-10 
                    flex items-center justify-center mb-3`}>
      <Icon className={`w-5 h-5 ${color}`} />
    </div>
    <div className="text-2xl font-bold text-gray-700">
      {value}
    </div>
    <div className="text-sm text-gray-400 mt-1">{label}</div>
  </div>
)

export default function Home() {
  const { user } = useAuth()

  return (
    <div className="min-h-screen bg-gradient-to-br from-sky-50 via-white to-blue-50/30">
      {/* 顶部欢迎区域 */}
      <div className="mb-10">
        {/* 成就标签 */}
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-100 to-sky-100 
                        rounded-full text-blue-600 text-sm font-medium mb-4 border border-blue-200/50">
          <Sparkles className="w-4 h-4" />
          今日已完成 {stats[0].value} 个练习 ✨
        </div>
        
        {/* 欢迎标题 */}
        <h1 className="text-3xl md:text-4xl font-bold text-gray-700 leading-tight">
          嗨，{user?.username}！
          <br />
          <span className="text-blue-500">今天想练习什么？</span>
        </h1>
        <p className="text-gray-400 mt-3 text-lg">选择一个模块，开始你的面试准备之旅</p>
      </div>

      {/* 功能卡片网格 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {cards.map((card, index) => (
          <div 
            key={card.to} 
            style={{ animationDelay: `${index * 0.1}s` }}
            className="animate-slide-up"
          >
            <FeatureCard {...card} />
          </div>
        ))}
      </div>

      {/* 底部统计卡片 */}
      <div className="mt-12 grid grid-cols-3 gap-4">
        {stats.map((stat) => (
          <StatCard key={stat.label} {...stat} />
        ))}
      </div>

      {/* 底部鼓励语 */}
      <div className="mt-8 text-center">
        <p className="text-gray-300 text-sm">
          每天进步一点点，offer 就在眼前 💪
        </p>
      </div>
    </div>
  )
}
