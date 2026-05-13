import { useQuery } from '@tanstack/react-query';

interface Trend {
  term: string;
  volume: number;
  tone: string;
  last_seen: string;
}

interface TrendsResponse {
  count: number;
  trends: Trend[];
}

async function fetchTrends(): Promise<TrendsResponse> {
  const response = await fetch('/trends/current?limit=30');
  if (!response.ok) {
    throw new Error('Failed to fetch trends');
  }
  return response.json();
}

export function useTrends() {
  return useQuery<TrendsResponse>({
    queryKey: ['trends'],
    queryFn: fetchTrends,
  });
}
