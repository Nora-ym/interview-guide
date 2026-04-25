/**
 * 日历组件
 *
 * 使用 react-big-calendar 库实现月视图日历。
 * 每个面试安排显示为一个事件块，颜色根据状态区分。
 *
 * dateFnsLocalizer 是什么？
 *   react-big-calendar 需要一个"日期本地化器"来处理日期的格式化。
 *   我们用 date-fns 库（轻量级日期处理库）作为本地化器。
 *   配置中文locale后，日历头部会显示中文的星期几和月份。
 */
import { Calendar, dateFnsLocalizer } from 'react-big-calendar'
import { format, parse, startOfWeek, getDay } from 'date-fns'
import { zhCN } from 'date-fns/locale'
import 'react-big-calendar/lib/css/react-big-calendar.css'

// 配置 date-fns 本地化器
const locales = { 'zh-CN': zhCN }
const localizer = dateFnsLocalizer({
  format,
  parse,
  startOfWeek: () => startOfWeek(new Date(), { weekStartsOn: 1 }), // 周一为一周起始
  getDay,
  locales,
})

export default function ScheduleCalendar({ events }: { events: any[] }) {
  return (
    <div className="h-[600px]">
      <Calendar
        localizer={localizer}
        events={events}
        culture="zh-CN"
        defaultView="month"
        views={['month', 'week', 'day', 'agenda']}
        style={{ height: '100%' }}
        // 为每个事件设置样式（颜色）
        eventPropGetter={(event) => ({
          style: {
            backgroundColor: event.color || '#3B82F6',
            borderRadius: '6px',
            border: 'none',
            opacity: 0.9,
          },
        })}
      />
    </div>
  )
}