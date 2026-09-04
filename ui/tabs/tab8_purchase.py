# ui/tabs/tab8_purchase.py — Tab 8: Analisis Laporan Pembelian

import streamlit as st

from analytics.purchase import analyze_purchase_data
from insights.generators import generate_purchase_insights
from ui.charts import create_horizontal_bar_chart
from formatters import format_rupiah


def build_tab8_purchase(filtered_purchase, total_sales_revenue):
    st.header("🛒 Analisis Biaya Pembelian (Purchase)")
    st.info("Tab ini menganalisis Laporan Pembelian (File 5) untuk melacak pengeluaran.")

    if filtered_purchase is None:
        st.warning("Silakan upload file Laporan Pembelian (File 5) di sidebar.")
        return
    if filtered_purchase.empty:
        st.warning("Tidak ada data pembelian untuk filter yang dipilih.")
        return

    total_cost, cost_by_cat, cost_by_sup, top_items, raw_data = analyze_purchase_data(filtered_purchase)

    # ── Food Cost % ────────────────────────────────────────
    fcp = (total_cost / total_sales_revenue * 100) if (total_sales_revenue and total_sales_revenue > 0) else 0

    st.subheader("📊 KPI Biaya Pembelian & Food Cost")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Biaya Pembelian", format_rupiah(total_cost),
              help="Numerator FCP — hanya baris dengan Total > 0")
    c2.metric("Total Sales Revenue", format_rupiah(total_sales_revenue or 0),
              help="Denominator FCP — dari data GMV")
    c3.metric("Food Cost Percentage (FCP)", f"{fcp:.1f}%",
              help="(Total Pembelian / Total Sales Revenue) × 100")

    st.markdown("---")

    # ── Grafik Rincian ─────────────────────────────────────
    st.subheader("📈 Analisis Rincian Biaya")
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("##### Biaya per Kategori (Top 10)")
        if not cost_by_cat.empty:
            st.plotly_chart(create_horizontal_bar_chart(
                cost_by_cat.nlargest(10, "Total"), "Total", "Category",
                "Total Biaya (Rp)", "Top 10 Biaya per Kategori"
            ), use_container_width=True)
    with g2:
        st.markdown("##### Biaya per Supplier (Top 10)")
        if not cost_by_sup.empty:
            st.plotly_chart(create_horizontal_bar_chart(
                cost_by_sup.nlargest(10, "Total"), "Total", "Supplier Name",
                "Total Biaya (Rp)", "Top 10 Biaya per Supplier"
            ), use_container_width=True)

    st.markdown("---")
    st.subheader("💸 Top 20 Item dengan Biaya Tertinggi")
    if not top_items.empty:
        st.plotly_chart(create_horizontal_bar_chart(
            top_items, "Total", "Product Name", "Total Biaya (Rp)", "Top 20 Item Termahal"
        ), use_container_width=True)

    with st.expander("Lihat Rincian Data Pembelian"):
        st.dataframe(
            raw_data.style.format({"Price": format_rupiah, "Total": format_rupiah}),
            use_container_width=True,
        )

    # ── Insight ────────────────────────────────────────────
    st.markdown("---")
    st.header("💡 Insight Otomatis (Analisis Pembelian)")
    insights = generate_purchase_insights(total_cost, cost_by_cat, cost_by_sup, top_items, fcp)
    with st.expander("Temuan Kunci dari Biaya Pembelian", expanded=True):
        for ins in insights:
            st.markdown(f"&bull; {ins}")
