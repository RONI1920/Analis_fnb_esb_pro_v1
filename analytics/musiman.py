# analytics/musiman.py — Analisis Musiman: Weekend, Libur, & Seasonal Effect

import pandas as pd
import streamlit as st


@st.cache_data
def analyze_tab11_weekend_effect(df_gmv: pd.DataFrame, df_kalender: pd.DataFrame):
    """
    Analisis efek weekend dan hari libur terhadap omzet.

    Kategori hari:
        1. Weekday Biasa      — hari kerja, bukan event apapun
        2. Weekend Biasa      — Sabtu/Minggu, bukan event
        3. Weekday Libur      — hari kerja yang jatuh pada event/libur
        4. Weekend & Libur    — Sabtu/Minggu yang juga event/libur

    Deteksi libur berdasarkan kolom Tipe_Event di df_kalender.
    Semua Tipe_Event selain nilai "biasa" / kosong dianggap hari non-biasa.
    """
    if df_gmv is None or df_gmv.empty or df_kalender is None or df_kalender.empty:
        return None, None

    try:
        col_tgl, col_rev = "Sales Date In", "Total After Bill Discount"

        # ── 1. Agregasi omzet harian ───────────────────────────────────────
        df_sales = df_gmv[[col_tgl, col_rev]].copy()
        df_sales[col_tgl] = pd.to_datetime(df_sales[col_tgl], errors="coerce")
        df_sales[col_rev] = pd.to_numeric(df_sales[col_rev], errors="coerce").fillna(0)
        df_sales = df_sales.dropna(subset=[col_tgl])

        df_daily = (
            df_sales
            .assign(Tanggal=df_sales[col_tgl].dt.floor("D"))
            .groupby("Tanggal", as_index=False)[col_rev]
            .sum()
        )

        # ── 2. Siapkan kalender ────────────────────────────────────────────
        df_kal = df_kalender.copy()
        df_kal["Tanggal"] = pd.to_datetime(df_kal["Tanggal"], errors="coerce")

        if "Tipe_Event" not in df_kal.columns:
            df_kal["Tipe_Event"] = "Biasa"
        df_kal["Tipe_Event"] = df_kal["Tipe_Event"].fillna("Biasa").astype(str)

        if "Nama_Event" not in df_kal.columns:
            df_kal["Nama_Event"] = ""
        df_kal["Nama_Event"] = df_kal["Nama_Event"].fillna("").astype(str)

        # Ambil satu baris per tanggal (prioritas: bukan "Biasa" duluan)
        df_kal = df_kal.sort_values(
            by="Tipe_Event",
            key=lambda s: s.str.lower().map(lambda v: 0 if v not in ("biasa", "") else 1),
        ).drop_duplicates(subset="Tanggal", keep="first")

        # ── 3. Merge & flagging ────────────────────────────────────────────
        df_merged = pd.merge(df_daily, df_kal, on="Tanggal", how="left")
        df_merged["Tipe_Event"] = df_merged["Tipe_Event"].fillna("Biasa")
        df_merged["Nama_Event"] = df_merged["Nama_Event"].fillna("")
        df_merged["Is_Weekend"] = df_merged["Tanggal"].dt.dayofweek >= 5

        # Hari non-biasa = semua Tipe_Event yang bukan "Biasa" / kosong
        NORMAL_TYPES = {"biasa", ""}
        df_merged["Is_Holiday"] = ~df_merged["Tipe_Event"].str.strip().str.lower().isin(
            NORMAL_TYPES
        )

        # ── 4. Kategorisasi ────────────────────────────────────────────────
        df_merged["Kategori_Hari"] = "1. Weekday Biasa"
        df_merged.loc[df_merged["Is_Weekend"], "Kategori_Hari"] = "2. Weekend Biasa"
        df_merged.loc[
            df_merged["Is_Holiday"] & ~df_merged["Is_Weekend"], "Kategori_Hari"
        ] = "3. Weekday Libur"
        df_merged.loc[
            df_merged["Is_Holiday"] & df_merged["Is_Weekend"], "Kategori_Hari"
        ] = "4. Weekend & Libur"

        # ── 5. Summary ─────────────────────────────────────────────────────
        df_summary = (
            df_merged.groupby("Kategori_Hari", as_index=False)
            .agg(
                Rata_Rata_Omzet=(col_rev, "mean"),
                Jumlah_Hari=("Tanggal", "count"),
                Total_Omzet=(col_rev, "sum"),
            )
        )

        category_order = [
            "1. Weekday Biasa",
            "2. Weekend Biasa",
            "3. Weekday Libur",
            "4. Weekend & Libur",
        ]
        df_summary["Kategori_Hari"] = pd.Categorical(
            df_summary["Kategori_Hari"], categories=category_order, ordered=True
        )
        df_summary = df_summary.sort_values("Kategori_Hari")

        return df_summary, df_merged

    except Exception as e:
        st.error(f"Error analisis musiman: {e}")
        return None, None