/**
 * Search API client for product search.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface SearchResult {
  product_id: string;
  score: number;
  reason?: string;
}

export interface SearchParams {
  q: string;
  user_id?: string;
  k?: number;
}

/**
 * Search for products.
 */
export async function searchProducts(
  query: string,
  userId?: string,
  k: number = 10
): Promise<SearchResult[]> {
  const params = new URLSearchParams({
    q: query,
    k: k.toString(),
  });

  if (userId) {
    params.append('user_id', userId);
  }

  const response = await fetch(`${API_BASE_URL}/search?${params.toString()}`);

  if (!response.ok) {
    throw new Error(`Search failed: ${response.statusText}`);
  }

  return response.json();
}

