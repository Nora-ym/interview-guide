/**
 * 侧边栏导航组件 - 温暖版
 * 
 * 设计理念：
 * - 浅色系设计，去除冰冷感
 * - 圆润的边角设计
 * - 亲切友好的配色
 */
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import {
  LayoutDashboard,
  FileText,
  MessageSquare,
  Mic,
  BookOpen,
  Calendar,
  LogOut,
  Sparkles,
  Heart,
} from 'lucide-react'

// 导航链接配置
const links = [
  { to: '/', icon: LayoutDashboard, label: '首页' },
  { to: '/resumes', icon: FileText, label: '简历管理' },
  { to: '/interviews', icon: MessageSquare, label: '模拟面试' },
  { to: '/voice-interview', icon: Mic, label: '语音面试' },
  { to: '/knowledge', icon: BookOpen, label: '知识库' },
  { to: '/schedules', icon: Calendar, label: '面试安排' },
]

export default function Sidebar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  // 点击退出登录
  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <aside className="w-64 bg-gradient-to-br from-blue-50 via-sky-50 to-indigo-50 flex flex-col 
                      rounded-r-3xl shadow-md shadow-blue-100/30 overflow-hidden border-r border-blue-100">
      {/* Logo 和用户名 */}
      <div className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="relative">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-100 to-sky-100 
                            flex items-center justify-center shadow-sm border border-blue-200/30">
              <Sparkles className="w-5 h-5 text-blue-400" />
            </div>
            <div className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 bg-gradient-to-br from-pink-200 to-pink-300 rounded-full flex items-center justify-center">
              <Heart className="w-2 h-2 text-white" />
            </div>
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-700">面试助手</h1>
            <p className="text-xs text-gray-400">AI 智能练习</p>
          </div>
        </div>
        
        {/* 用户信息卡片 */}
        <div className="bg-white/60 backdrop-blur-sm rounded-xl p-4 border border-blue-100/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-100 to-sky-100 
                           flex items-center justify-center text-blue-500 font-bold border border-blue-200/50">
              {user?.username?.charAt(0).toUpperCase()}
            </div>
            <div>
              <p className="text-gray-700 font-medium text-sm">{user?.username}</p>
              <p className="text-gray-400 text-xs">准备面试中</p>
            </div>
          </div>
        </div>
      </div>

      {/* 导航链接列表 */}
      <nav className="flex-1 px-4 pb-4">
        <div className="space-y-2">
          {links.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'bg-gradient-to-r from-blue-100 to-sky-100 text-blue-600 shadow-sm'
                    : 'text-gray-500 hover:bg-blue-50 hover:text-gray-700'
                }`
              }
            >
              <Icon size={18} className="text-gray-400" />
              {label}
            </NavLink>
          ))}
        </div>
      </nav>

      {/* 退出登录按钮 */}
      <div className="p-4 border-t border-blue-100/50">
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium 
                     text-gray-500 hover:bg-rose-50 hover:text-rose-500 w-full 
                     transition-all duration-200"
        >
          <LogOut size={18} />
          退出登录
        </button>
      </div>
    </aside>
  )
}
