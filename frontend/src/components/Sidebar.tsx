/**
 * 侧边栏导航组件
 *
 * 功能：
 *   1. 顶部显示应用名和当前用户名
 *   2. 中间是导航链接列表，点击切换页面
 *   3. 底部是退出登录按钮
 *
 * NavLink 是什么？
 *   React Router 提供的导航组件，和 <a> 标签类似，但：
 *   1. 不会触发整页刷新（SPA 单页应用）
 *   2. 提供 isActive 状态（当前页面高亮）
 *   3. className 可以是函数，根据 isActive 动态返回不同的样式
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
    <aside className="w-60 bg-white border-r flex flex-col">
      {/* Logo 和用户名 */}
      <div className="p-4 border-b">
        <h1 className="text-lg font-bold">🎯 Interview Guide</h1>
        <p className="text-xs text-gray-500 mt-1">{user?.username}</p>
      </div>

      {/* 导航链接列表 */}
      <nav className="flex-1 p-2 space-y-1">
        {links.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}  // end 表示精确匹配（/ 只匹配首页，不匹配 /resumes 等）
            className={({ isActive }) =>
              // isActive 为 true 时高亮蓝色，否则灰色
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'bg-blue-50 text-blue-700 font-medium'
                  : 'text-gray-600 hover:bg-gray-100'
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* 退出登录按钮 */}
      <div className="p-2 border-t">
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-600 hover:bg-red-50 hover:text-red-600 w-full"
        >
          <LogOut size={18} />
          退出登录
        </button>
      </div>
    </aside>
  )
}