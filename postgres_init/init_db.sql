CREATE TABLE IF NOT EXISTS inventory_items (
    item_id VARCHAR(255) PRIMARY KEY,
    stock_count INTEGER NOT NULL CHECK (stock_count >= 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   IF TG_OP = 'UPDATE' THEN
       NEW.updated_at = NOW();
   END IF;
   RETURN NEW;
END;
$$ language 'plpgsql';


DROP TRIGGER IF EXISTS update_inventory_items_updated_at ON inventory_items;

CREATE TRIGGER update_inventory_items_updated_at
BEFORE UPDATE ON inventory_items
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

INSERT INTO inventory_items (item_id, stock_count) VALUES
    ('sushi-set', 10),
    ('pho-bo', 20),
    ('pizza-pepperoni', 5),
    ('burger-classic', 15),
    ('fries-large', 30),
    ('item-zero-stock', 0)
ON CONFLICT (item_id) DO UPDATE SET
    stock_count = EXCLUDED.stock_count
    WHERE inventory_items.stock_count IS DISTINCT FROM EXCLUDED.stock_count;
