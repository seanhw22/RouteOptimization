-- Populate MDVRP Database with Sample Data
-- This script inserts data from CSV files into the normalized database schema
--
-- Usage:
--   psql -U mdvrp -d mdvrp -f database/populate_data.sql

BEGIN;

-- Insert test user (required by datasets foreign key)
INSERT INTO users (user_id, email, password, created_at)
VALUES (1, 'test@example.com', 'hashed_password_here', CURRENT_TIMESTAMP)
ON CONFLICT (user_id) DO NOTHING;

-- Insert dataset
INSERT INTO datasets (dataset_id, user_id, name, created_at)
VALUES (1, 1, 'Sample MDVRP Dataset', CURRENT_TIMESTAMP)
ON CONFLICT (dataset_id) DO NOTHING;

-- Insert nodes (coordinates for depots and customers)
INSERT INTO nodes (node_id, dataset_id, x, y) VALUES
    -- Depots
    ('D1', 1, -6.104563, 106.940091),
    ('D2', 1, -6.276544, 106.821847),
    -- Customers
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

-- Insert customers (reference nodes with deadlines)
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

-- Insert vehicles
INSERT INTO vehicles (vehicle_id, depot_id, dataset_id, vehicle_type, capacity_kg, max_operational_hrs, speed_kmh) VALUES
    ('V1', 'D1', 1, 'truck', 60, 10, 40),
    ('V2', 'D2', 1, 'truck', 60, 10, 40),
    ('V3', 'D1', 1, 'van', 50, 10, 40)
ON CONFLICT (vehicle_id) DO NOTHING;

-- Insert items
INSERT INTO items (item_id, dataset_id, weight_kg, expiry_hours) VALUES
    ('I1', 1, 5.0, 24),
    ('I2', 1, 3.0, 48)
ON CONFLICT (item_id) DO NOTHING;

-- Insert orders
INSERT INTO orders (customer_id, item_id, dataset_id, quantity) VALUES
    ('C1', 'I1', 1, 10),
    ('C1', 'I2', 1, 5),
    ('C2', 'I1', 1, 8),
    ('C2', 'I2', 1, 3),
    ('C3', 'I1', 1, 15),
    ('C3', 'I2', 1, 7),
    ('C4', 'I1', 1, 12),
    ('C4', 'I2', 1, 4),
    ('C5', 'I1', 1, 9),
    ('C5', 'I2', 1, 6),
    ('C6', 'I1', 1, 11),
    ('C6', 'I2', 1, 5),
    ('C7', 'I1', 1, 13),
    ('C7', 'I2', 1, 8),
    ('C8', 'I1', 1, 14),
    ('C8', 'I2', 1, 9)
ON CONFLICT DO NOTHING;

COMMIT;

-- Verification queries (run these to check the data)
-- SELECT * FROM datasets;
-- SELECT * FROM nodes ORDER BY node_id;
-- SELECT * FROM depots;
-- SELECT * FROM customers;
-- SELECT * FROM vehicles;
-- SELECT * FROM items;
-- SELECT * FROM orders;
