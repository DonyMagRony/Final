-- File: init-db.sql

-- Connect to the target database (optional, often handled by docker-entrypoint)
-- \c food_delivery_db;

CREATE TABLE IF NOT EXISTS inventory_items (
    item_id VARCHAR(255) PRIMARY KEY,
    stock_count INTEGER NOT NULL CHECK (stock_count >= 0), -- Ensure stock doesn't go negative
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Optional: Create a trigger to automatically update the updated_at timestamp on changes
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   -- Check if the trigger function exists before creating it
   IF TG_OP = 'UPDATE' THEN
       NEW.updated_at = NOW();
   END IF;
   RETURN NEW;
END;
$$ language 'plpgsql';

-- Drop the trigger if it exists before creating it to avoid errors on re-runs
DROP TRIGGER IF EXISTS update_inventory_items_updated_at ON inventory_items;

CREATE TRIGGER update_inventory_items_updated_at
BEFORE UPDATE ON inventory_items
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Insert some sample data (adjust item_ids to match order examples if needed)
-- Use ON CONFLICT to avoid errors if the script runs again on an existing DB
INSERT INTO inventory_items (item_id, stock_count) VALUES
    ('sushi-set', 10),
    ('pho-bo', 20),
    ('pizza-pepperoni', 5),
    ('burger-classic', 15),
    ('fries-large', 30),
    ('item-zero-stock', 0) -- Add an item with zero stock for testing
ON CONFLICT (item_id) DO UPDATE SET
    -- Example: update stock count only if the new value is different (optional)
    stock_count = EXCLUDED.stock_count
    WHERE inventory_items.stock_count IS DISTINCT FROM EXCLUDED.stock_count;

-- Grant privileges if needed (docker-entrypoint often uses the POSTGRES_USER)
-- GRANT ALL PRIVILEGES ON TABLE inventory_items TO "user"; -- Replace "user" if needed