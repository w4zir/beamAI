-- Create products table
CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    price NUMERIC(10, 2),
    popularity_score FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create events table (append-only)
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('view', 'add_to_cart', 'purchase')),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source TEXT CHECK (source IN ('search', 'recommendation', 'direct'))
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_events_user_id ON events(user_id);
CREATE INDEX IF NOT EXISTS idx_events_product_id ON events(product_id);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_popularity ON products(popularity_score DESC);

-- Add foreign key constraints (optional, for data integrity)
-- Note: These are commented out initially to allow flexible data loading
-- ALTER TABLE events ADD CONSTRAINT fk_events_user_id FOREIGN KEY (user_id) REFERENCES users(id);
-- ALTER TABLE events ADD CONSTRAINT fk_events_product_id FOREIGN KEY (product_id) REFERENCES products(id);

