import { Radar } from './Radar'

interface RadarChartProps {
  data?: Array<{signal: string, contribution: number}>
  title?: string
}

export function RadarChart({ data, title = "Risk Score Decomposition" }: RadarChartProps) {
  if (!data || data.length === 0) {
    return null
  }

  // Transform data for Radar component: {signal, contribution} -> {name, max, value}
  const maxContribution = Math.max(...data.map(i => i.contribution))
  const radarData = data.map(item => ({
    name: item.signal,
    max: maxContribution * 1.2, // Add some padding
    value: item.contribution
  }))

  return (
    <div className="w-full">
      {title && (
        <h3 className="text-center text-sm font-medium text-gray-700 mb-4">
          {title}
        </h3>
      )}
      <Radar data={radarData} />
    </div>
  )
}
