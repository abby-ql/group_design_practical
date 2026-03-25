import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Pill } from './ui'
import { useItems, useTrends, useAlerts } from './hooks'
import './index.css'

const queryClient = new QueryClient()

interface Item {
  created_at: string;
  risk: {
    bucket: string;
    total_score: number;
  };
  text: string;
}

interface Alert {
  created_at: string;
  trend_term: string;
  old_bucket?: string;
  new_bucket?: string;
  risk_delta?: number;
}

function App() {
  const [selectedItem, setSelectedItem] = useState<Item | null>(null)
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null)
  const [status, setStatus] = useState<string>('')

  const { data: itemsData, refetch: refetchItems } = useItems()
  const { data: trendsData, refetch: refetchTrends } = useTrends()
  const { data: alertsData, refetch: refetchAlerts } = useAlerts()

  const refreshAll = async () => {
    setStatus('Refreshing…')
    try {
      await refetchItems()
      await refetchTrends()
      await refetchAlerts()
      setStatus('Ready.')
    } catch (e: unknown) {
      setStatus('Error: ' + (e as Error).message)
    }
  }

  return (
    <QueryClientProvider client={queryClient}>
      <div className="font-sans m-5">
        <h1 className="mb-1.5">Trend‑aware Risk Signals — Demo UI</h1>
        <div className="toolbar flex gap-2 items-center m-2.5 mb-4.5 flex-wrap">
          <button onClick={refreshAll} className="px-3 py-2 rounded-lg border border-gray-300 bg-white hover:bg-gray-50 cursor-pointer">Refresh</button>
          <span className="text-gray-500 text-sm">{status}</span>
        </div>

        <div className="row flex gap-4 flex-wrap">
          <div className="card border border-gray-300 rounded-xl p-3 flex-1 min-w-80">
            <h3>Items</h3>
            <div className="text-gray-500 text-sm">
              {itemsData ? `${itemsData.count} items shown` : 'Loading...'}
            </div>
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  <th className="border-b border-gray-200 p-1.5 align-top">When</th>
                  <th className="border-b border-gray-200 p-1.5 align-top">Risk</th>
                  <th className="border-b border-gray-200 p-1.5 align-top">Text</th>
                </tr>
              </thead>
              <tbody>
                {itemsData?.items.map((item, index) => (
                  <tr 
                    key={index} 
                    onClick={() => setSelectedItem(item)}
                    className="cursor-pointer hover:bg-gray-50"
                  >
                    <td className="border-b border-gray-200 p-1.5 align-top">
                      {new Date(item.created_at).toISOString().slice(0,10)}
                    </td>
                    <td className="border-b border-gray-200 p-1.5 align-top">
                      <Pill bucket={item.risk.bucket} />
                      <span className="text-gray-500 text-sm">
                        ({item.risk.total_score})
                      </span>
                    </td>
                    <td className="border-b border-gray-200 p-1.5 align-top">
                      {item.text}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card border border-gray-300 rounded-xl p-3 flex-1 min-w-80">
            <h3>Why flagged?</h3>
            <div className="text-gray-500 text-sm">
              Click an item row to inspect its reasons + score decomposition.
            </div>
            <pre className="whitespace-pre-wrap break-words text-xs bg-gray-50 p-2.5 rounded-lg my-0">
              {selectedItem ? JSON.stringify(selectedItem, null, 2) : '(select an item)'}
            </pre>
          </div>
        </div>

        <div className="row flex gap-4 flex-wrap mt-4">
          <div className="card border border-gray-300 rounded-xl p-3 flex-1 min-w-80">
            <h3>UK trends (current)</h3>
            <div className="text-gray-500 text-sm">
              {trendsData ? `${trendsData.count} trends` : 'Loading...'}
            </div>
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  <th className="border-b border-gray-200 p-1.5 align-top">Term</th>
                  <th className="border-b border-gray-200 p-1.5 align-top">Vol</th>
                  <th className="border-b border-gray-200 p-1.5 align-top">Tone</th>
                  <th className="border-b border-gray-200 p-1.5 align-top">Last seen</th>
                </tr>
              </thead>
              <tbody>
                {trendsData?.trends.map((trend, index) => (
                  <tr key={index}>
                    <td className="border-b border-gray-200 p-1.5 align-top">
                      {trend.term}
                    </td>
                    <td className="border-b border-gray-200 p-1.5 align-top">
                      {trend.volume}
                    </td>
                    <td className="border-b border-gray-200 p-1.5 align-top">
                      {trend.tone}
                    </td>
                    <td className="border-b border-gray-200 p-1.5 align-top">
                      {new Date(trend.last_seen).toISOString().slice(0,19)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card border border-gray-300 rounded-xl p-3 flex-1 min-w-80">
            <h3>Alerts</h3>
            <div className="text-gray-500 text-sm">
              {alertsData ? `${alertsData.count} alerts` : 'Loading...'}
            </div>
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  <th className="border-b border-gray-200 p-1.5 align-top">When</th>
                  <th className="border-b border-gray-200 p-1.5 align-top">Trend</th>
                  <th className="border-b border-gray-200 p-1.5 align-top">Bucket</th>
                  <th className="border-b border-gray-200 p-1.5 align-top">Δ</th>
                </tr>
              </thead>
              <tbody>
                {alertsData?.alerts.map((alert, index) => (
                  <tr 
                    key={index}
                    onClick={() => setSelectedAlert(alert)}
                    className="cursor-pointer hover:bg-gray-50"
                  >
                    <td className="border-b border-gray-200 p-1.5 align-top">
                      {new Date(alert.created_at).toISOString().slice(0,19)}
                    </td>
                    <td className="border-b border-gray-200 p-1.5 align-top">
                      {alert.trend_term}
                    </td>
                    <td className="border-b border-gray-200 p-1.5 align-top">
                      <Pill bucket={alert.old_bucket || "low"} /> → <Pill bucket={alert.new_bucket || "low"} />
                    </td>
                    <td className="border-b border-gray-200 p-1.5 align-top">
                      {alert.risk_delta ?? ""}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <pre className="whitespace-pre-wrap break-words text-xs bg-gray-50 p-2.5 rounded-lg my-2.5 mx-0">
              {selectedAlert ? JSON.stringify(selectedAlert, null, 2) : '(select an alert)'}
            </pre>
          </div>
        </div>
      </div>
    </QueryClientProvider>
  )
}

export default App
