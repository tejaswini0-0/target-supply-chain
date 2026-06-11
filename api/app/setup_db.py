import psycopg2
import os
import time

def setup():
    time.sleep(5)

    conn = psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        user=os.environ["POSTGRES_USER"],
        dbname=os.environ["POSTGRES_DB"],
        port=int(os.environ["POSTGRES_PORT"]),
        password=os.environ["POSTGRES_PASSWORD"],
    )
    cur = conn.cursor()

    # Suppliers table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            supplier_id VARCHAR(100) PRIMARY KEY,
            supplier_name VARCHAR(200),
            country VARCHAR(100),
            reliability_score FLOAT,
            lead_time_days INTEGER
        );
    """)

    # Warehouses table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS warehouses (
            warehouse_id VARCHAR(100) PRIMARY KEY,
            warehouse_name VARCHAR(200),
            city VARCHAR(100),
            capacity INTEGER
        );
    """)

    # Stores table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stores (
            store_id VARCHAR(100) PRIMARY KEY,
            store_name VARCHAR(200),
            city VARCHAR(100),
            region VARCHAR(100)
        );
    """)

    # Products table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id VARCHAR(100) PRIMARY KEY,
            product_name VARCHAR(200),
            category VARCHAR(100),
            unit_cost FLOAT
        );
    """)

    # Supplier-Product relationships
    cur.execute("""
        CREATE TABLE IF NOT EXISTS supplier_products (
            supplier_id VARCHAR(100),
            product_id VARCHAR(100),
            supply_volume INTEGER,
            PRIMARY KEY (supplier_id, product_id)
        );
    """)

    # Supplier-Warehouse relationships
    cur.execute("""
        CREATE TABLE IF NOT EXISTS supplier_warehouses (
            supplier_id VARCHAR(100),
            warehouse_id VARCHAR(100),
            transit_days INTEGER,
            PRIMARY KEY (supplier_id, warehouse_id)
        );
    """)

    # Warehouse-Store relationships
    cur.execute("""
        CREATE TABLE IF NOT EXISTS warehouse_stores (
            warehouse_id VARCHAR(100),
            store_id VARCHAR(100),
            transit_days INTEGER,
            PRIMARY KEY (warehouse_id, store_id)
        );
    """)

    # Supply chain events log
    cur.execute("""
        CREATE TABLE IF NOT EXISTS supply_chain_events (
            id SERIAL PRIMARY KEY,
            event_type VARCHAR(100),
            entity_type VARCHAR(100),
            entity_id VARCHAR(100),
            details JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    # Seed suppliers
    cur.execute("""
        INSERT INTO suppliers (supplier_id, supplier_name, country, reliability_score, lead_time_days)
        VALUES
            ('SUP_001', 'Pacific Rim Textiles',     'China',        0.92, 14),
            ('SUP_002', 'American Cotton Co',        'USA',          0.98,  3),
            ('SUP_003', 'TechComponents Asia',       'Taiwan',       0.89, 21),
            ('SUP_004', 'European Electronics GmbH', 'Germany',      0.95,  7),
            ('SUP_005', 'South Asian Apparel',       'Bangladesh',   0.85, 18),
            ('SUP_006', 'Global Foods Inc',          'USA',          0.97,  2),
            ('SUP_007', 'MexiPack Logistics',        'Mexico',       0.91,  5),
            ('SUP_008', 'Nordic Home Goods',         'Sweden',       0.94,  9),
            ('SUP_009', 'BrazilNuts Foods',          'Brazil',       0.88, 12),
            ('SUP_010', 'IndoPharma Supplies',       'India',        0.86, 16)
        ON CONFLICT DO NOTHING;
    """)

    # Seed warehouses
    cur.execute("""
        INSERT INTO warehouses (warehouse_id, warehouse_name, city, capacity)
        VALUES
            ('WH_001', 'Northeast Distribution Center', 'Newark',      50000),
            ('WH_002', 'Southeast Distribution Center', 'Atlanta',     45000),
            ('WH_003', 'Midwest Distribution Center',   'Chicago',     60000),
            ('WH_004', 'West Coast Distribution Center','Los Angeles',  55000),
            ('WH_005', 'Central Distribution Center',   'Dallas',      48000)
        ON CONFLICT DO NOTHING;
    """)

    # Seed stores
    cur.execute("""
        INSERT INTO stores (store_id, store_name, city, region)
        VALUES
            ('STORE_NYC', 'Target Manhattan',      'New York',      'Northeast'),
            ('STORE_BOS', 'Target Boston',         'Boston',        'Northeast'),
            ('STORE_ATL', 'Target Atlanta',        'Atlanta',       'Southeast'),
            ('STORE_MIA', 'Target Miami',          'Miami',         'Southeast'),
            ('STORE_CHI', 'Target Chicago',        'Chicago',       'Midwest'),
            ('STORE_DET', 'Target Detroit',        'Detroit',       'Midwest'),
            ('STORE_LA',  'Target Los Angeles',    'Los Angeles',   'West'),
            ('STORE_SF',  'Target San Francisco',  'San Francisco', 'West'),
            ('STORE_DAL', 'Target Dallas',         'Dallas',        'South'),
            ('STORE_HOU', 'Target Houston',        'Houston',       'South')
        ON CONFLICT DO NOTHING;
    """)

    # Seed products
    cur.execute("""
        INSERT INTO products (product_id, product_name, category, unit_cost)
        VALUES
            ('PROD_001', 'Cotton T-Shirt',        'Apparel',     4.50),
            ('PROD_002', 'Denim Jeans',           'Apparel',    12.00),
            ('PROD_003', 'Running Shoes',         'Footwear',   25.00),
            ('PROD_004', 'Wireless Headphones',   'Electronics',35.00),
            ('PROD_005', 'Laptop Stand',          'Electronics',18.00),
            ('PROD_006', 'Organic Cereal',        'Grocery',     2.50),
            ('PROD_007', 'Laundry Detergent',     'Household',   3.80),
            ('PROD_008', 'Throw Pillow',          'Home',        8.00),
            ('PROD_009', 'Vitamin C Supplement',  'Health',      6.00),
            ('PROD_010', 'Toothbrush Pack',       'Health',      1.50)
        ON CONFLICT DO NOTHING;
    """)

    # Seed supplier-product relationships
    cur.execute("""
        INSERT INTO supplier_products (supplier_id, product_id, supply_volume)
        VALUES
            ('SUP_001', 'PROD_001', 5000),
            ('SUP_001', 'PROD_002', 3000),
            ('SUP_005', 'PROD_001', 4000),
            ('SUP_005', 'PROD_002', 2000),
            ('SUP_002', 'PROD_001', 2000),
            ('SUP_003', 'PROD_004', 1500),
            ('SUP_003', 'PROD_005', 2000),
            ('SUP_004', 'PROD_004', 1000),
            ('SUP_004', 'PROD_005', 1500),
            ('SUP_007', 'PROD_003', 3000),
            ('SUP_006', 'PROD_006', 8000),
            ('SUP_009', 'PROD_006', 5000),
            ('SUP_006', 'PROD_007', 6000),
            ('SUP_008', 'PROD_008', 2500),
            ('SUP_010', 'PROD_009', 4000),
            ('SUP_006', 'PROD_010', 7000)
        ON CONFLICT DO NOTHING;
    """)

    # Seed supplier-warehouse relationships
    cur.execute("""
        INSERT INTO supplier_warehouses (supplier_id, warehouse_id, transit_days)
        VALUES
            ('SUP_001', 'WH_004', 3),
            ('SUP_001', 'WH_003', 4),
            ('SUP_002', 'WH_001', 2),
            ('SUP_002', 'WH_003', 3),
            ('SUP_003', 'WH_004', 5),
            ('SUP_004', 'WH_001', 6),
            ('SUP_005', 'WH_004', 4),
            ('SUP_005', 'WH_002', 5),
            ('SUP_006', 'WH_003', 1),
            ('SUP_006', 'WH_005', 1),
            ('SUP_007', 'WH_005', 2),
            ('SUP_007', 'WH_004', 3),
            ('SUP_008', 'WH_001', 7),
            ('SUP_009', 'WH_002', 8),
            ('SUP_010', 'WH_002', 6),
            ('SUP_010', 'WH_005', 5)
        ON CONFLICT DO NOTHING;
    """)

    # Seed warehouse-store relationships
    cur.execute("""
        INSERT INTO warehouse_stores (warehouse_id, store_id, transit_days)
        VALUES
            ('WH_001', 'STORE_NYC', 1),
            ('WH_001', 'STORE_BOS', 1),
            ('WH_002', 'STORE_ATL', 1),
            ('WH_002', 'STORE_MIA', 2),
            ('WH_003', 'STORE_CHI', 1),
            ('WH_003', 'STORE_DET', 1),
            ('WH_004', 'STORE_LA',  1),
            ('WH_004', 'STORE_SF',  1),
            ('WH_005', 'STORE_DAL', 1),
            ('WH_005', 'STORE_HOU', 1)
        ON CONFLICT DO NOTHING;
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("Database setup complete.")

if __name__ == "__main__":
    setup()