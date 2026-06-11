import streamlit as st
import pandas as pd
import altair as alt
import os
import requests

API_URL = "http://supply_chain_api:80"

st.set_page_config(page_title="Target Supply Chain Dashboard", layout="wide")
st.title("Target Supply Chain Analytics Dashboard")
st.markdown("Real-time graph analytics on Target's supplier network.")

if st.button("🔄 Refresh Data"):
    st.rerun()

# HELPER

def fetch(endpoint):
    try:
        response = requests.get(f"{API_URL}{endpoint}")
        return response.json()
    except Exception as e:
        st.error(f"Could not reach API: {e}")
        return None

# NETWORK OVERVIEW

st.header("Network Overview", divider="red")

suppliers = fetch("/suppliers")
warehouses = fetch("/warehouses")
stores = fetch("/stores")
products = fetch("/products")

if all([suppliers, warehouses, stores, products]):
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Suppliers", len(suppliers["suppliers"]))
    col2.metric("Warehouses", len(warehouses["warehouses"]))
    col3.metric("Stores", len(stores["stores"]))
    col4.metric("Products", len(products["products"]))

    with st.expander("View Suppliers"):
        st.dataframe(pd.DataFrame(suppliers["suppliers"]), hide_index=True, use_container_width=True)

    with st.expander("View Warehouses"):
        st.dataframe(pd.DataFrame(warehouses["warehouses"]), hide_index=True, use_container_width=True)

# SINGLE POINTS OF FAILURE

st.header("🚨 Single Points of Failure", divider="red")
st.markdown("Suppliers whose disruption would affect the most stores.")

spof_data = fetch("/analytics/single-points-of-failure")
if spof_data:
    spof_df = pd.DataFrame(spof_data["single_points_of_failure"])

    chart = (
        alt.Chart(spof_df)
        .mark_bar()
        .encode(
            x=alt.X("stores_affected:Q", title="Stores Affected"),
            y=alt.Y("supplier_name:N", sort="-x", title="Supplier"),
            color=alt.Color("stores_affected:Q",
                scale=alt.Scale(scheme="reds"),
                legend=None
            ),
            tooltip=["supplier_name", "country", "reliability_score", "stores_affected"]
        )
        .properties(title="Suppliers by Stores Affected if Disrupted")
    )
    st.altair_chart(chart, use_container_width=True)
    st.dataframe(spof_df, hide_index=True, use_container_width=True)

# SUPPLIER DEPENDENCY RANK

st.header("📊 Supplier Dependency Ranking", divider="red")
st.markdown("Suppliers ranked by overall dependency score (products × stores reached).")

rank_data = fetch("/analytics/supplier-dependency-rank")
if rank_data:
    rank_df = pd.DataFrame(rank_data["supplier_dependency_rank"])

    scatter = (
        alt.Chart(rank_df)
        .mark_circle(size=150)
        .encode(
            x=alt.X("products_supplied:Q", title="Products Supplied"),
            y=alt.Y("stores_reached:Q", title="Stores Reached"),
            size=alt.Size("dependency_score:Q", title="Dependency Score"),
            color=alt.Color("reliability_score:Q",
                scale=alt.Scale(scheme="redyellowgreen"),
                title="Reliability Score"
            ),
            tooltip=["supplier_name", "country", "products_supplied",
                    "stores_reached", "dependency_score", "reliability_score"]
        )
        .properties(title="Supplier Dependency Map — Size = Dependency Score, Color = Reliability")
    )
    st.altair_chart(scatter, use_container_width=True)
    st.dataframe(rank_df, hide_index=True, use_container_width=True)

# SHORTEST PATH FINDER

st.header("🗺️ Delivery Path Finder", divider="red")
st.markdown("Find the shortest delivery path from any supplier to any store.")

if suppliers and stores:
    supplier_list = [s["supplier_id"] for s in suppliers["suppliers"]]
    supplier_names = {s["supplier_id"]: s["supplier_name"] for s in suppliers["suppliers"]}
    store_list = [s["store_id"] for s in stores["stores"]]
    store_names = {s["store_id"]: s["store_name"] for s in stores["stores"]}

    col1, col2 = st.columns(2)
    with col1:
        selected_supplier = st.selectbox(
            "From Supplier",
            supplier_list,
            format_func=lambda x: f"{x} — {supplier_names[x]}"
        )
    with col2:
        selected_store = st.selectbox(
            "To Store",
            store_list,
            format_func=lambda x: f"{x} — {store_names[x]}"
        )

    if st.button("Find Shortest Path"):
        path_data = fetch(f"/analytics/shortest-path/{selected_supplier}/{selected_store}")
        if path_data and path_data.get("path"):
            path = path_data["path"]
            st.success(f"Path found in {path['hops']} hops")
            cols = st.columns(len(path["path_nodes"]))
            for i, (node, col) in enumerate(zip(path["path_nodes"], cols)):
                with col:
                    if i < len(path["relationships"]):
                        st.markdown(f"**{node}**")
                        st.markdown(f"↓ *{path['relationships'][i]}*")
                    else:
                        st.markdown(f"**{node}**")
        else:
            st.warning("No path found between selected supplier and store.")

# DISRUPTION SIMULATOR

st.header("⚡ Supplier Disruption Simulator", divider="red")
st.markdown("Simulate what happens if a supplier goes down — see affected products, stores, and alternatives.")

if suppliers:
    sim_supplier = st.selectbox(
        "Select Supplier to Disrupt",
        supplier_list,
        format_func=lambda x: f"{x} — {supplier_names[x]}",
        key="sim_supplier"
    )

    if st.button("Simulate Disruption"):
        try:
            response = requests.post(f"{API_URL}/events/supplier-disruption",
                json={"supplier_id": sim_supplier, "reason": "Simulated disruption from dashboard"})
            result = response.json()

            if "impact" in result:
                impact = result["impact"]

                col1, col2, col3 = st.columns(3)
                col1.metric("Products Affected", len(impact["products_affected"]))
                col2.metric("Stores Affected", len(impact["stores_affected"]))
                col3.metric("Alternative Suppliers", len(set(
                    a["alt_supplier_id"] for a in impact["alternative_suppliers"]
                )))

                with st.expander("Affected Products"):
                    st.dataframe(pd.DataFrame(impact["products_affected"]),
                                hide_index=True, use_container_width=True)

                with st.expander("Affected Stores"):
                    st.dataframe(pd.DataFrame(impact["stores_affected"]),
                                hide_index=True, use_container_width=True)

                with st.expander("Alternative Suppliers Available"):
                    if impact["alternative_suppliers"]:
                        st.dataframe(pd.DataFrame(impact["alternative_suppliers"]),
                                    hide_index=True, use_container_width=True)
                    else:
                        st.error("No alternative suppliers available — critical single point of failure!")

        except Exception as e:
            st.error(f"Error simulating disruption: {e}")

# RELIABILITY UPDATE

st.header("⚙️ Update Supplier Reliability", divider="red")
st.markdown("Update a supplier's reliability score and sync changes to the graph in real time.")

if suppliers:
    col1, col2 = st.columns(2)
    with col1:
        update_supplier = st.selectbox(
            "Select Supplier",
            supplier_list,
            format_func=lambda x: f"{x} — {supplier_names[x]}",
            key="update_supplier"
        )
    with col2:
        new_score = st.slider("New Reliability Score", 0.0, 1.0, 0.90, 0.01)

    if st.button("Update Reliability Score"):
        try:
            response = requests.post(f"{API_URL}/events/reliability-update",
                json={"supplier_id": update_supplier, "reliability_score": new_score})
            if response.status_code == 200:
                st.success(f"Reliability score for {supplier_names[update_supplier]} updated to {new_score} and synced to graph.")
            else:
                st.error(f"Error: {response.text}")
        except Exception as e:
            st.error(f"Could not reach API: {e}")