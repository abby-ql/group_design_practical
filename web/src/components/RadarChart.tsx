import ReactECharts from 'echarts-for-react'

interface RadarChartProps {
  data?: Array<{signal: string, contribution: number}>
  title?: string
}

export function RadarChart({ data, title = "Risk Score Decomposition" }: RadarChartProps) {
  if (!data || data.length === 0) {
    return null
  }

  const indicators = data.map(i => ({
    name: i.signal,
    max: Math.max(...data.map(j => j.contribution)) * 1.2,
  }))

  const option = {
    title: {
      text: title,
      left: 'center',
      textStyle: {
        fontSize: 14,
        fontWeight: 'normal'
      }
    },
    tooltip: {
      trigger: 'item'
    },
    radar: {
      indicator: indicators,
      shape: 'polygon',
      splitNumber: 4,
      axisName: {
        color: '#666',
        fontSize: 11
      },
      splitLine: {
        lineStyle: {
          color: '#e0e0e0'
        }
      },
      splitArea: {
        show: true,
        areaStyle: {
          color: ['rgba(114, 172, 209, 0.2)', 'rgba(114, 172, 209, 0.1)']
        }
      },
      axisLine: {
        lineStyle: {
          color: '#ccc'
        }
      }
    },
    series: [{
      type: 'radar',
      data: [{
        value: data.map(i => i.contribution),
        name: 'Contribution',
        itemStyle: {
          color: '#5470c6'
        },
        areaStyle: {
          color: 'rgba(84, 112, 198, 0.3)'
        },
        lineStyle: {
          color: '#5470c6',
          width: 2
        }
      }]
    }]
  }

  return (
    <div style={{ width: '100%', height: '300px', marginTop: '16px' }}>
      <ReactECharts option={option} style={{ height: '100%', width: '100%' }} />
    </div>
  )
}
