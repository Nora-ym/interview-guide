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

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
})

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

api.interceptors.response.use(
  (response) => {
    // 后端所有接口都返回 { code, message, data } 的 ApiResponse 格式
    // 这里统一把 data 解出来，确保每个页面拿到的就是它需要的业务数据
    const resData = response.data
    if (resData && typeof resData === 'object' && 'data' in resData) {
      return { ...response, data: resData.data }
    }
    return response
  },
  (error) => {
    if (error.response?.status === 401) {
      const currentPath = window.location.pathname
      if (currentPath !== '/login' && currentPath !== '/register') {
        localStorage.removeItem('token')
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

export default api
