/**
 * HTTP 客户端封装
 *
 * axios 是什么？
 *   浏览器端最流行的 HTTP 请求库，比原生 fetch 好用：
 *   1. 自动把响应数据从 JSON 字符串解析成对象（fetch 需要手动 res.json()）
 *   2. 请求/响应拦截器（统一加 Token、统一处理错误）
 *   3. 超时设置、取消请求等高级功能
 *
 * 两个拦截器做了什么？
 *   请求拦截器：每次发请求前，自动从 localStorage 取出 Token
 *     加到请求头 Authorization: Bearer xxx
 *     这样不用在每个接口调用时手动传 Token
 *
 *   响应拦截器：
 *     正常响应：直接返回 res.data（即后端的 { code, message, data }）
 *     401 错误：Token 过期或无效 → 清除本地 Token → 跳转登录页
 *     其他错误：把错误信息传给调用方处理
 */
import axios from 'axios'
import type { ApiResponse } from '../types'

// 创建 axios 实例
const api = axios.create({
  baseURL: '/api/v1',   // 所有请求自动加这个前缀
  timeout: 60000,        // 60 秒超时（AI 生成可能较慢）
})

// ======== 请求拦截器 ========
api.interceptors.request.use(
  (config) => {
    // 从 localStorage 取出之前登录时存的 Token
    const token = localStorage.getItem('token')
    if (token) {
      // 加到请求头，后端会从这里取 Token 验证身份
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// ======== 响应拦截器 ========
api.interceptors.response.use(
  (response) => {
    // 正常响应：直接返回 data 部分（跳过 axios 的外层包装）
    return response.data as ApiResponse
  },
  (error) => {
    // 错误响应处理
    if (error.response?.status === 401) {
      // 401 = Token 过期或无效，跳转登录页
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    // 把错误信息传给调用方
    return Promise.reject(error.response?.data || error)
  },
)

export default api
