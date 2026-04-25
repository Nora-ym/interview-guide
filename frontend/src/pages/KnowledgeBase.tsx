/**
 * 知识库管理页
 *
 * 功能：
 *   1. 创建知识库 + 查看列表
 *   2. 每个知识库可以上传多个文档
 *   3. 查看文档处理状态
 *   4. 删除知识库
 *   5. 点击知识库名称跳转到聊天页
 */
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import FileUpload from '../components/FileUpload'
import type { KnowledgeBase, KnowledgeDocument } from '../types'

export default function KnowledgeBase() {
  const [kbs, setKbs] = useState<KnowledgeBase[]>([])
  const [docs, setDocs] = useState<Record<number, KnowledgeDocument[]>>({})
  const [uploadingKbId, setUploadingKbId] = useState<number | null>(null)

  // 加载知识库列表
  const fetchKbs = async () => {
    const res = await api.get('/knowledgebases')
    setKbs(res.data.items)
    // 为每个知识库加载文档列表
    for (const kb of res.data.items) {
      api.get(`/knowledgebases/${kb.id}/documents`).then((d: any) => {
        setDocs((prev) => ({ ...prev, [kb.id]: d.data }))
      })
    }
  }

  useEffect(() => {
    fetchKbs()
  }, [])

  // 创建知识库
  const handleCreate = async (name: string) => {
    if (!name.trim()) return
    await api.post('/knowledgebases', { name: name.trim() })
    fetchKbs()
  }

  // 删除知识库
  const handleDelete = async (kbId: number) => {
    if (!confirm('确定要删除这个知识库吗？')) return
    await api.delete(`/knowledgebases/${kbId}`)
    fetchKbs()
  }

  // 上传文档
  const handleUpload = async (file: File) => {
    if (!uploadingKbId) return
    const form = new FormData()
    form.append('file', file)
    await api.post(`/knowledgebases/${uploadingKbId}/documents`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    setUploadingKbId(null)
    fetchKbs()
  }

  // 状态显示映射
  const statusLabel: Record<string, string> = {
    pending: '⏳ 等待处理',
    processing: '⏳ 处理中',
    completed: '✅ 已完成',
    failed: '❌ 处理失败',
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-bold">📚 知识库</h1>
        <button
          onClick={() => {
            const name = prompt('请输入知识库名称')
            if (name) handleCreate(name)
          }}
          className="bg-blue-600 text-white rounded-lg px-4 py-2 text-sm hover:bg-blue-700"
        >
          + 新建知识库
        </button>
      </div>

      {/* 知识库列表 */}
      <div className="space-y-4">
        {kbs.map((kb) => (
          <div key={kb.id} className="border rounded-xl p-5 hover:shadow-md transition-shadow">
            {/* 头部：名称 + 操作按钮 */}
            <div className="flex items-center justify-between">
              <Link
                to={`/knowledge/${kb.id}`}
                className="text-lg font-medium hover:text-blue-600 hover:underline"
              >
                {kb.name}
              </Link>
              <div className="flex gap-2">
                <button
                  onClick={() => setUploadingKbId(kb.id)}
                  className="text-blue-600 hover:bg-blue-50 text-sm px-2 py-1 rounded"
                >
                  上传文档
                </button>
                <button
                  onClick={() => handleDelete(kb.id)}
                  className="text-red-500 hover:text-red-700 text-sm px-2 py-1"
                >
                  删除
                </button>
              </div>
            </div>

            {/* 统计信息 */}
            <div className="flex gap-6 text-sm text-gray-500 mt-1">
              <span>{kb.doc_count} 个文档</span>
              <span>{kb.chunk_count} 个分块</span>
            </div>

            {/* 文档列表 */}
            {docs[kb.id]?.length > 0 && (
              <div className="border-t mt-3 pt-3">
                <p className="text-xs text-gray-400 mb-2">文档列表</p>
                {docs[kb.id].map((doc: KnowledgeDocument) => (
                  <div key={doc.id} className="flex items-center justify-between py-2 border-b last:border-b-0">
                    <span className="text-sm">{doc.title}</span>
                    <span className="text-xs">{statusLabel[doc.process_status] || doc.process_status}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {kbs.length === 0 && (
        <p className="text-gray-400 text-center py-8">还没有知识库，创建一个开始吧</p>
      )}

      {/* 上传对话框（弹出式） */}
      {uploadingKbId !== null && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-md">
            <h3 className="font-semibold mb-4">上传文档</h3>
            <FileUpload onUpload={handleUpload} />
            <button
              onClick={() => setUploadingKbId(null)}
              className="mt-4 w-full border rounded-lg py-2 text-sm hover:bg-gray-50"
            >
              取消
            </button>
          </div>
        </div>
      )}
    </div>
  )
}