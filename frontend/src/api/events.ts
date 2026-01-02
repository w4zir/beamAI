/**
 * Event tracking API client.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export type EventType = 'view' | 'add_to_cart' | 'purchase';
export type EventSource = 'search' | 'recommendation' | 'direct';

export interface TrackEventParams {
  userId: string;
  productId: string;
  eventType: EventType;
  source?: EventSource;
}

/**
 * Track a user interaction event.
 */
export async function trackEvent(params: TrackEventParams): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/events`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      user_id: params.userId,
      product_id: params.productId,
      event_type: params.eventType,
      source: params.source,
    }),
  });

  if (!response.ok) {
    // Don't throw - event tracking failures shouldn't break the UI
    console.error('Failed to track event:', await response.text());
  }
}

