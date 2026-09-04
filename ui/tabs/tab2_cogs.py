# ui/tabs/tab2_cogs.py — Tab 2: COGS & Profit

import streamlit as st

from analytics.cogs import analyze_profit
from insights.generators import generate_cogs_insights
from ui.charts import create_horizontal_bar_chart
from formatters import format_rupiah, format_persen, format_angka_bulat


def build_tab2_cogs(filtered_cogs, df_gmv=None):  # ← tambah df_gmv=None
    if filtered_cogs is None:
        st.info("Silakan upload file Laporan COGS (File 2) di sidebar.")
        return
    if filtered_cogs.empty:
        st.warning("Tidak ada data COGS untuk filter yang dipilih.")
        return

    st.header("💰 Analisis Profitabilitas Menu (COGS)")
    profit_df = analyze_profit(filtered_cogs)

    # ── Ringkasan ──────────────────────────────────────────
    with st.expander("💰 Ringkasan Profitabilitas", expanded=True):
        total_rev = profit_df["Total Revenue (Rp)"].sum()
        total_cogs = profit_df["Total COGS (Rp)"].sum()
        total_profit = profit_df["Total Profit (Rp)"].sum()
        avg_margin = (total_profit / total_rev * 100) if total_rev > 0 else 0

        r1c1, r1c2 = st.columns(2)
        r1c1.metric("📈 Total Revenue (dari COGS)", format_rupiah(total_rev))
        r1c2.metric("📉 Total COGS", format_rupiah(total_cogs))

        r2c1, r2c2 = st.columns(2)
        r2c1.metric("💸 Total Profit", format_rupiah(total_profit))
        r2c2.metric("📊 Rata-rata Margin", format_persen(avg_margin))

    st.markdown("---")

    # ── Tabel Rincian ─────────────────────────────────────
    with st.expander("📝 Rincian Profitabilitas per Menu"):
        fmt_df = profit_df.copy()
        for col in ["Harga Jual", "COGS", "Margin (Rp)", "Total Revenue (Rp)", "Total COGS (Rp)", "Total Profit (Rp)"]:
            fmt_df[col] = fmt_df[col].apply(format_rupiah)
        fmt_df["Margin (%)"] = fmt_df["Margin (%)"].apply(format_persen)
        st.dataframe(fmt_df.set_index("Menu"), use_container_width=True)

    st.markdown("---")

    # ── Grafik Top & Bottom ────────────────────────────────
    with st.expander("📊 Analisis Performa Profit Menu (Top & Bottom 10)", expanded=True):
        top_profit = profit_df.nlargest(10, "Total Profit (Rp)")
        bot_profit = profit_df[profit_df["Qty"] > 0].nsmallest(10, "Total Profit (Rp)")
        top_margin = profit_df[profit_df["Qty"] > 0].nlargest(10, "Margin (%)")
        bot_margin = profit_df[profit_df["Qty"] > 0].nsmallest(10, "Margin (%)")

        r1, r2 = st.columns(2)
        with r1:
            st.markdown("##### 🏆 Menu Paling Untung (Profit Rp)")
            st.plotly_chart(create_horizontal_bar_chart(top_profit, "Total Profit (Rp)", "Menu", "Profit (Rp)", "Paling Untung"), use_container_width=True)
        with r2:
            st.markdown("##### 📈 Menu Margin Tertinggi (%)")
            st.plotly_chart(create_horizontal_bar_chart(top_margin, "Margin (%)", "Menu", "Margin (%)", "Margin Tertinggi"), use_container_width=True)

        r3, r4 = st.columns(2)
        with r3:
            st.markdown("##### 📉 Menu Paling Tidak Untung")
            st.plotly_chart(create_horizontal_bar_chart(bot_profit, "Total Profit (Rp)", "Menu", "Profit (Rp)", "Paling Tidak Untung", sort_order="x"), use_container_width=True)
        with r4:
            st.markdown("##### 📉 Menu Margin Terendah")
            st.plotly_chart(create_horizontal_bar_chart(bot_margin, "Margin (%)", "Menu", "Margin (%)", "Margin Terendah", sort_order="x"), use_container_width=True)

    # ── Insight ────────────────────────────────────────────
    st.markdown("---")
    st.header("💡 Insight Otomatis (COGS & Profit)")
    with st.expander("Temuan Kunci dari Data Profit", expanded=True):
        for ins in generate_cogs_insights(profit_df):
            st.markdown(f"&bull; {ins}")
