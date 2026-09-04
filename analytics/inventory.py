# analytics/inventory.py — Analisis Inventori & Pembelian Lanjutan
#
# Modul ini melengkapi purchase.py dengan:
#   ✅ Stock Turnover Rate
#   ✅ Reorder Point Estimation
#   ✅ Deteksi Pembelian Berlebih (Overbuying)
#   ✅ Korelasi Pembelian vs Penjualan (Food Cost Efficiency)
#   ✅ Supplier Reliability Score
#   ✅ Price Variance Monitoring

import pandas as pd
import numpy as np
import streamlit as st


# ──────────────────────────────────────────────────────────────────
# STOCK TURNOVER & REORDER POINT
# ──────────────────────────────────────────────────────────────────

@st.cache_data
def compute_stock_turnover(df_purchase: pd.DataFrame) -> pd.DataFrame:
    """
    Hitung Stock Turnover Rate per produk/kategori.

    Stock Turnover = Total Pembelian (unit) / Rata-rata Stok
    Karena data stok aktual tidak tersedia, kita gunakan proxy:
      - Total Qty dibeli sebagai proxy COGS
      - Avg monthly qty sebagai proxy rata-rata stok

    Returns: DataFrame dengan kolom turnover dan tier.
    """
    if df_purchase is None or df_purchase.empty:
        return pd.DataFrame()

    df = df_purchase.copy()
    df["Purchase Date"] = pd.to_datetime(df["Purchase Date"], errors="coerce")
    df = df.dropna(subset=["Purchase Date"])
    df["Receipt Qty"] = pd.to_numeric(df["Receipt Qty"], errors="coerce").fillna(0)
    df["Total"] = pd.to_numeric(df["Total"], errors="coerce").fillna(0)
    df["Price"] = pd.to_numeric(df["Price"], errors="coerce").fillna(0)

    # Periode analisis dalam bulan
    n_months = max(
        (df["Purchase Date"].max() - df["Purchase Date"].min()).days / 30, 1
    )

    product_df = (
        df.groupby("Product Name")
        .agg(
            Total_Qty=("Receipt Qty", "sum"),
            Total_Cost=("Total", "sum"),
            Avg_Price=("Price", "mean"),
            Order_Count=("Purchase Date", "nunique"),
            Category=("Category", "first"),
            Supplier=("Supplier Name", "first"),
        )
        .reset_index()
    )

    product_df["Monthly_Qty"] = product_df["Total_Qty"] / n_months
    product_df["Monthly_Cost"] = product_df["Total_Cost"] / n_months

    # Stock Turnover proxy: pembelian per bulan / (rata-rata stok = total / 2)
    # Ini heuristic — idealnya pakai data stok fisik
    product_df["Avg_Stock_Proxy"] = product_df["Total_Qty"] / 2
    product_df["Turnover_Rate"] = np.where(
        product_df["Avg_Stock_Proxy"] > 0,
        product_df["Total_Qty"] / product_df["Avg_Stock_Proxy"],
        0,
    )

    def _turnover_tier(rate):
        if rate >= 4:
            return "🟢 Fast Moving (>4x)"
        elif rate >= 2:
            return "🔵 Normal (2–4x)"
        elif rate >= 1:
            return "🟡 Slow Moving (1–2x)"
        else:
            return "🔴 Very Slow (<1x)"

    product_df["Turnover_Tier"] = product_df["Turnover_Rate"].apply(_turnover_tier)

    # Reorder Point sederhana: avg monthly usage × lead time (asumsi 2 minggu = 0.5 bulan)
    LEAD_TIME_MONTHS = 0.5
    SAFETY_STOCK_FACTOR = 1.5
    product_df["Reorder_Point_Qty"] = np.ceil(
        product_df["Monthly_Qty"] * LEAD_TIME_MONTHS * SAFETY_STOCK_FACTOR
    )
    product_df["Reorder_Point_Cost"] = (
        product_df["Reorder_Point_Qty"] * product_df["Avg_Price"]
    )

    return product_df.sort_values("Total_Cost", ascending=False).reset_index(drop=True)


@st.cache_data
def detect_overbuying(df_purchase: pd.DataFrame, df_gmv: pd.DataFrame = None) -> pd.DataFrame:
    """
    Deteksi kemungkinan pembelian berlebih berdasarkan:
    1. Konsistensi pembelian (CV tinggi = tidak stabil)
    2. Tren pembelian meningkat tanpa diikuti kenaikan penjualan

    Returns: DataFrame produk terindikasi overbuying.
    """
    if df_purchase is None or df_purchase.empty:
        return pd.DataFrame()

    df = df_purchase.copy()
    df["Purchase Date"] = pd.to_datetime(df["Purchase Date"], errors="coerce")
    df = df.dropna(subset=["Purchase Date"])
    df["Month"] = df["Purchase Date"].dt.to_period("M").dt.to_timestamp()
    df["Total"] = pd.to_numeric(df["Total"], errors="coerce").fillna(0)
    df["Receipt Qty"] = pd.to_numeric(df["Receipt Qty"], errors="coerce").fillna(0)

    monthly_by_product = (
        df.groupby(["Product Name", "Month"])
        .agg(Monthly_Cost=("Total", "sum"), Monthly_Qty=("Receipt Qty", "sum"))
        .reset_index()
    )

    consistency = (
        monthly_by_product.groupby("Product Name")
        .agg(
            Avg_Cost=("Monthly_Cost", "mean"),
            Std_Cost=("Monthly_Cost", "std"),
            Max_Cost=("Monthly_Cost", "max"),
            Min_Cost=("Monthly_Cost", "min"),
            Months_Active=("Month", "count"),
            Total_Cost=("Monthly_Cost", "sum"),
        )
        .reset_index()
    )
    consistency["Std_Cost"] = consistency["Std_Cost"].fillna(0)
    consistency["CV"] = (
        consistency["Std_Cost"] / consistency["Avg_Cost"].replace(0, 1)
    ) * 100

    # Tren pembelian: growth bulan terakhir vs sebelumnya
    last_two = monthly_by_product.groupby("Product Name").tail(2)
    growth_map = {}
    for prod, grp in last_two.groupby("Product Name"):
        if len(grp) >= 2:
            prev = grp.iloc[-2]["Monthly_Cost"]
            last = grp.iloc[-1]["Monthly_Cost"]
            growth_map[prod] = (last - prev) / (prev + 1) * 100
        else:
            growth_map[prod] = 0.0

    consistency["Purchase_Growth_%"] = consistency["Product Name"].map(growth_map).fillna(0)

    # Klasifikasi risiko overbuying
    def _risk(row):
        cv = row["CV"]
        growth = row["Purchase_Growth_%"]
        if cv > 80 and growth > 30:
            return "🔴 Risiko Tinggi"
        elif cv > 50 or growth > 50:
            return "🟡 Risiko Sedang"
        else:
            return "🟢 Normal"

    consistency["Overbuying_Risk"] = consistency.apply(_risk, axis=1)

    # Estimasi potensi pemborosan (bulan terakhir vs rata-rata)
    consistency["Potensi_Pemborosan"] = np.maximum(
        consistency["Max_Cost"] - consistency["Avg_Cost"], 0
    )

    return consistency[consistency["Months_Active"] >= 2].sort_values(
        "Potensi_Pemborosan", ascending=False
    ).reset_index(drop=True)


@st.cache_data
def get_purchase_vs_sales_correlation(
    df_purchase: pd.DataFrame, df_gmv: pd.DataFrame
) -> pd.DataFrame:
    """
    Korelasi bulanan antara total pembelian (cost) vs total penjualan (revenue).
    Berguna untuk melihat apakah food cost efisien.
    """
    if df_purchase is None or df_gmv is None:
        return pd.DataFrame()

    # Monthly purchase
    df_p = df_purchase.copy()
    df_p["Purchase Date"] = pd.to_datetime(df_p["Purchase Date"], errors="coerce")
    df_p["Total"] = pd.to_numeric(df_p["Total"], errors="coerce").fillna(0)
    df_p["Month"] = df_p["Purchase Date"].dt.to_period("M").dt.to_timestamp()
    monthly_purchase = (
        df_p.groupby("Month")["Total"].sum().reset_index().rename(columns={"Total": "Purchase_Cost"})
    )

    # Monthly sales
    df_g = df_gmv.copy()
    df_g["Sales Date In"] = pd.to_datetime(df_g["Sales Date In"], errors="coerce")
    df_g["Total After Bill Discount"] = pd.to_numeric(
        df_g["Total After Bill Discount"], errors="coerce"
    ).fillna(0)
    df_g["Month"] = df_g["Sales Date In"].dt.to_period("M").dt.to_timestamp()
    monthly_sales = (
        df_g.groupby("Month")["Total After Bill Discount"]
        .sum().reset_index().rename(columns={"Total After Bill Discount": "Revenue"})
    )

    merged = pd.merge(monthly_purchase, monthly_sales, on="Month", how="inner")
    if merged.empty:
        return pd.DataFrame()

    merged["Food_Cost_%"] = np.where(
        merged["Revenue"] > 0,
        merged["Purchase_Cost"] / merged["Revenue"] * 100,
        0,
    )
    merged["Food_Cost_Status"] = merged["Food_Cost_%"].apply(
        lambda x: "🟢 Ideal (<30%)" if x < 30
        else ("🟡 Aman (30–35%)" if x <= 35
              else "🔴 Tinggi (>35%)")
    )
    merged["Purchase_MoM_%"] = merged["Purchase_Cost"].pct_change() * 100
    merged["Revenue_MoM_%"] = merged["Revenue"].pct_change() * 100

    return merged.sort_values("Month")


@st.cache_data
def get_supplier_analysis(df_purchase: pd.DataFrame) -> pd.DataFrame:
    """
    Analisis performa supplier: total belanja, jumlah order, rata-rata per order,
    dan konsistensi harga.
    """
    if df_purchase is None or df_purchase.empty:
        return pd.DataFrame()

    df = df_purchase.copy()
    df["Total"] = pd.to_numeric(df["Total"], errors="coerce").fillna(0)
    df["Price"] = pd.to_numeric(df["Price"], errors="coerce").fillna(0)
    df["Receipt Qty"] = pd.to_numeric(df["Receipt Qty"], errors="coerce").fillna(0)
    df["Purchase Date"] = pd.to_datetime(df["Purchase Date"], errors="coerce")

    supplier_df = (
        df.groupby("Supplier Name")
        .agg(
            Total_Belanja=("Total", "sum"),
            Jumlah_Order=("Purchase Date", "nunique"),
            Jumlah_Produk=("Product Name", "nunique"),
            Avg_Per_Order=("Total", "mean"),
            First_Order=("Purchase Date", "min"),
            Last_Order=("Purchase Date", "max"),
        )
        .reset_index()
    )

    # Konsistensi harga per supplier (CV harga)
    price_cv = (
        df[df["Price"] > 0]
        .groupby("Supplier Name")["Price"]
        .agg(Std_Price="std", Avg_Price="mean")
        .reset_index()
    )
    price_cv["Price_CV"] = (
        price_cv["Std_Price"].fillna(0) / price_cv["Avg_Price"].replace(0, 1) * 100
    )

    supplier_df = pd.merge(supplier_df, price_cv[["Supplier Name", "Price_CV"]], on="Supplier Name", how="left")
    supplier_df["Price_CV"] = supplier_df["Price_CV"].fillna(0)

    def _reliability(row):
        cv = row["Price_CV"]
        orders = row["Jumlah_Order"]
        if cv < 10 and orders >= 3:
            return "🟢 Andalan"
        elif cv < 25:
            return "🔵 Cukup Andal"
        elif cv < 50:
            return "🟡 Perlu Negosiasi"
        else:
            return "🔴 Tidak Konsisten"

    supplier_df["Reliability"] = supplier_df.apply(_reliability, axis=1)
    supplier_df["Durasi_Hari"] = (
        supplier_df["Last_Order"] - supplier_df["First_Order"]
    ).dt.days.fillna(0)

    return supplier_df.sort_values("Total_Belanja", ascending=False).reset_index(drop=True)


@st.cache_data
def get_inventory_summary_stats(df_purchase: pd.DataFrame) -> dict:
    """Ringkasan statistik inventory untuk metrics cards."""
    if df_purchase is None or df_purchase.empty:
        return {}

    df = df_purchase.copy()
    df["Total"] = pd.to_numeric(df["Total"], errors="coerce").fillna(0)
    df["Purchase Date"] = pd.to_datetime(df["Purchase Date"], errors="coerce")

    n_months = max(
        (df["Purchase Date"].max() - df["Purchase Date"].min()).days / 30, 1
    )

    total_cost = df["Total"].sum()
    n_suppliers = df["Supplier Name"].nunique()
    n_products = df["Product Name"].nunique()
    monthly_avg = total_cost / n_months

    return {
        "total_cost": total_cost,
        "monthly_avg": monthly_avg,
        "n_suppliers": n_suppliers,
        "n_products": n_products,
        "n_months": round(n_months, 1),
    }
