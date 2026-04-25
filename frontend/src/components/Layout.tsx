/**
 * 布局组件
 *
 * 作用：
 *   所有需要登录才能访问的页面都套在这个布局里面。
 *   它提供：
 *   1. 登录检查：未登录自动跳转到 /login
 *   2. 加载状态：正在恢复登录态时显示"加载中"
 *   3. 侧边栏 + 主内容区的布局结构
 *
 * Outlet 是什么？
 *   React Router 的组件，表示"子路由渲染在这里"。
 *   例如：访问 /resumes 时，Outlet 的位置会渲染 ResumeList 组件。
 *   就像是一个"插槽"。
 */
import { Outlet, Navigate } from 'react-router-dom'
import Sidebar from './Sidebar'
import { useAuth } from '../hooks/useAuth'

export default function Layout() {
  const { user, loading } = useAuth()

  // 正在加载用户信息
  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        加载中...
      </div>
    )
  }

  // 没有用户信息 = 未登录，跳转到登录页
  if (!user) {
    return <Navigate to="/login" replace />
  }

  // 已登录：渲染侧边栏 + 主内容区
  return (
    <div className="flex h-screen">
      {/* 左侧导航栏 */}
      <Sidebar />
      {/* 右侧主内容区 */}
      <main className="flex-1 overflow-y-auto bg-gray-50 p-6">
        <Outlet />
      </main>
    </div>
  )
}