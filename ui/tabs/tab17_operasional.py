# ui/tabs/tab17_operasional.py — Tab 17: Analisis Operasional Lanjutan
#
# Mencakup:
#   - Table Turnover Rate
#   - Void & Cancelled Orders Analysis
#   - Upsell Conversion Rate per Waiter
#   - Peak Capacity Utilization

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pandas as pd

from analytics.operasional import (
    compute_table_turnover,
    get_table_turnover_summary,
    analyze_void_orders,
    get_upsell_rate_per_waiter,
    get_capacity_utilization,
)
from formatters import format_rupiah


def build_tab17_operasional(df_gmv: pd.DataFrame, df_waiter: pd.DataFrame = None):
    try:
        st.header("⚙️ Analisis Operasional Lanjutan")
        st.caption("Table turnover, void orders, upsell rate waiter, dan utilisasi kapasitas.")

        if df_gmv is None or df_gmv.empty:
            st.warning("Silakan upload file GMV di sidebar.")
            return

        tabs = st.tabs([
            "🔄 Table Turnover",
            "🚫 Void & Cancel Orders",
            "💬 Upsell Rate Waiter",
            "📊 Kapasitas & Utilisasi",
        ])

        # ════════════════════════════════════════════════════════
        # TAB A: TABLE TURNOVER
        # ════════════════════════════════════════════════════════
        with tabs[0]:
            st.subheader("🔄 Table Turnover Rate")
            st.info(
                "Table Turnover Rate = Jumlah transaksi / Jumlah meja. "
                "**Ideal untuk restoran kasual: 2–4x per hari.**"
            )

            n_tables = st.number_input(
                "Jumlah meja di restoran:", min_value=1, value=10, step=1, key="tt_tables"
            )

            with st.spinner("Menghitung table turnover..."):
                tt_df = compute_table_turnover(df_gmv, n_tables)

            if tt_df.empty:
                st.warning("Tidak ada data turnover.")
            else:
                summary = get_table_turnover_summary(tt_df)

                # KPI Cards
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Avg Turnover/Hari", f"{summary.get('avg_turnover', 0):.1f}x")
                c2.metric("Avg Weekday",        f"{summary.get('avg_weekday', 0):.1f}x")
                c3.metric("Avg Weekend",        f"{summary.get('avg_weekend', 0):.1f}x")
                c4.metric("Avg Revenue/Meja",   format_rupiah(summary.get("avg_revenue_per_table", 0)))

                c5, c6 = st.columns(2)
                c5.metric("Hari Terbaik",   summary.get("best_day", "—"))
                c6.metric("Hari Terlemah",  summary.get("worst_day", "—"))

                st.markdown("---")

                # Chart tren turnover
                fig_tt = go.Figure()
                fig_tt.add_trace(go.Scatter(
                    x=tt_df["Date"], y=tt_df["Turnover_Rate"],
                    mode="lines+markers",
                    name="Turnover Rate",
                    line=dict(color="#3498db"),
                    marker=dict(color=tt_df["Is_Weekend"].map({True: "#e74c3c", False: "#3498db"})),
                ))
                fig_tt.add_hline(y=2, line_dash="dash", line_color="#2ecc71",
                                 annotation_text="Target Minimum (2x)")
                fig_tt.add_hline(y=4, line_dash="dot", line_color="#f39c12",
                                 annotation_text="Excellent (4x)")
                fig_tt.update_layout(
                    template="plotly_white", height=380,
                    xaxis_title="Tanggal",
                    yaxis_title="Turnover Rate (x)",
                    hovermode="x unified",
                    margin=dict(l=10, r=10, t=20, b=10),
                )
                st.plotly_chart(fig_tt, use_container_width=True)
                st.caption("🔴 = Weekend | 🔵 = Weekday")

                # Distribusi per hari dalam seminggu
                dow_avg = (
                    tt_df.groupby("Day_Name")["Turnover_Rate"]
                    .mean()
                    .reindex(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
                    .reset_index()
                )
                fig_dow = px.bar(
                    dow_avg, x="Day_Name", y="Turnover_Rate",
                    title="Rata-rata Turnover per Hari dalam Seminggu",
                    color="Turnover_Rate", color_continuous_scale="RdYlGn",
                    text=dow_avg["Turnover_Rate"].round(2),
                )
                fig_dow.update_layout(template="plotly_white", height=320,
                                      coloraxis_showscale=False,
                                      margin=dict(l=10, r=10, t=40, b=10))
                st.plotly_chart(fig_dow, use_container_width=True)

        # ════════════════════════════════════════════════════════
        # TAB B: VOID & CANCELLED
        # ════════════════════════════════════════════════════════
        with tabs[1]:
            st.subheader("🚫 Analisis Void & Non-Sales Orders")

            if df_waiter is None or df_waiter.empty:
                st.warning("Upload file Waiter/SDM (File 3) untuk analisis void.")
            else:
                with st.spinner("Menganalisis void orders..."):
                    void_result = analyze_void_orders(df_waiter)

                if not void_result:
                    st.warning("Kolom 'Sales Type' tidak ditemukan di data Waiter.")
                else:
                    # KPI
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Total Void",         f"{void_result['total_voids']:,}")
                    c2.metric("Total Non-Sales",    f"{void_result['total_nonsales']:,}")
                    c3.metric("Void Rate",          f"{void_result['overall_void_rate']:.1f}%")
                    c4.metric("Est. Kerugian",      format_rupiah(void_result["estimated_loss"]))

                    st.markdown("---")

                    col_v1, col_v2 = st.columns(2)

                    # Tren void bulanan
                    with col_v1:
                        monthly = void_result.get("monthly_trend", pd.DataFrame())
                        if not monthly.empty:
                            fig_vm = go.Figure()
                            fig_vm.add_trace(go.Bar(
                                x=monthly["Month"], y=monthly["Total_Bills"],
                                name="Total Bills", opacity=0.5, marker_color="#3498db",
                            ))
                            fig_vm.add_trace(go.Scatter(
                                x=monthly["Month"], y=monthly["Void_Count"],
                                name="Void Count", mode="lines+markers",
                                line=dict(color="#e74c3c"),
                                yaxis="y2",
                            ))
                            fig_vm.update_layout(
                                title="Tren Void per Bulan",
                                template="plotly_white", height=360,
                                yaxis2=dict(overlaying="y", side="right"),
                                hovermode="x unified",
                                legend=dict(orientation="h", y=1.1),
                                margin=dict(l=10, r=10, t=40, b=10),
                            )
                            st.plotly_chart(fig_vm, use_container_width=True)

                    # Void per jam
                    with col_v2:
                        void_hour = void_result.get("void_by_hour", pd.DataFrame())
                        if not void_hour.empty:
                            fig_vh = px.bar(
                                void_hour, x="Hour", y="Void_Count",
                                title="Distribusi Void per Jam",
                                color="Void_Count", color_continuous_scale="Reds",
                            )
                            fig_vh.update_layout(
                                template="plotly_white", height=360,
                                coloraxis_showscale=False,
                                margin=dict(l=10, r=10, t=40, b=10),
                            )
                            st.plotly_chart(fig_vh, use_container_width=True)

                    # Void rate per waiter
                    void_waiter = void_result.get("void_by_waiter", pd.DataFrame())
                    if not void_waiter.empty:
                        st.subheader("⚠️ Void Rate per Waiter (Top 10)")
                        top_void = void_waiter.head(10)
                        fig_vw = px.bar(
                            top_void.sort_values("Void_Rate_%"),
                            x="Void_Rate_%", y="Waiter",
                            orientation="h",
                            color="Void_Rate_%",
                            color_continuous_scale="RdYlGn_r",
                            text=top_void.sort_values("Void_Rate_%")["Void_Rate_%"].round(1).astype(str) + "%",
                            title="Void Rate per Waiter (%)",
                        )
                        fig_vw.update_layout(
                            template="plotly_white", height=380,
                            coloraxis_showscale=False,
                            margin=dict(l=10, r=10, t=40, b=10),
                        )
                        st.plotly_chart(fig_vw, use_container_width=True)

        # ════════════════════════════════════════════════════════
        # TAB C: UPSELL RATE
        # ════════════════════════════════════════════════════════
        with tabs[2]:
            st.subheader("💬 Upsell Conversion Rate per Waiter")
            st.info(
                "Mengukur seberapa sering setiap waiter berhasil memasukkan menu "
                "bernilai tinggi (top 20% by revenue) ke dalam transaksi pelanggan."
            )

            if df_waiter is None or df_waiter.empty:
                st.warning("Upload file Waiter/SDM (File 3) untuk analisis upsell.")
            else:
                with st.spinner("Menghitung upsell rate..."):
                    upsell_df = get_upsell_rate_per_waiter(df_waiter, df_gmv)

                if upsell_df.empty:
                    st.warning("Data tidak cukup untuk analisis upsell.")
                else:
                    # KPI
                    avg_upsell = upsell_df["Upsell_Rate_%"].mean()
                    top_waiter = upsell_df.iloc[0]
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Avg Upsell Rate",    f"{avg_upsell:.1f}%")
                    c2.metric("🥇 Top Waiter",       top_waiter["Waiter"])
                    c3.metric("Rate Terbaik",        f"{top_waiter['Upsell_Rate_%']:.1f}%")

                    # Chart
                    fig_us = px.bar(
                        upsell_df.sort_values("Upsell_Rate_%"),
                        x="Upsell_Rate_%", y="Waiter",
                        orientation="h",
                        color="Upsell_Tier",
                        title="Upsell Conversion Rate per Waiter",
                        color_discrete_map={
                            "🥇 Excellent (≥50%)":       "#2ecc71",
                            "🥈 Good (30–50%)":           "#3498db",
                            "🥉 Average (15–30%)":        "#f39c12",
                            "📈 Needs Improvement (<15%)": "#e74c3c",
                        },
                        text=upsell_df.sort_values("Upsell_Rate_%")["Upsell_Rate_%"].round(1).astype(str) + "%",
                    )
                    fig_us.add_vline(x=avg_upsell, line_dash="dash",
                                     annotation_text=f"Avg: {avg_upsell:.1f}%")
                    fig_us.update_layout(
                        template="plotly_white", height=max(380, len(upsell_df) * 35),
                        margin=dict(l=10, r=10, t=40, b=10),
                    )
                    st.plotly_chart(fig_us, use_container_width=True)

                    # Tabel
                    tbl_us = upsell_df.copy()
                    tbl_us["ATV"] = tbl_us["ATV"].apply(format_rupiah)
                    tbl_us["Total_Revenue"] = tbl_us["Total_Revenue"].apply(format_rupiah)
                    tbl_us["Upsell_Rate_%"] = tbl_us["Upsell_Rate_%"].round(1).astype(str) + "%"

                    st.dataframe(
                        tbl_us.rename(columns={
                            "Waiter":         "Waiter",
                            "Upsell_Tier":    "Tier",
                            "Upsell_Rate_%":  "Upsell Rate",
                            "Upsell_Bills":   "Bills w/ Upsell",
                            "Total_Bills":    "Total Bills",
                            "ATV":            "ATV",
                            "Total_Revenue":  "Total Revenue",
                        }),
                        use_container_width=True, hide_index=True,
                    )

        # ════════════════════════════════════════════════════════
        # TAB D: KAPASITAS & UTILISASI
        # ════════════════════════════════════════════════════════
        with tabs[3]:
            st.subheader("📊 Estimasi Utilisasi Kapasitas per Jam")
            st.info(
                "Estimasi ini menggunakan asumsi rata-rata 2 tamu per bill. "
                "Akurasi bisa ditingkatkan jika data jumlah tamu tersedia."
            )

            col_p1, col_p2, col_p3 = st.columns(3)
            with col_p1:
                n_t = st.number_input("Jumlah meja:", 1, 200, 10, key="cap_tables")
            with col_p2:
                cap_t = st.number_input("Kapasitas per meja:", 1, 20, 4, key="cap_per_table")
            with col_p3:
                dining_min = st.number_input("Avg waktu makan (menit):", 15, 180, 60, key="cap_dining")

            with st.spinner("Menghitung utilisasi..."):
                cap_df = get_capacity_utilization(df_gmv, n_t, cap_t, dining_min)

            if cap_df.empty:
                st.warning("Tidak ada data utilisasi.")
            else:
                # Heatmap utilisasi per jam
                fig_cap = go.Figure()
                fig_cap.add_trace(go.Bar(
                    x=cap_df["Hour"],
                    y=cap_df["Avg_Utilization"],
                    name="Utilisasi %",
                    marker=dict(
                        color=cap_df["Avg_Utilization"],
                        colorscale="RdYlGn",
                        cmin=0, cmax=100,
                    ),
                    text=cap_df["Avg_Utilization"].round(0).astype(int).astype(str) + "%",
                    textposition="outside",
                ))
                fig_cap.add_hline(y=70, line_dash="dash", line_color="orange",
                                  annotation_text="Target 70%")
                fig_cap.update_layout(
                    template="plotly_white",
                    height=380,
                    xaxis=dict(title="Jam", tickmode="linear", tick0=0, dtick=1),
                    yaxis=dict(title="Utilisasi (%)", range=[0, 110]),
                    title="Rata-rata Utilisasi Kapasitas per Jam",
                    margin=dict(l=10, r=10, t=40, b=10),
                )
                st.plotly_chart(fig_cap, use_container_width=True)

                # Revenue per jam
                fig_rev_h = px.line(
                    cap_df, x="Hour", y="Avg_Revenue",
                    title="Rata-rata Revenue per Jam",
                    markers=True,
                )
                fig_rev_h.update_layout(
                    template="plotly_white", height=300,
                    xaxis=dict(title="Jam", tickmode="linear", tick0=0, dtick=1),
                    margin=dict(l=10, r=10, t=40, b=10),
                )
                st.plotly_chart(fig_rev_h, use_container_width=True)

                # Peak & Off-peak summary
                peak_hour = cap_df.nlargest(1, "Avg_Utilization").iloc[0]
                offpeak_hour = cap_df.nsmallest(1, "Avg_Utilization").iloc[0]
                c_a, c_b = st.columns(2)
                c_a.success(
                    f"**⚡ Jam Paling Sibuk:** Pukul **{int(peak_hour['Hour'])}:00** "
                    f"— utilisasi rata-rata **{peak_hour['Avg_Utilization']:.0f}%**"
                )
                c_b.info(
                    f"**💤 Jam Paling Sepi:** Pukul **{int(offpeak_hour['Hour'])}:00** "
                    f"— utilisasi rata-rata **{offpeak_hour['Avg_Utilization']:.0f}%**"
                )
    except Exception as _e:
        import streamlit as _st
        _st.error(f"⚠️ Terjadi kesalahan pada modul ini: {_e}")
