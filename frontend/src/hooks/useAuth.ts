/**
 * 认证 Hook（自定义 Hook）
 *
 * 自定义 Hook 是什么？
 *   把组件中可复用的逻辑抽出来，封装成函数。
 *   函数名以 "use" 开头，内部可以用其他 Hook（useState、useEffect 等）。
 *   在组件中使用：const { user, login, logout } = useAuth();
 *
 * 这个 Hook 管理什么？
 *   1. user：当前登录用户（null = 未登录）
 *   2. loading：是否正在加载用户信息（页面初始化时）
 *   3. login()：登录 → 存 Token → 设置用户
 *   4. register()：注册 → 存 Token → 设置用户
 *   5. logout()：清 Token → 清用户
 *
 * Token 存在哪里？
 *   localStorage（浏览器本地存储，关了浏览器还在）。
 *   页面刷新后，useEffect 自动调用 /auth/me 接口恢复登录态。
 */
import { useState, useEffect } from 'react'
import type { User } from '../types'
import api from '../api/client'

export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  // 登录
  const login = async (username: string, password: string) => {
    const res = await api.post('/auth/login', { username, password })
    // 登录成功：存 Token 到 localStorage
    localStorage.setItem('token', res.data.access_token)
    // 设置用户状态（组件会自动重新渲染）
    setUser(res.data.user)
    return res.data
  }

  // 注册
  const register = async (username: string, email: string, password: string) => {
    const res = await api.post('/auth/register', { username, email, password })
    localStorage.setItem('token', res.data.access_token)
    setUser(res.data.user)
    return res.data
  }

  // 退出登录
  const logout = () => {
    localStorage.removeItem('token')
    setUser(null)
  }

  // 恢复登录态：页面加载时，如果有 Token 就查一下用户信息
  const fetchMe = async () => {
    try {
      const res = await api.get('/auth/me')
      setUser(res.data)
    } catch {
      // Token 无效或过期，设为未登录
      setUser(null)
    } finally {
      setLoading(false)
    }
  }

  // 组件挂载时执行一次
  useEffect(() => {
    fetchMe()
  }, [])

  return { user, loading, login, register, logout }
}
