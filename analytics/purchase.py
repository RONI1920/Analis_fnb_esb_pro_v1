# analytics/purchase.py — Analisis Data Pembelian

import pandas as pd
import streamlit as st


@st.cache_data
def analyze_purchase_data(df: pd.DataFrame):
    """
    Analisis data pembelian yang sudah difilter.
    Returns: (total_cost, cost_by_category, cost_by_supplier, top_items, raw_data_filtered)
    """
    empty = (0, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame())

    if df is None or df.empty:
        return empty

    df_cost = df[df["Total"] > 0].copy()

    total_cost = df_cost["Total"].sum()

    cost_by_category = (
        df_cost.groupby("Category")["Total"]
        .sum().sort_values(ascending=False).reset_index()
    )

    cost_by_supplier = (
        df_cost.groupby("Supplier Name")["Total"]
        .sum().sort_values(ascending=False).reset_index()
    )

    top_items = (
        df_cost.groupby("Product Name")["Total"]
        .sum().nlargest(20).sort_values(ascending=False).reset_index()
    )

    display_cols = [
        "Purchase Date", "Supplier Name", "Category", "Sub Category",
        "Product Name", "Receipt Qty", "Price", "Total",
    ]
    raw_data_filtered = df_cost[
        [c for c in display_cols if c in df_cost.columns]
    ].sort_values(by="Total", ascending=False)

    return total_cost, cost_by_category, cost_by_supplier, top_items, raw_data_filtered
