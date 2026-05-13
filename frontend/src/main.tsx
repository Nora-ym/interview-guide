/**
 * 前端入口文件
 *
 * ReactDOM.createRoot：React 18 的新 API，把 React 组件渲染到 DOM 节点上
 * BrowserRouter：URL 路由器，让不同 URL 显示不同页面
 *   /login → 登录页
 *   / → 首页
 *   /resumes → 简历管理
 *   ...
 * StrictMode：严格模式，帮助发现潜在问题（开发环境用，生产环境无影响）
 */
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './styles/globals.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)