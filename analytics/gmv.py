# analytics/gmv.py — Fungsi Analisis GMV & Penjualan

import pandas as pd
import numpy as np
import streamlit as st

from config import DAY_MAP


def clean_payment_method(method_str: str) -> str:
    """Mengelompokkan metode pembayaran."""
    method_str = str(method_str).upper()
    if "VOUCHER" in method_str or "," in method_str:
        return "Voucher / Split"
    if "QRIS" in method_str:
        return "QRIS"
    if "VISA" in method_str:
        return "VISA"
    if "DEBIT CARD" in method_str:
        return "DEBIT CARD"
    if "BCA CARD" in method_str:
        return "BCA CARD"
    if "MASTER" in method_str:
        return "MASTER"
    if "CC " in method_str or "CREDIT CARD" in method_str:
        return "CREDIT CARD (Lainnya)"
    if "CASH" in method_str:
        return "CASH"
    if "TRANSFER" in method_str:
        return "TRANSFER"
    if "BRI CARD" in method_str:
        return "BRI CARD"
    if "BNI CARD" in method_str:
        return "BNI CARD"
    return "Lainnya"


@st.cache_data
def calculate_sales_kpi(df: pd.DataFrame) -> dict:
    """Menghitung KPI Penjualan Utama."""
    empty = {
        "Total Pendapatan Kotor": 0, "Total Penjualan Bersih (Nett)": 0,
        "Total Transaksi": 0, "Rata-rata Nilai Transaksi (ATV)": 0,
        "Total Item Terjual": 0, "Item per Transaksi (IPB)": 0,
        "Total Diskon": 0, "Total Service Charge": 0, "Total Pajak": 0,
    }
    if df is None or df.empty:
        return empty

    total_revenue = df["Total After Bill Discount"].sum()
    total_nett_sales = df["Total Nett Sales"].sum()
    unique_bills = df["Bill Number"].nunique()
    atv = total_revenue / unique_bills if unique_bills > 0 else 0
    total_items = df["Qty"].sum()
    ipb = total_items / unique_bills if unique_bills > 0 else 0
    total_discounts = (
        df["Difference Price"].sum() + df["Discount"].sum() + df["Bill Discount"].sum()
    )

    return {
        "Total Pendapatan Kotor": total_revenue,
        "Total Penjualan Bersih (Nett)": total_nett_sales,
        "Total Transaksi": unique_bills,
        "Rata-rata Nilai Transaksi (ATV)": atv,
        "Total Item Terjual": total_items,
        "Item per Transaksi (IPB)": ipb,
        "Total Diskon": total_discounts,
        "Total Service Charge": df["Service Charge"].sum(),
        "Total Pajak": df["Tax"].sum(),
    }


@st.cache_data
def get_payment_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Analisis penjualan berdasarkan metode pembayaran."""
    bill_data = (
        df.groupby("Bill Number")
        .agg(
            Bill_Revenue=("Total After Bill Discount", "sum"),
            Payment_Method=("Payment Method", "first"),
        )
        .reset_index()
    )
    bill_data["Cleaned_Payment"] = bill_data["Payment_Method"].apply(clean_payment_method)
    result = (
        bill_data.groupby("Cleaned_Payment")["Bill_Revenue"]
        .agg(Total_Penjualan="sum", Jumlah_Transaksi="count")
        .sort_values(by="Total_Penjualan", ascending=False)
    )
    return result.reset_index()


@st.cache_data
def get_visit_purpose_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Analisis penjualan berdasarkan tujuan kunjungan."""
    bill_data = (
        df.groupby("Bill Number")
        .agg(
            Bill_Revenue=("Total After Bill Discount", "sum"),
            Visit_Purpose=("Visit Purpose", "first"),
        )
        .reset_index()
    )
    result = (
        bill_data.groupby("Visit_Purpose")["Bill_Revenue"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
        .rename(columns={
            "Visit_Purpose": "Visit Purpose",
            "Bill_Revenue": "Total After Bill Discount",
        })
    )
    return result


@st.cache_data
def get_menu_performance(df: pd.DataFrame, filter_regex_items_str: str):
    """
    Analisis performa menu dan kategori.
    Returns: (top_selling, top_grossing, top_sell_cat, top_gross_cat,
              bottom_selling, bottom_grossing, menu_sales_cat_df)
    """
    menu_sales = df[~df["Menu"].str.contains("PACKAGE", na=False, case=False)]
    menu_sales = menu_sales[menu_sales["Price (Net)"] > 0]

    if filter_regex_items_str:
        for col in ["Menu Category", "Menu Category Detail", "Menu"]:
            if col in menu_sales.columns:
                menu_sales = menu_sales[
                    ~menu_sales[col].str.contains(
                        filter_regex_items_str, na=False, case=False, regex=True
                    )
                ]

    top_selling_categories = pd.DataFrame(columns=["Menu Category", "Qty"])
    top_grossing_categories = pd.DataFrame(columns=["Menu Category", "Total Nett Sales"])
    menu_sales_cat_df = pd.DataFrame()

    if "Menu Category" in df.columns:
        menu_sales_cat_df = menu_sales.copy()
        top_selling_categories = (
            menu_sales_cat_df.groupby("Menu Category")["Qty"]
            .sum().nlargest(10).sort_values(ascending=False)
        )
        top_grossing_categories = (
            menu_sales_cat_df.groupby("Menu Category")["Total Nett Sales"]
            .sum().nlargest(10).sort_values(ascending=False)
        )

    top_selling_items = menu_sales.groupby("Menu")["Qty"].sum().nlargest(10)
    top_grossing_items = menu_sales.groupby("Menu")["Total Nett Sales"].sum().nlargest(10)
    bottom_selling_items = (
        menu_sales.groupby("Menu")["Qty"].sum().nsmallest(10).sort_values(ascending=True)
    )
    bottom_grossing_items = (
        menu_sales.groupby("Menu")["Total Nett Sales"].sum()
        .nsmallest(10).sort_values(ascending=True)
    )

    return (
        top_selling_items.reset_index(),
        top_grossing_items.reset_index(),
        top_selling_categories.reset_index(),
        top_grossing_categories.reset_index(),
        bottom_selling_items.reset_index(),
        bottom_grossing_items.reset_index(),
        menu_sales_cat_df,
    )


@st.cache_data
def get_operational_kpi(df: pd.DataFrame):
    """Menghitung KPI Operasional (jam sibuk, hari sibuk, durasi makan)."""
    avg_dining_time = 0.0

    if "Visit Purpose" in df.columns and "Sales Date Out" in df.columns:
        df_dine = df[
            df["Visit Purpose"].str.contains("DINE IN", na=False, case=False)
        ].copy()
        df_dine.dropna(subset=["Sales Date In", "Sales Date Out"], inplace=True)
        bill_times = df_dine.groupby("Bill Number").agg(
            Start=("Sales Date In", "min"), End=("Sales Date Out", "max")
        )
        bill_times["Duration_minutes"] = (
            bill_times["End"] - bill_times["Start"]
        ).dt.total_seconds() / 60
        filtered = bill_times[
            (bill_times["Duration_minutes"] > 1) & (bill_times["Duration_minutes"] < 480)
        ]
        avg_dining_time = filtered["Duration_minutes"].mean()
        if pd.isna(avg_dining_time):
            avg_dining_time = 0.0

    df_hourly = df.copy()
    df_hourly["Hour"] = df_hourly["Sales Date In"].dt.hour
    peak_hours = (
        df_hourly.groupby("Hour")["Bill Number"].nunique().sort_values(ascending=False)
    )

    df_daily = df.copy()
    df_daily.dropna(subset=["Sales Date In"], inplace=True)
    df_daily["Day Name"] = df_daily["Sales Date In"].dt.day_name().map(DAY_MAP)
    peak_days = df_daily.groupby("Day Name")["Bill Number"].nunique().reset_index()

    return avg_dining_time, peak_hours.reset_index(), peak_days


@st.cache_data
def get_peak_time_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Analisis transaksi berdasarkan waktu (Breakfast, Lunch, Dinner)."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["Waktu Kunjungan", "Jumlah_Transaksi", "Total_Penjualan"])

    bill_df = (
        df.groupby("Bill Number")
        .agg(Order_Time=("Order Time", "first"), Total_Sales=("Total After Bill Discount", "sum"))
        .reset_index()
    )
    bill_df.dropna(subset=["Order_Time"], inplace=True)
    bill_df["Hour"] = bill_df["Order_Time"].dt.hour

    conditions = [
        (bill_df["Hour"] >= 10) & (bill_df["Hour"] < 12),
        (bill_df["Hour"] >= 12) & (bill_df["Hour"] < 17),
        (bill_df["Hour"] >= 17) & (bill_df["Hour"] < 22),
    ]
    choices = ["Breakfast/Brunch (10-12)", "Lunch (12-17)", "Dinner (17-22)"]
    bill_df["Waktu Kunjungan"] = np.select(conditions, choices, default="Luar Jam Buka")

    time_analysis = (
        bill_df.groupby("Waktu Kunjungan")
        .agg(Jumlah_Transaksi=("Bill Number", "nunique"), Total_Penjualan=("Total_Sales", "sum"))
        .reset_index()
    )

    time_order = ["Breakfast/Brunch (10-12)", "Lunch (12-17)", "Dinner (17-22)", "Luar Jam Buka"]
    try:
        time_analysis["Waktu Kunjungan"] = pd.Categorical(
            time_analysis["Waktu Kunjungan"], categories=time_order, ordered=True
        )
        time_analysis.sort_values("Waktu Kunjungan", inplace=True)
    except Exception:
        pass

    return time_analysis
