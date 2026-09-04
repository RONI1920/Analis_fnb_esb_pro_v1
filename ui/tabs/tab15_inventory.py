# ui/tabs/tab15_inventory.py — Tab 15: Analisis Inventori & Pembelian Lanjutan

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pandas as pd

from analytics.inventory import (
    compute_stock_turnover,
    detect_overbuying,
    get_purchase_vs_sales_correlation,
    get_supplier_analysis,
    get_inventory_summary_stats,
)
from formatters import format_rupiah


def build_tab15_inventory(df_purchase: pd.DataFrame, df_gmv: pd.DataFrame = None):
    try:
        st.header("📦 Analisis Inventori & Pembelian Lanjutan")
        st.caption("Turnover stok, reorder point, deteksi pembelian berlebih, dan analisis supplier.")

        if df_purchase is None or df_purchase.empty:
            st.warning("Silakan upload file Pembelian (File 5) di sidebar.")
            return

        stats = get_inventory_summary_stats(df_purchase)

        # ════════════════════════════════════════════════════════
        # 1. KPI RINGKASAN
        # ════════════════════════════════════════════════════════
        st.subheader("📊 Ringkasan Pembelian")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Belanja",       format_rupiah(stats.get("total_cost", 0)))
        c2.metric("Rata-rata / Bulan",   format_rupiah(stats.get("monthly_avg", 0)))
        c3.metric("Jumlah Supplier",     stats.get("n_suppliers", 0))
        c4.metric("Jumlah Produk",       stats.get("n_products", 0))

        # Food Cost % jika ada data GMV
        if df_gmv is not None and not df_gmv.empty:
            total_sales = df_gmv["Total After Bill Discount"].sum()
            fcp = (stats.get("total_cost", 0) / total_sales * 100) if total_sales > 0 else 0
            status = "🟢 Ideal" if fcp < 30 else ("🟡 Aman" if fcp <= 35 else "🔴 Tinggi")
            st.metric(f"Food Cost % {status}", f"{fcp:.1f}%",
                      help="Ideal untuk F&B: 25–35%")

        st.markdown("---")

        tabs = st.tabs([
            "📈 Stock Turnover",
            "⚠️ Deteksi Overbuying",
            "🔗 Korelasi Pembelian vs Penjualan",
            "🚚 Analisis Supplier",
        ])

        # ════════════════════════════════════════════════════════
        # TAB A: STOCK TURNOVER
        # ════════════════════════════════════════════════════════
        with tabs[0]:
            st.subheader("📈 Stock Turnover Rate & Reorder Point")
            st.info(
                "Stock Turnover Rate mengukur seberapa cepat produk digunakan. "
                "**Fast Moving** = permintaan tinggi, **Slow Moving** = perlu dievaluasi."
            )

            with st.spinner("Menghitung turnover..."):
                turnover_df = compute_stock_turnover(df_purchase)

            if turnover_df.empty:
                st.warning("Tidak ada data turnover.")
            else:
                # Filter
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    categories = ["Semua"] + sorted(turnover_df["Category"].dropna().unique().tolist())
                    sel_cat = st.selectbox("Filter Kategori:", categories, key="to_cat")
                with col_f2:
                    tiers = ["Semua"] + sorted(turnover_df["Turnover_Tier"].unique().tolist())
                    sel_tier = st.selectbox("Filter Tier:", tiers, key="to_tier")

                df_to = turnover_df.copy()
                if sel_cat != "Semua":
                    df_to = df_to[df_to["Category"] == sel_cat]
                if sel_tier != "Semua":
                    df_to = df_to[df_to["Turnover_Tier"] == sel_tier]

                # Tier distribution
                tier_counts = turnover_df["Turnover_Tier"].value_counts().reset_index()
                tier_counts.columns = ["Tier", "Jumlah"]
                fig_tier = px.bar(
                    tier_counts, x="Tier", y="Jumlah",
                    title="Distribusi Stock Turnover Tier",
                    color="Tier",
                    color_discrete_map={
                        "🟢 Fast Moving (>4x)": "#2ecc71",
                        "🔵 Normal (2–4x)":     "#3498db",
                        "🟡 Slow Moving (1–2x)": "#f1c40f",
                        "🔴 Very Slow (<1x)":   "#e74c3c",
                    },
                )
                fig_tier.update_layout(template="plotly_white", height=320,
                                       showlegend=False, margin=dict(l=10, r=10, t=40, b=10))
                st.plotly_chart(fig_tier, use_container_width=True)

                # Tabel
                tbl = df_to[[
                    "Product Name", "Category", "Supplier", "Turnover_Tier",
                    "Total_Qty", "Monthly_Qty", "Total_Cost",
                    "Reorder_Point_Qty", "Reorder_Point_Cost",
                ]].copy()
                tbl["Total_Cost"] = tbl["Total_Cost"].apply(format_rupiah)
                tbl["Reorder_Point_Cost"] = tbl["Reorder_Point_Cost"].apply(format_rupiah)
                tbl["Monthly_Qty"] = tbl["Monthly_Qty"].round(1)
                tbl["Reorder_Point_Qty"] = tbl["Reorder_Point_Qty"].astype(int)

                st.dataframe(
                    tbl.rename(columns={
                        "Product Name":      "Produk",
                        "Category":          "Kategori",
                        "Supplier":          "Supplier",
                        "Turnover_Tier":     "Tier",
                        "Total_Qty":         "Total Qty",
                        "Monthly_Qty":       "Qty/Bulan",
                        "Total_Cost":        "Total Biaya",
                        "Reorder_Point_Qty": "Reorder Point (Qty)",
                        "Reorder_Point_Cost": "Reorder Point (Rp)",
                    }),
                    use_container_width=True, hide_index=True,
                )

        # ════════════════════════════════════════════════════════
        # TAB B: OVERBUYING
        # ════════════════════════════════════════════════════════
        with tabs[1]:
            st.subheader("⚠️ Deteksi Pembelian Berlebih (Overbuying)")
            st.info(
                "Produk dengan fluktuasi pembelian tinggi (CV > 50%) atau "
                "lonjakan pembelian bulan terakhir tanpa diimbangi penjualan "
                "berisiko menyebabkan pemborosan."
            )

            with st.spinner("Menganalisis overbuying..."):
                over_df = detect_overbuying(df_purchase, df_gmv)

            if over_df.empty:
                st.success("✅ Tidak ada data overbuying yang terdeteksi.")
            else:
                risk_filter = st.selectbox(
                    "Filter Risiko:",
                    ["Semua", "🔴 Risiko Tinggi", "🟡 Risiko Sedang", "🟢 Normal"],
                    key="ob_risk",
                )
                df_ob = over_df if risk_filter == "Semua" else over_df[over_df["Overbuying_Risk"] == risk_filter]

                # Chart: top 15 pemborosan potensial
                top15 = df_ob.nlargest(15, "Potensi_Pemborosan")
                if not top15.empty:
                    fig_ob = px.bar(
                        top15.sort_values("Potensi_Pemborosan"),
                        x="Potensi_Pemborosan",
                        y="Product Name",
                        orientation="h",
                        color="Overbuying_Risk",
                        title="Top 15 Produk dengan Potensi Pemborosan Tertinggi",
                        color_discrete_map={
                            "🔴 Risiko Tinggi": "#e74c3c",
                            "🟡 Risiko Sedang": "#f1c40f",
                            "🟢 Normal":        "#2ecc71",
                        },
                        text=top15.sort_values("Potensi_Pemborosan")["Potensi_Pemborosan"].apply(format_rupiah),
                    )
                    fig_ob.update_layout(template="plotly_white", height=420,
                                         yaxis_title="", xaxis_title="Potensi Pemborosan (Rp)",
                                         margin=dict(l=10, r=10, t=40, b=10))
                    st.plotly_chart(fig_ob, use_container_width=True)

                tbl_ob = df_ob[[
                    "Product Name", "Overbuying_Risk", "Avg_Cost", "Max_Cost",
                    "CV", "Purchase_Growth_%", "Potensi_Pemborosan", "Months_Active",
                ]].copy()
                tbl_ob["Avg_Cost"] = tbl_ob["Avg_Cost"].apply(format_rupiah)
                tbl_ob["Max_Cost"] = tbl_ob["Max_Cost"].apply(format_rupiah)
                tbl_ob["Potensi_Pemborosan"] = tbl_ob["Potensi_Pemborosan"].apply(format_rupiah)
                tbl_ob["CV"] = tbl_ob["CV"].round(1).astype(str) + "%"
                tbl_ob["Purchase_Growth_%"] = tbl_ob["Purchase_Growth_%"].round(1).astype(str) + "%"

                st.dataframe(
                    tbl_ob.rename(columns={
                        "Product Name":     "Produk",
                        "Overbuying_Risk":  "Risiko",
                        "Avg_Cost":         "Avg Biaya/Bln",
                        "Max_Cost":         "Max Biaya/Bln",
                        "CV":               "CV Harga",
                        "Purchase_Growth_%": "Growth Terakhir",
                        "Potensi_Pemborosan": "Potensi Pemborosan",
                        "Months_Active":    "Bulan Aktif",
                    }),
                    use_container_width=True, hide_index=True,
                )

        # ════════════════════════════════════════════════════════
        # TAB C: KORELASI PEMBELIAN vs PENJUALAN
        # ════════════════════════════════════════════════════════
        with tabs[2]:
            st.subheader("🔗 Korelasi Pembelian vs Penjualan")

            if df_gmv is None or df_gmv.empty:
                st.warning("Upload file GMV untuk melihat korelasi pembelian vs penjualan.")
            else:
                with st.spinner("Menghitung korelasi..."):
                    corr_df = get_purchase_vs_sales_correlation(df_purchase, df_gmv)

                if corr_df.empty:
                    st.warning("Data tidak cukup untuk analisis korelasi.")
                else:
                    # Chart ganda
                    fig_corr = go.Figure()
                    fig_corr.add_trace(go.Bar(
                        x=corr_df["Month"], y=corr_df["Revenue"],
                        name="Revenue", marker_color="#3498db", opacity=0.7,
                    ))
                    fig_corr.add_trace(go.Bar(
                        x=corr_df["Month"], y=corr_df["Purchase_Cost"],
                        name="Purchase Cost", marker_color="#e74c3c", opacity=0.7,
                    ))
                    fig_corr.add_trace(go.Scatter(
                        x=corr_df["Month"], y=corr_df["Food_Cost_%"],
                        name="Food Cost %", mode="lines+markers",
                        yaxis="y2", line=dict(color="#f39c12", width=2),
                    ))
                    fig_corr.update_layout(
                        template="plotly_white", height=420,
                        barmode="group",
                        yaxis=dict(title="Nominal (Rp)"),
                        yaxis2=dict(title="Food Cost %", overlaying="y", side="right", ticksuffix="%"),
                        hovermode="x unified",
                        legend=dict(orientation="h", y=1.1),
                        margin=dict(l=10, r=10, t=20, b=10),
                    )
                    st.plotly_chart(fig_corr, use_container_width=True)

                    # Tabel
                    tbl_c = corr_df.copy()
                    tbl_c["Revenue"] = tbl_c["Revenue"].apply(format_rupiah)
                    tbl_c["Purchase_Cost"] = tbl_c["Purchase_Cost"].apply(format_rupiah)
                    tbl_c["Food_Cost_%"] = tbl_c["Food_Cost_%"].round(1).astype(str) + "%"
                    tbl_c["Purchase_MoM_%"] = tbl_c["Purchase_MoM_%"].round(1).fillna(0).astype(str) + "%"
                    tbl_c["Revenue_MoM_%"] = tbl_c["Revenue_MoM_%"].round(1).fillna(0).astype(str) + "%"
                    tbl_c["Month"] = tbl_c["Month"].dt.strftime("%b %Y")

                    st.dataframe(
                        tbl_c[["Month", "Revenue", "Purchase_Cost", "Food_Cost_%",
                                "Food_Cost_Status", "Revenue_MoM_%", "Purchase_MoM_%"]].rename(columns={
                            "Month":            "Bulan",
                            "Revenue":          "Revenue",
                            "Purchase_Cost":    "Biaya Pembelian",
                            "Food_Cost_%":      "Food Cost %",
                            "Food_Cost_Status": "Status",
                            "Revenue_MoM_%":    "Revenue MoM",
                            "Purchase_MoM_%":   "Purchase MoM",
                        }),
                        use_container_width=True, hide_index=True,
                    )

        # ════════════════════════════════════════════════════════
        # TAB D: SUPPLIER
        # ════════════════════════════════════════════════════════
        with tabs[3]:
            st.subheader("🚚 Analisis Supplier")

            with st.spinner("Menganalisis supplier..."):
                sup_df = get_supplier_analysis(df_purchase)

            if sup_df.empty:
                st.warning("Tidak ada data supplier.")
            else:
                # Chart top 10 supplier
                top10 = sup_df.head(10)
                fig_sup = px.bar(
                    top10.sort_values("Total_Belanja"),
                    x="Total_Belanja",
                    y="Supplier Name",
                    orientation="h",
                    color="Reliability",
                    title="Top 10 Supplier by Total Belanja",
                    color_discrete_map={
                        "🟢 Andalan":          "#2ecc71",
                        "🔵 Cukup Andal":      "#3498db",
                        "🟡 Perlu Negosiasi":  "#f1c40f",
                        "🔴 Tidak Konsisten":  "#e74c3c",
                    },
                    text=top10.sort_values("Total_Belanja")["Total_Belanja"].apply(format_rupiah),
                )
                fig_sup.update_layout(template="plotly_white", height=400,
                                      margin=dict(l=10, r=10, t=40, b=10))
                st.plotly_chart(fig_sup, use_container_width=True)

                tbl_s = sup_df.copy()
                tbl_s["Total_Belanja"] = tbl_s["Total_Belanja"].apply(format_rupiah)
                tbl_s["Avg_Per_Order"] = tbl_s["Avg_Per_Order"].apply(format_rupiah)
                tbl_s["Price_CV"] = tbl_s["Price_CV"].round(1).astype(str) + "%"

                st.dataframe(
                    tbl_s[[
                        "Supplier Name", "Reliability", "Total_Belanja", "Jumlah_Order",
                        "Jumlah_Produk", "Avg_Per_Order", "Price_CV",
                    ]].rename(columns={
                        "Supplier Name":  "Supplier",
                        "Reliability":    "Status",
                        "Total_Belanja":  "Total Belanja",
                        "Jumlah_Order":   "Jml Order",
                        "Jumlah_Produk":  "Jml Produk",
                        "Avg_Per_Order":  "Avg/Order",
                        "Price_CV":       "Konsistensi Harga (CV)",
                    }),
                    use_container_width=True, hide_index=True,
                )
    except Exception as _e:
        import streamlit as _st
        _st.error(f"⚠️ Terjadi kesalahan pada modul ini: {_e}")
