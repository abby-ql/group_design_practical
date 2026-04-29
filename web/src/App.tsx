import { useState } from "react";
import { Pill } from "./ui";
import { useItems, useTrends, useAlerts } from "./hooks";
import { Table } from "./components";
import { WhyFlaggedSection } from "./components/WhyFlaggedSection";
import { formatLastSeen, formatFullDate } from "./utils";
import "./index.css";
import type { Item } from "./hooks/useItems";
import { RefreshCw } from "lucide-react";

interface Alert {
  created_at: string;
  trend_term: string;
  old_bucket?: string;
  new_bucket?: string;
  risk_delta?: number;
  bucket_change: string; // Custom field for bucket changes
}

function App() {
  const [selectedItem, setSelectedItem] = useState<Item | null>(null);
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [status, setStatus] = useState<string>("");
  const [activeTab, setActiveTab] = useState<string>("items");
  const [uploadData, setUploadData] = useState<Array<{time: string, text: string, platform: string}>>([]);

  const { data: itemsData, refetch: refetchItems } = useItems();
  const { data: trendsData, refetch: refetchTrends } = useTrends();
  const { data: alertsData, refetch: refetchAlerts } = useAlerts();

  const refreshAll = async () => {
    setStatus("Refreshing…");
    try {
      await refetchItems();
      await refetchTrends();
      await refetchAlerts();
      setStatus("Ready.");
    } catch (e: unknown) {
      setStatus("Error: " + (e as Error).message);
    }
  };

  const addNewItem = () => {
    const newItem = {
      time: new Date().toISOString().slice(0, 16), // Format: YYYY-MM-DDTHH:mm
      text: "",
      platform: "twitter"
    };
    setUploadData([...uploadData, newItem]);
  };

  const handleUploadCSV = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      const lines = text.split('\n');
      
      // Skip header and parse data
      const newData = lines.slice(1)
        .filter(line => line.trim())
        .map(line => {
          const values = line.split(',');
          return {
            time: values[0]?.trim() || new Date().toISOString().slice(0, 16),
            text: values[1]?.trim() || "",
            platform: values[2]?.trim() || "twitter"
          };
        });
      
      setUploadData(newData);
      setStatus(`Loaded ${newData.length} items from CSV`);
    };
    reader.readAsText(file);
  };

  const updateUploadItem = (index: number, field: 'time' | 'text' | 'platform', value: string) => {
    const updatedData = [...uploadData];
    updatedData[index] = { ...updatedData[index], [field]: value };
    setUploadData(updatedData);
  };

  const deleteUploadItem = (index: number) => {
    setUploadData(uploadData.filter((_, i) => i !== index));
  };

  return (
    <div className="font-sans m-5">
      <h1 className="mb-1.5 text-2xl font-bold">Trend‑aware Risk Signals</h1>
      <div className="flex flex-row gap-4 justify-between">
        <nav className="flex gap-4">
          <button
            onClick={() => setActiveTab("items")}
            className={`
                py-2 px-1 border-b-2 font-medium text-sm transition-colors
                ${
                  activeTab === "items"
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                }
              `}
          >
            Items
          </button>
          <button
            onClick={() => setActiveTab("trends-alerts")}
            className={`
                py-2 px-1 border-b-2 font-medium text-sm transition-colors
                ${
                  activeTab === "trends-alerts"
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                }
              `}
          >
            Trends & Alerts
          </button>
          <button
            onClick={() => setActiveTab("upload")}
            className={`
                py-2 px-1 border-b-2 font-medium text-sm transition-colors
                ${
                  activeTab === "upload"
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                }
              `}
          >
            Upload Data
          </button>
        </nav>
        <div className="flex flex-row gap-2 items-center">
          <span className="text-gray-500 text-sm">{status}</span>
          <button
            onClick={refreshAll}
            className="px-3 py-2 rounded-lg border border-gray-300 bg-white hover:bg-gray-50 cursor-pointer"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Tab Navigation */}

      {/* Tab Content */}
      <div className="mt-4">
        {activeTab === "items" && (
          <div className="row flex gap-4 flex-wrap">
            <div className="card border border-gray-300 rounded-xl p-3 flex-1 min-w-80 max-h-screen overflow-y-scroll">
              <h3>Items</h3>
              <div className="text-gray-500 text-sm">
                {itemsData ? `${itemsData.count} items shown` : "Loading..."}
              </div>
              <Table
                data={itemsData?.items || []}
                columns={[
                  {
                    key: "created_at",
                    label: "Created",
                    render: (value) => (
                      <div title={formatFullDate(value as string)}>
                        {formatLastSeen(value as string)}
                      </div>
                    ),
                    sortable: true,
                  },
                  {
                    key: "text",
                    label: "Text",
                    sortable: true,
                  },
                ]}
                onRowClick={setSelectedItem}
              />
            </div>

            <WhyFlaggedSection selectedItem={selectedItem} />
          </div>
        )}

        {activeTab === "trends-alerts" && (
          <div className="row flex gap-4 flex-wrap">
            <div className="card border border-gray-300 rounded-xl p-3 flex-1 min-w-80">
              <h3>UK trends (current)</h3>
              <div className="text-gray-500 text-sm">
                {trendsData ? `${trendsData.count} trends` : "Loading..."}
              </div>
              <Table
                data={trendsData?.trends || []}
                columns={[
                  {
                    key: "term",
                    label: "Term",
                    sortable: false,
                  },
                  {
                    key: "volume",
                    label: "Vol",
                    sortable: true,
                  },
                  {
                    key: "tone",
                    label: "Tone",
                    sortable: true,
                  },
                  {
                    key: "last_seen",
                    label: "Last seen",
                    render: (value) => (
                      <div title={formatFullDate(value as string)}>
                        {formatLastSeen(value as string)}
                      </div>
                    ),
                    sortable: true,
                  },
                ]}
              />
            </div>

            <div className="card border border-gray-300 rounded-xl p-3 flex-1 min-w-80">
              <h3>Alerts</h3>
              <div className="text-gray-500 text-sm">
                {alertsData ? `${alertsData.count} alerts` : "Loading..."}
              </div>
              <Table
                data={alertsData?.alerts || []}
                columns={[
                  {
                    key: "created_at",
                    label: "When",
                    render: (value) =>
                      new Date(value as string).toISOString().slice(0, 19),
                    sortable: true,
                  },
                  {
                    key: "trend_term",
                    label: "Trend",
                    sortable: true,
                  },
                  {
                    key: "bucket_change",
                    label: "Bucket",
                    render: (_value: unknown, item: Alert) => (
                      <>
                        <Pill bucket={item.old_bucket || "low"} /> →{" "}
                        <Pill bucket={item.new_bucket || "low"} />
                      </>
                    ),
                    sortable: false,
                  },
                  {
                    key: "risk_delta",
                    label: "Δ",
                    sortable: true,
                  },
                ]}
                onRowClick={setSelectedAlert}
              />
              <pre className="whitespace-pre-wrap wrap-break-word text-xs bg-gray-50 p-2.5 rounded-lg my-2.5 mx-0">
                {selectedAlert
                  ? JSON.stringify(selectedAlert, null, 2)
                  : "(select an alert)"}
              </pre>
            </div>
          </div>
        )}

        {activeTab === "upload" && (
          <div className="card border border-gray-300 rounded-xl p-6 flex-1 min-w-80">
            <h3>Upload Data</h3>
            <div className="text-gray-500 text-sm mb-4">
              Add items manually or upload a CSV file with columns: time, text, platform
            </div>
            
            {/* Upload Table */}
            <div className="mb-4">
              {uploadData.length > 0 ? (
                <div className="border border-gray-200 rounded-lg overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 border-b border-gray-200">
                      <tr>
                        <th className="px-3 py-2 text-left font-medium text-gray-700">Time</th>
                        <th className="px-3 py-2 text-left font-medium text-gray-700">Text</th>
                        <th className="px-3 py-2 text-left font-medium text-gray-700">Platform</th>
                        <th className="px-3 py-2 text-left font-medium text-gray-700">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {uploadData.map((item, index) => (
                        <tr key={index} className="border-b border-gray-100 hover:bg-gray-50">
                          <td className="px-3 py-2">
                            <input
                              type="datetime-local"
                              value={item.time}
                              onChange={(e) => updateUploadItem(index, 'time', e.target.value)}
                              className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                            />
                          </td>
                          <td className="px-3 py-2">
                            <input
                              type="text"
                              value={item.text}
                              onChange={(e) => updateUploadItem(index, 'text', e.target.value)}
                              placeholder="Enter text content..."
                              className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                            />
                          </td>
                          <td className="px-3 py-2">
                            <select
                              value={item.platform}
                              onChange={(e) => updateUploadItem(index, 'platform', e.target.value)}
                              className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                            >
                              <option value="twitter">Twitter</option>
                              <option value="reddit">Reddit</option>
                              <option value="linkedin">LinkedIn</option>
                              <option value="blog">Blog</option>
                              <option value="forum">Forum</option>
                              <option value="other">Other</option>
                            </select>
                          </td>
                          <td className="px-3 py-2">
                            <button
                              onClick={() => deleteUploadItem(index)}
                              className="px-2 py-1 text-red-600 hover:bg-red-50 border border-red-300 rounded text-sm"
                            >
                              Delete
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-400 border-2 border-dashed border-gray-300 rounded-lg">
                  <div className="text-4xl mb-2">�</div>
                  <p className="text-sm">No items yet. Add items manually or upload a CSV file.</p>
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3 justify-between items-center">
              <div className="flex gap-3">
                <button
                  onClick={addNewItem}
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm font-medium"
                >
                  Add Item
                </button>
                
                <label className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 text-sm font-medium cursor-pointer">
                  Upload CSV
                  <input
                    type="file"
                    accept=".csv"
                    onChange={handleUploadCSV}
                    className="hidden"
                  />
                </label>
              </div>
              
              {uploadData.length > 0 && (
                <div className="text-sm text-gray-600">
                  {uploadData.length} item{uploadData.length !== 1 ? 's' : ''} ready
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
