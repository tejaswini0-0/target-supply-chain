from neo4j import GraphDatabase
import os

def get_driver():
    return GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(
            os.environ.get("NEO4J_USER", "neo4j"),
            os.environ.get("NEO4J_PASSWORD", "password")
        )
    )

def clear_graph(driver):
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    print("Graph cleared.")

def build_graph(driver, postgres_data):
    """Build the entire supply chain graph from PostgreSQL data."""
    with driver.session() as session:

        # Create supplier nodes
        for _, row in postgres_data["suppliers"].iterrows():
            session.run("""
                MERGE (s:Supplier {id: $id})
                SET s.name = $name,
                    s.country = $country,
                    s.reliability_score = $reliability_score,
                    s.lead_time_days = $lead_time_days
            """, id=row["supplier_id"], name=row["supplier_name"],
                country=row["country"],
                reliability_score=float(row["reliability_score"]),
                lead_time_days=int(row["lead_time_days"]))

        # Create warehouse nodes
        for _, row in postgres_data["warehouses"].iterrows():
            session.run("""
                MERGE (w:Warehouse {id: $id})
                SET w.name = $name,
                    w.city = $city,
                    w.capacity = $capacity
            """, id=row["warehouse_id"], name=row["warehouse_name"],
                city=row["city"], capacity=int(row["capacity"]))

        # Create store nodes
        for _, row in postgres_data["stores"].iterrows():
            session.run("""
                MERGE (st:Store {id: $id})
                SET st.name = $name,
                    st.city = $city,
                    st.region = $region
            """, id=row["store_id"], name=row["store_name"],
                city=row["city"], region=row["region"])

        # Create product nodes
        for _, row in postgres_data["products"].iterrows():
            session.run("""
                MERGE (p:Product {id: $id})
                SET p.name = $name,
                    p.category = $category,
                    p.unit_cost = $unit_cost
            """, id=row["product_id"], name=row["product_name"],
                category=row["category"], unit_cost=float(row["unit_cost"]))

        # Create SUPPLIES relationships (supplier -> product)
        for _, row in postgres_data["supplier_products"].iterrows():
            session.run("""
                MATCH (s:Supplier {id: $supplier_id})
                MATCH (p:Product {id: $product_id})
                MERGE (s)-[r:SUPPLIES]->(p)
                SET r.supply_volume = $supply_volume
            """, supplier_id=row["supplier_id"],
                product_id=row["product_id"],
                supply_volume=int(row["supply_volume"]))

        # Create SHIPS_TO relationships (supplier -> warehouse)
        for _, row in postgres_data["supplier_warehouses"].iterrows():
            session.run("""
                MATCH (s:Supplier {id: $supplier_id})
                MATCH (w:Warehouse {id: $warehouse_id})
                MERGE (s)-[r:SHIPS_TO]->(w)
                SET r.transit_days = $transit_days
            """, supplier_id=row["supplier_id"],
                warehouse_id=row["warehouse_id"],
                transit_days=int(row["transit_days"]))

        # Create DISTRIBUTES_TO relationships (warehouse -> store)
        for _, row in postgres_data["warehouse_stores"].iterrows():
            session.run("""
                MATCH (w:Warehouse {id: $warehouse_id})
                MATCH (st:Store {id: $store_id})
                MERGE (w)-[r:DISTRIBUTES_TO]->(st)
                SET r.transit_days = $transit_days
            """, warehouse_id=row["warehouse_id"],
                store_id=row["store_id"],
                transit_days=int(row["transit_days"]))

    print("Graph built successfully.")

def get_single_points_of_failure(driver):
    """Find suppliers whose removal would affect the most stores."""
    with driver.session() as session:
        result = session.run("""
            MATCH (s:Supplier)-[:SHIPS_TO]->(w:Warehouse)-[:DISTRIBUTES_TO]->(st:Store)
            WITH s, COUNT(DISTINCT st) as stores_affected
            ORDER BY stores_affected DESC
            RETURN s.id as supplier_id,
                   s.name as supplier_name,
                   s.country as country,
                   s.reliability_score as reliability_score,
                   stores_affected
        """)
        return [dict(r) for r in result]

def get_shortest_path(driver, supplier_id, store_id):
    """Find shortest delivery path from supplier to store."""
    with driver.session() as session:
        result = session.run("""
            MATCH path = shortestPath(
                (s:Supplier {id: $supplier_id})-[*]->(st:Store {id: $store_id})
            )
            RETURN [node in nodes(path) | coalesce(node.name, node.id)] as path_nodes,
                   [rel in relationships(path) | type(rel)] as relationships,
                   length(path) as hops
        """, supplier_id=supplier_id, store_id=store_id)
        rows = [dict(r) for r in result]
        return rows[0] if rows else None

def get_supplier_dependency_rank(driver):
    """Rank suppliers by how many products and stores they are critical for."""
    with driver.session() as session:
        result = session.run("""
            MATCH (s:Supplier)-[:SUPPLIES]->(p:Product)
            WITH s, COUNT(DISTINCT p) as products_supplied
            MATCH (s)-[:SHIPS_TO]->(w:Warehouse)-[:DISTRIBUTES_TO]->(st:Store)
            WITH s, products_supplied, COUNT(DISTINCT st) as stores_reached
            RETURN s.id as supplier_id,
                   s.name as supplier_name,
                   s.country as country,
                   s.reliability_score as reliability_score,
                   s.lead_time_days as lead_time_days,
                   products_supplied,
                   stores_reached,
                   (products_supplied * stores_reached) as dependency_score
            ORDER BY dependency_score DESC
        """)
        return [dict(r) for r in result]

def simulate_supplier_disruption(driver, supplier_id):
    """Show which products and stores are affected if a supplier goes down."""
    with driver.session() as session:
        # Products affected
        products_result = session.run("""
            MATCH (s:Supplier {id: $supplier_id})-[:SUPPLIES]->(p:Product)
            RETURN p.id as product_id, p.name as product_name, p.category as category
        """, supplier_id=supplier_id)
        products = [dict(r) for r in products_result]

        # Stores affected
        stores_result = session.run("""
            MATCH (s:Supplier {id: $supplier_id})-[:SHIPS_TO]->(w:Warehouse)-[:DISTRIBUTES_TO]->(st:Store)
            RETURN DISTINCT st.id as store_id, st.name as store_name,
                   st.city as city, st.region as region,
                   w.name as via_warehouse
        """, supplier_id=supplier_id)
        stores = [dict(r) for r in stores_result]

        # Alternative suppliers for affected products
        alternatives_result = session.run("""
            MATCH (s:Supplier {id: $supplier_id})-[:SUPPLIES]->(p:Product)
            MATCH (alt:Supplier)-[:SUPPLIES]->(p)
            WHERE alt.id <> $supplier_id
            RETURN DISTINCT alt.id as alt_supplier_id,
                   alt.name as alt_supplier_name,
                   alt.reliability_score as reliability_score,
                   alt.lead_time_days as lead_time_days,
                   p.name as product_name
            ORDER BY alt.reliability_score DESC
        """, supplier_id=supplier_id)
        alternatives = [dict(r) for r in alternatives_result]

        return {
            "supplier_id": supplier_id,
            "products_affected": products,
            "stores_affected": stores,
            "alternative_suppliers": alternatives
        }

def get_full_graph_data(driver):
    """Return all nodes and relationships for dashboard visualization."""
    with driver.session() as session:
        nodes_result = session.run("""
            MATCH (n)
            RETURN labels(n)[0] as label,
                   n.id as id,
                   n.name as name
        """)
        nodes = [dict(r) for r in nodes_result]

        rels_result = session.run("""
            MATCH (a)-[r]->(b)
            RETURN a.id as source, b.id as target, type(r) as relationship
        """)
        relationships = [dict(r) for r in rels_result]

        return {"nodes": nodes, "relationships": relationships}