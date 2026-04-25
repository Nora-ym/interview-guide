/**
 * Vite 构建配置
 *
 * Vite 是什么？
 *   新一代前端构建工具，替代 Webpack。
 *   开发时启动本地服务器，改了代码自动刷新（HMR 热更新）。
 *   打包时用 Rollup，速度极快。
 *
 * proxy 配置的作用：
 *   前端（localhost:5173）直接请求后端（localhost:8000）会跨域。
 *   浏览器的安全策略禁止不同端口之间的请求。
 *   解决方案：前端请求 /api/xxx → Vite 自动转发到 http://localhost:8000/api/xxx
 *   浏览器看到的是同源请求，不会报跨域错误。
 */
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // API 请求代理：/api/* → http://localhost:8000/api/*
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,  // 修改请求头中的 Origin 为目标地址
      },
      // WebSocket 代理：/ws/* → ws://localhost:8000/ws/*
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,  // 启用 WebSocket 代理
      },
    },
  },
})
