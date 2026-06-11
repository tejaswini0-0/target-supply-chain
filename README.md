# Target Supply Chain Graph Analytics
A production-style supply chain analytics system that models Target's supplier network as a graph database, enabling real-time graph traversal queries that relational databases cannot answer efficiently — single points of failure detection, shortest delivery path finding, supplier disruption simulation, and dependency ranking.

## Why a Graph Database?
Traditional SQL can answer "which suppliers do we have?" A graph database answers "if this supplier goes down, which stores are affected, what products are impacted, and who are the alternative suppliers?" — in a single query that would require multiple expensive JOINs in SQL. This is the core insight behind this project.

## Architecture
Supply chain data lives in PostgreSQL. A Kafka consumer syncs every change into Neo4j as a graph in real time. A FastAPI service runs graph traversal queries against Neo4j and exposes them as REST endpoints. A Streamlit dashboard visualizes the analytics. The Neo4j browser at localhost:7474 shows the full interactive network diagram.

## Services
- supply_chain_api — FastAPI app with graph analytics and supply chain event endpoints
- supply_chain_consumer — Kafka consumer that builds and syncs the Neo4j graph from PostgreSQL
- neo4j — Graph database storing the supplier network
- supply_chain_postgres — PostgreSQL storing raw supply chain data
- kafka — Apache Kafka for event streaming
- zookeeper — Kafka cluster coordinator
- supply_chain_dashboard — Streamlit dashboard with interactive analytics

## Graph Model
Nodes: Supplier, Warehouse, Store, Product
Relationships:
- (Supplier)-[:SUPPLIES]->(Product)
- (Supplier)-[:SHIPS_TO]->(Warehouse)
- (Warehouse)-[:DISTRIBUTES_TO]->(Store)

## Analytics Endpoints
- GET /analytics/single-points-of-failure — suppliers ranked by stores affected if disrupted
- GET /analytics/supplier-dependency-rank — suppliers ranked by products × stores dependency score
- GET /analytics/shortest-path/{supplier_id}/{store_id} — shortest delivery path between any supplier and store
- GET /analytics/disruption/{supplier_id} — full disruption simulation with affected products, stores, and alternative suppliers
- GET /analytics/graph — full graph data for visualization
- POST /events/supplier-disruption — trigger a disruption event and get instant impact analysis
- POST /events/reliability-update — update supplier reliability and sync to graph in real time

## Quick Start
```bash
git clone https://github.com/tejaswini0-0/target-supply-chain.git
cd target-supply-chain/api
docker compose up --build
```
Wait for Application startup complete. then in a second terminal:
```bash
docker compose exec supply_chain_api python setup_db.py
```
Open http://localhost:8501 for the dashboard.
Open http://localhost:7474 for the Neo4j graph browser (login: neo4j / password).
API at http://localhost:80/docs.

## Tech Stack
- Neo4j 5.20.0 — graph database
- Apache Kafka — event streaming
- FastAPI — REST API
- PostgreSQL — relational data store
- Streamlit — live dashboard
- Docker Compose — local microservices orchestration

## Data Model
10 suppliers across 6 countries, 5 distribution warehouses, 10 stores across 4 regions, 10 products across 5 categories — seeded to simulate a realistic Target supply chain network.