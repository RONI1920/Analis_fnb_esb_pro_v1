# ui/tabs/tab13_pl_advanced.py — Tambahan untuk Tab P&L: Analisis Lanjutan
#
# File ini MELENGKAPI tab13_pl.py yang sudah ada.
# Cara pakai: import fungsi ini dan panggil di akhir build_tab13_pl()
#
#   from ui.tabs.tab13_pl_advanced import build_pl_advanced_section
#   build_pl_advanced_section(df_pl, df_gmv)

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pandas as pd

from analytics.pl_advanced import (
    compute_pl_summary,
    get_pl_mom_comparison,
    get_pl_yoy_comparison,
    get_business_breakeven,
    get_expense_benchmark,
    get_cash_flow_projection,
)
from formatters import format_rupiah


def build_pl_advanced_section(df_pl: pd.DataFrame, df_gmv: pd.DataFrame = None):
    try:
        """
        Dipanggil dari build_tab13_pl() untuk menambahkan analisis lanjutan.
        Letakkan setelah bagian insight dasar.
        """
        if df_pl is None or df_pl.empty:
            return

        st.markdown("---")
        st.header("📊 Analisis P&L Lanjutan")

        tabs = st.tabs([
            "📅 MoM & YoY",
            "⚖️ Break-Even",
            "📐 Benchmark Industri",
            "🔮 Proyeksi Cash Flow",
        ])

        # ════════════════════════════════════════════════════════
        # TAB A: MOM & YOY
        # ════════════════════════════════════════════════════════
        with tabs[0]:
            st.subheader("📅 Tren Bulanan (MoM) & Perbandingan Tahunan (YoY)")

            mom_df = get_pl_mom_comparison(df_pl)
            if not mom_df.empty:
                st.markdown("#### Revenue, Gross Profit & Net Profit per Bulan")
                fig_mom = go.Figure()
                fig_mom.add_trace(go.Bar(
                    x=mom_df["Date"], y=mom_df["Revenue"],
                    name="Revenue", marker_color="#3498db", opacity=0.7,
                ))
                fig_mom.add_trace(go.Scatter(
                    x=mom_df["Date"], y=mom_df["Gross_Profit"],
                    name="Gross Profit", mode="lines+markers",
                    line=dict(color="#2ecc71", width=2),
                ))
                fig_mom.add_trace(go.Scatter(
                    x=mom_df["Date"], y=mom_df["Net_Profit"],
                    name="Net Profit", mode="lines+markers",
                    line=dict(color="#e74c3c", width=2, dash="dot"),
                ))
                fig_mom.update_layout(
                    template="plotly_white", height=400, hovermode="x unified",
                    legend=dict(orientation="h", y=1.1),
                    margin=dict(l=10, r=10, t=20, b=10),
                )
                st.plotly_chart(fig_mom, use_container_width=True)

                # Margin trend
                st.markdown("#### Tren Margin (%)")
                fig_margin = go.Figure()
                fig_margin.add_trace(go.Scatter(
                    x=mom_df["Date"], y=mom_df["GP_Margin_%"],
                    name="Gross Margin %", mode="lines+markers",
                    line=dict(color="#27ae60"),
                ))
                fig_margin.add_trace(go.Scatter(
                    x=mom_df["Date"], y=mom_df["NP_Margin_%"],
                    name="Net Profit Margin %", mode="lines+markers",
                    line=dict(color="#c0392b"),
                ))
                fig_margin.add_hline(y=15, line_dash="dash", annotation_text="Target NP 15%",
                                     line_color="gray", opacity=0.6)
                fig_margin.update_layout(
                    template="plotly_white", height=350, hovermode="x unified",
                    yaxis_ticksuffix="%",
                    legend=dict(orientation="h", y=1.1),
                    margin=dict(l=10, r=10, t=20, b=10),
                )
                st.plotly_chart(fig_margin, use_container_width=True)

            # YoY
            yoy_df = get_pl_yoy_comparison(df_pl)
            if not yoy_df.empty and len(yoy_df) >= 2:
                st.markdown("#### Perbandingan Tahun Ini vs Tahun Lalu (YoY)")

                display_cols = ["Periode", "Revenue", "Gross_Profit", "Net_Profit",
                                "GP_Margin_%", "NP_Margin_%"]
                tbl_yoy = yoy_df[display_cols].copy()
                for col in ["Revenue", "Gross_Profit", "Net_Profit"]:
                    tbl_yoy[col] = tbl_yoy[col].apply(
                        lambda x: f"{x:+.1f}%" if tbl_yoy["Periode"].iloc[tbl_yoy[tbl_yoy[col].name if False else col].name if False else 0] == "YoY Growth %"
                        else format_rupiah(x)
                    )
                # Simplified display
                for col in ["Revenue", "Gross_Profit", "Net_Profit"]:
                    tbl_yoy[col] = yoy_df[col].apply(
                        lambda x: f"{x:+.1f}%" if abs(x) < 1000 else format_rupiah(x)
                    )
                tbl_yoy["GP_Margin_%"] = yoy_df["GP_Margin_%"].round(1).astype(str) + "%"
                tbl_yoy["NP_Margin_%"] = yoy_df["NP_Margin_%"].round(1).astype(str) + "%"

                st.dataframe(
                    tbl_yoy.rename(columns={
                        "Periode":       "Periode",
                        "Revenue":       "Revenue",
                        "Gross_Profit":  "Gross Profit",
                        "Net_Profit":    "Net Profit",
                        "GP_Margin_%":   "GP Margin",
                        "NP_Margin_%":   "NP Margin",
                    }),
                    use_container_width=True, hide_index=True,
                )
            else:
                st.info("Data tahun lalu tidak tersedia untuk perbandingan YoY.")

        # ════════════════════════════════════════════════════════
        # TAB B: BREAK-EVEN
        # ════════════════════════════════════════════════════════
        with tabs[1]:
            st.subheader("⚖️ Break-Even Analysis Bisnis")
            st.caption("Menghitung titik balik modal bisnis secara keseluruhan.")

            be = get_business_breakeven(df_pl, df_gmv)
            if not be:
                st.warning("Data tidak cukup untuk break-even analysis.")
            else:
                status_icon = "✅" if be["is_above_be"] else "❌"
                status_text = "Di Atas BEP" if be["is_above_be"] else "Di Bawah BEP — Merugi"

                with st.container(border=True):
                    st.markdown(f"### {status_icon} Status: **{status_text}**")
                    st.divider()
                    b1, b2, b3 = st.columns(3)
                    b1.metric("Fixed Cost (Expense)",    format_rupiah(be["fixed_cost"]))
                    b2.metric("Variable Cost (COGS)",    format_rupiah(be["variable_cost"]))
                    b3.metric("Contribution Margin Ratio", f"{be['cmr']*100:.1f}%")

                    b4, b5, b6 = st.columns(3)
                    b4.metric("Break-Even Revenue",      format_rupiah(be["breakeven_revenue"]))
                    b5.metric("Actual Revenue",          format_rupiah(be["total_revenue"]))
                    b6.metric("Margin of Safety",
                              format_rupiah(be["margin_of_safety"]),
                              f"{be['mos_pct']:.1f}% dari revenue")

                if be.get("be_transactions"):
                    st.info(f"💡 Bisnis perlu minimal **{be['be_transactions']:,} transaksi** "
                            f"(berdasarkan rata-rata ATV) untuk mencapai Break-Even Point.")

                # Waterfall BEP
                fig_be = go.Figure(go.Waterfall(
                    measure=["absolute", "relative", "total", "relative", "total"],
                    x=["Revenue", "- Variable Cost", "Contribution Margin",
                       "- Fixed Cost", "Net Profit"],
                    y=[be["total_revenue"], -be["variable_cost"],
                       be["total_revenue"] - be["variable_cost"],
                       -be["fixed_cost"], be["total_revenue"] - be["variable_cost"] - be["fixed_cost"]],
                    text=[format_rupiah(v) for v in [
                        be["total_revenue"], -be["variable_cost"],
                        be["total_revenue"] - be["variable_cost"],
                        -be["fixed_cost"],
                        be["total_revenue"] - be["variable_cost"] - be["fixed_cost"]
                    ]],
                    textposition="outside",
                    connector={"line": {"color": "#BDC3C7"}},
                    increasing={"marker": {"color": "#2ECC71"}},
                    decreasing={"marker": {"color": "#E74C3C"}},
                    totals={"marker": {"color": "#3498DB"}},
                ))
                fig_be.update_layout(template="plotly_white", height=380,
                                     margin=dict(l=10, r=10, t=20, b=10))
                st.plotly_chart(fig_be, use_container_width=True)

        # ════════════════════════════════════════════════════════
        # TAB C: BENCHMARK
        # ════════════════════════════════════════════════════════
        with tabs[2]:
            st.subheader("📐 Benchmark vs Standar Industri F&B Indonesia")

            bench_df = get_expense_benchmark(df_pl)
            pl_summary = compute_pl_summary(df_pl)

            if pl_summary:
                st.markdown("#### Status vs Benchmark")
                bench_items = [
                    ("Gross Margin",       pl_summary.get("gp_margin", 0),     65.0, True,  "Ideal: ≥65%"),
                    ("Net Profit Margin",  pl_summary.get("np_margin", 0),     15.0, True,  "Ideal: ≥15%"),
                    ("Food Cost (COGS %)", pl_summary.get("cogs_pct", 0),      30.0, False, "Ideal: ≤30%"),
                    ("Overhead %",         pl_summary.get("exp_pct", 0),       25.0, False, "Ideal: ≤25%"),
                ]
                cols = st.columns(len(bench_items))
                for i, (label, actual, benchmark, higher_is_better, help_text) in enumerate(bench_items):
                    gap = actual - benchmark
                    if higher_is_better:
                        delta_color = "normal" if gap >= 0 else "inverse"
                    else:
                        delta_color = "inverse" if gap > 0 else "normal"
                    cols[i].metric(
                        label,
                        f"{actual:.1f}%",
                        f"{gap:+.1f}% vs benchmark",
                        delta_color=delta_color,
                        help=help_text,
                    )

            if not bench_df.empty:
                st.markdown("#### Detail Perbandingan")
                st.dataframe(
                    bench_df.rename(columns={
                        "Kategori":       "Kategori Biaya",
                        "Aktual (Rp)":    "Aktual (Rp)",
                        "Aktual (%)":     "Aktual (%)",
                        "Benchmark (%)":  "Benchmark F&B (%)",
                        "Gap (%)":        "Gap (%)",
                        "Status":         "Status",
                    }),
                    use_container_width=True, hide_index=True,
                )

            with st.expander("📚 Referensi Benchmark F&B Indonesia"):
                st.markdown("""
                | Metrik | Ideal | Warning |
                |--------|-------|---------|
                | Food Cost (COGS %) | ≤ 30% | > 35% |
                | Labor Cost % | ≤ 25% | > 35% |
                | Overhead % | ≤ 15% | > 25% |
                | Net Profit Margin | ≥ 15% | < 8% |
                | Gross Margin | ≥ 65% | < 55% |

                *Sumber: Benchmark F&B industri restoran Indonesia (kasual-menengah)*
                """)

        # ════════════════════════════════════════════════════════
        # TAB D: CASH FLOW PROJECTION
        # ════════════════════════════════════════════════════════
        with tabs[3]:
            st.subheader("🔮 Proyeksi Cash Flow")
            st.caption(
                "Proyeksi berdasarkan tren 3 bulan terakhir. "
                "Ini adalah estimasi sederhana — bukan pengganti analisis akuntansi profesional."
            )

            months_ahead = st.slider("Proyeksi ke depan (bulan):", 1, 6, 3, key="cf_months")

            with st.spinner("Menghitung proyeksi..."):
                cf_df = get_cash_flow_projection(df_pl, months_ahead)

            if cf_df.empty:
                st.warning("Data tidak cukup untuk proyeksi (minimal 2 bulan historis).")
            else:
                # Chart
                hist = cf_df[cf_df["Type"] == "Historis"]
                proj = cf_df[cf_df["Type"] == "Proyeksi"]

                fig_cf = go.Figure()
                for col, color, dash in [
                    ("Revenue", "#3498db", "solid"),
                    ("Gross_Profit", "#2ecc71", "solid"),
                    ("Net_Profit", "#e74c3c", "solid"),
                ]:
                    fig_cf.add_trace(go.Scatter(
                        x=hist["Date"], y=hist[col],
                        name=f"{col} (Historis)",
                        mode="lines+markers",
                        line=dict(color=color, dash=dash),
                    ))
                    if not proj.empty:
                        fig_cf.add_trace(go.Scatter(
                            x=proj["Date"], y=proj[col],
                            name=f"{col} (Proyeksi)",
                            mode="lines+markers",
                            line=dict(color=color, dash="dash"),
                            marker=dict(symbol="diamond"),
                        ))

                # Vertical line pemisah historis vs proyeksi
                if not hist.empty and not proj.empty:
                    fig_cf.add_vline(
                        x=hist["Date"].max(),
                        line_dash="dot", line_color="gray",
                        annotation_text="← Historis | Proyeksi →",
                    )

                fig_cf.update_layout(
                    template="plotly_white", height=420,
                    hovermode="x unified",
                    legend=dict(orientation="h", y=1.15),
                    margin=dict(l=10, r=10, t=20, b=10),
                )
                st.plotly_chart(fig_cf, use_container_width=True)

                if not proj.empty:
                    st.markdown("#### Ringkasan Proyeksi")
                    proj_display = proj.copy()
                    proj_display["Date"] = proj_display["Date"].dt.strftime("%B %Y")
                    for col in ["Revenue", "Gross_Profit", "Net_Profit"]:
                        proj_display[col] = proj_display[col].apply(format_rupiah)
                    proj_display["GP_Margin_%"] = proj_display["GP_Margin_%"].round(1).astype(str) + "%"
                    proj_display["NP_Margin_%"] = proj_display["NP_Margin_%"].round(1).astype(str) + "%"

                    st.dataframe(
                        proj_display[["Date", "Revenue", "Gross_Profit", "Net_Profit",
                                      "GP_Margin_%", "NP_Margin_%"]].rename(columns={
                            "Date":         "Bulan",
                            "Revenue":      "Est. Revenue",
                            "Gross_Profit": "Est. Gross Profit",
                            "Net_Profit":   "Est. Net Profit",
                            "GP_Margin_%":  "GP Margin",
                            "NP_Margin_%":  "NP Margin",
                        }),
                        use_container_width=True, hide_index=True,
                    )

                st.warning(
                    "⚠️ **Disclaimer:** Proyeksi ini hanya berdasarkan tren historis. "
                    "Faktor eksternal (inflasi, kompetisi, perubahan operasional) tidak diperhitungkan."
                )
    except Exception as _e:
        import streamlit as _st
        _st.error(f"⚠️ Terjadi kesalahan pada modul ini: {_e}")
