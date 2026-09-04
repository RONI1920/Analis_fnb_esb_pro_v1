# ui/tabs/tab9_rekomendasi.py — Tab 9: Rekomendasi Multi-Source (Enhanced)

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pandas as pd

from analytics.market_basket import get_market_basket_rules
from analytics.rekomendasi import (
    get_multi_source_recommendations,
    get_seasonal_menu_performance,
    get_upsell_opportunities,
)
from insights.generators import generate_recommendation_insights
from formatters import format_rupiah

REKOMEN_COLORS = {
    "🚀 Promosikan":      "#2ecc71",
    "✅ Pertahankan":     "#3498db",
    "💰 Repricing":       "#f39c12",
    "⚠️ Perlu Perhatian": "#e67e22",
    "🗑️ Evaluasi":        "#e74c3c",
}


def build_tab9_rekomendasi(filtered_gmv, data_cogs=None, data_kalender=None, data_ulasan=None):
    st.header("💡 Rekomendasi Menu — Multi-Source Analysis")

    if filtered_gmv is None or filtered_gmv.empty:
        st.warning("Silakan upload file Laporan GMV (File 1) di sidebar.")
        return

    if filtered_gmv["Bill Number"].nunique() < 50:
        st.warning(f"Transaksi terlalu sedikit ({filtered_gmv['Bill Number'].nunique()}). Minimal 50.")
        return

    # Info sumber data yang aktif
    sources = ["✅ GMV"]
    if data_cogs is not None:     sources.append("✅ COGS & Margin")
    else:                          sources.append("⚠️ COGS (tidak tersedia — margin default 50%)")
    if data_kalender is not None: sources.append("✅ Kalender Musiman")
    else:                          sources.append("⚠️ Kalender (tidak tersedia)")
    if data_ulasan is not None:   sources.append("✅ Ulasan Pelanggan")
    else:                          sources.append("⚠️ Ulasan (tidak tersedia)")

    with st.expander("📡 Sumber Data yang Digunakan", expanded=False):
        for s in sources:
            st.write(s)

    st.markdown("---")

    # ════════════════════════════════════════════════════════
    # SECTION 1: SKOR MULTI-SOURCE
    # ════════════════════════════════════════════════════════
    st.header("🎯 Skor Rekomendasi Multi-Source")
    st.caption("Skor gabungan dari: Popularitas (35%) + Margin (30%) + Tren MoM (20%) + Sentimen Ulasan (15%)")

    with st.spinner("Menghitung skor rekomendasi..."):
        df_rec = get_multi_source_recommendations(
            filtered_gmv, data_cogs, data_kalender, data_ulasan, top_n=30
        )

    if df_rec.empty:
        st.warning("Tidak ada data rekomendasi.")
    else:
        # KPI ringkasan
        k1, k2, k3, k4, k5 = st.columns(5)
        for col, label, emoji in zip(
            [k1, k2, k3, k4, k5],
            ["🚀 Promosikan", "✅ Pertahankan", "💰 Repricing", "⚠️ Perlu Perhatian", "🗑️ Evaluasi"],
            ["🚀", "✅", "💰", "⚠️", "🗑️"],
        ):
            count = (df_rec["Rekomendasi"] == label).sum()
            col.metric(label, f"{count} menu")

        st.markdown("---")

        # Scatter plot skor
        st.subheader("📊 Peta Posisi Menu")

        has_margin = df_rec["Margin_Pct"].notna().any()
        x_col = "Norm_Margin" if has_margin else "Norm_Popularitas"
        x_label = "Margin Score (0-100)" if has_margin else "Popularitas Score"

        fig_scatter = px.scatter(
            df_rec,
            x=x_col, y="Norm_Popularitas",
            color="Rekomendasi",
            color_discrete_map=REKOMEN_COLORS,
            size="Skor_Gabungan",
            size_max=35,
            hover_name="Menu",
            hover_data={
                "Skor_Gabungan": ":.1f",
                "Margin_Pct": ":.1f",
                "Growth_MoM": ":.1f",
                "Total_Revenue": ":,.0f",
                x_col: False,
                "Norm_Popularitas": False,
            },
            labels={
                x_col: x_label,
                "Norm_Popularitas": "Popularitas Score (0-100)",
            },
            height=500,
            title="Peta Menu: Margin vs Popularitas (ukuran bubble = skor gabungan)",
        )
        fig_scatter.add_vline(x=50, line_dash="dash", line_color="gray", opacity=0.4)
        fig_scatter.add_hline(y=50, line_dash="dash", line_color="gray", opacity=0.4)
        fig_scatter.add_annotation(x=85, y=85, text="⭐ Ideal",      showarrow=False, font=dict(color="#2ecc71", size=13))
        fig_scatter.add_annotation(x=85, y=15, text="💰 Repricing", showarrow=False, font=dict(color="#f39c12", size=13))
        fig_scatter.add_annotation(x=15, y=85, text="📣 Promosi",   showarrow=False, font=dict(color="#3498db", size=13))
        fig_scatter.add_annotation(x=15, y=15, text="🗑️ Evaluasi",  showarrow=False, font=dict(color="#e74c3c", size=13))
        st.plotly_chart(fig_scatter, use_container_width=True)

        st.markdown("---")

        # Bar chart top menu by skor
        st.subheader("🏆 Top 20 Menu by Skor Gabungan")
        fig_bar = px.bar(
            df_rec.head(20),
            x="Skor_Gabungan", y="Menu",
            color="Rekomendasi",
            color_discrete_map=REKOMEN_COLORS,
            orientation="h",
            height=550,
            labels={"Skor_Gabungan": "Skor Gabungan (0-100)", "Menu": ""},
            text=df_rec.head(20)["Skor_Gabungan"].apply(lambda x: f"{x:.1f}"),
        )
        fig_bar.update_traces(textposition="outside")
        fig_bar.update_layout(yaxis=dict(autorange="reversed"), legend_title="Aksi")
        st.plotly_chart(fig_bar, use_container_width=True)

        # Tabel detail per rekomendasi
        st.subheader("📋 Detail per Aksi Rekomendasi")
        tab_promo, tab_pert, tab_repr, tab_warn, tab_eval = st.tabs([
            "🚀 Promosikan", "✅ Pertahankan", "💰 Repricing", "⚠️ Perlu Perhatian", "🗑️ Evaluasi"
        ])

        def render_rec_table(tab, label):
            with tab:
                df_k = df_rec[df_rec["Rekomendasi"] == label].copy()
                if df_k.empty:
                    st.info("Tidak ada menu dalam kategori ini.")
                    return
                cols_show = ["Menu", "Skor_Gabungan", "Total_Revenue",
                             "Margin_Pct", "Growth_MoM", "Norm_Sentimen"]
                if "Kategori" in df_k.columns:
                    cols_show = ["Menu", "Kategori"] + cols_show[1:]
                df_k = df_k[[c for c in cols_show if c in df_k.columns]].copy()
                df_k["Total_Revenue"] = df_k["Total_Revenue"].apply(format_rupiah)
                df_k["Margin_Pct"]   = df_k["Margin_Pct"].apply(lambda x: f"{x:.1f}%")
                df_k["Growth_MoM"]   = df_k["Growth_MoM"].apply(lambda x: f"{x:+.1f}%")
                df_k["Skor_Gabungan"]= df_k["Skor_Gabungan"].apply(lambda x: f"{x:.1f}")
                if "Norm_Sentimen" in df_k.columns:
                    df_k["Norm_Sentimen"] = df_k["Norm_Sentimen"].apply(lambda x: f"{x:.0f}/100")
                st.dataframe(df_k, use_container_width=True, hide_index=True)

        render_rec_table(tab_promo, "🚀 Promosikan")
        render_rec_table(tab_pert,  "✅ Pertahankan")
        render_rec_table(tab_repr,  "💰 Repricing")
        render_rec_table(tab_warn,  "⚠️ Perlu Perhatian")
        render_rec_table(tab_eval,  "🗑️ Evaluasi")

    st.markdown("---")

    # ════════════════════════════════════════════════════════
    # SECTION 2: MARKET BASKET (existing, dipertahankan)
    # ════════════════════════════════════════════════════════
    st.header("🛒 Market Basket Analysis")
    st.caption("Menu yang sering dibeli bersamaan — untuk rekomendasi upsell ke pelanggan.")

    with st.spinner("Menganalisis pola pembelian..."):
        # Pre-filter: hanya menu yang muncul di >= 1% bill untuk hindari OOM
        _df_mb = filtered_gmv.copy()
        if "Price (Net)" in _df_mb.columns:
            _df_mb["Price (Net)"] = pd.to_numeric(_df_mb["Price (Net)"], errors="coerce").fillna(0)
            _df_mb = _df_mb[_df_mb["Price (Net)"] > 0]
        _df_mb = _df_mb[~_df_mb["Menu"].str.contains(
            r"PACKAGE|Refill|Ocha|ADD|Level|Mineral", na=False, case=False, regex=True
        )]
        _n_bills = _df_mb["Bill Number"].nunique()
        _min_bills = max(int(_n_bills * 0.005), 5)
        _top_menus = (
            _df_mb.groupby("Menu")["Bill Number"].nunique()
        )
        _top_menus = _top_menus[_top_menus >= _min_bills].index.tolist()
        _df_mb = _df_mb[_df_mb["Menu"].isin(_top_menus)]
        st.caption(f"Market basket menggunakan {len(_top_menus)} menu teratas dari {_n_bills:,} bill.")
        rules_df = get_market_basket_rules(_df_mb, 0.005)

    if not rules_df.empty:
        all_antecedents = sorted(rules_df["antecedents"].unique())
        filter_ant = st.multiselect(
            "JIKA Pelanggan Beli Menu Ini:",
            options=all_antecedents,
            placeholder="Kosong = tampilkan semua",
        )
        filtered_rules = (
            rules_df[rules_df["antecedents"].isin(filter_ant)] if filter_ant else rules_df
        ).sort_values("expected_value", ascending=False)

        st.markdown(f"**{len(filtered_rules)} aturan ditemukan**")

        col_ex1, col_ex2 = st.columns(2)
        col_ex1.success("**Confidence** — % pelanggan beli A juga beli B")
        col_ex2.info("**Expected Value** = Confidence × Harga B — nilai potensi per transaksi")

        st.dataframe(
            filtered_rules.rename(columns={
                "antecedents": "Jika Beli (A)",
                "consequents": "Tawarkan (B)",
                "confidence": "Confidence",
                "lift": "Lift",
                "consequent_price": "Harga (B)",
                "expected_value": "Expected Value",
            })[["Jika Beli (A)", "Tawarkan (B)", "Expected Value", "Confidence", "Harga (B)", "Lift"]]
            .style.format({
                "Confidence": "{:.2%}",
                "Lift": "{:.2f}x",
                "Harga (B)": format_rupiah,
                "Expected Value": format_rupiah,
            }),
            use_container_width=True,
        )
    else:
        st.warning("Tidak ada aturan market basket ditemukan.")

    st.markdown("---")

    # ════════════════════════════════════════════════════════
    # SECTION 3: PELUANG UPSELL
    # ════════════════════════════════════════════════════════
    st.header("💎 Peluang Upsell — Menu Margin Tinggi")
    st.caption("Menu dengan margin ≥ 60% yang masih bisa ditingkatkan penjualannya.")

    upsell = get_upsell_opportunities(filtered_gmv, data_cogs)
    if not upsell.empty:
        fig_upsell = px.scatter(
            upsell, x="Total_Qty", y="Margin",
            size="Total_Rev", size_max=40,
            color="Margin",
            color_continuous_scale="Greens",
            hover_name="Menu",
            labels={"Total_Qty": "Total Qty Terjual", "Margin": "Margin (%)"},
            height=400,
            title="Menu Margin Tinggi — Peluang Upsell",
        )
        fig_upsell.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig_upsell, use_container_width=True)

        tbl_up = upsell.copy()
        tbl_up["Total_Rev"] = tbl_up["Total_Rev"].apply(format_rupiah)
        tbl_up["Margin"]    = tbl_up["Margin"].apply(lambda x: f"{x:.1f}%")
        st.dataframe(tbl_up.rename(columns={
            "Total_Rev": "Total Revenue", "Total_Qty": "Qty Terjual", "Margin": "Margin %"
        }), use_container_width=True, hide_index=True)
    else:
        st.info("Data COGS diperlukan untuk analisis upsell margin.")

    st.markdown("---")

    # ════════════════════════════════════════════════════════
    # SECTION 4: PERFORMA MENU PER MUSIM
    # ════════════════════════════════════════════════════════
    if data_kalender is not None:
        st.header("🗓️ Performa Menu per Musim")
        st.caption("Menu yang penjualannya melonjak saat event tertentu.")

        seasonal = get_seasonal_menu_performance(filtered_gmv, data_kalender)
        if not seasonal.empty:
            # Top menu per tipe event
            top_seasonal = seasonal.nlargest(20, "Lift_vs_Normal")
            fig_sea = px.bar(
                top_seasonal, x="Lift_vs_Normal", y="Menu",
                color="Tipe_Event", orientation="h",
                height=500,
                labels={"Lift_vs_Normal": "Lift vs Hari Biasa", "Menu": ""},
                title="Menu dengan Lift Tertinggi saat Event",
            )
            fig_sea.update_layout(yaxis=dict(autorange="reversed"))
            fig_sea.add_vline(x=1, line_dash="dash", line_color="gray",
                              annotation_text="Baseline", annotation_position="top right")
            st.plotly_chart(fig_sea, use_container_width=True)

    st.markdown("---")

    # ════════════════════════════════════════════════════════
    # INSIGHT OTOMATIS
    # ════════════════════════════════════════════════════════
    st.header("💡 Insight & Rekomendasi Aksi")

    if not df_rec.empty:
        promo_menus = df_rec[df_rec["Rekomendasi"] == "🚀 Promosikan"]["Menu"].tolist()
        eval_menus  = df_rec[df_rec["Rekomendasi"] == "🗑️ Evaluasi"]["Menu"].tolist()
        repr_menus  = df_rec[df_rec["Rekomendasi"] == "💰 Repricing"]["Menu"].tolist()

        ic1, ic2, ic3 = st.columns(3)
        with ic1:
            st.subheader("🚀 Promosikan Segera")
            if promo_menus:
                st.success(f"{len(promo_menus)} menu layak dipromosikan:")
                for m in promo_menus[:5]:
                    st.write(f"• {m}")
                if len(promo_menus) > 5:
                    st.caption(f"+ {len(promo_menus)-5} menu lainnya")
            else:
                st.info("Tidak ada menu promosi teridentifikasi.")

        with ic2:
            st.subheader("💰 Repricing")
            if repr_menus:
                st.warning(f"{len(repr_menus)} menu populer tapi margin rendah:")
                for m in repr_menus[:5]:
                    st.write(f"• {m}")
            else:
                st.info("Tidak ada menu yang perlu repricing.")

        with ic3:
            st.subheader("🗑️ Pertimbangkan Hapus")
            if eval_menus:
                st.error(f"{len(eval_menus)} menu perlu dievaluasi:")
                for m in eval_menus[:5]:
                    st.write(f"• {m}")
            else:
                st.success("Tidak ada menu yang perlu dihapus.")

    if not rules_df.empty:
        insights = generate_recommendation_insights(rules_df)
        with st.expander("📄 Temuan dari Market Basket", expanded=False):
            for ins in insights:
                st.markdown(f"&bull; {ins}")