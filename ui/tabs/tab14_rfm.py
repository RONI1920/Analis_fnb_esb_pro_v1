# ui/tabs/tab14_rfm.py — Tab 14: RFM Analysis & Customer Segmentation

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pandas as pd

from analytics.rfm import (
    compute_rfm,
    get_retention_summary,
    get_segment_summary,
    get_rfm_action_map,
)
from formatters import format_rupiah


def build_tab14_rfm(df_gmv: pd.DataFrame):
    try:
        st.header("👥 RFM Analysis — Segmentasi Pelanggan")
        st.caption(
            "Segmentasi pelanggan berdasarkan **Recency** (kapan terakhir), "
            "**Frequency** (seberapa sering), dan **Monetary** (seberapa besar belanja)."
        )

        if df_gmv is None or df_gmv.empty:
            st.warning("Silakan upload file GMV di sidebar.")
            return

        # Cek apakah ada kolom pelanggan
        cust_candidates = ["Customer Name", "Nama", "Customer", "Member Name"]
        cust_col = next((c for c in cust_candidates if c in df_gmv.columns), None)

        if cust_col is None:
            st.error(
                "❌ **Data pelanggan tidak ditemukan.** "
                "RFM Analysis membutuhkan kolom nama/identitas pelanggan "
                "(misal: `Customer Name`, `Nama`, `Member Name`). "
                "File GMV yang diupload tidak memiliki kolom ini."
            )
            with st.expander("📋 Kolom yang tersedia di file GMV"):
                st.write(list(df_gmv.columns))
            return

        with st.spinner("Menghitung RFM..."):
            rfm_df = compute_rfm(df_gmv)

        if rfm_df is None or rfm_df.empty:
            st.warning(
                "Data RFM tidak dapat dihitung. Pastikan kolom pelanggan terisi "
                "dan tidak semuanya bernilai kosong/tidak diketahui."
            )
            return

        retention = get_retention_summary(rfm_df)
        segment_summary = get_segment_summary(rfm_df)
        action_map = get_rfm_action_map()

        # ════════════════════════════════════════════════════════
        # 1. KPI CARDS
        # ════════════════════════════════════════════════════════
        st.subheader("📊 Ringkasan Pelanggan")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Pelanggan",  f"{retention.get('total_customers', 0):,}")
        c2.metric("Pelanggan Repeat", f"{retention.get('repeat_customers', 0):,}")
        c3.metric("Retention Rate",   f"{retention.get('retention_rate', 0):.1f}%")
        c4.metric("Avg. Frekuensi",   f"{retention.get('avg_frequency', 0):.1f}x")
        c5.metric("Avg. Nilai Belanja", format_rupiah(retention.get("avg_monetary", 0)))

        c6, c7, c8 = st.columns(3)
        c6.metric("🏆 Champions",        retention.get("champions_count", 0))
        c7.metric("⚠️ At Risk",          retention.get("at_risk_count", 0))
        c8.metric("💀 Lost Customers",   retention.get("lost_count", 0))

        st.markdown("---")

        # ════════════════════════════════════════════════════════
        # 2. SEGMENT DISTRIBUTION
        # ════════════════════════════════════════════════════════
        st.subheader("🎯 Distribusi Segmen Pelanggan")

        col_pie, col_bar = st.columns(2)

        with col_pie:
            if not segment_summary.empty:
                fig_pie = px.pie(
                    segment_summary,
                    names="Segment_Label",
                    values="Jumlah_Pelanggan",
                    title="Distribusi Jumlah Pelanggan per Segmen",
                    color_discrete_sequence=px.colors.qualitative.Set3,
                    hole=0.4,
                )
                fig_pie.update_layout(template="plotly_white", height=380,
                                      margin=dict(l=10, r=10, t=40, b=10))
                st.plotly_chart(fig_pie, use_container_width=True)

        with col_bar:
            if not segment_summary.empty:
                fig_bar = px.bar(
                    segment_summary.sort_values("Total_Revenue", ascending=True),
                    x="Total_Revenue",
                    y="Segment_Label",
                    orientation="h",
                    title="Total Revenue per Segmen",
                    color="Revenue_Share_%",
                    color_continuous_scale="Greens",
                    text=segment_summary.sort_values("Total_Revenue", ascending=True)
                        ["Total_Revenue"].apply(format_rupiah),
                )
                fig_bar.update_layout(template="plotly_white", height=380,
                                      margin=dict(l=10, r=10, t=40, b=10),
                                      coloraxis_showscale=False)
                st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("---")

        # ════════════════════════════════════════════════════════
        # 3. RFM SCATTER PLOT
        # ════════════════════════════════════════════════════════
        st.subheader("📈 Peta RFM (Recency vs Monetary)")

        fig_scatter = px.scatter(
            rfm_df,
            x="Recency_Days",
            y="Monetary",
            color="Segment_Label",
            size="Frequency",
            hover_name="Customer",
            hover_data={
                "Recency_Days": True,
                "Frequency": True,
                "Segment_Label": True,
                "Monetary": False,
            },
            title="Recency vs Monetary — ukuran bubble = Frequency",
            color_discrete_sequence=px.colors.qualitative.Vivid,
        )
        fig_scatter.update_layout(
            template="plotly_white",
            height=450,
            xaxis_title="Recency (Hari sejak transaksi terakhir)",
            yaxis_title="Total Belanja (Monetary)",
            margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

        st.markdown("---")

        # ════════════════════════════════════════════════════════
        # 4. SEGMENT SUMMARY TABLE
        # ════════════════════════════════════════════════════════
        st.subheader("📋 Ringkasan per Segmen + Rekomendasi Aksi")

        if not segment_summary.empty:
            display = segment_summary.copy()
            display["Aksi"] = display["Segment_Label"].map(action_map).fillna("—")
            display["Avg_Monetary"] = display["Avg_Monetary"].apply(format_rupiah)
            display["Total_Revenue"] = display["Total_Revenue"].apply(format_rupiah)
            display["Avg_Frequency"] = display["Avg_Frequency"].round(1)
            display["Avg_Recency"] = display["Avg_Recency"].round(0).astype(int)
            display["Revenue_Share_%"] = display["Revenue_Share_%"].apply(lambda x: f"{x:.1f}%")

            st.dataframe(
                display.rename(columns={
                    "Segment_Label":     "Segmen",
                    "Jumlah_Pelanggan":  "Jml Pelanggan",
                    "Avg_Monetary":      "Avg Belanja",
                    "Avg_Frequency":     "Avg Frekuensi",
                    "Avg_Recency":       "Avg Recency (Hari)",
                    "Total_Revenue":     "Total Revenue",
                    "Revenue_Share_%":   "Share %",
                    "Aksi":              "💡 Rekomendasi Aksi",
                }),
                use_container_width=True,
                hide_index=True,
            )

        st.markdown("---")

        # ════════════════════════════════════════════════════════
        # 5. DETAIL PELANGGAN
        # ════════════════════════════════════════════════════════
        st.subheader("🔍 Detail Pelanggan per Segmen")

        all_segments = ["Semua"] + sorted(rfm_df["Segment_Label"].unique().tolist())
        sel_segment = st.selectbox("Filter Segmen:", all_segments, key="rfm_seg_filter")

        df_display = rfm_df if sel_segment == "Semua" else rfm_df[rfm_df["Segment_Label"] == sel_segment]

        tbl = df_display[[
            "Customer", "Segment_Label", "Recency_Days", "Frequency",
            "Monetary", "Avg_Order_Value", "R_Score", "F_Score", "M_Score", "RFM_Score"
        ]].copy()
        tbl["Monetary"] = tbl["Monetary"].apply(format_rupiah)
        tbl["Avg_Order_Value"] = tbl["Avg_Order_Value"].apply(format_rupiah)

        st.dataframe(
            tbl.rename(columns={
                "Customer":       "Pelanggan",
                "Segment_Label":  "Segmen",
                "Recency_Days":   "Recency (Hari)",
                "Frequency":      "Frekuensi",
                "Monetary":       "Total Belanja",
                "Avg_Order_Value": "Avg Order",
                "R_Score":        "R",
                "F_Score":        "F",
                "M_Score":        "M",
                "RFM_Score":      "Skor RFM",
            }),
            use_container_width=True,
            hide_index=True,
        )

        # Download
        csv = df_display.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download Data RFM (CSV)",
            csv,
            "rfm_analysis.csv",
            "text/csv",
            key="rfm_download",
        )
    except Exception as _e:
        import streamlit as _st
        _st.error(f"⚠️ Terjadi kesalahan pada modul ini: {_e}")
