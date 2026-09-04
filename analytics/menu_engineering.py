# analytics/menu_engineering.py — Menu Engineering: Stars, Plowhorses, Puzzles, Dogs

import pandas as pd
import streamlit as st


@st.cache_data
def analyze_menu_engineering(df_cogs: pd.DataFrame) -> pd.DataFrame | None:
    """
    Hitung matriks Menu Engineering per menu:
        - Popularitas  : Total_Qty vs rata-rata semua menu
        - Profitabilitas: Margin_Pct vs rata-rata semua menu

    Klasifikasi:
        ⭐ Stars       — Populer & Margin Tinggi  → Pertahankan & Promosikan
        🐄 Plowhorses  — Populer & Margin Rendah  → Repricing / Kurangi Porsi
        ❓ Puzzles     — Tidak Populer & Margin Tinggi → Tingkatkan Promosi
        🐶 Dogs        — Tidak Populer & Margin Rendah → Evaluasi / Hapus
    """
    if df_cogs is None or df_cogs.empty:
        return None

    try:
        df = df_cogs.copy()

        # load_cogs_data merename: Price → Harga Jual, COGS Total → COGS
        # Support keduanya agar tetap jalan bila dipanggil langsung dari file raw
        col_price = "Harga Jual" if "Harga Jual" in df.columns else "Price"
        col_cogs  = "COGS"       if "COGS"       in df.columns else "COGS Total"

        for col in ["Qty", col_price, col_cogs]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # Filter item dengan harga & qty valid
        df = df[(df[col_price] > 0) & (df["Qty"] > 0)]
        if df.empty:
            return None

        # COGS & margin per unit (median lebih robust vs outlier)
        df["COGS_per_unit"] = df[col_cogs] / df["Qty"]

        menu_df = (
            df.groupby(["Menu", "Menu Category"])
            .agg(
                Total_Qty=("Qty", "sum"),
                Avg_Price=(col_price, "median"),
                Avg_COGS=("COGS_per_unit", "median"),
            )
            .reset_index()
        )

        menu_df["Margin_Pct"] = (
            (menu_df["Avg_Price"] - menu_df["Avg_COGS"]) / menu_df["Avg_Price"]
        ) * 100

        menu_df["Total_Revenue"] = menu_df["Total_Qty"] * menu_df["Avg_Price"]
        menu_df["Total_Margin"]  = menu_df["Total_Qty"] * (menu_df["Avg_Price"] - menu_df["Avg_COGS"])

        # Threshold: rata-rata semua menu
        avg_qty    = menu_df["Total_Qty"].mean()
        avg_margin = menu_df["Margin_Pct"].mean()

        def classify(row):
            high_pop = row["Total_Qty"]    >= avg_qty
            high_mar = row["Margin_Pct"]   >= avg_margin
            if high_pop and high_mar:
                return "⭐ Stars"
            elif high_pop and not high_mar:
                return "🐄 Plowhorses"
            elif not high_pop and high_mar:
                return "❓ Puzzles"
            else:
                return "🐶 Dogs"

        menu_df["Klasifikasi"] = menu_df.apply(classify, axis=1)

        ACTION_MAP = {
            "⭐ Stars":      "Pertahankan & Promosikan",
            "🐄 Plowhorses": "Repricing / Kurangi Porsi COGS",
            "❓ Puzzles":    "Tingkatkan Promosi / Ubah Posisi Menu",
            "🐶 Dogs":       "Evaluasi — Pertimbangkan Hapus/Ganti",
        }
        menu_df["Rekomendasi"] = menu_df["Klasifikasi"].map(ACTION_MAP)

        return menu_df.sort_values(["Klasifikasi", "Total_Revenue"], ascending=[True, False])

    except Exception as e:
        st.error(f"Error menu engineering: {e}")
        return None


def get_menu_engineering_summary(df_result: pd.DataFrame) -> dict:
    """Ringkasan count & total revenue per klasifikasi."""
    if df_result is None or df_result.empty:
        return {}

    summary = (
        df_result.groupby("Klasifikasi")
        .agg(
            Jumlah_Menu=("Menu", "count"),
            Total_Revenue=("Total_Revenue", "sum"),
            Total_Margin=("Total_Margin", "sum"),
            Avg_Margin_Pct=("Margin_Pct", "mean"),
        )
        .reset_index()
    )
    return summary