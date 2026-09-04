# ui/tabs/tab_section_clarify.py
# Tab: Klarifikasi Section — Bar / Kitchen / Dessert & Pastry
# Memecah analisis penjualan berdasarkan Table Section atau Menu Category
# agar masing-masing departemen bisa melihat kinerjanya secara terpisah.

from __future__ import annotations

import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from formatters import format_rupiah, format_angka_bulat

# ──────────────────────────────────────────────────────────────────
# MAPPING DEFAULT SECTION
# Bisa di-override via session_state["section_keyword_map"]
# ──────────────────────────────────────────────────────────────────

DEFAULT_SECTION_MAP: dict[str, list[str]] = {
    "🍹 Bar": [
        "bar", "beverage", "minuman", "drink", "coffee", "tea",
        "juice", "smoothie", "cocktail", "mocktail", "milk",
    ],
    "🍳 Kitchen": [
        "kitchen", "food", "makanan", "main course", "appetizer",
        "soup", "rice", "noodle", "mie", "nasi", "pasta", "grill",
        "fried", "snack", "starter", "salad",
    ],
    "🍰 Dessert & Pastry": [
        "dessert", "pastry", "cake", "bakery", "sweet", "ice cream",
        "pudding", "waffle", "crepe", "donut", "kue", "roti",
        "tart", "pie", "bread",
    ],
}

SECTION_COLORS = {
    "🍹 Bar":             "#3b82f6",
    "🍳 Kitchen":         "#10b981",
    "🍰 Dessert & Pastry": "#f59e0b",
    "🔘 Lainnya":         "#6b7280",
}


# ──────────────────────────────────────────────────────────────────
# HELPER: Klasifikasi baris ke section
# ──────────────────────────────────────────────────────────────────

def _classify_section(df: pd.DataFrame, section_map: dict[str, list[str]]) -> pd.Series:
    """
    Klasifikasi setiap baris ke section berdasarkan:
    1. Kolom 'Table Section' jika ada
    2. Fallback ke 'Menu Category' dan 'Menu'
    """
    def _match(val: str) -> str | None:
        val_lower = val.lower()
        for section, keywords in section_map.items():
            for kw in keywords:
                if kw in val_lower:
                    return section
        return None

    result = []
    for _, row in df.iterrows():
        # Prioritas 1: Table Section
        ts = str(row.get("Table Section", "")).strip()
        if ts and ts.lower() not in ("nan", "none", ""):
            matched = _match(ts)
            if matched:
                result.append(matched)
                continue

        # Prioritas 2: Menu Category Detail
        mcd = str(row.get("Menu Category Detail", "")).strip()
        if mcd and mcd.lower() not in ("nan", "none", ""):
            matched = _match(mcd)
            if matched:
                result.append(matched)
                continue

        # Prioritas 3: Menu Category
        mc = str(row.get("Menu Category", "")).strip()
        if mc and mc.lower() not in ("nan", "none", ""):
            matched = _match(mc)
            if matched:
                result.append(matched)
                continue

        # Prioritas 4: Menu name
        menu = str(row.get("Menu", "")).strip()
        if menu and menu.lower() not in ("nan", "none", ""):
            matched = _match(menu)
            if matched:
                result.append(matched)
                continue

        result.append("🔘 Lainnya")

    return pd.Series(result, index=df.index)


def _kpi_card(col, label: str, value: str, delta: str = "", color: str = "#3b82f6"):
    with col:
        delta_html = f'<div style="font-size:11px;color:#6ee7b7;margin-top:4px">{delta}</div>' if delta else ""
        html = (
            f'<div style="background:linear-gradient(135deg,{color}18,{color}08);'
            f'border:1px solid {color}40;border-radius:12px;padding:16px 18px;'
            f'text-align:center;min-height:90px">'
            f'<div style="font-size:10px;color:#9ca3af;text-transform:uppercase;'
            f'letter-spacing:.1em;margin-bottom:6px">{label}</div>'
            f'<div style="font-size:1.45rem;font-weight:900;color:{color}">{value}</div>'
            f'{delta_html}'
            f'</div>'
        )
        st.markdown(html, unsafe_allow_html=True)


def _section_header(title: str, color: str):
    st.markdown(
        f"""<div style="background:linear-gradient(90deg,{color}22,transparent);
            border-left:4px solid {color};padding:10px 16px;border-radius:0 8px 8px 0;
            margin:18px 0 12px 0">
            <span style="font-size:1.1rem;font-weight:800;color:{color}">{title}</span>
        </div>""",
        unsafe_allow_html=True,
    )


# ──────────────────────────────────────────────────────────────────
# MAIN BUILD FUNCTION
# ──────────────────────────────────────────────────────────────────

def build_tab_section_clarify(filtered_gmv: pd.DataFrame | None, filtered_cogs: pd.DataFrame | None = None):
    if filtered_gmv is None or filtered_gmv.empty:
        st.markdown(
            """<div style="text-align:center;padding:60px 20px">
                <div style="font-size:4rem">🍽️</div>
                <h2 style="margin-top:12px">Data Belum Dimuat</h2>
                <p style="color:#aaa;max-width:380px;margin:10px auto 0">
                    Upload file GMV terlebih dahulu untuk melihat klarifikasi per section
                    (Bar, Kitchen, Dessert & Pastry).
                </p>
            </div>""",
            unsafe_allow_html=True,
        )
        return

    # ── Header ────────────────────────────────────────────────────
    st.markdown(
        """<div style="background:linear-gradient(135deg,#0d1b2e,#1a1f2e);
            border:1px solid #2d3a55;border-radius:14px;padding:20px 28px;
            margin-bottom:18px;text-align:center">
            <div style="font-size:11px;color:#60a5fa;text-transform:uppercase;
                 letter-spacing:.16em;font-weight:700;margin-bottom:6px">
                🍽️ &nbsp;KLARIFIKASI PER SECTION DEPARTEMEN
            </div>
            <div style="font-size:1.5rem;font-weight:900;color:#f0f2f5">
                Bar &nbsp;·&nbsp; Kitchen &nbsp;·&nbsp; Dessert & Pastry
            </div>
            <div style="font-size:12px;color:#9ca3af;margin-top:8px">
                Analisis kinerja penjualan, margin, dan menu terbaik per departemen
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    # ── Konfigurasi keyword mapping ───────────────────────────────
    with st.expander("⚙️ Konfigurasi Keyword Section", expanded=False):
        st.markdown(
            "<p style='font-size:12px;color:#9ca3af'>Sistem mengklasifikasi baris data ke section berdasarkan "
            "kolom <b>Table Section</b>, <b>Menu Category</b>, atau <b>nama Menu</b> yang cocok dengan keyword di bawah.</p>",
            unsafe_allow_html=True,
        )
        # Ambil atau inisialisasi dari session
        kw_map = st.session_state.get("section_keyword_map", DEFAULT_SECTION_MAP.copy())

        col_a, col_b, col_c = st.columns(3)
        for col, (sec_name, sec_kws) in zip([col_a, col_b, col_c], DEFAULT_SECTION_MAP.items()):
            with col:
                color = SECTION_COLORS.get(sec_name, "#6b7280")
                st.markdown(
                    f"<b style='color:{color}'>{sec_name}</b>",
                    unsafe_allow_html=True,
                )
                kw_text = st.text_area(
                    f"Keywords ({sec_name})",
                    value=", ".join(kw_map.get(sec_name, sec_kws)),
                    key=f"kw_{sec_name}",
                    height=80,
                    label_visibility="collapsed",
                    help="Pisahkan dengan koma. Kata kunci bersifat case-insensitive.",
                )
                kw_map[sec_name] = [k.strip().lower() for k in kw_text.split(",") if k.strip()]

        if st.button("💾 Simpan Konfigurasi", key="save_kw_map"):
            st.session_state["section_keyword_map"] = kw_map
            st.success("Konfigurasi keyword disimpan!")
            st.rerun()

        st.session_state.setdefault("section_keyword_map", kw_map)

    section_map = st.session_state.get("section_keyword_map", DEFAULT_SECTION_MAP)

    # ── Klasifikasi data ──────────────────────────────────────────
    df = filtered_gmv.copy()
    df["_section"] = _classify_section(df, section_map)

    # Kolom revenue
    rev_col = "Total After Bill Discount"
    if rev_col not in df.columns:
        rev_col = "Total Nett Sales" if "Total Nett Sales" in df.columns else "Total"

    qty_col = "Qty" if "Qty" in df.columns else None

    # ── Overview ringkasan distribusi ─────────────────────────────
    section_totals = (
        df.groupby("_section")[rev_col]
        .sum()
        .reset_index()
        .rename(columns={rev_col: "Revenue"})
        .sort_values("Revenue", ascending=False)
    )
    total_rev = section_totals["Revenue"].sum()
    if total_rev > 0:
        section_totals["Pct"] = section_totals["Revenue"] / total_rev * 100

    st.markdown("### 📊 Distribusi Revenue per Section")
    c1, c2 = st.columns([2, 3])
    with c1:
        fig_pie = px.pie(
            section_totals,
            values="Revenue",
            names="_section",
            color="_section",
            color_discrete_map={k: v for k, v in SECTION_COLORS.items()},
            hole=0.5,
        )
        fig_pie.update_traces(textposition="outside", textinfo="label+percent")
        fig_pie.update_layout(
            showlegend=False,
            margin=dict(t=20, b=20, l=10, r=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e5e7eb"),
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with c2:
        fig_bar = px.bar(
            section_totals,
            x="Revenue",
            y="_section",
            orientation="h",
            color="_section",
            color_discrete_map={k: v for k, v in SECTION_COLORS.items()},
            text=section_totals["Revenue"].apply(format_rupiah),
        )
        fig_bar.update_traces(textposition="outside")
        fig_bar.update_layout(
            showlegend=False,
            margin=dict(t=10, b=10, l=10, r=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e5e7eb"),
            xaxis=dict(title="", showticklabels=False),
            yaxis=dict(title=""),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()

    # ── Banner info: ajak upload COGS kalau belum ada ────────────
    if filtered_cogs is None or filtered_cogs.empty:
        st.info(
            "💡 **Upload file COGS** untuk memperkaya analisis ini dengan data Total COGS, "
            "Gross Profit, dan Margin % per section & per menu. "
            "Tanpa COGS, semua data revenue & qty tetap tampil lengkap.",
            icon="📂",
        )

    # ── Tabs per section ──────────────────────────────────────────
    sections_present = [s for s in list(DEFAULT_SECTION_MAP.keys()) + ["🔘 Lainnya"]
                        if s in df["_section"].unique()]

    if not sections_present:
        st.warning("Tidak ada data yang berhasil diklasifikasi. Cek konfigurasi keyword.")
        return

    tabs = st.tabs(sections_present)

    for tab_ui, sec_name in zip(tabs, sections_present):
        with tab_ui:
            df_sec = df[df["_section"] == sec_name].copy()
            if df_sec.empty:
                st.info(f"Tidak ada data untuk section {sec_name}.")
                continue

            sec_color = SECTION_COLORS.get(sec_name, "#6b7280")
            _section_header(f"{sec_name} — Ringkasan Kinerja", sec_color)

            # ── KPI Row ──────────────────────────────────────────
            total_revenue_sec  = df_sec[rev_col].sum()
            total_qty_sec      = df_sec[qty_col].sum() if qty_col else 0
            n_menu             = df_sec["Menu"].nunique() if "Menu" in df_sec.columns else 0
            n_bills            = df_sec["Bill Number"].nunique() if "Bill Number" in df_sec.columns else 0
            avg_bill           = total_revenue_sec / n_bills if n_bills > 0 else 0
            pct_of_total       = (total_revenue_sec / total_rev * 100) if total_rev > 0 else 0

            # ── Hitung COGS section jika tersedia ────────────────
            cogs_sec_total    = 0.0
            gross_profit_sec  = 0.0
            margin_sec        = 0.0
            cogs_sec_df       = None
            if filtered_cogs is not None and not filtered_cogs.empty and "Menu" in df_sec.columns:
                try:
                    menus_in_sec_kpi = df_sec["Menu"].unique()
                    _cs = filtered_cogs[filtered_cogs["Menu"].isin(menus_in_sec_kpi)].copy()
                    if not _cs.empty and "COGS" in _cs.columns and "Qty" in _cs.columns:
                        _cs["_cogs_total"] = _cs["COGS"] * _cs["Qty"]
                        cogs_sec_total   = _cs["_cogs_total"].sum()
                        gross_profit_sec = total_revenue_sec - cogs_sec_total
                        if total_revenue_sec > 0:
                            margin_sec = gross_profit_sec / total_revenue_sec * 100
                        cogs_sec_df = _cs
                except Exception:
                    pass

            if cogs_sec_df is not None and cogs_sec_total > 0:
                k1, k2, k3, k4, k5, k6, k7 = st.columns(7)
                _kpi_card(k1, "Total Revenue",    format_rupiah(total_revenue_sec), color=sec_color)
                _kpi_card(k2, "Total COGS",       format_rupiah(cogs_sec_total),    color="#ef4444")
                _kpi_card(k3, "Gross Profit",     format_rupiah(gross_profit_sec),  color="#10b981")
                _kpi_card(k4, "Margin %",         f"{margin_sec:.1f}%",             color="#10b981" if margin_sec >= 50 else "#f59e0b")
                _kpi_card(k5, "% dari Total Rev", f"{pct_of_total:.1f}%",           color=sec_color)
                _kpi_card(k6, "Total Qty Terjual", format_angka_bulat(total_qty_sec), color=sec_color)
                _kpi_card(k7, "Jumlah Menu",      str(n_menu),                      color=sec_color)
            else:
                k1, k2, k3, k4, k5 = st.columns(5)
                _kpi_card(k1, "Total Revenue",    format_rupiah(total_revenue_sec), color=sec_color)
                _kpi_card(k2, "% dari Total",     f"{pct_of_total:.1f}%",           color=sec_color)
                _kpi_card(k3, "Total Qty Terjual", format_angka_bulat(total_qty_sec), color=sec_color)
                _kpi_card(k4, "Avg per Bill",     format_rupiah(avg_bill),           color=sec_color)
                _kpi_card(k5, "Jumlah Menu",      str(n_menu),                      color=sec_color)

            st.markdown("---")

            # ── Trend Harian ──────────────────────────────────────
            date_col = "Sales Date In" if "Sales Date In" in df_sec.columns else None
            if date_col:
                df_trend = (
                    df_sec.groupby(df_sec[date_col].dt.date)[rev_col]
                    .sum()
                    .reset_index()
                    .rename(columns={date_col: "Tanggal", rev_col: "Revenue"})
                )
                if not df_trend.empty and len(df_trend) > 1:
                    fig_trend = px.area(
                        df_trend,
                        x="Tanggal",
                        y="Revenue",
                        title=f"Trend Revenue Harian — {sec_name}",
                        color_discrete_sequence=[sec_color],
                    )
                    fig_trend.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#e5e7eb"),
                        margin=dict(t=40, b=20),
                        yaxis=dict(title="Revenue (Rp)"),
                        xaxis=dict(title=""),
                    )
                    st.plotly_chart(fig_trend, use_container_width=True)

            # ── Top Menu ──────────────────────────────────────────
            c_left, c_right = st.columns(2)

            if "Menu" in df_sec.columns:
                with c_left:
                    st.markdown("#### 🏆 Top 10 Menu by Revenue")
                    top_menu = (
                        df_sec.groupby("Menu")[rev_col]
                        .sum()
                        .reset_index()
                        .sort_values(rev_col, ascending=False)
                        .head(10)
                    )
                    fig_top = px.bar(
                        top_menu,
                        x=rev_col,
                        y="Menu",
                        orientation="h",
                        color_discrete_sequence=[sec_color],
                        text=top_menu[rev_col].apply(format_rupiah),
                    )
                    fig_top.update_traces(textposition="outside")
                    fig_top.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#e5e7eb"),
                        margin=dict(t=10, b=10, l=10, r=40),
                        yaxis=dict(title="", autorange="reversed"),
                        xaxis=dict(title="", showticklabels=False),
                        showlegend=False,
                        height=350,
                    )
                    st.plotly_chart(fig_top, use_container_width=True)

                with c_right:
                    if qty_col and qty_col in df_sec.columns:
                        st.markdown("#### 📦 Top 10 Menu by Qty")
                        top_qty = (
                            df_sec.groupby("Menu")[qty_col]
                            .sum()
                            .reset_index()
                            .sort_values(qty_col, ascending=False)
                            .head(10)
                        )
                        fig_qty = px.bar(
                            top_qty,
                            x=qty_col,
                            y="Menu",
                            orientation="h",
                            color_discrete_sequence=[sec_color],
                            text=top_qty[qty_col].apply(lambda v: f"{v:,.0f}"),
                        )
                        fig_qty.update_traces(textposition="outside")
                        fig_qty.update_layout(
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="#e5e7eb"),
                            margin=dict(t=10, b=10, l=10, r=40),
                            yaxis=dict(title="", autorange="reversed"),
                            xaxis=dict(title="", showticklabels=False),
                            showlegend=False,
                            height=350,
                        )
                        st.plotly_chart(fig_qty, use_container_width=True)

            # ── COGS & Margin per section (jika ada data cogs) ────
            if cogs_sec_df is not None and not cogs_sec_df.empty and "COGS" in cogs_sec_df.columns:
                try:
                    st.markdown("---")
                    _section_header(f"💰 Analisis COGS & Profitabilitas — {sec_name}", sec_color)

                    # Agregasi per menu
                    agg_dict = {"COGS": "mean", "Qty": "sum"}
                    if "Harga Jual" in cogs_sec_df.columns:
                        agg_dict["Harga Jual"] = "mean"

                    cogs_agg = (
                        cogs_sec_df.groupby("Menu")
                        .agg(agg_dict)
                        .reset_index()
                    )
                    cogs_agg["COGS Total"] = cogs_agg["COGS"] * cogs_agg["Qty"]

                    # Gabung dengan revenue per menu dari df_sec
                    rev_per_menu = (
                        df_sec.groupby("Menu")[rev_col]
                        .sum()
                        .reset_index()
                        .rename(columns={rev_col: "Revenue"})
                    )
                    cogs_merged = cogs_agg.merge(rev_per_menu, on="Menu", how="left")
                    cogs_merged["Revenue"] = cogs_merged["Revenue"].fillna(0)
                    cogs_merged["Gross Profit"] = cogs_merged["Revenue"] - cogs_merged["COGS Total"]
                    cogs_merged["Margin (%)"] = (
                        cogs_merged["Gross Profit"]
                        / cogs_merged["Revenue"].replace(0, float("nan")) * 100
                    ).fillna(0)

                    # ── Kolom: Revenue vs COGS vs Profit ─────────
                    cm_left, cm_right = st.columns(2)

                    with cm_left:
                        st.markdown("##### 📊 Revenue vs COGS vs Gross Profit per Menu")
                        top15 = cogs_merged.nlargest(15, "Revenue")
                        fig_rvcp = go.Figure()
                        fig_rvcp.add_trace(go.Bar(
                            name="Revenue",
                            y=top15["Menu"],
                            x=top15["Revenue"],
                            orientation="h",
                            marker_color=sec_color,
                            opacity=0.85,
                            text=top15["Revenue"].apply(format_rupiah),
                            textposition="inside",
                        ))
                        fig_rvcp.add_trace(go.Bar(
                            name="COGS",
                            y=top15["Menu"],
                            x=top15["COGS Total"],
                            orientation="h",
                            marker_color="#ef4444",
                            opacity=0.75,
                            text=top15["COGS Total"].apply(format_rupiah),
                            textposition="inside",
                        ))
                        fig_rvcp.add_trace(go.Bar(
                            name="Gross Profit",
                            y=top15["Menu"],
                            x=top15["Gross Profit"],
                            orientation="h",
                            marker_color="#10b981",
                            opacity=0.85,
                            text=top15["Gross Profit"].apply(format_rupiah),
                            textposition="inside",
                        ))
                        fig_rvcp.update_layout(
                            barmode="group",
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="#e5e7eb"),
                            margin=dict(t=10, b=10, l=10, r=20),
                            yaxis=dict(title="", autorange="reversed"),
                            xaxis=dict(title="", showticklabels=False),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                            height=420,
                        )
                        st.plotly_chart(fig_rvcp, use_container_width=True)

                    with cm_right:
                        st.markdown("##### 📈 Margin % per Menu")
                        top_margin = cogs_merged.nlargest(15, "Margin (%)")
                        fig_m = px.bar(
                            top_margin,
                            x="Margin (%)",
                            y="Menu",
                            orientation="h",
                            color="Margin (%)",
                            color_continuous_scale=["#ef4444", "#f59e0b", "#10b981"],
                            text=top_margin["Margin (%)"].apply(lambda v: f"{v:.1f}%"),
                        )
                        fig_m.update_traces(textposition="outside")
                        fig_m.update_layout(
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="#e5e7eb"),
                            margin=dict(t=10, b=10, l=10, r=60),
                            yaxis=dict(title="", autorange="reversed"),
                            xaxis=dict(title="Margin (%)", range=[0, 105]),
                            coloraxis_showscale=False,
                            height=420,
                        )
                        st.plotly_chart(fig_m, use_container_width=True)

                    # ── Tabel ringkasan COGS per menu ─────────────
                    with st.expander(f"📋 Tabel COGS Detail — {sec_name}", expanded=False):
                        tbl = cogs_merged[["Menu", "Qty", "COGS", "COGS Total", "Revenue", "Gross Profit", "Margin (%)"]].copy()
                        tbl = tbl.sort_values("Revenue", ascending=False).reset_index(drop=True)
                        tbl_disp = tbl.copy()
                        for col in ["COGS", "COGS Total", "Revenue", "Gross Profit"]:
                            tbl_disp[col] = tbl_disp[col].apply(format_rupiah)
                        tbl_disp["Margin (%)"] = tbl_disp["Margin (%)"].apply(lambda v: f"{v:.1f}%")
                        tbl_disp["Qty"] = tbl_disp["Qty"].apply(lambda v: f"{v:,.0f}")
                        st.dataframe(tbl_disp, use_container_width=True, hide_index=True)

                except Exception:
                    pass

            # ── Tabel detail ──────────────────────────────────────
            with st.expander(f"📋 Tabel Detail Lengkap — {sec_name}", expanded=False):
                disp_cols = ["Menu", "Menu Category", rev_col]
                if qty_col:
                    disp_cols.append(qty_col)
                if "Branch" in df_sec.columns:
                    disp_cols.append("Branch")
                disp_cols = [c for c in disp_cols if c in df_sec.columns]

                summary_tbl = (
                    df_sec.groupby([c for c in disp_cols if c in ["Menu", "Menu Category", "Branch"]])
                    [[c for c in [rev_col, qty_col] if c and c in df_sec.columns]]
                    .sum()
                    .reset_index()
                    .sort_values(rev_col, ascending=False)
                )
                if rev_col in summary_tbl.columns:
                    summary_tbl[rev_col] = summary_tbl[rev_col].apply(format_rupiah)
                st.dataframe(summary_tbl, use_container_width=True, hide_index=True)

    # ── Perbandingan Section Side-by-Side ─────────────────────────
    st.divider()
    st.markdown("### ⚖️ Perbandingan Antar Section")

    if "Menu" in df.columns and date_col:
        try:
            df_monthly = df.copy()
            df_monthly["Bulan"] = df_monthly[date_col].dt.to_period("M").astype(str)
            monthly_by_sec = (
                df_monthly.groupby(["Bulan", "_section"])[rev_col]
                .sum()
                .reset_index()
                .rename(columns={rev_col: "Revenue"})
            )
            fig_compare = px.bar(
                monthly_by_sec,
                x="Bulan",
                y="Revenue",
                color="_section",
                barmode="group",
                color_discrete_map={k: v for k, v in SECTION_COLORS.items()},
                title="Revenue Bulanan per Section",
            )
            fig_compare.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e5e7eb"),
                margin=dict(t=40, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_compare, use_container_width=True)
        except Exception:
            pass

    # ── Perbandingan COGS Antar Section ──────────────────────────
    if filtered_cogs is not None and not filtered_cogs.empty and "Menu" in df.columns:
        try:
            # Gabungkan section label dari df GMV ke COGS via Menu
            menu_section_map = df[["Menu", "_section"]].drop_duplicates(subset="Menu")
            cogs_with_sec = filtered_cogs.merge(menu_section_map, on="Menu", how="left")
            cogs_with_sec["_section"] = cogs_with_sec["_section"].fillna("🔘 Lainnya")

            if "COGS" in cogs_with_sec.columns and "Qty" in cogs_with_sec.columns:
                cogs_with_sec["_cogs_total"] = cogs_with_sec["COGS"] * cogs_with_sec["Qty"]

                # Ringkasan per section
                sec_summary = cogs_with_sec.groupby("_section").agg(
                    COGS_Total=("_cogs_total", "sum"),
                ).reset_index()

                # Gabung revenue per section
                sec_summary = sec_summary.merge(
                    section_totals[["_section", "Revenue"]],
                    on="_section", how="left"
                )
                sec_summary["Revenue"]    = sec_summary["Revenue"].fillna(0)
                sec_summary["Gross Profit"] = sec_summary["Revenue"] - sec_summary["COGS_Total"]
                sec_summary["Margin (%)"]   = (
                    sec_summary["Gross Profit"]
                    / sec_summary["Revenue"].replace(0, float("nan")) * 100
                ).fillna(0)
                sec_summary = sec_summary[sec_summary["Revenue"] > 0]

                if not sec_summary.empty:
                    st.divider()
                    st.markdown("### 💰 Perbandingan COGS & Profitabilitas Antar Section")

                    # ── KPI cards per section ─────────────────────
                    n_cols = len(sec_summary)
                    kpi_cols = st.columns(n_cols)
                    for i, row in sec_summary.iterrows():
                        sn   = row["_section"]
                        sc   = SECTION_COLORS.get(sn, "#6b7280")
                        mg   = row["Margin (%)"]
                        mg_c = "#10b981" if mg >= 60 else ("#f59e0b" if mg >= 40 else "#ef4444")
                        with kpi_cols[i % n_cols]:
                            st.markdown(
                                f"""<div style="background:linear-gradient(135deg,{sc}18,{sc}08);
                                    border:1px solid {sc}40;border-radius:12px;padding:14px 16px;
                                    text-align:center;margin-bottom:8px">
                                    <div style="font-size:13px;font-weight:700;color:{sc};margin-bottom:8px">{sn}</div>
                                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px">
                                      <div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:8px">
                                        <div style="font-size:9px;color:#9ca3af;text-transform:uppercase;letter-spacing:.08em">Revenue</div>
                                        <div style="font-size:13px;font-weight:800;color:#f0f2f5">{format_rupiah(row["Revenue"])}</div>
                                      </div>
                                      <div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:8px">
                                        <div style="font-size:9px;color:#9ca3af;text-transform:uppercase;letter-spacing:.08em">COGS</div>
                                        <div style="font-size:13px;font-weight:800;color:#ef4444">{format_rupiah(row["COGS_Total"])}</div>
                                      </div>
                                      <div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:8px">
                                        <div style="font-size:9px;color:#9ca3af;text-transform:uppercase;letter-spacing:.08em">Gross Profit</div>
                                        <div style="font-size:13px;font-weight:800;color:#10b981">{format_rupiah(row["Gross Profit"])}</div>
                                      </div>
                                      <div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:8px">
                                        <div style="font-size:9px;color:#9ca3af;text-transform:uppercase;letter-spacing:.08em">Margin %</div>
                                        <div style="font-size:14px;font-weight:900;color:{mg_c}">{mg:.1f}%</div>
                                      </div>
                                    </div>
                                </div>""",
                                unsafe_allow_html=True,
                            )

                    # ── Grouped bar: Revenue vs COGS vs Gross Profit ──
                    fig_cmp = go.Figure()
                    fig_cmp.add_trace(go.Bar(
                        name="Revenue",
                        x=sec_summary["_section"],
                        y=sec_summary["Revenue"],
                        marker_color=[SECTION_COLORS.get(s, "#6b7280") for s in sec_summary["_section"]],
                        opacity=0.85,
                        text=sec_summary["Revenue"].apply(format_rupiah),
                        textposition="outside",
                    ))
                    fig_cmp.add_trace(go.Bar(
                        name="Total COGS",
                        x=sec_summary["_section"],
                        y=sec_summary["COGS_Total"],
                        marker_color="#ef4444",
                        opacity=0.75,
                        text=sec_summary["COGS_Total"].apply(format_rupiah),
                        textposition="outside",
                    ))
                    fig_cmp.add_trace(go.Bar(
                        name="Gross Profit",
                        x=sec_summary["_section"],
                        y=sec_summary["Gross Profit"],
                        marker_color="#10b981",
                        opacity=0.85,
                        text=sec_summary["Gross Profit"].apply(format_rupiah),
                        textposition="outside",
                    ))
                    fig_cmp.update_layout(
                        barmode="group",
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#e5e7eb"),
                        margin=dict(t=40, b=20),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        xaxis=dict(title=""),
                        yaxis=dict(title="Rp", showticklabels=False),
                        title="Revenue vs COGS vs Gross Profit per Section",
                    )
                    st.plotly_chart(fig_cmp, use_container_width=True)

                    # ── Margin % bar antar section ─────────────────
                    col_mg1, col_mg2 = st.columns(2)
                    with col_mg1:
                        fig_mg = px.bar(
                            sec_summary.sort_values("Margin (%)", ascending=False),
                            x="_section",
                            y="Margin (%)",
                            color="Margin (%)",
                            color_continuous_scale=["#ef4444", "#f59e0b", "#10b981"],
                            text=sec_summary.sort_values("Margin (%)", ascending=False)["Margin (%)"].apply(lambda v: f"{v:.1f}%"),
                            title="Margin % per Section",
                        )
                        fig_mg.update_traces(textposition="outside")
                        fig_mg.update_layout(
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="#e5e7eb"),
                            margin=dict(t=40, b=10),
                            xaxis=dict(title=""),
                            yaxis=dict(title="", range=[0, sec_summary["Margin (%)"].max() * 1.25]),
                            coloraxis_showscale=False,
                        )
                        st.plotly_chart(fig_mg, use_container_width=True)

                    with col_mg2:
                        # Donut: proporsi COGS antar section
                        fig_cogs_pie = px.pie(
                            sec_summary,
                            values="COGS_Total",
                            names="_section",
                            color="_section",
                            color_discrete_map={k: v for k, v in SECTION_COLORS.items()},
                            hole=0.5,
                            title="Distribusi Total COGS per Section",
                        )
                        fig_cogs_pie.update_traces(textposition="outside", textinfo="label+percent")
                        fig_cogs_pie.update_layout(
                            showlegend=False,
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="#e5e7eb"),
                            margin=dict(t=40, b=20, l=10, r=10),
                        )
                        st.plotly_chart(fig_cogs_pie, use_container_width=True)

                    # ── Tabel ringkasan ────────────────────────────
                    with st.expander("📋 Tabel Ringkasan COGS & Profit per Section", expanded=True):
                        tbl_sec = sec_summary.copy()
                        tbl_sec.rename(columns={"_section": "Section", "COGS_Total": "Total COGS"}, inplace=True)
                        for col in ["Revenue", "Total COGS", "Gross Profit"]:
                            tbl_sec[col] = tbl_sec[col].apply(format_rupiah)
                        tbl_sec["Margin (%)"] = tbl_sec["Margin (%)"].apply(lambda v: f"{v:.1f}%")
                        st.dataframe(tbl_sec[["Section", "Revenue", "Total COGS", "Gross Profit", "Margin (%)"]], use_container_width=True, hide_index=True)

        except Exception:
            pass

    # ── Peak Hour per Section ─────────────────────────────────────
    if "Order Time" in df.columns or date_col:
        try:
            ot_col = "Order Time" if "Order Time" in df.columns else date_col
            df_hour = df.copy()
            df_hour["Jam"] = pd.to_datetime(df_hour[ot_col], errors="coerce").dt.hour
            hour_by_sec = (
                df_hour.groupby(["Jam", "_section"])[rev_col]
                .sum()
                .reset_index()
                .rename(columns={rev_col: "Revenue"})
            )
            if not hour_by_sec.empty:
                st.markdown("### ⏰ Peak Hour per Section")
                fig_hour = px.line(
                    hour_by_sec,
                    x="Jam",
                    y="Revenue",
                    color="_section",
                    color_discrete_map={k: v for k, v in SECTION_COLORS.items()},
                    markers=True,
                    title="Revenue per Jam Operasional",
                )
                fig_hour.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#e5e7eb"),
                    margin=dict(t=40, b=20),
                    xaxis=dict(title="Jam", dtick=1),
                    yaxis=dict(title="Revenue (Rp)"),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                )
                st.plotly_chart(fig_hour, use_container_width=True)
        except Exception:
            pass
