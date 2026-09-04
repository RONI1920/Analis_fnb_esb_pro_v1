# ui/tabs/tab13_pl.py — Tab 13: Profit & Loss Dashboard

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from insights.generators import generate_pl_insights
from formatters import format_rupiah


def build_tab13_pl(df_pl):
    try:
        st.header("📉 Profit & Loss Dashboard")
        st.caption("Ringkasan performa bisnis dan profitabilitas perusahaan.")

        if df_pl is None or df_pl.empty:
            st.warning("⚠️ Data P&L belum tersedia. Silakan upload file di sidebar.")
            return

        # ── Filter Periode ─────────────────────────────────────
        if "Year_Type" in df_pl.columns:
            years = sorted(df_pl["Year_Type"].dropna().unique(), reverse=True)
            sel_year = st.selectbox("📅 Pilih Periode", years)
            df_f = df_pl[df_pl["Year_Type"] == sel_year]
        else:
            df_f = df_pl.copy()

        if df_f.empty:
            st.warning("Data kosong untuk periode ini.")
            return

        if "Date" in df_f.columns:
            df_f = df_f.copy()
            df_f["Date"] = pd.to_datetime(df_f["Date"], errors="coerce")

        # ── Hitung KPI ─────────────────────────────────────────
        total_rev = df_f[df_f["Category"] == "Revenue"]["Value"].sum()
        total_cogs = df_f[df_f["Category"] == "COGS"]["Value"].sum()
        total_exp = df_f[df_f["Category"] == "Expense"]["Value"].sum()
        gross_profit = total_rev - total_cogs
        net_profit = gross_profit - total_exp

        gp_margin = (gross_profit / total_rev * 100) if total_rev > 0 else 0
        np_margin = (net_profit / total_rev * 100) if total_rev > 0 else 0
        cogs_pct = (total_cogs / total_rev * 100) if total_rev > 0 else 0
        exp_pct = (total_exp / total_rev * 100) if total_rev > 0 else 0

        # ── KPI Cards ──────────────────────────────────────────
        st.subheader("📌 Ringkasan Keuangan")
        r1c1, r1c2, r1c3 = st.columns(3)
        r1c1.metric("Revenue", format_rupiah(total_rev))
        r1c2.metric("COGS", format_rupiah(total_cogs), f"{cogs_pct:.1f}%")
        r1c3.metric("Gross Profit", format_rupiah(gross_profit), f"{gp_margin:.1f}%")

        r2c1, r2c2 = st.columns(2)
        r2c1.metric("Operating Expense", format_rupiah(total_exp), f"{exp_pct:.1f}%")
        r2c2.metric("Net Profit", format_rupiah(net_profit), f"{np_margin:.1f}%")

        st.markdown("---")

        # ── Executive Summary ──────────────────────────────────
        st.subheader("🧠 Executive Summary")
        status = "🟢 Sangat Sehat" if np_margin >= 20 else ("🟡 Cukup Sehat" if np_margin >= 10 else "🔴 Profit Rendah")
        with st.container(border=True):
            st.markdown(f"""
            ### Status Profitabilitas
            **Net Profit Margin:** {np_margin:.1f}% | **Kondisi:** {status}
            ---
            • Revenue: {format_rupiah(total_rev)}
            • Gross Profit: {format_rupiah(gross_profit)}
            • Net Profit: {format_rupiah(net_profit)}
            """)

        st.markdown("---")

        # ── Charts ─────────────────────────────────────────────
        ch1, ch2 = st.columns(2)

        with ch1:
            st.markdown("#### 💧 Profit Flow (Waterfall)")
            fig_wf = go.Figure(go.Waterfall(
                measure=["relative", "relative", "total", "relative", "total"],
                x=["Revenue", "COGS", "Gross Profit", "Expense", "Net Profit"],
                y=[total_rev, -total_cogs, gross_profit, -total_exp, net_profit],
                text=[format_rupiah(v) for v in [total_rev, -total_cogs, gross_profit, -total_exp, net_profit]],
                textposition="outside",
                connector={"line": {"color": "#BDC3C7"}},
                increasing={"marker": {"color": "#2ECC71"}},
                decreasing={"marker": {"color": "#E74C3C"}},
                totals={"marker": {"color": "#3498DB"}},
            ))
            fig_wf.update_layout(template="plotly_white", height=420, showlegend=False,
                                  margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_wf, use_container_width=True)

        with ch2:
            st.markdown("#### 📈 Revenue vs Net Profit")
            if "Date" in df_f.columns:
                df_monthly = (
                    df_f.groupby("Date").apply(lambda x: pd.Series({
                        "Revenue": x[x["Category"] == "Revenue"]["Value"].sum(),
                        "Net_Profit": (
                            x[x["Category"] == "Revenue"]["Value"].sum()
                            - x[x["Category"] == "COGS"]["Value"].sum()
                            - x[x["Category"] == "Expense"]["Value"].sum()
                        ),
                    })).reset_index()
                )
                fig_tr = go.Figure()
                fig_tr.add_trace(go.Bar(x=df_monthly["Date"], y=df_monthly["Revenue"], name="Revenue", opacity=0.7))
                fig_tr.add_trace(go.Scatter(x=df_monthly["Date"], y=df_monthly["Net_Profit"],
                                            name="Net Profit", mode="lines+markers"))
                fig_tr.update_layout(template="plotly_white", height=420, hovermode="x unified",
                                      margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig_tr, use_container_width=True)

        st.markdown("---")

        # ── Cost Structure ─────────────────────────────────────
        st.subheader("💸 Struktur Pengeluaran")
        cs1, cs2 = st.columns([1, 1.3])

        with cs1:
            fig_dn = go.Figure(data=[go.Pie(
                labels=["COGS", "Expense", "Net Profit"],
                values=[total_cogs, total_exp, max(net_profit, 0)],
                hole=0.55,
            )])
            fig_dn.update_layout(template="plotly_white", height=350, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_dn, use_container_width=True)

        with cs2:
            st.markdown("#### 🔥 Top Expense")
            df_exp = df_f[df_f["Category"] == "Expense"]
            if not df_exp.empty:
                top_exp = (df_exp.groupby("Description")["Value"].sum()
                           .reset_index().sort_values("Value", ascending=False).head(10))
                fig_bar = go.Figure(go.Bar(
                    x=top_exp["Value"], y=top_exp["Description"], orientation="h",
                    text=[format_rupiah(v) for v in top_exp["Value"]], textposition="auto"
                ))
                fig_bar.update_layout(template="plotly_white", height=350,
                                      yaxis=dict(autorange="reversed"),
                                      margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("---")

        # ── Insight ────────────────────────────────────────────
        st.subheader("💡 Insight Bisnis")
        with st.container(border=True):
            for ins in generate_pl_insights(df_pl):
                st.markdown(f"• {ins}")

        with st.expander("📋 Lihat Detail Expense"):
            if not df_exp.empty:
                detail = (df_exp.groupby("Description")["Value"].sum()
                          .reset_index().sort_values("Value", ascending=False))
                detail["Value"] = detail["Value"].apply(format_rupiah)
                st.dataframe(detail.rename(columns={"Description": "Expense", "Value": "Total"}),
                             use_container_width=True, hide_index=True)
    except Exception as _e:
        import streamlit as _st
        _st.error(f"⚠️ Terjadi kesalahan pada modul ini: {_e}")
