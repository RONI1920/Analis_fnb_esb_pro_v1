# analytics/gmv_advanced.py — Analisis GMV Lanjutan: Pareto, Tren, Cohort, Branch

import pandas as pd
import numpy as np
import streamlit as st


@st.cache_data
def get_pareto_analysis(df: pd.DataFrame, filter_regex: str = "") -> pd.DataFrame:
    """
    Pareto analysis: menu mana yang menyumbang 80% revenue.
    Returns DataFrame dengan kolom kumulatif untuk chart.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    menu_df = df[df["Price (Net)"] > 0].copy()
    if filter_regex:
        menu_df = menu_df[~menu_df["Menu"].str.contains(filter_regex, na=False, case=False, regex=True)]

    rev = (
        menu_df.groupby("Menu")
        .agg(Revenue=("Total After Bill Discount", "sum"), Qty=("Qty", "sum"))
        .sort_values("Revenue", ascending=False)
        .reset_index()
    )
    rev["Revenue_Pct"]    = rev["Revenue"] / rev["Revenue"].sum() * 100
    rev["Revenue_Cumsum"] = rev["Revenue_Pct"].cumsum()
    rev["Rank"]           = range(1, len(rev) + 1)
    rev["Zone"]           = rev["Revenue_Cumsum"].apply(
        lambda x: "🔴 Top 20% (80% Revenue)" if x <= 80 else "⚪ Bottom 80%"
    )
    return rev


@st.cache_data
def get_revenue_trend(df: pd.DataFrame, granularity: str = "W") -> pd.DataFrame:
    """
    Tren revenue harian / mingguan / bulanan.
    granularity: 'D' = harian, 'W' = mingguan, 'M' = bulanan
    """
    if df is None or df.empty:
        return pd.DataFrame()

    df2 = df.copy()
    df2["Period"] = df2["Sales Date In"].dt.to_period(granularity).dt.to_timestamp()
    trend = (
        df2.groupby("Period")
        .agg(
            Revenue=("Total After Bill Discount", "sum"),
            Transactions=("Bill Number", "nunique"),
            Avg_Transaction=("Total After Bill Discount", lambda x: x.sum() / df2.loc[x.index, "Bill Number"].nunique() if df2.loc[x.index, "Bill Number"].nunique() > 0 else 0),
        )
        .reset_index()
    )
    trend["Revenue_MA7"] = trend["Revenue"].rolling(3, min_periods=1).mean()
    return trend


@st.cache_data
def get_branch_performance(df: pd.DataFrame) -> pd.DataFrame:
    """Perbandingan performa antar cabang per bulan."""
    if df is None or df.empty or "Branch" not in df.columns:
        return pd.DataFrame()

    df2 = df.copy()
    df2["Month"] = df2["Sales Date In"].dt.to_period("M").dt.to_timestamp()
    branch = (
        df2.groupby(["Month", "Branch"])
        .agg(
            Revenue=("Total After Bill Discount", "sum"),
            Transactions=("Bill Number", "nunique"),
        )
        .reset_index()
    )
    branch["ATV"] = branch["Revenue"] / branch["Transactions"]
    return branch


@st.cache_data
def get_weekly_cohort(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cohort penjualan mingguan: heatmap revenue per minggu.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    df2 = df.copy()
    df2["Week"]    = df2["Sales Date In"].dt.isocalendar().week.astype(int)
    df2["Weekday"] = df2["Sales Date In"].dt.day_name()
    df2["Month"]   = df2["Sales Date In"].dt.strftime("%b %Y")

    cohort = (
        df2.groupby(["Month", "Weekday"])
        .agg(Revenue=("Total After Bill Discount", "sum"))
        .reset_index()
    )
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    cohort["Weekday"] = pd.Categorical(cohort["Weekday"], categories=day_order, ordered=True)
    cohort = cohort.sort_values(["Month", "Weekday"])
    return cohort


@st.cache_data
def get_hourly_heatmap(df: pd.DataFrame) -> pd.DataFrame:
    """Heatmap revenue per jam x hari dalam seminggu."""
    if df is None or df.empty:
        return pd.DataFrame()

    df2 = df.copy()
    df2["Hour"]    = df2["Sales Date In"].dt.hour
    df2["Weekday"] = df2["Sales Date In"].dt.day_name()

    heatmap = (
        df2.groupby(["Weekday", "Hour"])
        .agg(Revenue=("Total After Bill Discount", "sum"), Transactions=("Bill Number", "nunique"))
        .reset_index()
    )
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    heatmap["Weekday"] = pd.Categorical(heatmap["Weekday"], categories=day_order, ordered=True)
    return heatmap.sort_values(["Weekday", "Hour"])


@st.cache_data
def get_category_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Tren revenue per kategori menu per bulan."""
    if df is None or df.empty or "Menu Category" not in df.columns:
        return pd.DataFrame()

    df2 = df.copy()
    df2["Month"] = df2["Sales Date In"].dt.to_period("M").dt.to_timestamp()

    # Top 6 kategori by total revenue
    top_cats = (
        df2.groupby("Menu Category")["Total After Bill Discount"]
        .sum().nlargest(6).index.tolist()
    )
    df2 = df2[df2["Menu Category"].isin(top_cats)]

    trend = (
        df2.groupby(["Month", "Menu Category"])
        .agg(Revenue=("Total After Bill Discount", "sum"))
        .reset_index()
    )
    return trend


@st.cache_data
def get_growth_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """MoM growth per bulan."""
    if df is None or df.empty:
        return pd.DataFrame()

    df2 = df.copy()
    df2["Month"] = df2["Sales Date In"].dt.to_period("M").dt.to_timestamp()
    monthly = (
        df2.groupby("Month")
        .agg(Revenue=("Total After Bill Discount", "sum"), Transactions=("Bill Number", "nunique"))
        .reset_index()
    )
    monthly["Revenue_Growth"]      = monthly["Revenue"].pct_change() * 100
    monthly["Transaction_Growth"]  = monthly["Transactions"].pct_change() * 100
    monthly["ATV"]                 = monthly["Revenue"] / monthly["Transactions"]
    monthly["ATV_Growth"]          = monthly["ATV"].pct_change() * 100
    return monthly