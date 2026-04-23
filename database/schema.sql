-- MDVRP Database Schema for PostgreSQL
-- Run this in your PostgreSQL database to create all tables

-- Core data tables (used by MDVRP solver)

CREATE TABLE nodes (
    node_id VARCHAR(50) PRIMARY KEY,
    dataset_id INTEGER NOT NULL,
    x DOUBLE PRECISION NOT NULL,
    y DOUBLE PRECISION NOT NULL
);

CREATE TABLE depots (
    depot_id VARCHAR(50) PRIMARY KEY,
    node_id VARCHAR(50) NOT NULL,
    dataset_id INTEGER NOT NULL,
    FOREIGN KEY (node_id) REFERENCES nodes(node_id)
);

CREATE TABLE customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    node_id VARCHAR(50) NOT NULL,
    dataset_id INTEGER NOT NULL,
    deadline_hours INTEGER NOT NULL,
    FOREIGN KEY (node_id) REFERENCES nodes(node_id)
);

CREATE TABLE vehicles (
    vehicle_id VARCHAR(50) PRIMARY KEY,
    depot_id VARCHAR(50) NOT NULL,
    dataset_id INTEGER NOT NULL,
    vehicle_type VARCHAR(50) NOT NULL,
    capacity_kg NUMERIC(8,2) NOT NULL,
    max_operational_hrs NUMERIC(8,2) NOT NULL,
    speed_kmh NUMERIC(8,2) NOT NULL,
    FOREIGN KEY (depot_id) REFERENCES depots(depot_id)
);

CREATE TABLE items (
    item_id VARCHAR(50) PRIMARY KEY,
    dataset_id INTEGER NOT NULL,
    weight_kg NUMERIC(8,2) NOT NULL,
    expiry_hours INTEGER NOT NULL
);

CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL,
    item_id VARCHAR(50) NOT NULL,
    dataset_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (item_id) REFERENCES items(item_id)
);

-- Webapp tables (not used by solver, but needed for webapp)

CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

CREATE TABLE sessions (
    session_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE datasets (
    dataset_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_id INTEGER,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

-- Add foreign key to core tables (need datasets table first)
ALTER TABLE nodes ADD CONSTRAINT fk_nodes_dataset FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id);
ALTER TABLE depots ADD CONSTRAINT fk_depots_dataset FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id);
ALTER TABLE customers ADD CONSTRAINT fk_customers_dataset FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id);
ALTER TABLE vehicles ADD CONSTRAINT fk_vehicles_dataset FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id);
ALTER TABLE items ADD CONSTRAINT fk_items_dataset FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id);
ALTER TABLE orders ADD CONSTRAINT fk_orders_dataset FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id);

-- Experiment tracking tables

CREATE TABLE experiments (
    experiment_id SERIAL PRIMARY KEY,
    dataset_id INTEGER NOT NULL,
    algorithm VARCHAR(100) NOT NULL,
    population_size INTEGER,
    mutation_rate DOUBLE PRECISION,
    crossover_rate DOUBLE PRECISION,
    seed INTEGER,
    FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id)
);

CREATE TABLE result_metrics (
    result_id SERIAL PRIMARY KEY,
    experiment_id INTEGER NOT NULL,
    runtime_id NUMERIC(8,2),
    constraint_violation INTEGER,
    FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
);

CREATE TABLE routes (
    route_id SERIAL PRIMARY KEY,
    experiment_id INTEGER NOT NULL,
    vehicle_id VARCHAR(50) NOT NULL,
    node_start_id VARCHAR(50) NOT NULL,
    node_end_id VARCHAR(50) NOT NULL,
    total_distance NUMERIC(8,2),
    FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id),
    FOREIGN KEY (node_start_id) REFERENCES nodes(node_id),
    FOREIGN KEY (node_end_id) REFERENCES nodes(node_id)
);

-- Optional: Pre-computed distances (not used in initial implementation)
CREATE TABLE node_distances (
    distance_id SERIAL PRIMARY KEY,
    node_start_id VARCHAR(50) NOT NULL,
    node_end_id VARCHAR(50) NOT NULL,
    dataset_id INTEGER NOT NULL,
    distance NUMERIC(8,2),
    travel_time NUMERIC(8,2),
    FOREIGN KEY (node_start_id) REFERENCES nodes(node_id),
    FOREIGN KEY (node_end_id) REFERENCES nodes(node_id),
    FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id)
);

-- Indexes for performance
CREATE INDEX idx_nodes_dataset ON nodes(dataset_id);
CREATE INDEX idx_depots_dataset ON depots(dataset_id);
CREATE INDEX idx_depots_node ON depots(node_id);
CREATE INDEX idx_customers_dataset ON customers(dataset_id);
CREATE INDEX idx_customers_node ON customers(node_id);
CREATE INDEX idx_vehicles_dataset ON vehicles(dataset_id);
CREATE INDEX idx_vehicles_depot ON vehicles(depot_id);
CREATE INDEX idx_items_dataset ON items(dataset_id);
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_dataset ON orders(dataset_id);
CREATE INDEX idx_experiments_dataset ON experiments(dataset_id);
CREATE INDEX idx_result_metrics_experiment ON result_metrics(experiment_id);
CREATE INDEX idx_routes_experiment ON routes(experiment_id);
CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_token ON sessions(session_token);
CREATE INDEX idx_datasets_user ON datasets(user_id);
