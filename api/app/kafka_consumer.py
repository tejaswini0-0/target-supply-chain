import json
import os
import time
from kafka import KafkaConsumer
from postgres import run_postgres_query
from graph_db import get_driver, build_graph, clear_graph

POSTGRES_DB_ARGS = dict(
    host=os.environ["POSTGRES_HOST"],
    user=os.environ["POSTGRES_USER"],
    dbname=os.environ["POSTGRES_DB"],
    port=int(os.environ["POSTGRES_PORT"]),
    password=os.environ["POSTGRES_PASSWORD"],
)

def load_postgres_data():
    """Load all supply chain tables from PostgreSQL."""
    return {
        "suppliers":           run_postgres_query("SELECT * FROM suppliers",           **POSTGRES_DB_ARGS),
        "warehouses":          run_postgres_query("SELECT * FROM warehouses",          **POSTGRES_DB_ARGS),
        "stores":              run_postgres_query("SELECT * FROM stores",              **POSTGRES_DB_ARGS),
        "products":            run_postgres_query("SELECT * FROM products",            **POSTGRES_DB_ARGS),
        "supplier_products":   run_postgres_query("SELECT * FROM supplier_products",   **POSTGRES_DB_ARGS),
        "supplier_warehouses": run_postgres_query("SELECT * FROM supplier_warehouses", **POSTGRES_DB_ARGS),
        "warehouse_stores":    run_postgres_query("SELECT * FROM warehouse_stores",    **POSTGRES_DB_ARGS),
    }

def run_consumer():
    # Wait for all services
    time.sleep(15)

    # Connect to Kafka
    consumer = None
    for i in range(20):
        try:
            consumer = KafkaConsumer(
                "supply-chain-events",
                bootstrap_servers=os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                group_id="supply-chain-consumer-group-v1",
                auto_offset_reset="latest",
                enable_auto_commit=True,
                session_timeout_ms=30000,
            )
            print("Consumer connected to Kafka.")
            break
        except Exception as e:
            print(f"Kafka not ready, retrying ({i+1}/20)... {e}")
            time.sleep(5)

    if consumer is None:
        raise Exception("Could not connect to Kafka")

    # Connect to Neo4j and do initial graph build
    print("Building initial graph from PostgreSQL...")
    driver = get_driver()
    
    for attempt in range(20):
        try:
            postgres_data = load_postgres_data()
            clear_graph(driver)
            build_graph(driver, postgres_data)
            print("Initial graph build complete.")
            break
        except Exception as e:
            print(f"Graph build failed (attempt {attempt+1}/20): {e} — retrying in 5s...")
            time.sleep(5)

    print("Consumer listening for supply chain events...")

    for message in consumer:
        event = message.value
        print(f"Received event: {event}")

        try:
            # On any supply chain change, rebuild the graph from PostgreSQL
            # This keeps Neo4j perfectly in sync with PostgreSQL
            print("Rebuilding graph after supply chain change...")
            postgres_data = load_postgres_data()
            clear_graph(driver)
            build_graph(driver, postgres_data)
            print("Graph rebuilt successfully.")

        except Exception as e:
            print(f"Error processing event: {e}")

if __name__ == "__main__":
    run_consumer()