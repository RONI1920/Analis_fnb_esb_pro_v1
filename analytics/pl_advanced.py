# analytics/pl_advanced.py — Analisis P&L Lanjutan
#
# Melengkapi tab13_pl.py yang sudah ada dengan:
#   ✅ P&L Summary lengkap (Revenue - COGS - Overhead = Net Profit)
#   ✅ MoM & YoY Comparison
#   ✅ Expense Ratio Benchmark (vs standar industri F&B)
#   ✅ Break-Even Analysis bisnis keseluruhan
#   ✅ Cash Flow Projection sederhana
#   ✅ Target vs Actual tracking per kategori

import pandas as pd
import numpy as np
import streamlit as st


# ──────────────────────────────────────────────────────────────────
# BENCHMARK INDUSTRI F&B (INDONESIA)
# ──────────────────────────────────────────────────────────────────

FNB_BENCHMARKS = {
    "COGS_pct":      {"ideal": 30.0, "warning": 35.0, "label": "Food Cost %"},
    "Labor_pct":     {"ideal": 25.0, "warning": 35.0, "label": "Labor Cost %"},
    "Overhead_pct":  {"ideal": 15.0, "warning": 25.0, "label": "Overhead %"},
    "Net_Profit_pct": {"ideal": 15.0, "warning": 8.0,  "label": "Net Profit Margin %"},
    "Gross_Margin":  {"ideal": 65.0, "warning": 55.0, "label": "Gross Margin %"},
}


# ──────────────────────────────────────────────────────────────────
# FUNGSI UTAMA
# ──────────────────────────────────────────────────────────────────

@st.cache_data
def compute_pl_summary(df_pl: pd.DataFrame) -> dict:
    """
    Hitung ringkasan P&L komprehensif dari data yang sudah di-melt.

    Struktur df_pl yang diharapkan (dari load_pl_data):
        - Account, Description, Date, Month_Name, Year_Type, Branch, Value, Category

    Returns: dict dengan semua KPI finansial.
    """
    if df_pl is None or df_pl.empty:
        return {}

    df_curr = df_pl[df_pl.get("Year_Type", pd.Series()) == "Current Year"] if "Year_Type" in df_pl.columns else df_pl
    if df_curr.empty:
        df_curr = df_pl.copy()

    total_rev  = df_curr[df_curr["Category"] == "Revenue"]["Value"].sum()
    total_cogs = df_curr[df_curr["Category"] == "COGS"]["Value"].sum()
    total_exp  = df_curr[df_curr["Category"] == "Expense"]["Value"].sum()

    gross_profit = total_rev - total_cogs
    net_profit   = gross_profit - total_exp
    ebitda       = net_profit  # Simplified — tanpa D&A karena tidak ada data

    gp_margin  = (gross_profit / total_rev * 100) if total_rev > 0 else 0
    np_margin  = (net_profit   / total_rev * 100) if total_rev > 0 else 0
    cogs_pct   = (total_cogs   / total_rev * 100) if total_rev > 0 else 0
    exp_pct    = (total_exp    / total_rev * 100) if total_rev > 0 else 0

    # Benchmark status
    def _status(value, benchmark_key, higher_is_better=True):
        b = FNB_BENCHMARKS.get(benchmark_key, {})
        ideal   = b.get("ideal", 0)
        warning = b.get("warning", 0)
        if higher_is_better:
            if value >= ideal:    return "🟢"
            elif value >= warning: return "🟡"
            else:                  return "🔴"
        else:
            if value <= ideal:    return "🟢"
            elif value <= warning: return "🟡"
            else:                  return "🔴"

    return {
        "total_revenue":   total_rev,
        "total_cogs":      total_cogs,
        "total_expense":   total_exp,
        "gross_profit":    gross_profit,
        "net_profit":      net_profit,
        "ebitda":          ebitda,
        "gp_margin":       gp_margin,
        "np_margin":       np_margin,
        "cogs_pct":        cogs_pct,
        "exp_pct":         exp_pct,
        "status_gm":       _status(gp_margin,  "Gross_Margin",  True),
        "status_npm":      _status(np_margin,  "Net_Profit_pct", True),
        "status_cogs":     _status(cogs_pct,   "COGS_pct",      False),
        "status_exp":      _status(exp_pct,    "Overhead_pct",  False),
        "health_label":    (
            "🟢 Sangat Sehat" if np_margin >= 20
            else ("🟡 Cukup Sehat" if np_margin >= 10
                  else ("🟠 Waspada" if np_margin >= 0
                        else "🔴 Merugi"))
        ),
    }


@st.cache_data
def get_pl_mom_comparison(df_pl: pd.DataFrame) -> pd.DataFrame:
    """
    MoM (Month-over-Month) comparison untuk Revenue, COGS, Gross Profit, Net Profit.
    """
    if df_pl is None or df_pl.empty or "Date" not in df_pl.columns:
        return pd.DataFrame()

    df = df_pl.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df_curr = df[df.get("Year_Type", pd.Series()) == "Current Year"] if "Year_Type" in df.columns else df

    monthly = (
        df_curr.groupby("Date")
        .apply(lambda x: pd.Series({
            "Revenue":      x[x["Category"] == "Revenue"]["Value"].sum(),
            "COGS":         x[x["Category"] == "COGS"]["Value"].sum(),
            "Expense":      x[x["Category"] == "Expense"]["Value"].sum(),
        }))
        .reset_index()
    )
    monthly["Gross_Profit"] = monthly["Revenue"] - monthly["COGS"]
    monthly["Net_Profit"]   = monthly["Gross_Profit"] - monthly["Expense"]
    monthly["GP_Margin_%"]  = np.where(monthly["Revenue"] > 0, monthly["Gross_Profit"] / monthly["Revenue"] * 100, 0)
    monthly["NP_Margin_%"]  = np.where(monthly["Revenue"] > 0, monthly["Net_Profit"]   / monthly["Revenue"] * 100, 0)

    for col in ["Revenue", "Gross_Profit", "Net_Profit"]:
        monthly[f"{col}_MoM_%"] = monthly[col].pct_change() * 100

    return monthly.sort_values("Date")


@st.cache_data
def get_pl_yoy_comparison(df_pl: pd.DataFrame) -> pd.DataFrame:
    """
    YoY comparison (Current Year vs Last Year) jika data tersedia.
    """
    if df_pl is None or df_pl.empty or "Year_Type" not in df_pl.columns:
        return pd.DataFrame()

    df = df_pl.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    results = []
    for year_type in ["Current Year", "Last Year"]:
        sub = df[df["Year_Type"] == year_type]
        if sub.empty:
            continue
        rev  = sub[sub["Category"] == "Revenue"]["Value"].sum()
        cogs = sub[sub["Category"] == "COGS"]["Value"].sum()
        exp  = sub[sub["Category"] == "Expense"]["Value"].sum()
        gp   = rev - cogs
        np_  = gp - exp
        results.append({
            "Periode":       year_type,
            "Revenue":       rev,
            "COGS":          cogs,
            "Gross_Profit":  gp,
            "Expense":       exp,
            "Net_Profit":    np_,
            "GP_Margin_%":   (gp  / rev * 100) if rev > 0 else 0,
            "NP_Margin_%":   (np_ / rev * 100) if rev > 0 else 0,
        })

    if len(results) < 2:
        return pd.DataFrame(results)

    df_yoy = pd.DataFrame(results)
    # Hitung growth
    curr = df_yoy[df_yoy["Periode"] == "Current Year"].iloc[0]
    prev = df_yoy[df_yoy["Periode"] == "Last Year"].iloc[0]

    growth_row = {"Periode": "YoY Growth %"}
    for col in ["Revenue", "Gross_Profit", "Net_Profit"]:
        growth_row[col] = (curr[col] - prev[col]) / (prev[col] + 1) * 100
    growth_row["COGS"]       = (curr["COGS"] - prev["COGS"]) / (prev["COGS"] + 1) * 100
    growth_row["Expense"]    = (curr["Expense"] - prev["Expense"]) / (prev["Expense"] + 1) * 100
    growth_row["GP_Margin_%"] = curr["GP_Margin_%"] - prev["GP_Margin_%"]
    growth_row["NP_Margin_%"] = curr["NP_Margin_%"] - prev["NP_Margin_%"]

    return pd.concat([df_yoy, pd.DataFrame([growth_row])], ignore_index=True)


@st.cache_data
def get_business_breakeven(df_pl: pd.DataFrame, df_gmv: pd.DataFrame = None) -> dict:
    """
    Break-Even Analysis untuk bisnis secara keseluruhan.

    Break-Even Revenue = Fixed Cost / Contribution Margin Ratio
    CMR = (Revenue - Variable Cost) / Revenue
    """
    if df_pl is None or df_pl.empty:
        return {}

    df = df_pl.copy()
    df_curr = df[df.get("Year_Type", pd.Series()) == "Current Year"] if "Year_Type" in df.columns else df

    total_rev  = df_curr[df_curr["Category"] == "Revenue"]["Value"].sum()
    total_cogs = df_curr[df_curr["Category"] == "COGS"]["Value"].sum()
    total_exp  = df_curr[df_curr["Category"] == "Expense"]["Value"].sum()

    if total_rev <= 0:
        return {}

    # Asumsi: COGS = variable cost, Expense = fixed cost
    variable_cost = total_cogs
    fixed_cost    = total_exp

    contribution_margin = total_rev - variable_cost
    cmr = contribution_margin / total_rev if total_rev > 0 else 0

    breakeven_revenue = fixed_cost / cmr if cmr > 0 else 0
    breakeven_pct     = (breakeven_revenue / total_rev * 100) if total_rev > 0 else 0
    margin_of_safety  = total_rev - breakeven_revenue
    mos_pct           = (margin_of_safety / total_rev * 100) if total_rev > 0 else 0

    # Estimasi berapa transaksi perlu BEP (butuh data GMV)
    be_transactions = None
    if df_gmv is not None and not df_gmv.empty:
        avg_transaction = df_gmv["Total After Bill Discount"].sum() / df_gmv["Bill Number"].nunique()
        if avg_transaction > 0:
            be_transactions = int(np.ceil(breakeven_revenue / avg_transaction))

    return {
        "total_revenue":      total_rev,
        "fixed_cost":         fixed_cost,
        "variable_cost":      variable_cost,
        "contribution_margin": contribution_margin,
        "cmr":                cmr,
        "breakeven_revenue":  breakeven_revenue,
        "breakeven_pct":      breakeven_pct,
        "margin_of_safety":   margin_of_safety,
        "mos_pct":            mos_pct,
        "be_transactions":    be_transactions,
        "is_above_be":        total_rev > breakeven_revenue,
    }


@st.cache_data
def get_expense_benchmark(df_pl: pd.DataFrame) -> pd.DataFrame:
    """
    Bandingkan struktur biaya aktual vs benchmark industri F&B.
    """
    if df_pl is None or df_pl.empty:
        return pd.DataFrame()

    df = df_pl.copy()
    df_curr = df[df.get("Year_Type", pd.Series()) == "Current Year"] if "Year_Type" in df.columns else df

    total_rev = df_curr[df_curr["Category"] == "Revenue"]["Value"].sum()
    if total_rev <= 0:
        return pd.DataFrame()

    rows = []
    for cat, label, benchmark_pct in [
        ("COGS",    "Food Cost (COGS)",   30.0),
        ("Expense", "Operating Expense",  25.0),
    ]:
        actual = df_curr[df_curr["Category"] == cat]["Value"].sum()
        actual_pct = actual / total_rev * 100
        gap = actual_pct - benchmark_pct
        rows.append({
            "Kategori":        label,
            "Aktual (Rp)":     actual,
            "Aktual (%)":      round(actual_pct, 1),
            "Benchmark (%)":   benchmark_pct,
            "Gap (%)":         round(gap, 1),
            "Status":          (
                "🟢 Di Bawah Benchmark" if gap <= 0
                else ("🟡 Sedikit Tinggi (+{:.1f}%)".format(gap) if gap <= 5
                      else "🔴 Di Atas Benchmark (+{:.1f}%)".format(gap))
            ),
        })

    return pd.DataFrame(rows)


@st.cache_data
def get_cash_flow_projection(df_pl: pd.DataFrame, months_ahead: int = 3) -> pd.DataFrame:
    """
    Proyeksi cash flow sederhana berdasarkan tren historis.
    Menggunakan rata-rata 3 bulan terakhir + growth rate sebagai dasar.
    """
    if df_pl is None or df_pl.empty or "Date" not in df_pl.columns:
        return pd.DataFrame()

    monthly = get_pl_mom_comparison(df_pl)
    if monthly.empty or len(monthly) < 2:
        return pd.DataFrame()

    last_date = pd.to_datetime(monthly["Date"].max())

    # Growth rate rata-rata 3 bulan terakhir
    recent = monthly.tail(3)
    avg_rev_growth   = recent["Revenue_MoM_%"].mean() / 100 if "Revenue_MoM_%" in recent else 0
    avg_cogs_growth  = recent["COGS"].pct_change().mean()
    avg_exp_growth   = recent["Expense"].pct_change().mean()

    avg_rev_growth  = np.clip(avg_rev_growth, -0.2, 0.3)
    avg_cogs_growth = np.clip(avg_cogs_growth if not np.isnan(avg_cogs_growth) else 0, -0.2, 0.3)
    avg_exp_growth  = np.clip(avg_exp_growth  if not np.isnan(avg_exp_growth)  else 0, -0.1, 0.2)

    base_rev  = monthly.iloc[-1]["Revenue"]
    base_cogs = monthly.iloc[-1]["COGS"]
    base_exp  = monthly.iloc[-1]["Expense"]

    projections = []
    for i in range(1, months_ahead + 1):
        proj_date  = last_date + pd.DateOffset(months=i)
        proj_rev   = base_rev  * (1 + avg_rev_growth)  ** i
        proj_cogs  = base_cogs * (1 + avg_cogs_growth) ** i
        proj_exp   = base_exp  * (1 + avg_exp_growth)  ** i
        proj_gp    = proj_rev  - proj_cogs
        proj_np    = proj_gp   - proj_exp

        projections.append({
            "Date":          proj_date,
            "Revenue":       proj_rev,
            "COGS":          proj_cogs,
            "Expense":       proj_exp,
            "Gross_Profit":  proj_gp,
            "Net_Profit":    proj_np,
            "GP_Margin_%":   (proj_gp / proj_rev * 100) if proj_rev > 0 else 0,
            "NP_Margin_%":   (proj_np / proj_rev * 100) if proj_rev > 0 else 0,
            "Type":          "Proyeksi",
        })

    # Gabungkan histori + proyeksi
    hist = monthly.copy()
    hist["Type"] = "Historis"
    hist = hist[["Date", "Revenue", "COGS", "Expense", "Gross_Profit", "Net_Profit",
                 "GP_Margin_%", "NP_Margin_%", "Type"]]

    combined = pd.concat([hist, pd.DataFrame(projections)], ignore_index=True)
    return combined.sort_values("Date").reset_index(drop=True)
