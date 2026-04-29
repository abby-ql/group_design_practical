import { SocialMediaIcon } from './SocialMediaIcon';
import { RadarChart } from './RadarChart';

interface WhyFlaggedSectionProps {
  selectedItem: any;
}

export function WhyFlaggedSection({ selectedItem }: WhyFlaggedSectionProps) {
  if (!selectedItem) {
    return (
      <div className="card border border-gray-300 rounded-xl p-3 flex-1 min-w-80">
        <h3 className="text-sm font-medium text-gray-900 mb-2">Why flagged?</h3>
        <div className="text-gray-500 text-sm">
          Click an item row to inspect its reasons + score decomposition.
        </div>
      </div>
    );
  }

  const reasons = selectedItem?.risk?.reasons || [];
  const decomposition = selectedItem?.risk?.decomposition || [];
  
  // Extract platforms and trend terms from the data
  const platforms = selectedItem?.platform || 'unknown';
  
  // Group reasons by type for better organization
  const groupedReasons = reasons.reduce((acc: any, reason: any) => {
    const type = reason.signal || 'unknown';
    if (!acc[type]) acc[type] = [];
    acc[type].push(reason);
    return acc;
  }, {});

  return (
    <div className="card border border-gray-300 rounded-xl p-3 flex-1 min-w-80">
      <h3 className="text-sm font-medium text-gray-900 mb-3">Why flagged?</h3>
      
      {/* Platform Information */}
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-medium text-gray-600">Source:</span>
          <div className="flex items-center gap-1">
            <SocialMediaIcon 
              platform={platforms} 
              size={14} 
              className="text-gray-600"
            />
            <span className="text-xs text-gray-700 capitalize">{platforms}</span>
          </div>
        </div>
      </div>

      {/* Risk Score Summary */}
      {selectedItem?.risk && (
        <div className="mb-4 p-2 bg-gray-50 rounded-lg">
          <div className="flex justify-between items-center mb-1">
            <span className="text-xs font-medium text-gray-600">Risk Score:</span>
            <span className={`text-xs font-bold px-2 py-1 rounded ${
              selectedItem.risk.bucket === 'critical' ? 'bg-red-100 text-red-800' :
              selectedItem.risk.bucket === 'high' ? 'bg-orange-100 text-orange-800' :
              selectedItem.risk.bucket === 'medium' ? 'bg-yellow-100 text-yellow-800' :
              'bg-green-100 text-green-800'
            }`}>
              {selectedItem.risk.total_score.toFixed(1)} ({selectedItem.risk.bucket})
            </span>
          </div>
        </div>
      )}

      {/* Flag Reasons */}
      {reasons.length > 0 && (
        <div className="mb-4">
          <h4 className="text-xs font-medium text-gray-700 mb-2">Flag Reasons:</h4>
          <div className="space-y-2">
            {Object.entries(groupedReasons).map(([signalType, signalReasons]: [string, any]) => (
              <div key={signalType} className="p-2 bg-blue-50 rounded border border-blue-200">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium text-blue-900 capitalize">
                    {signalType.replace('_', ' ')}
                  </span>
                  <span className="text-xs text-blue-700">
                    +{signalReasons.reduce((sum: number, r: any) => sum + (r.contribution || 0), 0).toFixed(1)}
                  </span>
                </div>
                
                {/* Show trend terms if available */}
                {signalReasons.some((r: any) => r.trend_term) && (
                  <div className="mt-1">
                    <div className="flex flex-wrap gap-1">
                      {signalReasons
                        .filter((r: any) => r.trend_term)
                        .map((r: any, idx: number) => (
                          <span 
                            key={idx}
                            className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded"
                          >
                            {r.trend_term}
                          </span>
                        ))}
                    </div>
                  </div>
                )}

                {/* Show overlapping trends if available */}
                {signalReasons.some((r: any) => r.overlaps) && (
                  <div className="mt-1">
                    <div className="text-xs text-gray-600">
                      Overlapping trends:
                    </div>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {signalReasons
                        .flatMap((r: any) => r.overlaps || [])
                        .map((overlap: any, idx: number) => (
                          <div key={idx} className="flex items-center gap-1">
                            {overlap.source && (
                              <SocialMediaIcon 
                                platform={overlap.source} 
                                size={10} 
                                className="text-gray-500"
                              />
                            )}
                            <span className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded">
                              {overlap.term}
                            </span>
                          </div>
                        ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Radar Chart */}
      {decomposition.length > 0 && (
        <div className="mt-4">
          <h4 className="text-xs font-medium text-gray-700 mb-2">Score Breakdown:</h4>
          <div className="text-xs text-gray-500 mb-3">
            Contribution of each signal to the total risk score
          </div>
          <RadarChart 
            data={decomposition} 
            title=""
          />
        </div>
      )}
    </div>
  );
}
