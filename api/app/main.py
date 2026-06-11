from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from datetime import datetime
from postgres import run_postgres_query, run_postgres_write
from kafka_producer import get_producer, publish_event
from graph_db import (
    get_driver,
    get_single_points_of_failure,
    get_shortest_path,
    get_supplier_dependency_rank,
    simulate_supplier_disruption,
    get_full_graph_data
)

POSTGRES_DB_ARGS = dict(
    host=os.environ["POSTGRES_HOST"],
    user=os.environ["POSTGRES_USER"],
    dbname=os.environ["POSTGRES_DB"],
    port=int(os.environ["POSTGRES_PORT"]),
    password=os.environ["POSTGRES_PASSWORD"],
)

app = FastAPI(title="Target Supply Chain Analytics API")
kafka_producer = None
neo4j_driver = None

def get_kafka_producer():
    global kafka_producer
    if kafka_producer is None:
        kafka_producer = get_producer()
    return kafka_producer

def get_neo4j_driver():
    global neo4j_driver
    if neo4j_driver is None:
        neo4j_driver = get_driver()
    return neo4j_driver

# BASIC DATA ENDPOINTS

@app.get("/suppliers")
def get_suppliers():
    try:
        df = run_postgres_query("SELECT * FROM suppliers ORDER BY supplier_id", **POSTGRES_DB_ARGS)
        return {"suppliers": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/warehouses")
def get_warehouses():
    try:
        df = run_postgres_query("SELECT * FROM warehouses ORDER BY warehouse_id", **POSTGRES_DB_ARGS)
        return {"warehouses": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stores")
def get_stores():
    try:
        df = run_postgres_query("SELECT * FROM stores ORDER BY store_id", **POSTGRES_DB_ARGS)
        return {"stores": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/products")
def get_products():
    try:
        df = run_postgres_query("SELECT * FROM products ORDER BY product_id", **POSTGRES_DB_ARGS)
        return {"products": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# GRAPH ANALYTICS ENDPOINTS

@app.get("/analytics/single-points-of-failure")
def single_points_of_failure():
    try:
        results = get_single_points_of_failure(get_neo4j_driver)
        return {"single_points_of_failure": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/supplier-dependency-rank")
def supplier_dependency_rank():
    try:
        results = get_supplier_dependency_rank(get_neo4j_driver)
        return {"supplier_dependency_rank": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/shortest-path/{supplier_id}/{store_id}")
def shortest_path(supplier_id: str, store_id: str):
    try:
        result = get_shortest_path(get_neo4j_driver, supplier_id, store_id)
        if result is None:
            raise HTTPException(status_code=404, detail="No path found between supplier and store")
        return {"path": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/disruption/{supplier_id}")
def supplier_disruption(supplier_id: str):
    try:
        result = simulate_supplier_disruption(get_neo4j_driver, supplier_id)
        return {"disruption_simulation": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/graph")
def full_graph():
    try:
        result = get_full_graph_data(get_neo4j_driver)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# SUPPLY CHAIN EVENT ENDPOINTS

class SupplierReliabilityUpdate(BaseModel):
    supplier_id: str
    reliability_score: float

class SupplierDisruptionEvent(BaseModel):
    supplier_id: str
    reason: str

@app.post("/events/reliability-update")
def update_reliability(event: SupplierReliabilityUpdate):
    try:
        run_postgres_write(
            f"""UPDATE suppliers SET reliability_score = {event.reliability_score}
                WHERE supplier_id = '{event.supplier_id}'""",
            **POSTGRES_DB_ARGS
        )
        publish_event(get_kafka_producer, "supply-chain-events", {
            "event_type": "reliability_update",
            "supplier_id": event.supplier_id,
            "reliability_score": event.reliability_score,
            "timestamp": datetime.now().isoformat()
        })
        return {"status": "ok", "event": event.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/events/supplier-disruption")
def supplier_disruption_event(event: SupplierDisruptionEvent):
    try:
        publish_event(kafka_producer, "supply-chain-events", {
            "event_type": "supplier_disruption",
            "supplier_id": event.supplier_id,
            "reason": event.reason,
            "timestamp": datetime.now().isoformat()
        })
        # Run disruption simulation
        result = simulate_supplier_disruption(neo4j_driver, event.supplier_id)
        return {
            "status": "disruption_simulated",
            "event": event.model_dump(),
            "impact": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# HEALTH CHECK

@app.get("/health")
def health():
    try:
        run_postgres_query("SELECT 1", **POSTGRES_DB_ARGS)
        get_neo4j_driver.verify_connectivity()
        return {"status": "healthy", "postgres": "up", "neo4j": "up", "kafka": "up"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))