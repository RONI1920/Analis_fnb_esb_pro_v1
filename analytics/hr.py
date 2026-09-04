# analytics/hr.py — Analisis SDM: Waiter Performance & Fraud Detection

import numpy as np
import pandas as pd
import streamlit as st


@st.cache_data
def get_waiter_performance(df: pd.DataFrame) -> pd.DataFrame:
    """Analisis performa Top 10 Waiter."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["Waiter", "Total_Penjualan", "Jumlah_Transaksi"])

    bill_df = (
        df.groupby("Bill Number")
        .agg(Waiter=("Waiter", "first"), Total_Sales=("Total After Bill Discount", "sum"))
        .reset_index()
    )
    bill_df["Waiter"] = bill_df["Waiter"].fillna("Tidak Diketahui")

    waiter_perf = (
        bill_df.groupby("Waiter")
        .agg(
            Total_Penjualan=("Total_Sales", "sum"),
            Jumlah_Transaksi=("Bill Number", "nunique"),
        )
        .reset_index()
    )
    return waiter_perf.nlargest(10, "Total_Penjualan")


def get_fraud_analysis(df: pd.DataFrame):
    """
    Analisis kecurangan berbasis deteksi anomali (Mean + 2*StdDev).
    Returns: (result_dict | None, status_message)
    """
    COL_WAITER = "Waiter"
    COL_TYPE = "Sales Type"

    if COL_TYPE not in df.columns or COL_WAITER not in df.columns:
        return None, f"Kolom '{COL_WAITER}' atau '{COL_TYPE}' tidak ditemukan."

    df_clean = df.copy()
    df_clean[COL_TYPE] = df_clean[COL_TYPE].replace(
        {"Void Sales": "Void", "Void sales": "Void", "VOID": "Void"}
    )

    fraud_pivot = pd.crosstab(df_clean[COL_WAITER], df_clean[COL_TYPE])

    if "Void Sales" in fraud_pivot.columns:
        fraud_pivot = fraud_pivot.drop(columns=["Void Sales"])

    for col in ["Void", "Non Sales"]:
        if col not in fraud_pivot.columns:
            fraud_pivot[col] = 0

    def _analyze(counts, min_threshold):
        avg = counts.mean()
        std = counts.std()
        threshold = np.ceil(max(min_threshold, avg + 2 * std))
        suspects = fraud_pivot[counts > threshold].sort_values(
            by=counts.name, ascending=False
        )
        return {
            "suspects": suspects[[counts.name]],
            "avg": avg,
            "threshold": threshold,
            "std": std,
        }

    return {
        "raw_data": fraud_pivot,
        "void": _analyze(fraud_pivot["Void"], 2.0),
        "nonsales": _analyze(fraud_pivot["Non Sales"], 3.0),
    }, "Success"