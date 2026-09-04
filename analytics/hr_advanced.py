# analytics/hr_advanced.py — Analisis SDM Lanjutan: Leaderboard, Trend, Shift

import pandas as pd
import numpy as np
import streamlit as st

from config import DAY_MAP


@st.cache_data
def get_waiter_leaderboard(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    Leaderboard waiter lengkap dengan ranking, revenue, transaksi, ATV, dan badge.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    bill_df = (
        df.groupby("Bill Number")
        .agg(
            Waiter=("Waiter", "first"),
            Revenue=("Total After Bill Discount", "sum"),
        )
        .reset_index()
    )
    bill_df["Waiter"] = bill_df["Waiter"].fillna("Tidak Diketahui")

    leaderboard = (
        bill_df.groupby("Waiter")
        .agg(
            Total_Revenue=("Revenue", "sum"),
            Jumlah_Bill=("Bill Number", "nunique"),
        )
        .reset_index()
    )
    leaderboard["ATV"]           = leaderboard["Total_Revenue"] / leaderboard["Jumlah_Bill"]
    leaderboard                  = leaderboard.nlargest(top_n, "Total_Revenue").reset_index(drop=True)
    leaderboard["Rank"]          = leaderboard.index + 1
    leaderboard["Revenue_Share"] = leaderboard["Total_Revenue"] / leaderboard["Total_Revenue"].sum() * 100

    def badge(rank):
        return "🥇" if rank == 1 else ("🥈" if rank == 2 else ("🥉" if rank == 3 else f"#{rank}")  )

    leaderboard["Badge"] = leaderboard["Rank"].apply(badge)
    return leaderboard


@st.cache_data
def get_waiter_monthly_trend(df: pd.DataFrame, top_n: int = 8) -> pd.DataFrame:
    """
    Tren performa waiter per bulan — hanya top N waiter by total revenue.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    df2 = df.copy()

    # Resolve kolom tanggal
    date_col = "Order Time" if "Order Time" in df2.columns else "Sales Date In"
    df2[date_col] = pd.to_datetime(df2[date_col], errors="coerce")
    df2["Month"] = df2[date_col].dt.to_period("M").dt.to_timestamp()
    df2["Waiter"] = df2["Waiter"].fillna("Tidak Diketahui")

    # Hitung per bill dulu untuk menghindari double count
    bill_df = (
        df2.groupby(["Bill Number", "Month"])
        .agg(Waiter=("Waiter", "first"), Revenue=("Total After Bill Discount", "sum"))
        .reset_index()
    )

    # Top N waiter by total revenue
    top_waiters = (
        bill_df.groupby("Waiter")["Revenue"]
        .sum().nlargest(top_n).index.tolist()
    )

    bill_df = bill_df[bill_df["Waiter"].isin(top_waiters)]

    trend = (
        bill_df.groupby(["Month", "Waiter"])
        .agg(Revenue=("Revenue", "sum"), Bills=("Bill Number", "nunique"))
        .reset_index()
    )
    trend["ATV"] = trend["Revenue"] / trend["Bills"]
    return trend


@st.cache_data
def get_waiter_consistency_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Skor konsistensi waiter: CV (Coefficient of Variation) revenue per bulan.
    CV rendah = konsisten, CV tinggi = fluktuatif.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    df2 = df.copy()
    date_col = "Order Time" if "Order Time" in df2.columns else "Sales Date In"
    df2[date_col] = pd.to_datetime(df2[date_col], errors="coerce")
    df2["Month"] = df2[date_col].dt.to_period("M").dt.to_timestamp()
    df2["Waiter"] = df2["Waiter"].fillna("Tidak Diketahui")

    bill_df = (
        df2.groupby(["Bill Number", "Month"])
        .agg(Waiter=("Waiter", "first"), Revenue=("Total After Bill Discount", "sum"))
        .reset_index()
    )

    monthly = (
        bill_df.groupby(["Waiter", "Month"])["Revenue"].sum().reset_index()
    )

    consistency = (
        monthly.groupby("Waiter")["Revenue"]
        .agg(
            Avg_Revenue="mean",
            Std_Revenue="std",
            Max_Revenue="max",
            Min_Revenue="min",
            Months_Active="count",
        )
        .reset_index()
    )
    consistency["Std_Revenue"] = consistency["Std_Revenue"].fillna(0)
    consistency["CV"] = (consistency["Std_Revenue"] / consistency["Avg_Revenue"].replace(0, 1)) * 100
    consistency["Skor_Konsistensi"] = 100 - consistency["CV"].clip(0, 100)

    def label(score):
        if score >= 75:
            return "🟢 Konsisten"
        elif score >= 50:
            return "🟡 Cukup Konsisten"
        else:
            return "🔴 Fluktuatif"

    consistency["Status"] = consistency["Skor_Konsistensi"].apply(label)
    return consistency[consistency["Months_Active"] >= 2].sort_values(
        "Avg_Revenue", ascending=False
    ).reset_index(drop=True)


@st.cache_data
def get_waiter_shift_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """
    Analisis performa waiter per shift (Pagi/Siang/Malam).
    """
    if df is None or df.empty:
        return pd.DataFrame()

    df2 = df.copy()
    date_col = "Order Time" if "Order Time" in df2.columns else "Sales Date In"
    df2[date_col] = pd.to_datetime(df2[date_col], errors="coerce")
    df2["Hour"] = df2[date_col].dt.hour
    df2["Waiter"] = df2["Waiter"].fillna("Tidak Diketahui")

    conditions = [
        (df2["Hour"] >= 8)  & (df2["Hour"] < 14),
        (df2["Hour"] >= 14) & (df2["Hour"] < 19),
        (df2["Hour"] >= 19) | (df2["Hour"] < 8),
    ]
    df2["Shift"] = np.select(conditions, ["🌅 Pagi (08-14)", "☀️ Siang (14-19)", "🌙 Malam (19+)"], default="Lainnya")

    bill_df = (
        df2.groupby(["Bill Number", "Shift"])
        .agg(Waiter=("Waiter", "first"), Revenue=("Total After Bill Discount", "sum"))
        .reset_index()
    )

    shift_perf = (
        bill_df.groupby(["Waiter", "Shift"])
        .agg(Revenue=("Revenue", "sum"), Bills=("Bill Number", "nunique"))
        .reset_index()
    )
    shift_perf["ATV"] = shift_perf["Revenue"] / shift_perf["Bills"]

    # Hanya top 10 waiter
    top_waiters = (
        shift_perf.groupby("Waiter")["Revenue"].sum().nlargest(10).index.tolist()
    )
    return shift_perf[shift_perf["Waiter"].isin(top_waiters)]


@st.cache_data
def get_waiter_vs_avg(df: pd.DataFrame) -> pd.DataFrame:
    """
    Bandingkan setiap waiter vs rata-rata toko (revenue & ATV).
    """
    if df is None or df.empty:
        return pd.DataFrame()

    bill_df = (
        df.groupby("Bill Number")
        .agg(Waiter=("Waiter", "first"), Revenue=("Total After Bill Discount", "sum"))
        .reset_index()
    )
    bill_df["Waiter"] = bill_df["Waiter"].fillna("Tidak Diketahui")

    waiter_df = (
        bill_df.groupby("Waiter")
        .agg(Revenue=("Revenue", "sum"), Bills=("Bill Number", "nunique"))
        .reset_index()
    )
    waiter_df["ATV"] = waiter_df["Revenue"] / waiter_df["Bills"]

    avg_revenue = waiter_df["Revenue"].mean()
    avg_atv     = waiter_df["ATV"].mean()

    waiter_df["Revenue_vs_Avg"] = (waiter_df["Revenue"] - avg_revenue) / avg_revenue * 100
    waiter_df["ATV_vs_Avg"]     = (waiter_df["ATV"]     - avg_atv)     / avg_atv     * 100
    waiter_df["Avg_Revenue"]    = avg_revenue
    waiter_df["Avg_ATV"]        = avg_atv

    return waiter_df.sort_values("Revenue", ascending=False)