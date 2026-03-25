import { useQuery } from '@tanstack/react-query';

interface Alert {
  created_at: string;
  trend_term: string;
  old_bucket?: string;
  new_bucket?: string;
  risk_delta?: number;
}

interface AlertsResponse {
  count: number;
  alerts: Alert[];
}

async function fetchAlerts(): Promise<AlertsResponse> {
  const response = await fetch('/alerts?limit=50');
  if (!response.ok) {
    throw new Error('Failed to fetch alerts');
  }
  return response.json();
}

export function useAlerts() {
  return useQuery<AlertsResponse>({
    queryKey: ['alerts'],
    queryFn: fetchAlerts,
  });
}
