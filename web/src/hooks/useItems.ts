import { useQuery } from '@tanstack/react-query';

interface Risk {
  bucket: string;
  total_score: number;
}

interface Item {
  created_at: string;
  risk: Risk;
  text: string;
}

interface ItemsResponse {
  count: number;
  items: Item[];
}

async function fetchItems(): Promise<ItemsResponse> {
  const response = await fetch('/risk/items?limit=50&include_trends=true');
  if (!response.ok) {
    throw new Error('Failed to fetch items');
  }
  return response.json();
}

export function useItems() {
  return useQuery<ItemsResponse>({
    queryKey: ['items'],
    queryFn: fetchItems,
  });
}
