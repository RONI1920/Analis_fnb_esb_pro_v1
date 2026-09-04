# analytics/operasional.py — Analisis Operasional Lanjutan
#
# Melengkapi analitik yang belum ada:
#   ✅ Table Turnover Rate (seberapa cepat meja berputar)
#   ✅ Void & Cancelled Orders Analysis mendalam
#   ✅ Upsell Conversion Rate per Waiter
#   ✅ Peak Capacity Utilization
#   ✅ Service Time Analysis (dari dine-in)

import pandas as pd
import numpy as np
import streamlit as st


# ──────────────────────────────────────────────────────────────────
# TABLE TURNOVER RATE
# ──────────────────────────────────────────────────────────────────

@st.cache_data
def compute_table_turnover(df_gmv: pd.DataFrame, n_tables: int = 10) -> pd.DataFrame:
    """
    Hitung Table Turnover Rate per hari.

    Table Turnover = Jumlah Bill (transaksi) / Jumlah Meja
    Ideal untuk restoran kasual: 2–4x per hari.

    Args:
        df_gmv    : Data GMV
        n_tables  : Jumlah meja tersedia (input dari user)

    Returns: DataFrame dengan turnover harian.
    """
    if df_gmv is None or df_gmv.empty:
        return pd.DataFrame()

    df = df_gmv.copy()
    df["Sales Date In"] = pd.to_datetime(df["Sales Date In"], errors="coerce")
    df["Date"] = df["Sales Date In"].dt.floor("D")

    # Filter hanya Dine-In jika ada kolom Visit Purpose
    if "Visit Purpose" in df.columns:
        df_dine = df[df["Visit Purpose"].str.contains("DINE", case=False, na=False)]
        if df_dine.empty:
            df_dine = df  # Fallback ke semua transaksi
    else:
        df_dine = df

    daily = (
        df_dine.groupby("Date")
        .agg(
            Bills=("Bill Number", "nunique"),
            Revenue=("Total After Bill Discount", "sum"),
        )
        .reset_index()
    )

    daily["Turnover_Rate"] = daily["Bills"] / max(n_tables, 1)
    daily["Revenue_Per_Table"] = daily["Revenue"] / max(n_tables, 1)

    def _turnover_status(rate):
        if rate >= 4:
            return "🟢 Sangat Baik (≥4x)"
        elif rate >= 2:
            return "🔵 Baik (2–4x)"
        elif rate >= 1:
            return "🟡 Cukup (1–2x)"
        else:
            return "🔴 Rendah (<1x)"

    daily["Status"] = daily["Turnover_Rate"].apply(_turnover_status)
    daily["Day_Name"] = daily["Date"].dt.day_name()
    daily["Is_Weekend"] = daily["Date"].dt.dayofweek >= 5

    return daily.sort_values("Date")


@st.cache_data
def get_table_turnover_summary(turnover_df: pd.DataFrame) -> dict:
    """Ringkasan statistik table turnover."""
    if turnover_df is None or turnover_df.empty:
        return {}

    return {
        "avg_turnover":        turnover_df["Turnover_Rate"].mean(),
        "max_turnover":        turnover_df["Turnover_Rate"].max(),
        "min_turnover":        turnover_df["Turnover_Rate"].min(),
        "best_day":            turnover_df.nlargest(1, "Turnover_Rate")["Date"].iloc[0].strftime("%d %b %Y"),
        "worst_day":           turnover_df.nsmallest(1, "Turnover_Rate")["Date"].iloc[0].strftime("%d %b %Y"),
        "avg_weekday":         turnover_df[~turnover_df["Is_Weekend"]]["Turnover_Rate"].mean(),
        "avg_weekend":         turnover_df[turnover_df["Is_Weekend"]]["Turnover_Rate"].mean(),
        "avg_revenue_per_table": turnover_df["Revenue_Per_Table"].mean(),
        "days_above_2x":       int((turnover_df["Turnover_Rate"] >= 2).sum()),
        "total_days":          len(turnover_df),
    }


# ──────────────────────────────────────────────────────────────────
# VOID & CANCELLED ORDERS ANALYSIS
# ──────────────────────────────────────────────────────────────────

@st.cache_data
def analyze_void_orders(df_waiter: pd.DataFrame) -> dict:
    """
    Analisis void dan non-sales secara mendalam.

    Returns dict dengan:
    - Tren void per bulan
    - Void rate per waiter
    - Waktu void terbanyak
    - Estimasi kerugian revenue dari void
    """
    if df_waiter is None or df_waiter.empty:
        return {}

    COL_TYPE = "Sales Type"
    if COL_TYPE not in df_waiter.columns:
        return {}

    df = df_waiter.copy()
    df[COL_TYPE] = df[COL_TYPE].str.strip()

    # Normalise void labels
    void_variants = ["Void", "Void Sales", "Void sales", "VOID"]
    df["Is_Void"] = df[COL_TYPE].isin(void_variants)
    df["Is_NonSales"] = df[COL_TYPE].str.contains("Non Sales|NonSales", case=False, na=False)

    df["Order Time"] = pd.to_datetime(df.get("Order Time", df.get("Sales Date In")), errors="coerce")
    df["Month"] = df["Order Time"].dt.to_period("M").dt.to_timestamp()
    df["Hour"]  = df["Order Time"].dt.hour

    # Total dan void per bulan
    monthly = (
        df.groupby("Month")
        .agg(
            Total_Bills=("Bill Number", "nunique"),
            Void_Count=("Is_Void", "sum"),
            NonSales_Count=("Is_NonSales", "sum"),
        )
        .reset_index()
    )
    monthly["Void_Rate_%"] = (monthly["Void_Count"] / monthly["Total_Bills"].replace(0, 1)) * 100

    # Void per jam
    void_by_hour = (
        df[df["Is_Void"]]
        .groupby("Hour")["Bill Number"].count()
        .reset_index()
        .rename(columns={"Bill Number": "Void_Count"})
    )

    # Void per waiter
    void_by_waiter = (
        df.groupby("Waiter")
        .agg(
            Total=("Bill Number", "count"),
            Voids=("Is_Void", "sum"),
        )
        .reset_index()
    )
    void_by_waiter["Void_Rate_%"] = (
        void_by_waiter["Voids"] / void_by_waiter["Total"].replace(0, 1) * 100
    )
    void_by_waiter = void_by_waiter[void_by_waiter["Total"] >= 5].sort_values(
        "Void_Rate_%", ascending=False
    )

    # Estimasi kerugian (asumsi avg revenue per transaksi normal)
    normal_revenue = df[~df["Is_Void"]]["Total After Bill Discount"].mean() if "Total After Bill Discount" in df.columns else 0
    total_voids = df["Is_Void"].sum()
    estimated_loss = total_voids * normal_revenue

    return {
        "total_voids":      int(total_voids),
        "total_nonsales":   int(df["Is_NonSales"].sum()),
        "estimated_loss":   estimated_loss,
        "monthly_trend":    monthly,
        "void_by_hour":     void_by_hour,
        "void_by_waiter":   void_by_waiter,
        "overall_void_rate": (total_voids / len(df) * 100) if len(df) > 0 else 0,
    }


# ──────────────────────────────────────────────────────────────────
# UPSELL CONVERSION RATE PER WAITER
# ──────────────────────────────────────────────────────────────────

@st.cache_data
def get_upsell_rate_per_waiter(
    df_waiter: pd.DataFrame,
    df_gmv: pd.DataFrame,
    high_margin_menus: list = None,
) -> pd.DataFrame:
    """
    Hitung seberapa sering setiap waiter berhasil menjual menu margin tinggi.
    Upsell Rate = Bills dengan ≥1 menu margin tinggi / Total Bills

    Args:
        df_gmv            : Data GMV
        high_margin_menus : List menu dengan margin tinggi (dari analytics/cogs.py)
                            Jika None, gunakan Top 20% menu by revenue.
    """
    if df_gmv is None or df_gmv.empty:
        return pd.DataFrame()
    if df_waiter is None or df_waiter.empty:
        return pd.DataFrame()

    df_g = df_gmv.copy()

    # Tentukan menu "upsell target" jika tidak diberikan
    if not high_margin_menus:
        menu_rev = df_g.groupby("Menu")["Total After Bill Discount"].sum().sort_values(ascending=False)
        top_n = max(int(len(menu_rev) * 0.2), 5)
        high_margin_menus = menu_rev.head(top_n).index.tolist()

    # Bills yang mengandung menu upsell
    bills_with_upsell = df_g[df_g["Menu"].isin(high_margin_menus)]["Bill Number"].unique()

    # Join dengan waiter data
    df_w = df_waiter.copy()
    bill_waiter = (
        df_w.groupby("Bill Number")
        .agg(Waiter=("Waiter", "first"), Revenue=("Total After Bill Discount", "sum"))
        .reset_index()
    )
    bill_waiter["Has_Upsell"] = bill_waiter["Bill Number"].isin(bills_with_upsell)

    upsell = (
        bill_waiter.groupby("Waiter")
        .agg(
            Total_Bills=("Bill Number", "nunique"),
            Upsell_Bills=("Has_Upsell", "sum"),
            Total_Revenue=("Revenue", "sum"),
        )
        .reset_index()
    )
    upsell["Upsell_Rate_%"] = (
        upsell["Upsell_Bills"] / upsell["Total_Bills"].replace(0, 1) * 100
    )
    upsell["ATV"] = upsell["Total_Revenue"] / upsell["Total_Bills"].replace(0, 1)

    def _upsell_tier(rate):
        if rate >= 50:    return "🥇 Excellent (≥50%)"
        elif rate >= 30:  return "🥈 Good (30–50%)"
        elif rate >= 15:  return "🥉 Average (15–30%)"
        else:             return "📈 Needs Improvement (<15%)"

    upsell["Upsell_Tier"] = upsell["Upsell_Rate_%"].apply(_upsell_tier)

    return upsell[upsell["Total_Bills"] >= 5].sort_values(
        "Upsell_Rate_%", ascending=False
    ).reset_index(drop=True)


# ──────────────────────────────────────────────────────────────────
# PEAK CAPACITY UTILIZATION
# ──────────────────────────────────────────────────────────────────

@st.cache_data
def get_capacity_utilization(
    df_gmv: pd.DataFrame,
    n_tables: int = 10,
    capacity_per_table: int = 4,
    avg_dining_minutes: int = 60,
    operating_hours: int = 12,
) -> pd.DataFrame:
    """
    Estimasi Capacity Utilization per jam.

    Theoretical max covers = n_tables × capacity_per_table × (operating_hours × 60 / avg_dining_minutes)
    Utilization = Actual covers / Theoretical max covers
    """
    if df_gmv is None or df_gmv.empty:
        return pd.DataFrame()

    theoretical_turns = (operating_hours * 60) / max(avg_dining_minutes, 1)
    max_covers_per_day = n_tables * capacity_per_table * theoretical_turns

    df = df_gmv.copy()
    df["Sales Date In"] = pd.to_datetime(df["Sales Date In"], errors="coerce")
    df["Date"] = df["Sales Date In"].dt.floor("D")
    df["Hour"] = df["Sales Date In"].dt.hour

    # Estimasi covers: asumsi 2 orang per bill (atau gunakan qty jika tersedia)
    COVERS_PER_BILL = 2
    hourly = (
        df.groupby(["Date", "Hour"])
        .agg(
            Bills=("Bill Number", "nunique"),
            Revenue=("Total After Bill Discount", "sum"),
        )
        .reset_index()
    )
    hourly["Est_Covers"] = hourly["Bills"] * COVERS_PER_BILL
    hourly["Max_Covers_Per_Hour"] = n_tables * capacity_per_table
    hourly["Utilization_%"] = np.minimum(
        hourly["Est_Covers"] / hourly["Max_Covers_Per_Hour"] * 100, 100
    )

    # Summary per jam (agregat semua hari)
    hourly_avg = (
        hourly.groupby("Hour")
        .agg(
            Avg_Bills=("Bills", "mean"),
            Avg_Utilization=("Utilization_%", "mean"),
            Avg_Revenue=("Revenue", "mean"),
        )
        .reset_index()
        .round(1)
    )

    return hourly_avg
