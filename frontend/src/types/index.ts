/**
 * 全局类型定义
 *
 * TypeScript 的作用：
 *   在写代码时就发现类型错误，而不是等运行时才报错。
 *   例如：把 string 赋给 number 会直接标红提示。
 *
 * 这些类型和后端的 Schema 保持一致，
 * 前后端通过统一的类型定义保证数据结构兼容。
 */

// ---- 用户 ----
export interface User {
  id: number;
  username: string;
  email: string;
  avatar_url: string | null;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}

// ---- 统一 API 响应格式 ----
// 后端所有接口都返回这个格式：{ code: 200, message: "success", data: {...} }
export interface ApiResponse<T = any> {
  code: number;
  message: string;
  data: T | null;
}

// ---- 分页结果 ----
export interface PageResult<T> {
  total: number;       // 总记录数
  page: number;        // 当前页码
  page_size: number;   // 每页数量
  items: T[];          // 当前页的数据列表
}

// ---- 简历 ----
export interface Resume {
  id: number;
  title: string;              // 简历标题（通常是文件名）
  file_url: string;           // 文件存储路径
  file_type: string;          // 文件类型：pdf/docx/txt
  file_size: number;          // 文件大小（字节）
  analysis_status: string;    // 分析状态：pending/analyzing/completed/failed
  analysis_result: any;       // AI 分析结果（JSON 对象，结构不固定）
  report_url: string | null;  // PDF 报告下载路径
  created_at: string;
  updated_at: string;
}

// ---- 面试会话 ----
export interface Interview {
  id: number;
  skill_id: string;           // 技能方向标识
  skill_name: string;         // 技能方向显示名
  difficulty: string;         // 难度：easy/medium/hard
  interview_type: string;     // 类型：text/voice
  status: string;             // 状态：in_progress/completed/cancelled
  current_round: number;      // 当前轮次
  max_rounds: number;         // 最大轮次
  total_score: number | null; // 总分（面试结束后有值）
  evaluation: any;            // 评估结果（JSON）
  report_url: string | null;  // PDF 报告路径
  started_at: string | null;
  ended_at: string | null;
  messages: InterviewMessage[];  // 面试中的所有消息
  created_at?: string;           // 创建时间
}

// ---- 面试消息 ----
export interface InterviewMessage {
  id: number;
  role: string;          // 角色：interviewer（面试官）/ candidate（候选人）
  content: string;       // 消息内容
  message_type: string;  // 类型：text/audio
  round: number;         // 第几轮
  created_at: string;
}

// ---- 知识库 ----
export interface KnowledgeBase {
  id: number;
  name: string;
  description: string | null;
  doc_count: number;      // 文档数量
  chunk_count: number;    // 分块数量
  created_at: string;
}

// ---- 知识库文档 ----
export interface KnowledgeDocument {
  id: number;
  title: string;
  file_type: string;
  file_size: number;
  process_status: string;    // pending/processing/completed/failed
  chunk_count: number;
  error_message: string | null;
  created_at: string;
}

// ---- 面试安排 ----
export interface Schedule {
  id: number;
  company: string | null;         // 公司名称
  position: string | null;        // 岗位名称
  interview_type: string | null;  // 面试类型
  interview_time: string;         // 面试时间
  duration_minutes: number;       // 面试时长（分钟）
  meeting_platform: string | null; // 会议平台
  meeting_link: string | null;     // 会议链接
  meeting_id: string | null;       // 会议号
  status: string;                  // upcoming/completed/cancelled
  location: string | null;         // 面试地点
  interviewer_name: string | null; // 面试官姓名
  notes: string | null;            // 备注
  reminder_sent: boolean;          // 是否已发提醒
  created_at: string;
}
