-- Populate MDVRP Database with Data Matching CSV Files
-- This script inserts data EXACTLY matching the CSV files in data/
--
-- Usage:
--   psql -U postgres -d mdvrp_new -f database/populate_data_from_csv.sql

BEGIN;

-- Insert test user (required by datasets foreign key)
INSERT INTO users (user_id, email, password, created_at)
VALUES (1, 'test@example.com', 'hashed_password_here', CURRENT_TIMESTAMP)
ON CONFLICT (user_id) DO NOTHING;

-- Insert dataset
INSERT INTO datasets (dataset_id, user_id, name, created_at)
VALUES (1, 1, 'Sample MDVRP Dataset', CURRENT_TIMESTAMP)
ON CONFLICT (dataset_id) DO NOTHING;

-- Clear existing data for dataset_id=1
DELETE FROM orders WHERE dataset_id = 1;
DELETE FROM items WHERE dataset_id = 1;
DELETE FROM vehicles WHERE dataset_id = 1;
DELETE FROM customers WHERE dataset_id = 1;
DELETE FROM depots WHERE dataset_id = 1;
DELETE FROM nodes WHERE dataset_id = 1;

-- Insert nodes (coordinates for depots and customers) - EXACTLY FROM CSV
INSERT INTO nodes (node_id, dataset_id, x, y) VALUES
    -- Depots (from data/depots.csv)
    ('D1', 1, -6.104563, 106.940091),
    ('D2', 1, -6.276544, 106.821847),
    -- Customers (from data/customers.csv)
    ('C1', 1, -6.224176, 106.80089),
    ('C2', 1, -6.13793, 106.780949),
    ('C3', 1, -6.350793, 107.193915),
    ('C4', 1, -6.152645, 106.781724),
    ('C5', 1, -6.137156, 106.781724),
    ('C6', 1, -6.208763, 106.845667),
    ('C7', 1, -6.175392, 106.827153),
    ('C8', 1, -6.283756, 106.813567)
ON CONFLICT (node_id) DO NOTHING;

-- Insert depots (reference nodes)
INSERT INTO depots (depot_id, node_id, dataset_id) VALUES
    ('D1', 'D1', 1),
    ('D2', 'D2', 1)
ON CONFLICT (depot_id) DO NOTHING;

-- Insert customers (reference nodes with deadlines) - EXACTLY FROM CSV
INSERT INTO customers (customer_id, node_id, dataset_id, deadline_hours) VALUES
    ('C1', 'C1', 1, 8),
    ('C2', 'C2', 1, 8),
    ('C3', 'C3', 1, 8),
    ('C4', 'C4', 1, 8),
    ('C5', 'C5', 1, 8),
    ('C6', 'C6', 1, 8),
    ('C7', 'C7', 1, 8),
    ('C8', 'C8', 1, 8)
ON CONFLICT (customer_id) DO NOTHING;

-- Insert vehicles - EXACTLY FROM CSV
INSERT INTO vehicles (vehicle_id, depot_id, dataset_id, vehicle_type, capacity_kg, max_operational_hrs, speed_kmh) VALUES
    ('V1', 'D1', 1, 'truck', 60, 10, 40),
    ('V2', 'D2', 1, 'truck', 60, 10, 40),
    ('V3', 'D1', 1, 'van', 50, 10, 40)
ON CONFLICT (vehicle_id) DO NOTHING;

-- Insert items - EXACTLY FROM CSV
INSERT INTO items (item_id, dataset_id, weight_kg, expiry_hours) VALUES
    ('I1', 1, 6.41, 100),
    ('I2', 1, 7.16, 100)
ON CONFLICT (item_id) DO NOTHING;

-- Insert orders - EXACTLY FROM CSV
INSERT INTO orders (customer_id, item_id, dataset_id, quantity) VALUES
    ('C1', 'I1', 1, 1),
    ('C1', 'I2', 1, 2),
    ('C2', 'I1', 1, 2),
    ('C2', 'I2', 1, 1),
    ('C3', 'I1', 1, 1),
    ('C3', 'I2', 1, 1),
    ('C4', 'I1', 1, 2),
    ('C4', 'I2', 1, 1),
    ('C5', 'I1', 1, 1),
    ('C5', 'I2', 1, 1),
    ('C6', 'I1', 1, 2),
    ('C6', 'I2', 1, 2),
    ('C7', 'I1', 1, 1),
    ('C7', 'I2', 1, 2),
    ('C8', 'I1', 1, 1),
    ('C8', 'I2', 1, 1)
ON CONFLICT DO NOTHING;

COMMIT;

-- Verification queries (run these to check the data)
-- SELECT * FROM datasets;
-- SELECT * FROM nodes ORDER BY node_id;
-- SELECT * FROM depots;
-- SELECT * FROM customers;
-- SELECT * FROM vehicles;
-- SELECT * FROM items;
-- SELECT * FROM orders ORDER BY customer_id, item_id;
