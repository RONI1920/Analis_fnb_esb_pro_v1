# ui/tabs/tab11_musiman.py — Tab 11: Analisis Weekend vs Tanggal Merah

import plotly.express as px
import streamlit as st

from analytics.musiman import analyze_tab11_weekend_effect  # ← dipindah dari hr.py
from formatters import format_rupiah


def build_tab11_musiman(df_gmv, df_kalender):
    try:
        st.header("⚔️ Analisis Weekend vs Tanggal Merah")
        st.info("Perbandingan omzet antara weekday, weekend, dan hari libur nasional.")

        df_summary, df_raw = analyze_tab11_weekend_effect(df_gmv, df_kalender)

        if df_summary is None or df_summary.empty:
            st.warning("Tidak ada data hasil analisis. Pastikan file GMV dan Kalender tersedia.")
            return

        col_rev = "Total After Bill Discount"

        # ── Metrik ─────────────────────────────────────────────
        st.subheader("📊 Ringkasan")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Hari", int(df_summary["Jumlah_Hari"].sum()))
        c2.metric("Total Omzet", format_rupiah(df_summary["Total_Omzet"].sum()))
        c3.metric("Rata-rata Harian", format_rupiah(df_summary["Rata_Rata_Omzet"].mean()))

        st.markdown("---")

        # ── Bar Chart ──────────────────────────────────────────
        st.subheader("📈 Total Omzet per Jenis Hari")
        df_summary["Label"] = df_summary["Total_Omzet"].apply(
            lambda v: "Rp " + f"{int(v):,}".replace(",", ".")
        )
        fig = px.bar(
            df_summary, x="Kategori_Hari", y="Total_Omzet",
            color="Kategori_Hari", text="Label",
            hover_data=["Rata_Rata_Omzet", "Jumlah_Hari"],
            color_discrete_map={
                "1. Weekday Biasa":   "#bdc3c7",
                "2. Weekend Biasa":   "#3498db",
                "3. Weekday Libur":   "#e67e22",
                "4. Weekend & Libur": "#e74c3c",
            },
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(showlegend=False, height=500, yaxis_title="Total Omzet")
        st.plotly_chart(fig, use_container_width=True)

        # ── Tabel ─────────────────────────────────────────────
        st.markdown("---")
        st.subheader("📋 Summary Table")
        tbl = df_summary.copy()
        tbl["Rata_Rata_Omzet"] = tbl["Rata_Rata_Omzet"].apply(format_rupiah)
        tbl["Total_Omzet"] = tbl["Total_Omzet"].apply(format_rupiah)
        st.dataframe(tbl, use_container_width=True, hide_index=True)

        # ── Box Plot ──────────────────────────────────────────
        if df_raw is not None and col_rev in df_raw.columns:
            st.markdown("---")
            st.subheader("📦 Distribusi Omzet Harian")
            fig_box = px.box(
                df_raw, x="Kategori_Hari", y=col_rev,
                color="Kategori_Hari", points="suspectedoutliers",
                hover_data=["Nama_Event", "Tipe_Event"],  # ← manfaatkan kolom kalender
            )
            fig_box.update_layout(showlegend=False, height=500)
            st.plotly_chart(fig_box, use_container_width=True)

        # ── Insight ────────────────────────────────────────────
        st.markdown("---")
        st.header("💡 Insight")

        avg_map = dict(zip(df_summary["Kategori_Hari"], df_summary["Rata_Rata_Omzet"]))
        avg_wd    = avg_map.get("1. Weekday Biasa", 0)
        avg_libur = avg_map.get("3. Weekday Libur", 0)
        avg_we    = avg_map.get("2. Weekend Biasa", 0)
        avg_we_libur = avg_map.get("4. Weekend & Libur", 0)

        ic1, ic2 = st.columns(2)
        with ic1:
            st.subheader("📅 Efek Tanggal Merah")
            if avg_wd > 0 and avg_libur > 0:
                diff = (avg_libur - avg_wd) / avg_wd * 100
                if diff > 0:
                    st.success(f"Omzet tanggal merah **naik {diff:.1f}%** dibanding weekday biasa.")
                else:
                    st.warning(f"Omzet tanggal merah **turun {abs(diff):.1f}%** dibanding weekday biasa.")
            else:
                st.info("Data weekday libur belum tersedia.")

        with ic2:
            st.subheader("🆚 Weekend vs Libur")
            if avg_we > 0 and avg_libur > 0:
                if avg_we_libur > 0:
                    best = max(
                        {"Weekend Biasa": avg_we, "Weekday Libur": avg_libur, "Weekend & Libur": avg_we_libur},
                        key=lambda k: {"Weekend Biasa": avg_we, "Weekday Libur": avg_libur, "Weekend & Libur": avg_we_libur}[k],
                    )
                    st.info(f"Rata-rata omzet tertinggi: **{best}**.")
                else:
                    st.info("Weekend biasa lebih kuat." if avg_we > avg_libur else "Tanggal merah weekday lebih kuat dari weekend biasa.")
            else:
                st.info("Data pembanding belum cukup.")

        # ── Breakdown per Tipe Event ───────────────────────────
        if df_raw is not None and "Tipe_Event" in df_raw.columns:
            st.markdown("---")
            st.subheader("🗓️ Breakdown per Tipe Event")
            df_tipe = (
                df_raw.groupby("Tipe_Event", as_index=False)
                .agg(
                    Rata_Rata_Omzet=(col_rev, "mean"),
                    Jumlah_Hari=("Tanggal", "count"),
                    Total_Omzet=(col_rev, "sum"),
                )
                .sort_values("Rata_Rata_Omzet", ascending=False)
            )
            df_tipe_display = df_tipe.copy()
            df_tipe_display["Rata_Rata_Omzet"] = df_tipe_display["Rata_Rata_Omzet"].apply(format_rupiah)
            df_tipe_display["Total_Omzet"] = df_tipe_display["Total_Omzet"].apply(format_rupiah)
            st.dataframe(df_tipe_display, use_container_width=True, hide_index=True)

        with st.expander("📄 Lihat Detail Data"):
            cols_show = ["Tanggal", "Total After Bill Discount", "Nama_Event", "Tipe_Event", "Kategori_Hari"]
            cols_show = [c for c in cols_show if c in df_raw.columns]
            st.dataframe(
                df_raw[cols_show].head(1000) if df_raw is not None else st.empty(),
                use_container_width=True,
            )
    except Exception as _e:
        import streamlit as _st
        _st.error(f"⚠️ Terjadi kesalahan pada modul ini: {_e}")