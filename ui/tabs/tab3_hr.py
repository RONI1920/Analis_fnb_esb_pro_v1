# ui/tabs/tab3_hr.py — Tab 3: SDM, Waiter Performance & Deteksi Anomali (Enhanced)

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pandas as pd

from analytics.gmv import get_peak_time_analysis
from analytics.hr import get_waiter_performance, get_fraud_analysis
from analytics.hr_advanced import (
    get_waiter_leaderboard,
    get_waiter_monthly_trend,
    get_waiter_consistency_score,
    get_waiter_shift_analysis,
    get_waiter_vs_avg,
)
from insights.generators import generate_hr_insights, generate_fraud_insights
from ui.charts import create_horizontal_bar_chart, create_vertical_bar_chart
from formatters import format_rupiah, format_angka_bulat


def build_tab3_hr(filtered_waiter, df_gmv=None):  # ← tambah df_gmv=None
    if filtered_waiter is None:
        st.info("Silakan upload file Rekapitulasi Detail (File 3) di sidebar.")
        return
    if filtered_waiter.empty:
        st.warning("Tidak ada data Waiter untuk rentang waktu yang dipilih.")
        return

    st.header("🧑‍🍳 Analisis Kinerja SDM & Waiter")

    # ── Pre-load semua data ────────────────────────────────
    time_data = get_peak_time_analysis(filtered_waiter)
    leaderboard = get_waiter_leaderboard(filtered_waiter)
    trend = get_waiter_monthly_trend(filtered_waiter)
    consistency = get_waiter_consistency_score(filtered_waiter)
    shift_perf = get_waiter_shift_analysis(filtered_waiter)
    vs_avg = get_waiter_vs_avg(filtered_waiter)
    fraud_result, status_msg = get_fraud_analysis(filtered_waiter)

    # ════════════════════════════════════════════════════════
    # 1. KPI RINGKASAN
    # ════════════════════════════════════════════════════════
    st.subheader("📊 Ringkasan SDM")

    total_waiter = (
        filtered_waiter["Waiter"].nunique()
        if "Waiter" in filtered_waiter.columns
        else 0
    )
    total_bills = filtered_waiter["Bill Number"].nunique()
    total_revenue = filtered_waiter["Total After Bill Discount"].sum()
    avg_atv = total_revenue / total_bills if total_bills > 0 else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("👥 Total Waiter Aktif", f"{total_waiter}")
    k2.metric("🧾 Total Transaksi", f"{total_bills:,}")
    k3.metric("💰 Total Revenue", format_rupiah(total_revenue))
    k4.metric("💸 ATV", format_rupiah(avg_atv))

    st.markdown("---")

    # ════════════════════════════════════════════════════════
    # 2. LEADERBOARD
    # ════════════════════════════════════════════════════════
    st.header("🏆 Leaderboard Waiter")

    if not leaderboard.empty:
        # Podium Top 3
        top3 = leaderboard.head(3)
        p1, p2, p3 = st.columns(3)
        for col, (_, row) in zip([p1, p2, p3], top3.iterrows()):
            with col:
                st.markdown(f"### {row['Badge']} {row['Waiter']}")
                st.metric("Revenue", format_rupiah(row["Total_Revenue"]))
                st.metric("Bill", f"{int(row['Jumlah_Bill']):,}")
                st.metric("ATV", format_rupiah(row["ATV"]))
                st.caption(f"Share: {row['Revenue_Share']:.1f}%")

        st.markdown("---")

        # Full leaderboard bar chart
        fig_lb = px.bar(
            leaderboard,
            x="Total_Revenue",
            y="Waiter",
            orientation="h",
            color="Revenue_Share",
            color_continuous_scale="Blues",
            text=leaderboard["Total_Revenue"].apply(
                lambda v: "Rp " + f"{int(v):,}".replace(",", ".")
            ),
            labels={"Total_Revenue": "Total Revenue", "Revenue_Share": "Share (%)"},
            height=max(350, len(leaderboard) * 45),
            title="Top 10 Waiter by Revenue",
        )
        fig_lb.update_traces(textposition="outside")
        fig_lb.update_layout(
            yaxis=dict(autorange="reversed"),
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_lb, use_container_width=True)

        # Leaderboard table
        with st.expander("📋 Tabel Leaderboard Lengkap"):
            tbl = leaderboard.copy()
            tbl["Total_Revenue"] = tbl["Total_Revenue"].apply(format_rupiah)
            tbl["ATV"] = tbl["ATV"].apply(format_rupiah)
            tbl["Revenue_Share"] = tbl["Revenue_Share"].apply(lambda x: f"{x:.1f}%")
            st.dataframe(
                tbl[
                    [
                        "Badge",
                        "Waiter",
                        "Total_Revenue",
                        "Jumlah_Bill",
                        "ATV",
                        "Revenue_Share",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

    st.markdown("---")

    # ════════════════════════════════════════════════════════
    # 3. TREN PERFORMA PER BULAN
    # ════════════════════════════════════════════════════════
    st.header("📈 Tren Performa Waiter per Bulan")

    if not trend.empty:
        trnd_opt = st.radio(
            "Metrik:", ["Revenue", "Bills", "ATV"], horizontal=True, key="trend_metric"
        )

        fig_trend = px.line(
            trend,
            x="Month",
            y=trnd_opt,
            color="Waiter",
            markers=True,
            height=420,
            labels={
                "Month": "Bulan",
                "Revenue": "Revenue (Rp)",
                "Bills": "Jumlah Bill",
                "ATV": "ATV (Rp)",
            },
            title=f"Tren {trnd_opt} per Bulan — Top 8 Waiter",
        )
        fig_trend.update_layout(
            hovermode="x unified",
            legend_title="Waiter",
            xaxis_tickformat="%b %Y",
        )
        st.plotly_chart(fig_trend, use_container_width=True)

        # Heatmap waiter × bulan
        st.subheader("🔥 Heatmap Revenue Waiter × Bulan")
        pivot = trend.pivot_table(
            index="Waiter",
            columns="Month",
            values="Revenue",
            aggfunc="sum",
            fill_value=0,
        )
        pivot.columns = [c.strftime("%b %Y") for c in pivot.columns]

        fig_heat = px.imshow(
            pivot,
            color_continuous_scale="Blues",
            labels=dict(x="Bulan", y="Waiter", color="Revenue"),
            aspect="auto",
            height=max(300, len(pivot) * 40),
            title="Revenue per Waiter per Bulan",
        )
        fig_heat.update_xaxes(tickangle=-30)
        st.plotly_chart(fig_heat, use_container_width=True)

    st.markdown("---")

    # ════════════════════════════════════════════════════════
    # 4. KONSISTENSI WAITER
    # ════════════════════════════════════════════════════════
    st.header("🎯 Skor Konsistensi Waiter")
    st.caption(
        "Waiter dengan skor tinggi = performa stabil setiap bulan. Skor rendah = fluktuatif."
    )

    if not consistency.empty:
        cons_col1, cons_col2 = st.columns(2)

        with cons_col1:
            fig_cons = px.bar(
                consistency.head(12),
                x="Skor_Konsistensi",
                y="Waiter",
                orientation="h",
                color="Skor_Konsistensi",
                color_continuous_scale="RdYlGn",
                range_color=[0, 100],
                text=consistency.head(12)["Skor_Konsistensi"].apply(
                    lambda x: f"{x:.0f}"
                ),
                height=420,
                title="Skor Konsistensi (0-100)",
            )
            fig_cons.update_traces(textposition="outside")
            fig_cons.update_layout(
                yaxis=dict(autorange="reversed"), coloraxis_showscale=False
            )
            st.plotly_chart(fig_cons, use_container_width=True)

        with cons_col2:
            status_count = consistency["Status"].value_counts().reset_index()
            status_count.columns = ["Status", "Jumlah"]
            fig_status = px.pie(
                status_count,
                names="Status",
                values="Jumlah",
                color="Status",
                color_discrete_map={
                    "🟢 Konsisten": "#2ecc71",
                    "🟡 Cukup Konsisten": "#f39c12",
                    "🔴 Fluktuatif": "#e74c3c",
                },
                height=300,
                title="Distribusi Konsistensi",
            )
            fig_status.update_traces(textinfo="percent+label")
            fig_status.update_layout(showlegend=False)
            st.plotly_chart(fig_status, use_container_width=True)

            st.markdown("##### Detail Konsistensi")
            tbl_cons = consistency[
                [
                    "Waiter",
                    "Avg_Revenue",
                    "CV",
                    "Skor_Konsistensi",
                    "Status",
                    "Months_Active",
                ]
            ].copy()
            tbl_cons["Avg_Revenue"] = tbl_cons["Avg_Revenue"].apply(format_rupiah)
            tbl_cons["CV"] = tbl_cons["CV"].apply(lambda x: f"{x:.1f}%")
            tbl_cons["Skor_Konsistensi"] = tbl_cons["Skor_Konsistensi"].apply(
                lambda x: f"{x:.0f}"
            )
            st.dataframe(tbl_cons, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ════════════════════════════════════════════════════════
    # 5. ANALISIS SHIFT
    # ════════════════════════════════════════════════════════
    st.header("🕒 Performa Waiter per Shift")

    if not shift_perf.empty:
        sh1, sh2 = st.columns(2)

        with sh1:
            fig_shift_rev = px.bar(
                shift_perf,
                x="Waiter",
                y="Revenue",
                color="Shift",
                barmode="group",
                height=400,
                title="Revenue per Shift",
                color_discrete_sequence=["#f39c12", "#3498db", "#2c3e50"],
            )
            fig_shift_rev.update_layout(xaxis_tickangle=-30, legend_title="Shift")
            st.plotly_chart(fig_shift_rev, use_container_width=True)

        with sh2:
            fig_shift_atv = px.bar(
                shift_perf,
                x="Waiter",
                y="ATV",
                color="Shift",
                barmode="group",
                height=400,
                title="ATV per Shift",
                color_discrete_sequence=["#f39c12", "#3498db", "#2c3e50"],
            )
            fig_shift_atv.update_layout(xaxis_tickangle=-30, legend_title="Shift")
            st.plotly_chart(fig_shift_atv, use_container_width=True)

    st.markdown("---")

    # ════════════════════════════════════════════════════════
    # 6. WAITER VS RATA-RATA TOKO
    # ════════════════════════════════════════════════════════
    st.header("⚖️ Waiter vs Rata-rata Toko")

    if not vs_avg.empty:
        avg_rev = vs_avg["Avg_Revenue"].iloc[0]
        avg_atv = vs_avg["Avg_ATV"].iloc[0]

        va1, va2 = st.columns(2)
        va1.metric("Rata-rata Revenue per Waiter", format_rupiah(avg_rev))
        va2.metric("Rata-rata ATV per Waiter", format_rupiah(avg_atv))

        fig_vs = px.scatter(
            vs_avg,
            x="Revenue_vs_Avg",
            y="ATV_vs_Avg",
            text="Waiter",
            color="Revenue_vs_Avg",
            color_continuous_scale="RdYlGn",
            size="Bills",
            size_max=30,
            labels={
                "Revenue_vs_Avg": "Revenue vs Avg (%)",
                "ATV_vs_Avg": "ATV vs Avg (%)",
            },
            height=450,
            title="Posisi Waiter vs Rata-rata Toko",
        )
        fig_vs.add_vline(x=0, line_dash="dash", line_color="gray", opacity=0.5)
        fig_vs.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        fig_vs.add_annotation(
            x=50,
            y=50,
            text="⭐ Revenue & ATV Tinggi",
            showarrow=False,
            font=dict(color="#27ae60"),
        )
        fig_vs.add_annotation(
            x=-50,
            y=-50,
            text="⚠️ Revenue & ATV Rendah",
            showarrow=False,
            font=dict(color="#e74c3c"),
        )
        fig_vs.update_traces(textposition="top center")
        fig_vs.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig_vs, use_container_width=True)

    st.markdown("---")

    # ════════════════════════════════════════════════════════
    # 7. WAKTU KUNJUNGAN
    # ════════════════════════════════════════════════════════
    st.header("🕒 Analisis Waktu Kunjungan Pelanggan")

    with st.expander("Lihat Analisis Waktu Kunjungan", expanded=False):
        sort_time = [
            "Breakfast/Brunch (10-12)",
            "Lunch (12-17)",
            "Dinner (17-22)",
            "Luar Jam Buka",
        ]
        t1, t2 = st.columns(2)
        with t1:
            st.markdown("##### Berdasarkan Jumlah Transaksi")
            st.plotly_chart(
                create_vertical_bar_chart(
                    time_data,
                    "Waktu Kunjungan",
                    "Jumlah_Transaksi",
                    "Waktu",
                    "Jumlah Transaksi",
                    "O",
                    sort_order=sort_time,
                ),
                use_container_width=True,
            )
        with t2:
            st.markdown("##### Berdasarkan Total Penjualan")
            st.plotly_chart(
                create_vertical_bar_chart(
                    time_data,
                    "Waktu Kunjungan",
                    "Total_Penjualan",
                    "Waktu",
                    "Total Penjualan (Rp)",
                    "O",
                    sort_order=sort_time,
                ),
                use_container_width=True,
            )
        st.dataframe(
            time_data.set_index("Waktu Kunjungan").style.format(
                {
                    "Total_Penjualan": format_rupiah,
                    "Jumlah_Transaksi": format_angka_bulat,
                }
            ),
            use_container_width=True,
        )

    st.markdown("---")

    # ════════════════════════════════════════════════════════
    # 8. DETEKSI ANOMALI
    # ════════════════════════════════════════════════════════
    st.header("🕵️ Deteksi Anomali & Potensi Kecurangan")
    st.caption("Analisis pola 'Void Sales' dan 'Non Sales' yang tidak wajar.")

    if not fraud_result:
        st.warning(f"Gagal menjalankan analisa: {status_msg}")
    else:
        tab_void, tab_ns, tab_raw = st.tabs(
            ["🔴 Analisa Void", "🟠 Analisa Non-Sales", "📋 Data Mentah"]
        )

        with tab_void:
            res = fraud_result["void"]
            df_voids = filtered_waiter[
                filtered_waiter["Sales Type"].isin(
                    ["Void", "Void Sales", "Void sales", "VOID"]
                )
            ].copy()

            if not df_voids.empty:
                col_uang = "Net Sales" if "Net Sales" in df_voids.columns else "Total"
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Kejadian Void", f"{len(df_voids)} kali")
                c2.metric(
                    "Total Nilai Void",
                    (
                        format_rupiah(df_voids[col_uang].sum())
                        if col_uang in df_voids.columns
                        else "Rp 0"
                    ),
                )
                c3.metric("Rata-rata per Waiter", f"{res['avg']:.1f} kali")

                st.markdown("---")
                desired = [
                    "Sales Date In",
                    "Time",
                    "Waiter",
                    "Qty",
                    "Net Sales",
                    "Total",
                    "Table",
                    "Section",
                ]
                final_cols = [c for c in desired if c in df_voids.columns]
                sort_cols = [c for c in ["Sales Date In", "Time"] if c in final_cols]
                df_disp = (
                    df_voids[final_cols].sort_values(by=sort_cols, ascending=False)
                    if sort_cols
                    else df_voids[final_cols]
                )

                fmt = {}
                if "Net Sales" in final_cols:
                    fmt["Net Sales"] = format_rupiah
                elif "Total" in final_cols:
                    fmt["Total"] = format_rupiah
                if "Qty" in final_cols:
                    fmt["Qty"] = "{:.0f}"

                st.dataframe(df_disp.style.format(fmt), use_container_width=True)
                st.download_button(
                    "📥 Download Data Void (CSV)",
                    df_voids[final_cols].to_csv(index=False).encode("utf-8"),
                    "laporan_void.csv",
                    "text/csv",
                )
            else:
                st.success("✅ Tidak ada transaksi Void sama sekali.")

            if not res["suspects"].empty:
                st.markdown("---")
                st.error(
                    f"⚠️ {len(res['suspects'])} Karyawan anomali Void (Threshold: {res['threshold']:.0f}x):"
                )
                st.table(res["suspects"].style.highlight_max(axis=0, color="pink"))

        with tab_ns:
            res_ns = fraud_result["nonsales"]
            if not res_ns["suspects"].empty:
                st.error(
                    f"⚠️ {len(res_ns['suspects'])} Karyawan anomali Non-Sales (Threshold: {res_ns['threshold']:.0f}x):"
                )
                st.table(res_ns["suspects"].style.highlight_max(axis=0, color="orange"))
            else:
                st.success("✅ Tidak ada anomali Non-Sales.")
                st.caption(f"Rata-rata Non-Sales: {res_ns['avg']:.1f} kali/waiter.")

        with tab_raw:
            st.dataframe(fraud_result["raw_data"], use_container_width=True)

    st.markdown("---")

    # ════════════════════════════════════════════════════════
    # 9. INSIGHT OTOMATIS
    # ════════════════════════════════════════════════════════
    st.header("💡 Insight Otomatis")

    # Leaderboard insight
    if not leaderboard.empty:
        top1 = leaderboard.iloc[0]
        st.success(
            f"🥇 Waiter terbaik: **{top1['Waiter']}** — Revenue {format_rupiah(top1['Total_Revenue'])} ({top1['Revenue_Share']:.1f}% share)"
        )

    # Konsistensi insight
    if not consistency.empty:
        n_konsisten = (consistency["Status"] == "🟢 Konsisten").sum()
        n_fluktuatif = (consistency["Status"] == "🔴 Fluktuatif").sum()
        if n_fluktuatif > 0:
            st.warning(
                f"⚠️ {n_fluktuatif} waiter performa fluktuatif — perlu coaching atau evaluasi jadwal."
            )
        if n_konsisten > 0:
            st.info(f"✅ {n_konsisten} waiter performa konsisten setiap bulan.")

    # Void insight
    if fraud_result:
        void_suspects = fraud_result["void"]["suspects"]
        if not void_suspects.empty:
            st.error(
                f"🔴 {len(void_suspects)} waiter memiliki pola Void tidak wajar — perlu investigasi."
            )

    insights = generate_hr_insights(time_data, get_waiter_performance(filtered_waiter))
    if fraud_result:
        insights += generate_fraud_insights(fraud_result)

    with st.expander("📄 Temuan Kunci dari Data SDM", expanded=True):
        for ins in insights:
            st.markdown(f"&bull; {ins}")
