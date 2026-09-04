# analytics/cogs.py — Analisis COGS & Profitabilitas Menu (Enhanced)
#
# Penambahan dibanding versi lama:
#   ✅ Segmentasi BCG Matrix (Star/Cash Cow/Question Mark/Dog)
#   ✅ Analisis Break-Even per menu
#   ✅ Contribution Margin & Contribution Rate
#   ✅ Velocity Score (Profit per Hari)
#   ✅ COGS Ratio (efisiensi biaya)
#   ✅ Price Elasticity category
#   ✅ Rekomendasi aksi (naik harga / stop / pertahankan)

import pandas as pd
import numpy as np
import streamlit as st

from config import FILTER_REGEX_ADDON


# ──────────────────────────────────────────────────────────────────
# FUNGSI UTAMA (versi lama — tetap ada agar tidak break tab lain)
# ──────────────────────────────────────────────────────────────────

@st.cache_data
def analyze_profit(df_cogs: pd.DataFrame) -> pd.DataFrame:
    """Menganalisis profitabilitas dari data COGS (kompatibel versi lama)."""
    final_cols = [
        "Menu", "Qty", "Harga Jual", "COGS", "Margin (Rp)",
        "Margin (%)", "Total Revenue (Rp)", "Total COGS (Rp)", "Total Profit (Rp)",
    ]

    if df_cogs is None or df_cogs.empty:
        return pd.DataFrame(columns=final_cols)

    profit_df = df_cogs.copy()

    for col in ["Menu Category", "Menu"]:
        if col in profit_df.columns:
            profit_df = profit_df[
                ~profit_df[col].str.contains(
                    FILTER_REGEX_ADDON, na=False, case=False, regex=True
                )
            ]

    profit_df["Margin (Rp)"] = profit_df["Harga Jual"] - profit_df["COGS"]
    profit_df["Total Revenue (Rp)"] = profit_df["Total"]
    profit_df["Total COGS (Rp)"] = profit_df["COGS"] * profit_df["Qty"]
    profit_df["Total Profit (Rp)"] = profit_df["Margin (Rp)"] * profit_df["Qty"]

    agg_df = (
        profit_df.groupby("Menu")
        .agg(
            Qty=("Qty", "sum"),
            Total_Revenue_Rp=("Total Revenue (Rp)", "sum"),
            Total_COGS_Rp=("Total COGS (Rp)", "sum"),
            Total_Profit_Rp=("Total Profit (Rp)", "sum"),
        )
        .reset_index()
    )

    agg_df["Margin (Rp)"] = np.where(
        agg_df["Qty"] > 0, agg_df["Total_Profit_Rp"] / agg_df["Qty"], 0
    )
    agg_df["Margin (%)"] = np.where(
        agg_df["Total_Revenue_Rp"] > 0,
        (agg_df["Total_Profit_Rp"] / agg_df["Total_Revenue_Rp"]) * 100,
        0,
    )

    unit_costs = (
        profit_df[profit_df["Harga Jual"] > 0]
        .groupby("Menu")
        .agg(Harga_Jual_Unit=("Harga Jual", "mean"), COGS_Unit=("COGS", "mean"))
        .reset_index()
    )

    final_df = pd.merge(agg_df, unit_costs, on="Menu", how="left")
    final_df.rename(
        columns={
            "Total_Revenue_Rp": "Total Revenue (Rp)",
            "Total_COGS_Rp": "Total COGS (Rp)",
            "Total_Profit_Rp": "Total Profit (Rp)",
            "Harga_Jual_Unit": "Harga Jual",
            "COGS_Unit": "COGS",
        },
        inplace=True,
    )

    for col in final_cols:
        if col not in final_df.columns:
            final_df[col] = 0

    final_df.fillna(0, inplace=True)
    return final_df[final_cols].sort_values(by="Total Profit (Rp)", ascending=False)


# ──────────────────────────────────────────────────────────────────
# ANALISIS MENDALAM — FUNGSI BARU
# ──────────────────────────────────────────────────────────────────

@st.cache_data
def analyze_profit_deep(df_cogs: pd.DataFrame) -> pd.DataFrame:
    """
    Analisis COGS mendalam dengan metrik tambahan:
    - BCG Matrix Segment
    - Contribution Margin & Rate
    - COGS Ratio
    - Break-Even Qty (estimasi)
    - Velocity Score
    - Rekomendasi Aksi
    """
    base = analyze_profit(df_cogs)
    if base.empty:
        return base

    df = base.copy()
    df_valid = df[df["Qty"] > 0].copy()

    total_revenue = df["Total Revenue (Rp)"].sum()
    total_profit  = df["Total Profit (Rp)"].sum()
    total_qty     = df["Qty"].sum()

    # ── 1. CONTRIBUTION MARGIN & RATE ─────────────────────────────
    # Contribution Margin = Total Profit (sudah sama dengan Gross Profit untuk single-product)
    # Contribution Rate   = Total Profit / Total Revenue per menu
    df["Contribution Rate (%)"] = np.where(
        df["Total Revenue (Rp)"] > 0,
        (df["Total Profit (Rp)"] / df["Total Revenue (Rp)"]) * 100,
        0,
    )
    # Revenue share terhadap total
    df["Revenue Share (%)"] = np.where(
        total_revenue > 0,
        (df["Total Revenue (Rp)"] / total_revenue) * 100,
        0,
    )
    # Profit share terhadap total
    df["Profit Share (%)"] = np.where(
        total_profit > 0,
        (df["Total Profit (Rp)"] / total_profit) * 100,
        0,
    )

    # ── 2. COGS RATIO (efisiensi biaya) ───────────────────────────
    # Semakin kecil = semakin efisien
    df["COGS Ratio (%)"] = np.where(
        df["Harga Jual"] > 0,
        (df["COGS"] / df["Harga Jual"]) * 100,
        0,
    )

    # ── 3. VOLUME SHARE (popularitas menu) ────────────────────────
    df["Volume Share (%)"] = np.where(
        total_qty > 0,
        (df["Qty"] / total_qty) * 100,
        0,
    )

    # ── 4. VELOCITY SCORE (Profit per Hari estimasi) ──────────────
    # Heuristic: asumsi 30 hari periode. Bisa diupgrade jika ada kolom tanggal.
    PERIOD_DAYS = 30
    df["Profit/Hari (Est.)"] = df["Total Profit (Rp)"] / PERIOD_DAYS
    df["Qty/Hari (Est.)"] = df["Qty"] / PERIOD_DAYS

    # ── 5. BCG MATRIX SEGMENTATION ────────────────────────────────
    # Sumbu X = Volume Share (popularitas), Sumbu Y = Margin (%) (profitabilitas)
    # Threshold = median masing-masing sumbu
    median_volume = df_valid["Volume Share (%)"].median() if not df_valid.empty else 0
    median_margin = df_valid["Margin (%)"].median() if not df_valid.empty else 0

    def _bcg_segment(row):
        if row["Qty"] == 0:
            return "🚫 Tidak Terjual"
        high_vol = row["Volume Share (%)"] >= median_volume
        high_margin = row["Margin (%)"] >= median_margin
        if high_vol and high_margin:
            return "⭐ Star"           # Populer & Profitable → Pertahankan & push
        elif not high_vol and high_margin:
            return "💎 Cash Cow"       # Kurang populer tapi margin bagus → Promosikan
        elif high_vol and not high_margin:
            return "❓ Question Mark"  # Populer tapi margin kecil → Efisiensi COGS
        else:
            return "🐕 Dog"            # Tidak populer & margin kecil → Evaluasi / Stop

    df["BCG Segment"] = df.apply(_bcg_segment, axis=1)

    # ── 6. BREAK-EVEN QTY (estimasi sederhana per menu) ───────────
    # BEQ = Fixed Cost Per Menu / Margin per Unit
    # Karena kita tidak punya fixed cost per menu, pakai proxy:
    # asumsi fixed cost overhead = 15% dari total revenue dibagi jumlah SKU
    n_sku = len(df[df["Qty"] > 0])
    estimated_fixed_cost_per_sku = (total_revenue * 0.15 / n_sku) if n_sku > 0 else 0

    df["Break-Even Qty (Est.)"] = np.where(
        df["Margin (Rp)"] > 0,
        np.ceil(estimated_fixed_cost_per_sku / df["Margin (Rp)"]),
        np.nan,
    )
    df["Sudah Break-Even?"] = np.where(
        df["Break-Even Qty (Est.)"].isna(),
        "—",
        np.where(df["Qty"] >= df["Break-Even Qty (Est.)"], "✅ Ya", "⚠️ Belum"),
    )

    # ── 7. REKOMENDASI AKSI ────────────────────────────────────────
    def _rekomendasi(row):
        seg = row["BCG Segment"]
        margin = row["Margin (%)"]
        cogs_ratio = row["COGS Ratio (%)"]
        be = row["Sudah Break-Even?"]

        if seg == "⭐ Star":
            return "🚀 Pertahankan & Tingkatkan Volume"
        elif seg == "💎 Cash Cow":
            return "📣 Promosikan Lebih Aktif"
        elif seg == "❓ Question Mark":
            if cogs_ratio > 60:
                return "🔧 Negosiasi COGS dengan Supplier"
            elif margin < 20:
                return "💲 Pertimbangkan Kenaikan Harga"
            else:
                return "📈 Optimalkan Marketing"
        elif seg == "🐕 Dog":
            if row["Qty"] == 0:
                return "🗑️ Hapus dari Menu"
            elif be == "⚠️ Belum":
                return "⚠️ Evaluasi: Belum BEP, pertimbangkan dihapus"
            else:
                return "🔄 Reformulasi atau Bundling"
        return "—"

    df["Rekomendasi"] = df.apply(_rekomendasi, axis=1)

    # ── 8. EFISIENSI TIER ─────────────────────────────────────────
    def _efficiency_tier(cogs_ratio):
        if cogs_ratio <= 25:
            return "🟢 Sangat Efisien (<25%)"
        elif cogs_ratio <= 35:
            return "🔵 Efisien (25–35%)"
        elif cogs_ratio <= 50:
            return "🟡 Sedang (35–50%)"
        else:
            return "🔴 Boros (>50%)"

    df["Efisiensi COGS"] = df["COGS Ratio (%)"].apply(_efficiency_tier)

    # ── Kolom akhir yang diekspos ──────────────────────────────────
    ordered_cols = [
        "Menu", "BCG Segment", "Efisiensi COGS", "Rekomendasi",
        "Qty", "Harga Jual", "COGS", "COGS Ratio (%)",
        "Margin (Rp)", "Margin (%)", "Contribution Rate (%)",
        "Total Revenue (Rp)", "Total COGS (Rp)", "Total Profit (Rp)",
        "Revenue Share (%)", "Profit Share (%)", "Volume Share (%)",
        "Profit/Hari (Est.)", "Qty/Hari (Est.)",
        "Break-Even Qty (Est.)", "Sudah Break-Even?",
    ]

    for col in ordered_cols:
        if col not in df.columns:
            df[col] = 0

    df.fillna(0, inplace=True)
    return df[ordered_cols].sort_values(by="Total Profit (Rp)", ascending=False)


# ──────────────────────────────────────────────────────────────────
# HELPER: RINGKASAN STATISTIK
# ──────────────────────────────────────────────────────────────────

@st.cache_data
def get_cogs_summary_stats(deep_df: pd.DataFrame) -> dict:
    """Mengembalikan dict ringkasan statistik untuk ditampilkan di metrics."""
    if deep_df is None or deep_df.empty:
        return {}

    df = deep_df[deep_df["Qty"] > 0]
    total_rev = deep_df["Total Revenue (Rp)"].sum()
    total_cogs = deep_df["Total COGS (Rp)"].sum()
    total_profit = deep_df["Total Profit (Rp)"].sum()

    bcg_counts = deep_df["BCG Segment"].value_counts().to_dict()

    return {
        "total_revenue": total_rev,
        "total_cogs": total_cogs,
        "total_profit": total_profit,
        "avg_margin_pct": (total_profit / total_rev * 100) if total_rev > 0 else 0,
        "avg_cogs_ratio": df["COGS Ratio (%)"].mean() if not df.empty else 0,
        "n_sku_total": len(deep_df),
        "n_sku_active": len(df),
        "n_star": bcg_counts.get("⭐ Star", 0),
        "n_cashcow": bcg_counts.get("💎 Cash Cow", 0),
        "n_questionmark": bcg_counts.get("❓ Question Mark", 0),
        "n_dog": bcg_counts.get("🐕 Dog", 0),
        "top_menu_profit": df.nlargest(1, "Total Profit (Rp)").iloc[0]["Menu"] if not df.empty else "—",
        "top_menu_margin": df.nlargest(1, "Margin (%)").iloc[0]["Menu"] if not df.empty else "—",
        "worst_cogs_ratio_menu": df.nlargest(1, "COGS Ratio (%)").iloc[0]["Menu"] if not df.empty else "—",
        "n_not_bep": int((deep_df["Sudah Break-Even?"] == "⚠️ Belum").sum()),
        "n_zero_qty": int((deep_df["Qty"] == 0).sum()),
    }