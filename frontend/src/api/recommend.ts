/**
 * Recommendation API client for product recommendations.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface RecommendResult {
  product_id: string;
  score: number;
  reason?: string;
}

/**
 * Get product recommendations for a user.
 */
export async function getRecommendations(
  userId: string,
  k: number = 10
): Promise<RecommendResult[]> {
  const params = new URLSearchParams({
    k: k.toString(),
  });

  const response = await fetch(`${API_BASE_URL}/recommend/${userId}?${params.toString()}`);

  if (!response.ok) {
    throw new Error(`Recommendations failed: ${response.statusText}`);
  }

  return response.json();
}

