import { useState } from 'react'
import { Pill } from './ui'
import { useItems, useTrends, useAlerts } from './hooks'
import { Table, RadarChart } from './components'
import { formatLastSeen, formatFullDate } from './utils'
import './index.css'
import type { Item } from './hooks/useItems'

interface Alert {
  created_at: string;
  trend_term: string;
  old_bucket?: string;
  new_bucket?: string;
  risk_delta?: number;
  bucket_change: string; // Custom field for bucket changes
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
            <Table
              data={itemsData?.items || []}
              columns={[
                {
                  key: 'created_at',
                  label: 'When',
                  render: (value) => new Date(value as string).toISOString().slice(0, 10),
                  sortable: true
                },
                {
                  key: 'risk',
                  label: 'Risk',
                  render: (_value: unknown, item: Item) => {
                    const risk = item.risk;
                    return (
                      <>
                        <Pill bucket={risk.bucket} />
                        <span className="text-gray-500 text-sm">
                          ({risk.total_score})
                        </span>
                      </>
                    );
                  },
                  sortable: (item: Item) => item.risk.total_score 
                },
                {
                  key: 'text',
                  label: 'Text',
                  sortable: true
                }
              ]}
              onRowClick={setSelectedItem}
            />
          </div>

          <div className="card border border-gray-300 rounded-xl p-3 flex-1 min-w-80">
            <h3>Why flagged?</h3>
            <div className="text-gray-500 text-sm">
              Click an item row to inspect its reasons + score decomposition.
            </div>
            <pre className="whitespace-pre-wrap wrap-break-word text-xs bg-gray-50 p-2.5 rounded-lg my-0">
              {selectedItem ? JSON.stringify(selectedItem, null, 2) : '(select an item)'}
            </pre>
            <RadarChart 
              data={selectedItem?.risk?.decomposition} 
              title="Risk Score Breakdown"
            />
          </div>
        </div>

        <div className="row flex gap-4 flex-wrap mt-4">
          <div className="card border border-gray-300 rounded-xl p-3 flex-1 min-w-80">
            <h3>UK trends (current)</h3>
            <div className="text-gray-500 text-sm">
              {trendsData ? `${trendsData.count} trends` : 'Loading...'}
            </div>
            <Table
              data={trendsData?.trends || []}
              columns={[
                {
                  key: 'term',
                  label: 'Term',
                  sortable: false
                },
                {
                  key: 'volume',
                  label: 'Vol',
                  sortable: true
                },
                {
                  key: 'tone',
                  label: 'Tone',
                  sortable: true
                },
                {
                  key: 'last_seen',
                  label: 'Last seen',
                  render: (value) => (
                    <div title={formatFullDate(value as string)}>
                      {formatLastSeen(value as string)}
                    </div>
                  ),
                  sortable: true
                }
              ]}
            />
          </div>

          <div className="card border border-gray-300 rounded-xl p-3 flex-1 min-w-80">
            <h3>Alerts</h3>
            <div className="text-gray-500 text-sm">
              {alertsData ? `${alertsData.count} alerts` : 'Loading...'}
            </div>
            <Table
              data={alertsData?.alerts || []}
              columns={[
                {
                  key: 'created_at',
                  label: 'When',
                  render: (value) => new Date(value as string).toISOString().slice(0, 19),
                  sortable: true
                },
                {
                  key: 'trend_term',
                  label: 'Trend',
                  sortable: true
                },
                {
                  key: 'bucket_change',
                  label: 'Bucket',
                  render: (_value: unknown, item: Alert) => (
                    <>
                      <Pill bucket={item.old_bucket || "low"} /> → <Pill bucket={item.new_bucket || "low"} />
                    </>
                  ),
                  sortable: false
                },
                {
                  key: 'risk_delta',
                  label: 'Δ',
                  sortable: true
                }
              ]}
              onRowClick={setSelectedAlert}
            />
            <pre className="whitespace-pre-wrap wrap-break-word text-xs bg-gray-50 p-2.5 rounded-lg my-2.5 mx-0">
              {selectedAlert ? JSON.stringify(selectedAlert, null, 2) : '(select an alert)'}
            </pre>
          </div>
        </div>
      </div>
  )
}

export default App
