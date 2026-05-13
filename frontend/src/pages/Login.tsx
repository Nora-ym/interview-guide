/**
 * 登录页 - 温暖版
 * 
 * 设计理念：
 * - 非常浅的蓝色（接近天空的颜色）
 * - 温暖的配色，去除冰冷感
 * - 圆润的设计，更亲切
 * - 像朋友一样欢迎你
 */
import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { Sparkles, Mail, Lock, ArrowRight, Heart } from 'lucide-react'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  // 表单提交处理
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await login(username, password)
      navigate('/')
    } catch (err: any) {
      setError(err.detail || '登录失败，请检查用户名或密码')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-sky-50 via-blue-50 to-indigo-100">
      {/* 装饰元素 - 柔和的云朵感 */}
      <div className="absolute top-10 left-10 w-32 h-32 bg-blue-100/40 rounded-full blur-3xl" />
      <div className="absolute bottom-10 right-10 w-48 h-48 bg-sky-100/40 rounded-full blur-3xl" />
      <div className="absolute top-1/2 left-1/4 w-24 h-24 bg-cyan-100/30 rounded-full blur-2xl" />
      
      <form
        onSubmit={handleSubmit}
        className="relative bg-white/95 backdrop-blur-md rounded-3xl shadow-lg shadow-blue-100/30 p-8 w-full max-w-md mx-4 border border-blue-100/50"
      >
        {/* Logo 和欢迎语 */}
        <div className="flex flex-col items-center mb-8">
          <div className="relative">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-sky-100 to-blue-100 
                            flex items-center justify-center shadow-sm border border-blue-200/30">
              <Sparkles className="w-8 h-8 text-blue-400" />
            </div>
            <div className="absolute -top-1 -right-1 w-5 h-5 bg-gradient-to-br from-pink-200 to-pink-300 rounded-full flex items-center justify-center">
              <Heart className="w-3 h-3 text-white" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-gray-700 mt-4">嗨，欢迎回来！</h1>
          <p className="text-gray-400 text-sm mt-1">准备好今天的面试练习了吗？</p>
        </div>

        {/* 错误提示 - 柔和的红色 */}
        {error && (
          <div className="flex items-center gap-2 px-4 py-3 bg-rose-50 border border-rose-100 rounded-xl mb-4">
            <span className="text-rose-400">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </span>
            <span className="text-rose-500 text-sm">{error}</span>
          </div>
        )}

        {/* 用户名输入框 - 柔和的样式 */}
        <div className="relative mb-4">
          <div className="absolute left-4 top-1/2 -translate-y-1/2 text-blue-300">
            <Mail className="w-5 h-5" />
          </div>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="你的用户名"
            className="w-full pl-12 pr-4 py-3.5 bg-blue-50/50 border border-blue-100 rounded-xl 
                       text-sm focus:outline-none focus:ring-2 focus:ring-blue-200 
                       focus:border-blue-200 transition-all placeholder:text-gray-300"
            required
          />
        </div>

        {/* 密码输入框 */}
        <div className="relative mb-6">
          <div className="absolute left-4 top-1/2 -translate-y-1/2 text-blue-300">
            <Lock className="w-5 h-5" />
          </div>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="你的密码"
            className="w-full pl-12 pr-4 py-3.5 bg-blue-50/50 border border-blue-100 rounded-xl 
                       text-sm focus:outline-none focus:ring-2 focus:ring-blue-200 
                       focus:border-blue-200 transition-all placeholder:text-gray-300"
            required
          />
        </div>

        {/* 登录按钮 - 温暖的浅蓝色 */}
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-gradient-to-r from-blue-100 to-sky-100 text-blue-600 py-3.5 rounded-xl 
                     font-medium border border-blue-200 hover:from-blue-200 hover:to-sky-200 
                     hover:shadow-md hover:shadow-blue-100/50 transition-all duration-300
                     disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <div className="w-4 h-4 border-2 border-blue-300 border-t-blue-500 rounded-full animate-spin" />
              正在准备...
            </>
          ) : (
            <>
              开始练习
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>

        {/* 注册链接 - 柔和的颜色 */}
        <p className="text-center text-gray-400 text-sm mt-6">
          还没有账号？{' '}
          <Link 
            to="/register" 
            className="text-blue-400 font-medium hover:text-blue-500 transition-colors"
          >
            快来加入我们
          </Link>
        </p>

        {/* 底部装饰文字 */}
        <p className="text-center text-gray-300 text-xs mt-4">
          每天进步一点点 💪
        </p>
      </form>
    </div>
  )
}
