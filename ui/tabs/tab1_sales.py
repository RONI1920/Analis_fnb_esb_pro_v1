# ui/tabs/tab1_sales.py — Tab 1: Analisis Penjualan (GMV) Enhanced

import altair as alt
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pandas as pd

from analytics.gmv import (
    calculate_sales_kpi,
    get_menu_performance,
    get_operational_kpi,
    get_payment_analysis,
    get_visit_purpose_analysis,
)
from analytics.gmv_advanced import (
    get_pareto_analysis,
    get_revenue_trend,
    get_branch_performance,
    get_weekly_cohort,
    get_hourly_heatmap,
    get_category_trend,
    get_growth_metrics,
)
from insights.generators import generate_gmv_insights
from ui.charts import create_horizontal_bar_chart, create_vertical_bar_chart
from formatters import format_rupiah, format_angka_bulat

DAY_ID = {
    "Monday": "Senin",
    "Tuesday": "Selasa",
    "Wednesday": "Rabu",
    "Thursday": "Kamis",
    "Friday": "Jumat",
    "Saturday": "Sabtu",
    "Sunday": "Minggu",
}


def build_tab1_sales(filtered_gmv):
    if filtered_gmv is None:
        st.markdown(
            """
            <div style="text-align:center;padding:60px 20px;">
                <div style="font-size:5rem;">📂</div>
                <h2 style="margin-top:12px;">Data Belum Dimuat</h2>
                <p style="color:#aaa;font-size:1rem;max-width:400px;margin:10px auto 0;">
                    Silakan <b>upload file Laporan GMV (File 1)</b> melalui panel sidebar di sebelah kiri
                    untuk mulai menampilkan analisis penjualan.
                </p>
                <div style="margin-top:20px;padding:12px 24px;background:#1e2535;border-radius:8px;
                            display:inline-block;color:#6ee7b7;font-size:0.95rem;">
                    ⬅️ Buka Sidebar → Upload Laporan GMV
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return
    if filtered_gmv.empty:
        st.warning("Tidak ada data GMV untuk rentang waktu yang dipilih.")
        return

    start = filtered_gmv["Sales Date In"].min().strftime("%d-%m-%Y")
    end = filtered_gmv["Sales Date In"].max().strftime("%d-%m-%Y")
    st.subheader(f"Periode Analisis: {start} s.d. {end}")

    # ── Filter Menu — Multiselect checkbox per menu ─────────────────
    import re as _re

    _all_menus = (
        sorted(filtered_gmv["Menu"].dropna().unique().tolist())
        if "Menu" in filtered_gmv.columns
        else []
    )

    # Default: menu yang match regex awal
    _DEFAULT_EXCLUDED = [
        m
        for m in _all_menus
        if _re.search(
            r"\bOcha\b|Refill|Mineral Water|ADD[ -]?ON|ADDITIONAL|Level",
            m,
            _re.IGNORECASE,
        )
    ]
    if "excluded_menus" not in st.session_state:
        st.session_state["excluded_menus"] = []  # default: tidak ada menu dikecualikan

    # Hanya simpan menu yang masih ada di data aktif
    _saved_excluded = [m for m in st.session_state.get("excluded_menus", []) if m in _all_menus]

    with st.expander("⚙️ Filter Menu — Pilih menu yang TIDAK dihitung", expanded=False):
        st.markdown(
            "<p style='font-size:12px;color:#9ca3af;margin-bottom:4px'>"
            "Menu yang <b style='color:#f87171'>dicentang ✓</b> akan "
            "<b>DIKECUALIKAN</b> dari seluruh analisis — "
            "Total Pendapatan, KPI, semua chart & tab lainnya.</p>",
            unsafe_allow_html=True,
        )
        st.info(
            "ℹ️ **Filter ini hanya berlaku untuk tampilan dashboard** — tidak mengubah "
            "data yang tersimpan di database. Database selalu menyimpan semua menu lengkap. "
            "Filter ini diterapkan ulang otomatis setiap kali dashboard dibuka.",
            icon=None,
        )

        # ── Tombol aksi cepat ──────────────────────────────────────
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if st.button("☑ Pilih Semua", key="excl_sel_all", use_container_width=True):
                st.session_state["excluded_menus"] = _all_menus.copy()
                st.rerun()
        with c2:
            if st.button("☐ Hapus Semua", key="excl_clr_all", use_container_width=True):
                st.session_state["excluded_menus"] = []
                st.rerun()
        with c3:
            if st.button(
                "↩ Default",
                key="excl_default",
                use_container_width=True,
                help="Kembalikan ke filter default: Ocha, Refill, Mineral Water, Add-on, Level",
            ):
                st.session_state["excluded_menus"] = _DEFAULT_EXCLUDED.copy()
                st.rerun()
        with c4:
            excl_search = st.text_input(
                "Cari menu",
                placeholder="🔍 Cari nama menu...",
                key="excl_menu_search",
                label_visibility="collapsed",
            )

        st.divider()

        # ── Kelompokkan per kategori ───────────────────────────────
        _cat_map = {}
        if "Menu Category" in filtered_gmv.columns:
            for m in _all_menus:
                rows_m = filtered_gmv[filtered_gmv["Menu"] == m]
                cat = (
                    str(rows_m["Menu Category"].iloc[0])
                    if not rows_m.empty
                    else "Lainnya"
                )
                _cat_map.setdefault(cat, []).append(m)
        else:
            _cat_map["Semua Menu"] = _all_menus

        newly_excluded = []

        for cat in sorted(_cat_map.keys()):
            menus_in_cat = _cat_map[cat]
            if excl_search:
                menus_in_cat = [
                    m for m in menus_in_cat if excl_search.lower() in m.lower()
                ]
            if not menus_in_cat:
                continue

            n_excl_cat = sum(1 for m in menus_in_cat if m in _saved_excluded)
            badge_col = "#ef4444" if n_excl_cat else "#374151"
            badge_bg = "#450a0a" if n_excl_cat else "#111827"

            st.markdown(
                f"<div style='margin:10px 0 4px 0;display:flex;align-items:center;gap:8px'>"
                f"<b style='color:#93c5fd;font-size:12px'>{cat}</b>"
                f"<span style='background:{badge_bg};color:{badge_col};border:1px solid {badge_col}40;"
                f"padding:1px 8px;border-radius:5px;font-size:10px;font-weight:700'>"
                f"{n_excl_cat}/{len(menus_in_cat)} dikecualikan</span></div>",
                unsafe_allow_html=True,
            )

            cols2 = st.columns(2)
            for idx, menu_name in enumerate(sorted(menus_in_cat)):
                tabd_val = filtered_gmv[filtered_gmv["Menu"] == menu_name][
                    "Total After Bill Discount"
                ].sum()
                rev_str = f"  ·  Rp {tabd_val:,.0f}" if tabd_val > 0 else "  ·  Rp 0"
                is_on = menu_name in _saved_excluded
                with cols2[idx % 2]:
                    # FIX: pakai cat+idx sebagai key, bukan hash (hash bisa collision)
                    safe_cat = str(cat).replace(" ", "_")[:20]
                    chk = st.checkbox(
                        f"{menu_name}{rev_str}",
                        value=is_on,
                        key=f"excl_m_{safe_cat}_{idx}",
                    )
                if chk:
                    newly_excluded.append(menu_name)

        # Update state
        st.session_state["excluded_menus"] = newly_excluded

        # ── Summary ───────────────────────────────────────────────
        rev_excl = (
            filtered_gmv[filtered_gmv["Menu"].isin(newly_excluded)][
                "Total After Bill Discount"
            ].sum()
            if newly_excluded
            else 0
        )
        rev_total = filtered_gmv["Total After Bill Discount"].sum()
        pct_excl = (rev_excl / rev_total * 100) if rev_total > 0 else 0
        n_excl = (
            filtered_gmv[filtered_gmv["Menu"].isin(newly_excluded)].shape[0]
            if newly_excluded
            else 0
        )

        st.divider()
        if newly_excluded:
            st.markdown(
                f"""<div style="background:#1c0a0a;border:1px solid #7f1d1d;border-radius:8px;
                padding:10px 16px;display:flex;flex-wrap:wrap;gap:16px;align-items:center">
                <span style="color:#fca5a5;font-weight:700;font-size:12px">
                    🚫 {len(newly_excluded)} menu dikecualikan ({n_excl:,} baris)
                </span>
                <span style="color:#f87171;font-size:12px">
                    − Rp {rev_excl:,.0f} &nbsp;({pct_excl:.1f}%)
                </span>
                <span style="color:#34d399;font-weight:700;font-size:12px">
                    ✅ Dihitung: Rp {rev_total - rev_excl:,.0f}
                </span>
                </div>""",
                unsafe_allow_html=True,
            )
        else:
            st.success("✅ Tidak ada menu dikecualikan — semua menu masuk perhitungan.")

    # ── Terapkan filter ke df sebelum hitung KPI & semua analitik ─
    _excluded_list = st.session_state.get("excluded_menus", [])
    df_for_kpi = (
        filtered_gmv[~filtered_gmv["Menu"].isin(_excluded_list)].copy()
        if _excluded_list
        else filtered_gmv
    )
    if _excluded_list:
        n_excl_rows = len(filtered_gmv) - len(df_for_kpi)
        st.caption(
            f"⚙️ Filter menu aktif: **{len(_excluded_list)} menu** ({n_excl_rows:,} baris) dikecualikan dari analisis."
        )

    filter_regex = ""  # tidak dipakai lagi, pakai _excluded_list

    # ── Hitung semua data dari df yang sudah difilter ──────
    kpi = calculate_sales_kpi(df_for_kpi)
    (
        top_selling,
        top_grossing,
        top_sell_cat,
        top_gross_cat,
        bottom_selling,
        bottom_grossing,
        menu_sales_cat_df,
    ) = get_menu_performance(df_for_kpi, filter_regex)
    growth = get_growth_metrics(df_for_kpi)
    pareto = get_pareto_analysis(df_for_kpi, filter_regex)
    trend_w = get_revenue_trend(df_for_kpi, "W")
    trend_m = get_revenue_trend(df_for_kpi, "M")
    branch_perf = get_branch_performance(df_for_kpi)
    cat_trend = get_category_trend(df_for_kpi)
    heatmap_df = get_hourly_heatmap(df_for_kpi)
    cohort_df = get_weekly_cohort(df_for_kpi)

    # ════════════════════════════════════════════════════════
    # 1. KPI UTAMA
    # ════════════════════════════════════════════════════════
    st.header("📊 KPI Kinerja Penjualan")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Total Pendapatan", format_rupiah(kpi["Total Pendapatan Kotor"]))
    c2.metric("🧾 Total Transaksi", f"{kpi['Total Transaksi']:,}")
    c3.metric("💸 ATV", format_rupiah(kpi["Rata-rata Nilai Transaksi (ATV)"]))
    c4.metric("📦 IPB", f"{kpi['Item per Transaksi (IPB)']:.2f}")

    # FIX: tampilkan info jumlah data aktif vs total di DB agar user tahu filter apa yang aktif
    _total_rows_full   = len(filtered_gmv) if filtered_gmv is not None else 0
    _total_rows_kpi    = len(df_for_kpi) if df_for_kpi is not None else 0
    _excluded_count    = len(st.session_state.get("excluded_menus", []))
    _af                = st.session_state.get("applied_filter", {})
    _period_active     = _af.get("period", "Semua") if _af else "Semua"
    _branch_active     = _af.get("branch", "Semua") if _af else "Semua"

    _info_parts = [f"📊 **{_total_rows_kpi:,}** baris data aktif"]
    if _total_rows_kpi < _total_rows_full:
        _info_parts.append(f"(dari {_total_rows_full:,} total)")
    if _period_active != "Semua":
        _info_parts.append(f"· 🗓️ Periode: **{_period_active}**")
    if _branch_active not in ("Semua", "Semua Cabang"):
        _info_parts.append(f"· 🏪 Cabang: **{_branch_active}**")
    if _excluded_count > 0:
        _info_parts.append(f"· 🚫 **{_excluded_count}** menu dikecualikan")
    st.caption("  ".join(_info_parts))

    # MoM Growth cards
    if not growth.empty and len(growth) >= 2:
        last = growth.iloc[-1]
        st.markdown("##### 📈 Month-over-Month Growth (Bulan Terakhir)")
        g1, g2, g3 = st.columns(3)
        rev_g = last["Revenue_Growth"] if pd.notna(last["Revenue_Growth"]) else 0
        trx_g = (
            last["Transaction_Growth"] if pd.notna(last["Transaction_Growth"]) else 0
        )
        atv_g = last["ATV_Growth"] if pd.notna(last["ATV_Growth"]) else 0
        g1.metric("Revenue MoM", format_rupiah(last["Revenue"]), f"{rev_g:+.1f}%")
        g2.metric("Transaksi MoM", f"{int(last['Transactions']):,}", f"{trx_g:+.1f}%")
        g3.metric("ATV MoM", format_rupiah(last["ATV"]), f"{atv_g:+.1f}%")

    with st.expander("Lihat Rincian (Diskon, Service, Pajak)"):
        e1, e2, e3 = st.columns(3)
        e1.metric("📉 Total Diskon", format_rupiah(kpi["Total Diskon"]))
        e2.metric("🛎️ Service Charge", format_rupiah(kpi["Total Service Charge"]))
        e3.metric("🧾 Pajak", format_rupiah(kpi["Total Pajak"]))

    st.markdown("---")

    # ════════════════════════════════════════════════════════
    # 2. TREN REVENUE
    # ════════════════════════════════════════════════════════
    st.header("📈 Tren Revenue")

    gran_opt = st.radio(
        "Granularitas:", ["Mingguan", "Bulanan"], horizontal=True, key="gran"
    )
    trend_df = trend_w if gran_opt == "Mingguan" else trend_m

    if not trend_df.empty:
        fig_trend = go.Figure()
        fig_trend.add_trace(
            go.Bar(
                x=trend_df["Period"],
                y=trend_df["Revenue"],
                name="Revenue",
                marker_color="#3498db",
                opacity=0.7,
                hovertemplate="<b>%{x}</b><br>Revenue: Rp %{y:,.0f}<extra></extra>",
            )
        )
        fig_trend.add_trace(
            go.Scatter(
                x=trend_df["Period"],
                y=trend_df["Revenue_MA7"],
                name="Moving Average (3 periode)",
                line=dict(color="#e74c3c", width=2.5),
                hovertemplate="MA: Rp %{y:,.0f}<extra></extra>",
            )
        )
        fig_trend.update_layout(
            height=380,
            yaxis_title="Revenue (Rp)",
            legend=dict(orientation="h", y=1.1),
            hovermode="x unified",
        )
        st.plotly_chart(fig_trend, use_container_width=True)

    # MoM Growth table
    if not growth.empty:
        with st.expander("📊 Detail MoM Growth per Bulan"):
            tbl = growth.copy()
            tbl["Month"] = tbl["Month"].dt.strftime("%b %Y")
            tbl["Revenue"] = tbl["Revenue"].apply(format_rupiah)
            tbl["ATV"] = tbl["ATV"].apply(format_rupiah)
            tbl["Revenue_Growth"] = tbl["Revenue_Growth"].apply(
                lambda x: f"{x:+.1f}%" if pd.notna(x) else "-"
            )
            tbl["Transaction_Growth"] = tbl["Transaction_Growth"].apply(
                lambda x: f"{x:+.1f}%" if pd.notna(x) else "-"
            )
            tbl["ATV_Growth"] = tbl["ATV_Growth"].apply(
                lambda x: f"{x:+.1f}%" if pd.notna(x) else "-"
            )
            tbl = tbl.rename(
                columns={
                    "Month": "Bulan",
                    "Revenue": "Revenue",
                    "Transactions": "Transaksi",
                    "Revenue_Growth": "Growth Revenue",
                    "Transaction_Growth": "Growth Trx",
                    "ATV_Growth": "Growth ATV",
                }
            )
            st.dataframe(
                tbl[
                    [
                        "Bulan",
                        "Revenue",
                        "Transaksi",
                        "Growth Revenue",
                        "Growth Trx",
                        "ATV",
                        "Growth ATV",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

    st.markdown("---")

    # ════════════════════════════════════════════════════════
    # 3. TREN KATEGORI
    # ════════════════════════════════════════════════════════
    st.header("🍽️ Tren Revenue per Kategori")

    if not cat_trend.empty:
        fig_cat = px.line(
            cat_trend,
            x="Month",
            y="Revenue",
            color="Menu Category",
            markers=True,
            height=400,
            labels={"Revenue": "Revenue (Rp)", "Month": "Bulan"},
        )
        fig_cat.update_layout(hovermode="x unified", legend_title="Kategori")
        st.plotly_chart(fig_cat, use_container_width=True)

    st.markdown("---")

    # ════════════════════════════════════════════════════════
    # 4. PERBANDINGAN CABANG
    # ════════════════════════════════════════════════════════
    if not branch_perf.empty and branch_perf["Branch"].nunique() > 1:
        st.header("🏪 Perbandingan Performa Cabang")

        fig_branch = px.bar(
            branch_perf,
            x="Month",
            y="Revenue",
            color="Branch",
            barmode="group",
            height=420,
            labels={"Revenue": "Revenue (Rp)", "Month": "Bulan"},
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig_branch.update_layout(
            hovermode="x unified", legend_title="Cabang", xaxis_tickformat="%b %Y"
        )
        st.plotly_chart(fig_branch, use_container_width=True)

        # ATV per cabang
        atv_branch = (
            branch_perf.groupby("Branch")
            .agg(
                Total_Revenue=("Revenue", "sum"),
                Total_Transactions=("Transactions", "sum"),
            )
            .reset_index()
        )
        atv_branch["ATV"] = (
            atv_branch["Total_Revenue"] / atv_branch["Total_Transactions"]
        )
        atv_branch = atv_branch.sort_values("Total_Revenue", ascending=False)

        bc1, bc2 = st.columns(2)
        with bc1:
            fig_atv = px.bar(
                atv_branch,
                x="Branch",
                y="ATV",
                color="Branch",
                title="ATV per Cabang",
                height=350,
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig_atv.update_layout(showlegend=False, xaxis_tickangle=-20)
            st.plotly_chart(fig_atv, use_container_width=True)
        with bc2:
            fig_trx = px.bar(
                atv_branch,
                x="Branch",
                y="Total_Transactions",
                color="Branch",
                title="Total Transaksi per Cabang",
                height=350,
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig_trx.update_layout(showlegend=False, xaxis_tickangle=-20)
            st.plotly_chart(fig_trx, use_container_width=True)

        st.markdown("---")

    # ════════════════════════════════════════════════════════
    # 5. PARETO ANALYSIS
    # ════════════════════════════════════════════════════════
    st.header("📐 Pareto Analysis — 80/20 Rule")

    if not pareto.empty:
        n_top = (pareto["Revenue_Cumsum"] <= 80).sum()
        total_menu = len(pareto)
        pct_menu = n_top / total_menu * 100

        pa1, pa2, pa3 = st.columns(3)
        pa1.metric("Menu Penyumbang 80% Revenue", f"{n_top} menu")
        pa2.metric("Dari Total Menu", f"{total_menu} menu")
        pa3.metric("Konsentrasi Revenue", f"{pct_menu:.1f}% menu = 80% omzet")

        # Chart Pareto
        fig_pareto = go.Figure()
        colors = [
            "#e74c3c" if z == "🔴 Top 20% (80% Revenue)" else "#bdc3c7"
            for z in pareto["Zone"]
        ]
        fig_pareto.add_trace(
            go.Bar(
                x=pareto["Rank"],
                y=pareto["Revenue"],
                marker_color=colors,
                name="Revenue per Menu",
                hovertemplate="<b>%{customdata}</b><br>Revenue: Rp %{y:,.0f}<extra></extra>",
                customdata=pareto["Menu"],
            )
        )
        fig_pareto.add_trace(
            go.Scatter(
                x=pareto["Rank"],
                y=pareto["Revenue_Cumsum"],
                yaxis="y2",
                name="Kumulatif %",
                line=dict(color="#2c3e50", width=2),
                hovertemplate="Kumulatif: %{y:.1f}%<extra></extra>",
            )
        )
        fig_pareto.add_hline(
            y=80,
            yref="y2",
            line_dash="dash",
            line_color="#e74c3c",
            annotation_text="80%",
        )
        fig_pareto.update_layout(
            height=450,
            yaxis=dict(title="Revenue (Rp)"),
            yaxis2=dict(
                title="Kumulatif (%)",
                overlaying="y",
                side="right",
                range=[0, 105],
                showgrid=False,
            ),
            legend=dict(orientation="h", y=1.1),
            hovermode="x unified",
        )
        st.plotly_chart(fig_pareto, use_container_width=True)

        # Top Pareto table
        with st.expander(f"📋 Lihat {n_top} Menu Penyumbang 80% Revenue"):
            top_pareto = pareto[pareto["Zone"] == "🔴 Top 20% (80% Revenue)"].copy()
            top_pareto["Revenue"] = top_pareto["Revenue"].apply(format_rupiah)
            top_pareto["Revenue_Pct"] = top_pareto["Revenue_Pct"].apply(
                lambda x: f"{x:.2f}%"
            )
            top_pareto["Revenue_Cumsum"] = top_pareto["Revenue_Cumsum"].apply(
                lambda x: f"{x:.1f}%"
            )
            st.dataframe(
                top_pareto[
                    ["Rank", "Menu", "Qty", "Revenue", "Revenue_Pct", "Revenue_Cumsum"]
                ],
                use_container_width=True,
                hide_index=True,
            )

    st.markdown("---")

    # ════════════════════════════════════════════════════════
    # 6. HEATMAP JAM × HARI
    # ════════════════════════════════════════════════════════
    st.header("🔥 Heatmap Transaksi — Jam × Hari")

    if not heatmap_df.empty:
        heatmap_df["Hari"] = heatmap_df["Weekday"].map(DAY_ID)
        heatmap_pivot = heatmap_df.pivot_table(
            index="Weekday",
            columns="Hour",
            values="Transactions",
            aggfunc="sum",
            fill_value=0,
        )
        day_order_en = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        day_order_id = [DAY_ID[d] for d in day_order_en]
        heatmap_pivot = heatmap_pivot.reindex(day_order_en)
        heatmap_pivot.index = day_order_id

        fig_heat = px.imshow(
            heatmap_pivot,
            color_continuous_scale="YlOrRd",
            labels=dict(x="Jam", y="Hari", color="Transaksi"),
            aspect="auto",
            height=340,
            title="Jumlah Transaksi per Jam per Hari",
        )
        fig_heat.update_xaxes(
            tickmode="linear",
            dtick=1,
            ticktext=[f"{h:02d}:00" for h in range(24)],
            tickvals=list(range(24)),
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    st.markdown("---")

    # ════════════════════════════════════════════════════════
    # 7. COHORT PENJUALAN PER HARI × BULAN
    # ════════════════════════════════════════════════════════
    st.header("📅 Cohort Revenue — Hari × Bulan")

    if not cohort_df.empty:
        cohort_df["Hari"] = cohort_df["Weekday"].map(DAY_ID)
        cohort_pivot = cohort_df.pivot_table(
            index="Hari", columns="Month", values="Revenue", aggfunc="sum", fill_value=0
        )
        day_order_id = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
        cohort_pivot = cohort_pivot.reindex(
            [d for d in day_order_id if d in cohort_pivot.index]
        )

        fig_cohort = px.imshow(
            cohort_pivot,
            color_continuous_scale="Blues",
            labels=dict(x="Bulan", y="Hari", color="Revenue"),
            aspect="auto",
            height=320,
            title="Revenue per Hari dalam Seminggu × Bulan",
            text_auto=False,
        )
        st.plotly_chart(fig_cohort, use_container_width=True)

    st.markdown("---")

    # ════════════════════════════════════════════════════════
    # 8. ANALISIS MENU & KATEGORI (existing, dipertahankan)
    # ════════════════════════════════════════════════════════
    st.header("🍽️ Analisis Menu & Kategori")

    if "Menu Category" in filtered_gmv.columns and not menu_sales_cat_df.empty:
        with st.expander("🍰 Analisis Kategori Menu Interaktif", expanded=True):
            data_kat = (
                menu_sales_cat_df.groupby("Menu Category")["Qty"].sum().reset_index()
            )
            data_kat_sorted = data_kat.sort_values("Qty", ascending=False)

            N_TOP = 15
            top_n = data_kat_sorted.head(N_TOP)
            others = data_kat_sorted.iloc[N_TOP:]
            if not others.empty:
                top_n = pd.concat(
                    [
                        top_n,
                        pd.DataFrame(
                            [
                                {
                                    "Menu Category": "Lainnya (Others)",
                                    "Qty": others["Qty"].sum(),
                                }
                            ]
                        ),
                    ]
                ).reset_index(drop=True)

            show_all = st.checkbox("Tampilkan Semua Kategori", value=False)
            data_grafik = data_kat_sorted if show_all else top_n

            data_menu_item = (
                menu_sales_cat_df.groupby(["Menu Category", "Menu"])["Qty"]
                .sum()
                .reset_index()
            )
            sel_kat = alt.selection_point(fields=["Menu Category"])

            chart_kat = (
                alt.Chart(data_grafik)
                .mark_bar()
                .encode(
                    x=alt.X(
                        "Qty:Q", title="Kuantiti Terjual", axis=alt.Axis(orient="top")
                    ),
                    y=alt.Y(
                        "Menu Category:N", sort="-x", axis=alt.Axis(labelLimit=300)
                    ),
                    tooltip=["Menu Category", "Qty"],
                    color=alt.condition(
                        sel_kat, alt.value("orange"), alt.value("steelblue")
                    ),
                )
                .add_params(sel_kat)
                .properties(
                    title="Klik kategori untuk drill-down",
                    height=min(max(len(data_grafik) * 25, 150), 400),
                )
            )
            chart_detail = (
                alt.Chart(data_menu_item)
                .mark_bar()
                .encode(
                    x=alt.X("Qty:Q", axis=alt.Axis(orient="top")),
                    y=alt.Y("Menu:N", sort="-x", axis=alt.Axis(labelLimit=300)),
                    tooltip=["Menu Category", "Menu", "Qty"],
                )
                .transform_filter(sel_kat)
                .properties(
                    title="Detail per Menu Item",
                    height=min(
                        max(len(data_menu_item["Menu"].unique()) * 25, 150), 400
                    ),
                )
            )
            st.altair_chart(
                alt.vconcat(chart_kat, chart_detail, spacing=40).resolve_scale(
                    y="independent"
                ),
                use_container_width=True,
            )

    with st.expander("🏆 Top 10 Menu (Terlaris)"):
        t1, t2 = st.columns(2)
        with t1:
            st.markdown("##### Menu Terlaris (Qty)")
            st.dataframe(
                top_selling.set_index("Menu").style.format({"Qty": format_angka_bulat})
            )
        with t2:
            st.markdown("##### Pendapatan Tertinggi")
            st.dataframe(
                top_grossing.set_index("Menu").style.format(
                    {"Total Nett Sales": format_rupiah}
                )
            )

        g1, g2 = st.columns(2)
        with g1:
            st.plotly_chart(
                create_horizontal_bar_chart(
                    top_selling, "Qty", "Menu", "Kuantitas", "Terlaris by Qty"
                ),
                use_container_width=True,
            )
        with g2:
            st.plotly_chart(
                create_horizontal_bar_chart(
                    top_grossing,
                    "Total Nett Sales",
                    "Menu",
                    "Nett Sales (Rp)",
                    "Tertinggi by Revenue",
                ),
                use_container_width=True,
            )

    with st.expander("📉 Bottom 10 Menu (Kurang Laku)"):
        b1, b2 = st.columns(2)
        with b1:
            st.markdown("##### Paling Jarang Terjual")
            st.dataframe(
                bottom_selling.set_index("Menu").style.format(
                    {"Qty": format_angka_bulat}
                )
            )
        with b2:
            st.markdown("##### Pendapatan Terendah")
            st.dataframe(
                bottom_grossing.set_index("Menu").style.format(
                    {"Total Nett Sales": format_rupiah}
                )
            )

    st.markdown("---")

    # ════════════════════════════════════════════════════════
    # 9. OPERASIONAL
    # ════════════════════════════════════════════════════════
    st.header("⚙️ Analisis Operasional")

    avg_time, peak_hours, peak_days = get_operational_kpi(filtered_gmv)

    op1, op2, op3 = st.columns(3)
    if avg_time > 0:
        op1.metric("⏱️ Avg Durasi Makan", f"{avg_time:.1f} menit")

    o1, o2 = st.columns(2)
    with o1:
        st.subheader("🕒 Jam Sibuk")
        peak_h = peak_hours.copy()
        peak_h["Jam_Label"] = peak_h["Hour"].apply(lambda h: f"{h:02d}:00")
        hour_order = peak_h.sort_values("Hour")["Jam_Label"].tolist()
        st.plotly_chart(
            create_vertical_bar_chart(
                peak_h,
                "Jam_Label",
                "Bill Number",
                "Jam",
                "Jumlah Transaksi",
                x_type="O",
                sort_order=hour_order,
            ),
            use_container_width=True,
        )
    with o2:
        st.subheader("🗓️ Hari Sibuk")
        day_order = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
        st.plotly_chart(
            create_vertical_bar_chart(
                peak_days,
                "Day Name",
                "Bill Number",
                "Hari",
                "Jumlah Transaksi",
                x_type="O",
                sort_order=day_order,
            ),
            use_container_width=True,
        )

    with st.expander("💳 Analisis Transaksi (Pembayaran & Kunjungan)", expanded=False):
        if "Payment Method" in filtered_gmv.columns:
            st.subheader("💳 Metode Pembayaran")
            st.plotly_chart(
                create_horizontal_bar_chart(
                    get_payment_analysis(filtered_gmv),
                    "Total_Penjualan",
                    "Cleaned_Payment",
                    "Total Penjualan (Rp)",
                    "Metode Pembayaran",
                ),
                use_container_width=True,
            )
        if "Visit Purpose" in filtered_gmv.columns:
            st.subheader("🏪 Tipe Kunjungan")
            st.plotly_chart(
                create_horizontal_bar_chart(
                    get_visit_purpose_analysis(filtered_gmv),
                    "Total After Bill Discount",
                    "Visit Purpose",
                    "Total Penjualan (Rp)",
                    "Tipe Kunjungan",
                ),
                use_container_width=True,
            )

    st.markdown("---")

    # ════════════════════════════════════════════════════════
    # 10. INSIGHT OTOMATIS
    # ════════════════════════════════════════════════════════
    st.header("💡 Insight Otomatis")

    # Pareto insight
    if not pareto.empty:
        n_top = (pareto["Revenue_Cumsum"] <= 80).sum()
        pct = n_top / len(pareto) * 100
        if pct < 25:
            st.success(
                f"✅ **Pareto Sehat:** Hanya {n_top} menu ({pct:.0f}%) menyumbang 80% revenue. Fokus pertahankan menu-menu ini."
            )
        else:
            st.warning(
                f"⚠️ **Revenue Tersebar:** {n_top} menu ({pct:.0f}%) perlu mencapai 80% revenue. Pertimbangkan simplifikasi menu."
            )

    # Growth insight
    if not growth.empty and len(growth) >= 2:
        last_growth = growth.iloc[-1]["Revenue_Growth"]
        if pd.notna(last_growth):
            if last_growth > 5:
                st.success(
                    f"✅ Revenue bulan terakhir tumbuh **{last_growth:+.1f}%** MoM."
                )
            elif last_growth < -5:
                st.error(
                    f"🔴 Revenue bulan terakhir turun **{last_growth:+.1f}%** MoM. Perlu tindakan segera."
                )
            else:
                st.info(
                    f"📊 Revenue bulan terakhir relatif stabil (**{last_growth:+.1f}%** MoM)."
                )

    # Branch insight
    if not branch_perf.empty and branch_perf["Branch"].nunique() > 1:
        best_branch = branch_perf.groupby("Branch")["Revenue"].sum().idxmax()
        st.info(f"🏪 Cabang dengan revenue tertinggi: **{best_branch}**")

    insights = generate_gmv_insights(
        kpi, top_selling, bottom_selling, peak_hours, peak_days
    )
    with st.expander("📄 Temuan Kunci dari Data Penjualan", expanded=True):
        for ins in insights:
            st.markdown(f"&bull; {ins}")
