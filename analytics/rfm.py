# analytics/rfm.py — RFM Analysis: Recency, Frequency, Monetary
#
# Analisis segmentasi pelanggan berdasarkan:
#   - Recency   : Kapan terakhir pelanggan bertransaksi
#   - Frequency : Seberapa sering pelanggan bertransaksi
#   - Monetary  : Seberapa besar nilai transaksi pelanggan
#
# Catatan: Data GMV pada umumnya tidak memiliki kolom ID pelanggan.
# Modul ini menggunakan kolom "Customer Name" / "Nama" jika tersedia,
# atau fallback ke "Bill Number" sebagai proxy transaksi unik.

import pandas as pd
import numpy as np
import streamlit as st


# ──────────────────────────────────────────────────────────────────
# FUNGSI UTAMA
# ──────────────────────────────────────────────────────────────────

@st.cache_data
def compute_rfm(df: pd.DataFrame) -> pd.DataFrame:
    """
    Hitung RFM dari data GMV.

    Kolom yang dibutuhkan:
        - "Sales Date In"               : tanggal transaksi
        - "Total After Bill Discount"   : nilai transaksi
        - "Bill Number"                 : nomor transaksi unik
        - "Customer Name" (opsional)    : nama pelanggan

    Returns:
        DataFrame dengan kolom:
        Customer, Recency_Days, Frequency, Monetary,
        R_Score, F_Score, M_Score, RFM_Score, RFM_Segment, Segment_Label
    """
    if df is None or df.empty:
        return pd.DataFrame()

    df2 = df.copy()
    df2["Sales Date In"] = pd.to_datetime(df2["Sales Date In"], errors="coerce")
    df2["Total After Bill Discount"] = pd.to_numeric(
        df2["Total After Bill Discount"], errors="coerce"
    ).fillna(0)
    df2.dropna(subset=["Sales Date In", "Bill Number"], inplace=True)

    # Tentukan kolom identitas pelanggan
    cust_col = None
    for candidate in ["Customer Name", "Nama", "Customer", "Member Name"]:
        if candidate in df2.columns:
            cust_col = candidate
            break

    if cust_col is None:
        # Tidak ada data pelanggan — RFM tidak bisa dihitung
        return pd.DataFrame()

    df2[cust_col] = df2[cust_col].fillna("Tidak Diketahui").astype(str).str.strip()
    # Buang pelanggan yang tidak teridentifikasi
    df2 = df2[~df2[cust_col].str.lower().isin(["", "nan", "none", "tidak diketahui", "-"])]
    if df2.empty:
        return pd.DataFrame()

    snapshot_date = df2["Sales Date In"].max() + pd.Timedelta(days=1)

    # Agregasi per pelanggan
    bill_df = (
        df2.groupby([cust_col, "Bill Number"])
        .agg(
            Bill_Date=("Sales Date In", "max"),
            Bill_Revenue=("Total After Bill Discount", "sum"),
        )
        .reset_index()
    )

    rfm = (
        bill_df.groupby(cust_col)
        .agg(
            Last_Purchase=("Bill_Date", "max"),
            Frequency=("Bill Number", "nunique"),
            Monetary=("Bill_Revenue", "sum"),
        )
        .reset_index()
        .rename(columns={cust_col: "Customer"})
    )

    rfm["Recency_Days"] = (snapshot_date - rfm["Last_Purchase"]).dt.days

    # Scoring 1–4 menggunakan kuantil (4 = terbaik)
    rfm["R_Score"] = _score_recency(rfm["Recency_Days"])
    rfm["F_Score"] = _score_standard(rfm["Frequency"])
    rfm["M_Score"] = _score_standard(rfm["Monetary"])

    rfm["RFM_Score"] = rfm["R_Score"].astype(str) + rfm["F_Score"].astype(str) + rfm["M_Score"].astype(str)
    rfm["RFM_Total"] = rfm["R_Score"] + rfm["F_Score"] + rfm["M_Score"]
    rfm["Segment_Label"] = rfm.apply(_segment_label, axis=1)

    # Ringkasan nilai per segmen
    rfm["Avg_Order_Value"] = rfm["Monetary"] / rfm["Frequency"].replace(0, 1)

    return rfm.sort_values("RFM_Total", ascending=False).reset_index(drop=True)


def _score_recency(series: pd.Series) -> pd.Series:
    """Recency: makin kecil (baru) = skor makin tinggi."""
    try:
        return pd.qcut(series, q=4, labels=[4, 3, 2, 1], duplicates="drop").astype(int)
    except Exception:
        return pd.Series([2] * len(series), index=series.index)


def _score_standard(series: pd.Series) -> pd.Series:
    """Frequency / Monetary: makin besar = skor makin tinggi."""
    try:
        return pd.qcut(series, q=4, labels=[1, 2, 3, 4], duplicates="drop").astype(int)
    except Exception:
        return pd.Series([2] * len(series), index=series.index)


def _segment_label(row) -> str:
    r, f, m = row["R_Score"], row["F_Score"], row["M_Score"]
    total = r + f + m

    if r == 4 and f == 4 and m == 4:
        return "🏆 Champions"
    elif r >= 3 and f >= 3:
        return "❤️ Loyal Customers"
    elif r == 4 and f <= 2:
        return "🆕 Recent Customers"
    elif r >= 3 and f <= 2 and m >= 3:
        return "💎 Potential Loyalists"
    elif r <= 2 and f >= 3 and m >= 3:
        return "⚠️ At Risk"
    elif r == 1 and f >= 3:
        return "😴 Hibernating"
    elif r == 1 and f == 1:
        return "💀 Lost Customers"
    elif total >= 9:
        return "⭐ High Value"
    elif total >= 6:
        return "🔄 Regular"
    else:
        return "🌱 New / Low Engagement"


# ──────────────────────────────────────────────────────────────────
# RETENTION & REPEAT ANALYSIS
# ──────────────────────────────────────────────────────────────────

@st.cache_data
def get_retention_summary(rfm_df: pd.DataFrame) -> dict:
    """
    Ringkasan retention: berapa % pelanggan yang kembali vs satu kali saja.
    """
    if rfm_df is None or rfm_df.empty:
        return {}

    total = len(rfm_df)
    repeat = (rfm_df["Frequency"] >= 2).sum()
    one_time = total - repeat

    return {
        "total_customers": total,
        "repeat_customers": int(repeat),
        "one_time_customers": int(one_time),
        "retention_rate": (repeat / total * 100) if total > 0 else 0,
        "avg_frequency": rfm_df["Frequency"].mean(),
        "avg_monetary": rfm_df["Monetary"].mean(),
        "avg_recency_days": rfm_df["Recency_Days"].mean(),
        "top_segment": rfm_df["Segment_Label"].value_counts().idxmax() if total > 0 else "—",
        "champions_count": int((rfm_df["Segment_Label"] == "🏆 Champions").sum()),
        "at_risk_count": int((rfm_df["Segment_Label"] == "⚠️ At Risk").sum()),
        "lost_count": int((rfm_df["Segment_Label"] == "💀 Lost Customers").sum()),
    }


@st.cache_data
def get_segment_summary(rfm_df: pd.DataFrame) -> pd.DataFrame:
    """Ringkasan per segmen: jumlah pelanggan, rata-rata Monetary, Frequency, Recency."""
    if rfm_df is None or rfm_df.empty:
        return pd.DataFrame()

    summary = (
        rfm_df.groupby("Segment_Label")
        .agg(
            Jumlah_Pelanggan=("Customer", "count"),
            Avg_Monetary=("Monetary", "mean"),
            Avg_Frequency=("Frequency", "mean"),
            Avg_Recency=("Recency_Days", "mean"),
            Total_Revenue=("Monetary", "sum"),
        )
        .reset_index()
        .sort_values("Total_Revenue", ascending=False)
    )
    summary["Revenue_Share_%"] = (
        summary["Total_Revenue"] / summary["Total_Revenue"].sum() * 100
    ).round(1)
    return summary


@st.cache_data
def get_rfm_action_map() -> dict:
    """Mapping segmen → rekomendasi aksi."""
    return {
        "🏆 Champions":          "🎁 Berikan reward eksklusif, ajak jadi brand ambassador.",
        "❤️ Loyal Customers":    "🎯 Upsell produk premium, beri loyalty points.",
        "💎 Potential Loyalists": "📣 Kirim promo personal, dorong frekuensi kunjungan.",
        "🆕 Recent Customers":   "🤝 Onboarding hangat, tawarkan trial menu baru.",
        "⭐ High Value":          "💌 Jaga hubungan, tawarkan member card.",
        "🔄 Regular":            "📈 Naikkan basket size dengan bundle / upsell.",
        "⚠️ At Risk":            "🚨 Win-back campaign: diskon spesial + reminder.",
        "😴 Hibernating":        "📧 Reaktivasi: pesan personal + incentive kunjungan.",
        "💀 Lost Customers":     "🔁 Kampanye re-engagement agresif atau relakan.",
        "🌱 New / Low Engagement": "🎉 Sambut dengan promo first-time repeat purchase.",
    }
