# Purpose

This document defines the canonical data model for the system. The model is designed to:

- Be compatible with the Olist e-commerce dataset for development and testing
- Remain stable when migrating to real production data
- Support search, recommendations, and analytics at scale

The Olist dataset is treated as a source dataset, not as a perfect schema. We adapt it into a clean, production-grade model.

## Canonical Tables (System-Owned)

### products

Represents sellable items in the catalog.

- `id` (TEXT, PRIMARY KEY) — mapped from `olist_products.product_id`
- `name` (TEXT) — derived from product category or enriched name
- `description` (TEXT) — optional, may be enriched or synthetic in Olist
- `category` (TEXT) — mapped from `product_category_name_english`
- `price` (NUMERIC)
- `popularity_score` (FLOAT)
- `created_at` (TIMESTAMP)

**Notes:**

- Olist does not provide rich product descriptions; placeholders or enriched text may be used for search experiments.
- Popularity score is computed offline.

### users

Represents end users (customers).

- `id` (TEXT, PRIMARY KEY) — mapped from `olist_customers.customer_unique_id`
- `created_at` (TIMESTAMP)

**Notes:**

- Olist has both `customer_id` and `customer_unique_id`; `customer_unique_id` is canonical.

### events

Represents all user–product interactions. This is the most important table.

- `user_id` (TEXT) — FK → `users.id`
- `product_id` (TEXT) — FK → `products.id`
- `event_type` (TEXT) — one of: `view`, `add_to_cart`, `purchase`
- `timestamp` (TIMESTAMP)
- `source` (TEXT) — optional (`search`, `recommendation`, `direct`)

**Rules:**

- Append-only table
- No updates
- No deletes
- This table may grow to billions of rows

### experiment_exposures

Tracks which users and products were exposed to which ranking experiments or A/B tests.

- `id` (TEXT, PRIMARY KEY)
- `user_id` (TEXT) — FK → `users.id`, nullable (for product-level experiments)
- `product_id` (TEXT) — FK → `products.id`, nullable (for user-level experiments)
- `experiment_id` (TEXT) — identifier for the experiment
- `variant` (TEXT) — which variant was shown (e.g., "control", "treatment")
- `exposed_at` (TIMESTAMP)
- `experiment_ended_at` (TIMESTAMP) — used for retention policy

**Rules:**

- Used for experiment analysis and bias detection
- Retention: 60 days after experiment ends

### user_preferences

Stores explicit or inferred user preferences for personalization.

- `user_id` (TEXT, PRIMARY KEY) — FK → `users.id`
- `preferences` (JSONB) — flexible structure for various preference types
- `updated_at` (TIMESTAMP)

**Rules:**

- One row per user
- Preferences may include category preferences, price ranges, brand preferences, etc.
- Retention: Until user deletion request

## Source Tables (Olist – Read Only)

These tables are not modified. They are ingested and transformed into canonical tables.

- `olist_orders`
- `olist_order_items`
- `olist_products`
- `olist_customers`
- `olist_order_reviews`

## Mapping Rules (Olist → Canonical)

### Purchases → events

From `olist_order_items`:

- `user_id` → `customer_unique_id`
- `product_id` → `product_id`
- `event_type` → `purchase`
- `timestamp` → `order_purchase_timestamp`

### Product Metadata

From `olist_products` + category translation:

- `product_id` → `products.id`
- `product_category_name_english` → `products.category`

## Data Retention Policy

### Hot Data (Postgres)
- events: 90 days
- experiment_exposures: 60 days after experiment ends
- user preferences: Until user deletion request

### Warm Data (S3/GCS)
- events (aggregated): 2 years
- Model training data: 1 year

### Cold Archive
- Compliance backups: 7 years
- Anonymized analytics: Indefinite

## Privacy & Deletion

### User Deletion Request
1. Remove from `users` table
2. Anonymize `user_id` in `events` → replace with hash
3. Purge from Redis cache
4. Exclude from future model training
5. Response time: 30 days

### Data Minimization
- Don't log: IP addresses, user agents, precise locations
- Do log: user_id, timestamps, product interactions

## Explicit Non-Goals

- We do NOT mirror the Olist schema directly in APIs
- We do NOT couple ML logic to raw Olist tables
- We do NOT perform joins on raw Olist tables at serving time
