# analytics/rekomendasi.py — Rekomendasi Multi-Source: MBA + COGS + Musiman + Ulasan

import pandas as pd
import numpy as np
import streamlit as st


@st.cache_data
def get_menu_margin_map(df_cogs: pd.DataFrame) -> dict:
    """
    Buat mapping menu → margin_pct dari data COGS.
    Returns: {menu_name: margin_pct}
    """
    if df_cogs is None or df_cogs.empty:
        return {}

    col_price = "Harga Jual" if "Harga Jual" in df_cogs.columns else "Price"
    col_cogs  = "COGS"       if "COGS"       in df_cogs.columns else "COGS Total"

    df = df_cogs.copy()
    for col in ["Qty", col_price, col_cogs]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df = df[(df[col_price] > 0) & (df["Qty"] > 0)].copy()
    if df.empty:
        return {}

    df["COGS_per_unit"] = df[col_cogs] / df["Qty"]
    menu_df = df.groupby("Menu").agg(
        Price=(col_price, "median"),
        COGS=("COGS_per_unit", "median"),
    ).reset_index()
    menu_df["Margin_Pct"] = ((menu_df["Price"] - menu_df["COGS"]) / menu_df["Price"]) * 100
    return dict(zip(menu_df["Menu"], menu_df["Margin_Pct"]))


@st.cache_data
def get_seasonal_menu_performance(df_gmv: pd.DataFrame, df_kalender: pd.DataFrame) -> pd.DataFrame:
    """
    Hitung rata-rata penjualan per menu per tipe event (musiman).
    Returns: DataFrame [Menu, Tipe_Event, Avg_Daily_Revenue, Lift_vs_Normal]
    """
    if df_gmv is None or df_kalender is None:
        return pd.DataFrame()

    df = df_gmv.copy()
    df["Tanggal"] = pd.to_datetime(df["Sales Date In"]).dt.normalize()
    df["Total After Bill Discount"] = pd.to_numeric(df["Total After Bill Discount"], errors="coerce").fillna(0)

    kal = df_kalender.copy()
    kal["Tanggal"] = pd.to_datetime(kal["Tanggal"])
    kal["Tipe_Event"] = kal["Tipe_Event"].fillna("Biasa").astype(str)
    NORMAL = {"biasa", ""}
    kal["Is_Event"] = ~kal["Tipe_Event"].str.strip().str.lower().isin(NORMAL)

    df = df.merge(kal[["Tanggal", "Tipe_Event", "Is_Event"]], on="Tanggal", how="left")
    df["Tipe_Event"] = df["Tipe_Event"].fillna("Biasa")
    df["Is_Event"]   = df["Is_Event"].fillna(False)

    # Avg revenue per menu per tipe event
    menu_event = (
        df.groupby(["Menu", "Tipe_Event"])
        .agg(Total_Revenue=("Total After Bill Discount", "sum"),
             Days=("Tanggal", "nunique"))
        .reset_index()
    )
    menu_event["Avg_Daily"] = menu_event["Total_Revenue"] / menu_event["Days"].replace(0, 1)

    # Lift vs "Biasa"
    normal_avg = menu_event[menu_event["Tipe_Event"] == "Biasa"].set_index("Menu")["Avg_Daily"]
    menu_event["Lift_vs_Normal"] = menu_event.apply(
        lambda r: r["Avg_Daily"] / normal_avg.get(r["Menu"], r["Avg_Daily"])
        if r["Tipe_Event"] != "Biasa" else 1.0,
        axis=1,
    )
    return menu_event[menu_event["Tipe_Event"] != "Biasa"].sort_values("Lift_vs_Normal", ascending=False)


@st.cache_data
def get_multi_source_recommendations(
    df_gmv: pd.DataFrame,
    df_cogs: pd.DataFrame = None,
    df_kalender: pd.DataFrame = None,
    df_ulasan: pd.DataFrame = None,
    top_n: int = 20,
) -> pd.DataFrame:
    """
    Skor rekomendasi menu gabungan dari 4 sumber:
      1. Popularitas     — total qty terjual (dari GMV)
      2. Profitabilitas  — margin % (dari COGS)
      3. Tren            — growth MoM (dari GMV)
      4. Sentimen ulasan — proporsi ulasan positif (dari Ulasan)

    Setiap dimensi dinormalisasi 0-100, lalu digabung dengan bobot.
    Returns: DataFrame rekomendasi dengan skor gabungan.
    """
    if df_gmv is None or df_gmv.empty:
        return pd.DataFrame()

    df = df_gmv.copy()
    df["Total After Bill Discount"] = pd.to_numeric(df["Total After Bill Discount"], errors="coerce").fillna(0)
    df["Qty"] = pd.to_numeric(df["Qty"], errors="coerce").fillna(0)
    df["Sales Date In"] = pd.to_datetime(df["Sales Date In"], errors="coerce")
    df = df[df.get("Price (Net)", pd.Series(dtype=float)).gt(0) | True]  # keep all

    # Filter noise
    if "Price (Net)" in df.columns:
        df["Price (Net)"] = pd.to_numeric(df["Price (Net)"], errors="coerce").fillna(0)
        df = df[df["Price (Net)"] > 0]

    # ── Skor 1: Popularitas ────────────────────────────────
    pop = df.groupby("Menu").agg(
        Total_Qty=("Qty", "sum"),
        Total_Revenue=("Total After Bill Discount", "sum"),
    ).reset_index()

    # ── Skor 2: Tren MoM ──────────────────────────────────
    df["Month"] = df["Sales Date In"].dt.to_period("M")
    monthly = df.groupby(["Menu", "Month"])["Total After Bill Discount"].sum().reset_index()
    monthly = monthly.sort_values(["Menu", "Month"])

    # Growth = (bulan terakhir - bulan sebelumnya) / bulan sebelumnya
    last_two = monthly.groupby("Menu").tail(2)
    growth_map = {}
    for menu, grp in last_two.groupby("Menu"):
        if len(grp) >= 2:
            prev, last = grp.iloc[-2]["Total After Bill Discount"], grp.iloc[-1]["Total After Bill Discount"]
            growth_map[menu] = (last - prev) / (prev + 1) * 100
        else:
            growth_map[menu] = 0.0

    pop["Growth_MoM"] = pop["Menu"].map(growth_map).fillna(0)

    # ── Skor 3: Margin (dari COGS) ─────────────────────────
    margin_map = get_menu_margin_map(df_cogs) if df_cogs is not None else {}
    pop["Margin_Pct"] = pop["Menu"].map(margin_map).fillna(50.0)  # default 50% jika tidak ada data COGS

    # ── Skor 4: Sentimen Ulasan ────────────────────────────
    sentiment_map = {}
    if df_ulasan is not None and not df_ulasan.empty and "Ulasan" in df_ulasan.columns:
        # Cari mention menu dalam teks ulasan
        for menu in pop["Menu"].unique():
            menu_lower = menu.lower()
            mentions = df_ulasan["Ulasan"].astype(str).str.lower().str.contains(
                menu_lower[:10], regex=False, na=False  # first 10 chars to avoid false negatives
            )
            if mentions.sum() > 0:
                rating_col = "Rating_Clean" if "Rating_Clean" in df_ulasan.columns else "Rating"
                pos_rate = (df_ulasan[mentions][rating_col].astype(float) >= 4).mean() * 100
                sentiment_map[menu] = pos_rate
    pop["Sentimen_Positif"] = pop["Menu"].map(sentiment_map).fillna(70.0)  # default 70% jika tidak ada data

    # ── Normalisasi 0-100 ──────────────────────────────────
    def normalize(series):
        mn, mx = series.min(), series.max()
        if mx == mn:
            return pd.Series([50.0] * len(series), index=series.index)
        return (series - mn) / (mx - mn) * 100

    pop["Norm_Popularitas"]  = normalize(pop["Total_Qty"])
    pop["Norm_Tren"]         = normalize(pop["Growth_MoM"])
    pop["Norm_Margin"]       = normalize(pop["Margin_Pct"].clip(0, 100))
    pop["Norm_Sentimen"]     = normalize(pop["Sentimen_Positif"])

    # ── Skor Gabungan (bobot) ──────────────────────────────
    WEIGHTS = {
        "popularitas": 0.35,
        "margin":      0.30,
        "tren":        0.20,
        "sentimen":    0.15,
    }
    pop["Skor_Gabungan"] = (
        pop["Norm_Popularitas"] * WEIGHTS["popularitas"] +
        pop["Norm_Margin"]      * WEIGHTS["margin"]      +
        pop["Norm_Tren"]        * WEIGHTS["tren"]        +
        pop["Norm_Sentimen"]    * WEIGHTS["sentimen"]
    )

    # ── Klasifikasi Rekomendasi ────────────────────────────
    threshold_high = pop["Skor_Gabungan"].quantile(0.75)
    threshold_low  = pop["Skor_Gabungan"].quantile(0.25)

    def classify(row):
        score = row["Skor_Gabungan"]
        margin = row["Margin_Pct"]
        growth = row["Growth_MoM"]
        if score >= threshold_high:
            return "🚀 Promosikan"
        elif margin < 30 and row["Norm_Popularitas"] > 50:
            return "💰 Repricing"
        elif growth < -20:
            return "⚠️ Perlu Perhatian"
        elif score <= threshold_low:
            return "🗑️ Evaluasi"
        else:
            return "✅ Pertahankan"

    pop["Rekomendasi"] = pop.apply(classify, axis=1)

    # Tambah kategori jika ada
    if "Menu Category" in df.columns:
        cat_map = df.groupby("Menu")["Menu Category"].first()
        pop["Kategori"] = pop["Menu"].map(cat_map)

    return pop.sort_values("Skor_Gabungan", ascending=False).head(top_n).reset_index(drop=True)


@st.cache_data
def get_upsell_opportunities(df_gmv: pd.DataFrame, df_cogs: pd.DataFrame = None) -> pd.DataFrame:
    """
    Identifikasi peluang upsell: menu populer dengan margin tinggi
    yang jarang dibeli bersama menu laris.
    """
    if df_gmv is None or df_gmv.empty:
        return pd.DataFrame()

    df = df_gmv.copy()
    df["Total After Bill Discount"] = pd.to_numeric(df["Total After Bill Discount"], errors="coerce").fillna(0)
    if "Price (Net)" in df.columns:
        df["Price (Net)"] = pd.to_numeric(df["Price (Net)"], errors="coerce").fillna(0)
        df = df[df["Price (Net)"] > 0]

    margin_map = get_menu_margin_map(df_cogs) if df_cogs is not None else {}

    # Menu dengan margin > 60% dan cukup populer
    menu_stats = df.groupby("Menu").agg(
        Total_Rev=("Total After Bill Discount", "sum"),
        Total_Qty=("Qty", "sum"),
    ).reset_index()
    menu_stats["Margin"] = menu_stats["Menu"].map(margin_map).fillna(50)
    menu_stats = menu_stats[
        (menu_stats["Margin"] >= 60) &
        (menu_stats["Total_Qty"] >= menu_stats["Total_Qty"].quantile(0.3))
    ].sort_values("Margin", ascending=False)

    return menu_stats.head(15)