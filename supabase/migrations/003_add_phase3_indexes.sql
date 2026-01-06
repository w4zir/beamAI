-- Phase 3.4: Additional database indexes for query optimization
-- Per DATABASE_OPTIMIZATION.md

-- Composite index for user-product queries (common in recommendations and CF)
CREATE INDEX IF NOT EXISTS idx_events_user_product ON events(user_id, product_id);

-- Composite index for user events with timestamp (for time-decayed features)
CREATE INDEX IF NOT EXISTS idx_events_user_timestamp ON events(user_id, timestamp DESC);

-- Composite index for product events with timestamp (for popularity computation)
CREATE INDEX IF NOT EXISTS idx_events_product_timestamp ON events(product_id, timestamp DESC);

-- Composite index for user events by type and timestamp (for filtering)
CREATE INDEX IF NOT EXISTS idx_events_user_type_timestamp ON events(user_id, event_type, timestamp DESC);

-- Index on products.id for faster lookups (if not already primary key index)
-- Note: Primary key already creates an index, but this ensures it exists
-- CREATE INDEX IF NOT EXISTS idx_products_id ON products(id);  -- Not needed, PK already indexed

-- Analyze tables to update statistics (helps query planner)
ANALYZE products;
ANALYZE events;
ANALYZE users;

