/**
 * 路由配置
 *
 * Routes：路由容器，里面定义所有的 URL → 组件映射
 * Route：单条路由规则
 *   path：URL 路径
 *   element：渲染的组件
 *
 * 嵌套路由：
 *   <Route element={<Layout />}> 是父路由
 *   里面的 <Route path="/resumes" element={<ResumeList />} /> 是子路由
 *   子路由会渲染在 Layout 组件的 <Outlet /> 位置
 *
 * 不需要登录的页面（login、register）放在 Layout 外面
 * 需要登录的页面放在 Layout 里面（Layout 会检查登录状态）
 */
import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import Login from './pages/Login'
import Register from './pages/Register'
import ResumeList from './pages/ResumeList'
import ResumeDetail from './pages/ResumeDetail'
import InterviewList from './pages/InterviewList'
import InterviewChat from './pages/InterviewChat'
import VoiceInterview from './pages/VoiceInterview'
import KnowledgeBase from './pages/KnowledgeBase'
import KnowledgeChat from './pages/KnowledgeChat'
import SchedulePage from './pages/SchedulePage'

export default function App() {
  return (
    <Routes>
      {/* 不需要登录的页面 */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* 需要登录的页面（嵌套在 Layout 中） */}
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/resumes" element={<ResumeList />} />
        <Route path="/resumes/:id" element={<ResumeDetail />} />
        <Route path="/interviews" element={<InterviewList />} />
        <Route path="/interviews/:id" element={<InterviewChat />} />
        <Route path="/voice-interview" element={<VoiceInterview />} />
        <Route path="/knowledge" element={<KnowledgeBase />} />
        <Route path="/knowledge/:id" element={<KnowledgeChat />} />
        <Route path="/schedules" element={<SchedulePage />} />
      </Route>
    </Routes>
  )
}