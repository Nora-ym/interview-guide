/**
 * 布局组件 - 温暖版
 * 
 * 设计理念：
 * - 浅色系背景
 * - 更好的加载状态
 * - 更舒适的内容区样式
 */
import { Outlet, Navigate } from 'react-router-dom'
import Sidebar from './Sidebar'
import { useAuth } from '../hooks/useAuth'

export default function Layout() {
  const { user, loading } = useAuth()

  // 正在加载用户信息
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-sky-50 via-blue-50 to-indigo-100">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-blue-200 border-t-blue-400 rounded-full animate-spin" />
          <p className="text-gray-400 font-medium">正在准备面试助手...</p>
        </div>
      </div>
    )
  }

  // 没有用户信息 = 未登录，跳转到登录页
  if (!user) {
    return <Navigate to="/login" replace />
  }

  // 已登录：渲染侧边栏 + 主内容区
  return (
    <div className="flex h-screen bg-gradient-to-br from-sky-50 via-white to-blue-50/30">
      {/* 左侧导航栏 */}
      <Sidebar />
      {/* 右侧主内容区 */}
      <main className="flex-1 overflow-y-auto p-8">
        <div className="max-w-6xl mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
