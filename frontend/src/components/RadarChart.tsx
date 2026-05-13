/**
 * 雷达图组件
 *
 * 用于面试评估结果页，展示各维度的得分。
 * 例如：技术深度 20/25、问题解决 18/25、沟通表达 22/25、项目经验 21/25
 *
 * 使用 Recharts 库（React 生态最流行的图表库）。
 * RadarChart = 雷达图
 * PolarGrid = 雷达图的网格线（蛛网状）
 * PolarAngleAxis = 角度轴（各维度名称）
 * PolarRadiusAxis = 半径轴（数值刻度）
 * Radar = 数据区域（蓝色半透明多边形）
 */
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
} from 'recharts'

export default function RadarChartComponent({
  data,
}: {
  data: { dimension: string; score: number }[]
}) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <RadarChart data={data}>
        <PolarGrid />
        <PolarAngleAxis dataKey="dimension" tick={{ fontSize: 12 }} />
        <PolarRadiusAxis angle={30} domain={[0, 25]} />
        <Radar
          name="得分"
          dataKey="score"
          stroke="#3B82F6"
          fill="#3B82F6"
          fillOpacity={0.3}
        />
      </RadarChart>
    </ResponsiveContainer>
  )
}