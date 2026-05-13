/**
 * 简历列表页
 *
 * 功能：
 *   1. 顶部是文件上传组件
 *   2. 下方是简历列表，每项显示标题、状态、大小、时间
 *   3. 点击某一项跳转到详情页查看分析结果
 *
 * 上传流程：
 *   选择文件 → FormData 包装 → POST /resumes/upload
 *   → 后端保存文件 + 触发 Celery 分析 → 立即返回
 *   → 刷新列表（新简历状态为"待分析"）
 */
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import FileUpload from '../components/FileUpload'
import type { Resume } from '../types'

export default function ResumeList() {
  const [resumes, setResumes] = useState<Resume[]>([])
  const [uploading, setUploading] = useState(false)

  // 获取简历列表
  const fetchResumes = async () => {
    const res = await api.get('/resumes')
    setResumes(res.data.items)
  }

  // 组件挂载时加载一次
  useEffect(() => {
    fetchResumes()
  }, [])

  // 上传处理
  const handleUpload = async (file: File) => {
    setUploading(true)
    // FormData：用于上传文件的格式（multipart/form-data）
    const form = new FormData()
    form.append('file', file)
    await api.post('/resumes/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    setUploading(false)
    fetchResumes()  // 刷新列表
  }

  return (
    <div>
      <h1 className="text-xl font-bold mb-4">简历管理</h1>

      {/* 上传区域 */}
      <div className="mb-6">
        <FileUpload onUpload={handleUpload} />
      </div>
      {uploading && (
        <p className="text-sm text-blue-600 mb-4">上传中...</p>
      )}

      {/* 简历列表 */}


      <div className="space-y-3">
        {resumes && resumes.length > 0 ? (
          resumes.map((r) => (
            <Link
              key={r.id}
              to={`/resumes/${r.id}`}
              className="block border rounded-xl p-4 hover:shadow-md transition-shadow"
          >
              <div className="flex items-center justify-between">
                <span className="font-medium">{r.title}</span>
                <span
                  className={`text-xs px-2 py-1 rounded-full ${
                    r.analysis_status === 'completed'
                      ? 'bg-green-100 text-green-700'
                      : 'bg-gray-100 text-gray-600'
                  }`}
               >
                    {r.analysis_status === 'completed' ? '已完成' : '待分析'}
                </span>
              </div>
              <p className="text-xs text-gray-400 mt-1">
                {r.file_type} · {(r.file_size / 1024).toFixed(1)} KB ·{' '}
                {new Date(r.created_at).toLocaleString()}
              </p>
          </Link>
        ))
      ) : (
        <p className="text-gray-400 text-center py-8">
          暂无简历，上传一份开始吧
          </p>
        )}
      </div>
    </div>
  )
}