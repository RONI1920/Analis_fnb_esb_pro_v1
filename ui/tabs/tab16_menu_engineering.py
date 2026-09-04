# ui/tabs/tab16_menu_engineering.py — Tab 16: Menu Engineering

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pandas as pd

from analytics.menu_engineering import analyze_menu_engineering, get_menu_engineering_summary
from formatters import format_rupiah

COLOR_MAP = {
    "⭐ Stars":      "#f1c40f",
    "🐄 Plowhorses": "#3498db",
    "❓ Puzzles":    "#9b59b6",
    "🐶 Dogs":       "#e74c3c",
}


def build_tab16_menu_engineering(df_cogs: pd.DataFrame):
    try:
        st.header("🍽️ Menu Engineering")
        st.info(
            "Analisis popularitas vs profitabilitas setiap menu menggunakan matriks "
            "Stars / Plowhorses / Puzzles / Dogs."
        )

        if df_cogs is None or df_cogs.empty:
            st.warning("Data COGS belum tersedia. Upload file COGS terlebih dahulu.")
            return

        df_result = analyze_menu_engineering(df_cogs)
        if df_result is None or df_result.empty:
            st.warning("Tidak ada data hasil analisis menu engineering.")
            return

        summary = get_menu_engineering_summary(df_result)
        avg_qty    = df_result["Total_Qty"].mean()
        avg_margin = df_result["Margin_Pct"].mean()

        # ── Metrik Ringkasan ───────────────────────────────────
        st.subheader("📊 Ringkasan Klasifikasi")
        cols = st.columns(4)
        klasifikasi_order = ["⭐ Stars", "🐄 Plowhorses", "❓ Puzzles", "🐶 Dogs"]
        for i, klas in enumerate(klasifikasi_order):
            row = summary[summary["Klasifikasi"] == klas] if not summary.empty else pd.DataFrame()
            jumlah  = int(row["Jumlah_Menu"].values[0])  if not row.empty else 0
            revenue = row["Total_Revenue"].values[0]      if not row.empty else 0
            margin  = row["Avg_Margin_Pct"].values[0]     if not row.empty else 0
            with cols[i]:
                st.metric(klas, f"{jumlah} menu")
                st.caption(f"Omzet: {format_rupiah(revenue)}")
                st.caption(f"Avg Margin: {margin:.1f}%")

        st.markdown("---")

        # ── Scatter Matrix ─────────────────────────────────────
        st.subheader("📈 Matriks Popularitas vs Profitabilitas")

        fig = px.scatter(
            df_result,
            x="Total_Qty",
            y="Margin_Pct",
            color="Klasifikasi",
            color_discrete_map=COLOR_MAP,
            hover_name="Menu",
            hover_data={
                "Menu Category": True,
                "Avg_Price": ":,.0f",
                "Total_Revenue": ":,.0f",
                "Rekomendasi": True,
                "Total_Qty": True,
                "Margin_Pct": ":.1f",
            },
            size="Total_Revenue",
            size_max=40,
            labels={
                "Total_Qty": "Total Terjual (Popularitas)",
                "Margin_Pct": "Margin (%)",
            },
            height=600,
        )

        # Garis threshold
        fig.add_vline(x=avg_qty,    line_dash="dash", line_color="gray", opacity=0.5,
                      annotation_text=f"Avg Qty: {avg_qty:.0f}", annotation_position="top right")
        fig.add_hline(y=avg_margin, line_dash="dash", line_color="gray", opacity=0.5,
                      annotation_text=f"Avg Margin: {avg_margin:.1f}%", annotation_position="top right")

        # Label kuadran
        x_max = df_result["Total_Qty"].max() * 1.05
        fig.add_annotation(x=x_max * 0.75, y=df_result["Margin_Pct"].max() * 0.95,
                           text="⭐ STARS", showarrow=False, font=dict(size=14, color="#f1c40f"))
        fig.add_annotation(x=x_max * 0.75, y=df_result["Margin_Pct"].min() * 0.5,
                           text="🐄 PLOWHORSES", showarrow=False, font=dict(size=14, color="#3498db"))
        fig.add_annotation(x=avg_qty * 0.1, y=df_result["Margin_Pct"].max() * 0.95,
                           text="❓ PUZZLES", showarrow=False, font=dict(size=14, color="#9b59b6"))
        fig.add_annotation(x=avg_qty * 0.1, y=df_result["Margin_Pct"].min() * 0.5,
                           text="🐶 DOGS", showarrow=False, font=dict(size=14, color="#e74c3c"))

        fig.update_layout(showlegend=True, legend_title="Klasifikasi")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # ── Filter per Klasifikasi ─────────────────────────────
        st.subheader("📋 Detail Menu per Klasifikasi")

        tab_stars, tab_plow, tab_puzz, tab_dogs = st.tabs(
            ["⭐ Stars", "🐄 Plowhorses", "❓ Puzzles", "🐶 Dogs"]
        )

        def render_table(tab, klas):
            with tab:
                df_k = df_result[df_result["Klasifikasi"] == klas].copy()
                if df_k.empty:
                    st.info(f"Tidak ada menu dalam kategori {klas}.")
                    return
                df_k["Avg_Price"]     = df_k["Avg_Price"].apply(lambda x: f"Rp {int(x):,}".replace(",","."))
                df_k["Total_Revenue"] = df_k["Total_Revenue"].apply(format_rupiah)
                df_k["Total_Margin"]  = df_k["Total_Margin"].apply(format_rupiah)
                df_k["Margin_Pct"]    = df_k["Margin_Pct"].apply(lambda x: f"{x:.1f}%")
                cols_show = ["Menu", "Menu Category", "Total_Qty", "Avg_Price",
                             "Margin_Pct", "Total_Revenue", "Total_Margin", "Rekomendasi"]
                st.dataframe(df_k[cols_show], use_container_width=True, hide_index=True)

        render_table(tab_stars, "⭐ Stars")
        render_table(tab_plow,  "🐄 Plowhorses")
        render_table(tab_puzz,  "❓ Puzzles")
        render_table(tab_dogs,  "🐶 Dogs")

        st.markdown("---")

        # ── Bar Chart Revenue per Kategori ─────────────────────
        st.subheader("💰 Total Omzet per Klasifikasi")
        if not summary.empty:
            summary_display = summary.copy()
            summary_display["Label"] = summary_display["Total_Revenue"].apply(
                lambda v: "Rp " + f"{int(v):,}".replace(",", ".")
            )
            fig_bar = px.bar(
                summary_display, x="Klasifikasi", y="Total_Revenue",
                color="Klasifikasi", color_discrete_map=COLOR_MAP, text="Label",
                labels={"Total_Revenue": "Total Omzet"},
                height=400,
            )
            fig_bar.update_traces(textposition="outside")
            fig_bar.update_layout(showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("---")

        # ── Top 10 per Klasifikasi ─────────────────────────────
        st.subheader("🏆 Top 10 Menu per Klasifikasi")
        selected_klas = st.selectbox(
            "Pilih Klasifikasi:",
            ["⭐ Stars", "🐄 Plowhorses", "❓ Puzzles", "🐶 Dogs"],
        )
        df_top = (
            df_result[df_result["Klasifikasi"] == selected_klas]
            .nlargest(10, "Total_Revenue")
            .copy()
        )
        if not df_top.empty:
            fig_top = px.bar(
                df_top, x="Total_Revenue", y="Menu",
                orientation="h", color="Margin_Pct",
                color_continuous_scale="RdYlGn",
                labels={"Total_Revenue": "Total Omzet", "Margin_Pct": "Margin (%)"},
                height=450,
            )
            fig_top.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig_top, use_container_width=True)

        st.markdown("---")

        # ── Insight Otomatis ───────────────────────────────────
        st.header("💡 Insight & Rekomendasi")

        total_menu = len(df_result)
        stars_pct  = len(df_result[df_result["Klasifikasi"] == "⭐ Stars"]) / total_menu * 100 if total_menu > 0 else 0
        dogs_pct   = len(df_result[df_result["Klasifikasi"] == "🐶 Dogs"])  / total_menu * 100 if total_menu > 0 else 0

        ic1, ic2, ic3 = st.columns(3)
        with ic1:
            st.subheader("⭐ Stars")
            top_stars = df_result[df_result["Klasifikasi"] == "⭐ Stars"].nlargest(3, "Total_Revenue")["Menu"].tolist()
            if top_stars:
                st.success(f"**{stars_pct:.0f}%** menu masuk kategori Stars.")
                st.write("Top 3 Stars:")
                for m in top_stars:
                    st.write(f"• {m}")
            else:
                st.info("Belum ada menu Stars.")

        with ic2:
            st.subheader("🐄 Plowhorses")
            top_plow = df_result[df_result["Klasifikasi"] == "🐄 Plowhorses"].nlargest(3, "Total_Qty")["Menu"].tolist()
            if top_plow:
                st.warning("Menu ini populer tapi margin rendah — pertimbangkan **repricing** atau kurangi porsi COGS:")
                for m in top_plow:
                    st.write(f"• {m}")
            else:
                st.info("Tidak ada menu Plowhorses.")

        with ic3:
            st.subheader("🐶 Dogs")
            top_dogs = df_result[df_result["Klasifikasi"] == "🐶 Dogs"].nlargest(3, "Total_Qty")["Menu"].tolist()
            if top_dogs:
                st.error(f"**{dogs_pct:.0f}%** menu termasuk Dogs. Pertimbangkan evaluasi:")
                for m in top_dogs:
                    st.write(f"• {m}")
            else:
                st.info("Tidak ada menu Dogs.")

        with st.expander("📄 Lihat Semua Data"):
            st.dataframe(df_result, use_container_width=True, hide_index=True)
    except Exception as _e:
        import streamlit as _st
        _st.error(f"⚠️ Terjadi kesalahan pada modul ini: {_e}")