/**
 * 文件上传组件
 *
 * 支持两种上传方式：
 *   1. 点击上传：点击区域弹出文件选择对话框
 *   2. 拖拽上传：把文件拖到虚线框区域
 *
 * 实现原理：
 *   - 点击：隐藏的 <input type="file">，点击外层 div 时触发 input 的 click()
 *   - 拖拽：监听 onDragOver（拖入时高亮）和 onDrop（松手时获取文件）
 *   - accept 属性限制可选的文件类型
 */
import { useRef, useState } from 'react'
import { Upload } from 'lucide-react'

export default function FileUpload({
  onUpload,
  accept = '.pdf,.docx,.doc,.txt,.md,.pptx',
}: {
  onUpload: (file: File) => void  // 文件选择后的回调函数
  accept?: string                  // 允许的文件类型
}) {
  const inputRef = useRef<HTMLInputElement>(null)  // 隐藏的 file input 的引用
  const [dragging, setDragging] = useState(false)  // 是否正在拖拽

  // 拖拽松手：获取文件并调用回调
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()       // 阻止浏览器默认行为（默认会打开文件）
    setDragging(false)
    if (e.dataTransfer.files[0]) {
      onUpload(e.dataTransfer.files[0])
    }
  }

  return (
    <div
      className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
        dragging
          ? 'border-blue-500 bg-blue-50'
          : 'border-gray-300 hover:border-gray-400'
      }`}
      // 点击整个区域 → 触发隐藏 input 的 click
      onClick={() => inputRef.current?.click()}
      // 拖拽事件
      onDragOver={(e) => {
        e.preventDefault()
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
    >
      <Upload className="mx-auto mb-3 text-gray-400" size={40} />
      <p className="text-sm text-gray-500">点击或拖拽文件到此处上传</p>
      <p className="text-xs text-gray-400 mt-1">支持 {accept}</p>

      {/* 隐藏的文件选择 input */}
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => {
          if (e.target.files?.[0]) {
            onUpload(e.target.files[0])
          }
        }}
      />
    </div>
  )
}