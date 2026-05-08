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
  
  // Define max values based on scoring configuration
  const dimensionMaxValues: Record<string, number> = {
    'sentiment': 10,      // max from negative_strong weight
    'toxicity': 30,       // max_contribution from config
    'topics': 35,         // max_contribution from config
    'age': 10,            // max_contribution from config
    'trend_overlap': 25,   // max_contribution from config
  }
  
  const radarData = data.map(item => ({
    name: item.signal[0].toUpperCase() + item.signal.slice(1).replaceAll("_", " "),
    max: dimensionMaxValues[item.signal] || Math.max(maxContribution, 1),
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
