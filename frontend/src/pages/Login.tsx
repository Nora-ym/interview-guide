/**
 * 登录页
 *
 * 交互流程：
 *   1. 用户输入用户名和密码
 *   2. 点击"登录"按钮 → 调用 login API
 *   3. 成功 → 跳转首页（navigate('/')）
 *   4. 失败 → 显示红色错误提示
 */
import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const { login } = useAuth()
  const navigate = useNavigate()

  // 表单提交处理
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()  // 阻止默认的表单提交（会刷新页面）
    try {
      await login(username, password)
      navigate('/')  // 登录成功跳转首页
    } catch (err: any) {
      setError(err.detail || '登录失败')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <form
        onSubmit={handleSubmit}
        className="bg-white rounded-2xl shadow-lg p-8 w-full max-w-sm"
      >
        <h1 className="text-2xl font-bold text-center mb-6">🎯 Interview Guide</h1>

        {/* 错误提示 */}
        {error && (
          <p className="text-red-500 text-sm mb-4 text-center">{error}</p>
        )}

        {/* 用户名输入框 */}
        <input
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="用户名"
          className="w-full border rounded-lg px-4 py-2 mb-3 text-sm"
          required
        />

        {/* 密码输入框 */}
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="密码"
          className="w-full border rounded-lg px-4 py-2 mb-4 text-sm"
          required
        />

        {/* 登录按钮 */}
        <button
          type="submit"
          className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
        >
          登录
        </button>

        {/* 注册链接 */}
        <p className="text-center text-sm text-gray-500 mt-4">
          还没有账号？<Link to="/register" className="text-blue-600">注册</Link>
        </p>
      </form>
    </div>
  )
}