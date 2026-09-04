# ui/tabs/tab7_ulasan.py — Tab 7: Analisis Ulasan & Sentimen Pelanggan (Enhanced)

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pandas as pd

from analytics.ulasan_analysis import (
    prepare_ulasan,
    get_word_frequency,
    get_topic_sentiment_breakdown,
    get_rating_distribution,
    get_nps_breakdown,
    get_notable_reviews,
    KEYWORD_DICT,
)


def build_tab7_ulasan(data_ulasan):
    st.header("❤️ Analisis Sentimen & Ulasan Pelanggan")

    if data_ulasan is None or data_ulasan.empty:
        st.warning("Silakan upload file Laporan Ulasan (File 4) di sidebar.")
        return

    df = prepare_ulasan(data_ulasan)
    nps = get_nps_breakdown(df)

    # ── KPI Utama ──────────────────────────────────────────
    st.subheader("📊 KPI Sentimen Pelanggan")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Ulasan", f"{nps['total']}")
    c2.metric("Rata-rata Rating", f"{nps['avg_rating']:.2f} / 5 ⭐")
    c3.metric("Net Promoter Score", f"{nps['nps']:.1f}",
              help="NPS = %Promoter − %Detractor. Skor > 50 = Excellent.")
    c4.metric("Promoter Rate", f"{nps['promoters_pct']:.1f}%",
              delta=f"-{nps['detractors_pct']:.1f}% Detractor")

    st.markdown("---")

    # ── NPS Gauge + Rating Distribution ───────────────────
    col_gauge, col_dist = st.columns(2)

    with col_gauge:
        st.subheader("🎯 NPS Gauge")
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=nps["nps"],
            delta={"reference": 0, "increasing": {"color": "#2ecc71"}, "decreasing": {"color": "#e74c3c"}},
            gauge={
                "axis": {"range": [-100, 100]},
                "bar": {"color": "#3498db"},
                "steps": [
                    {"range": [-100, 0],  "color": "#fadbd8"},
                    {"range": [0, 50],    "color": "#fef9e7"},
                    {"range": [50, 100],  "color": "#d5f5e3"},
                ],
                "threshold": {"line": {"color": "green", "width": 4}, "value": 50},
            },
            title={"text": "NPS Score"},
        ))
        fig_gauge.update_layout(height=280)
        st.plotly_chart(fig_gauge, use_container_width=True)

        # NPS breakdown
        nps_data = pd.DataFrame({
            "Kategori": ["Promoter (⭐5)", "Passive (⭐4)", "Detractor (⭐1-3)"],
            "Jumlah": [nps["promoters"], nps["passives"], nps["detractors"]],
            "Persen": [nps["promoters_pct"], nps["passives_pct"], nps["detractors_pct"]],
        })
        fig_nps = px.bar(
            nps_data, x="Kategori", y="Jumlah",
            color="Kategori",
            color_discrete_map={
                "Promoter (⭐5)": "#2ecc71",
                "Passive (⭐4)": "#f39c12",
                "Detractor (⭐1-3)": "#e74c3c",
            },
            text=nps_data["Persen"].apply(lambda x: f"{x:.1f}%"),
            height=280,
        )
        fig_nps.update_traces(textposition="outside")
        fig_nps.update_layout(showlegend=False, yaxis_title="Jumlah Ulasan")
        st.plotly_chart(fig_nps, use_container_width=True)

    with col_dist:
        st.subheader("⭐ Distribusi Rating")
        dist = get_rating_distribution(df)
        STAR_COLORS = {1: "#e74c3c", 2: "#e67e22", 3: "#f1c40f", 4: "#2ecc71", 5: "#27ae60"}
        fig_dist = px.bar(
            dist, x="Rating", y="Jumlah",
            color="Rating",
            color_discrete_map=STAR_COLORS,
            text=dist["Persen"].apply(lambda x: f"{x:.1f}%"),
            labels={"Rating": "Bintang", "Jumlah": "Jumlah Ulasan"},
            height=320,
        )
        fig_dist.update_traces(textposition="outside")
        fig_dist.update_layout(showlegend=False, xaxis=dict(tickmode="linear"))
        st.plotly_chart(fig_dist, use_container_width=True)

        # Ringkasan sentimen
        sent_count = df["Sentimen"].value_counts().reset_index()
        sent_count.columns = ["Sentimen", "Jumlah"]
        fig_sent = px.pie(
            sent_count, names="Sentimen", values="Jumlah",
            color="Sentimen",
            color_discrete_map={"Positif": "#2ecc71", "Netral": "#f39c12", "Negatif": "#e74c3c"},
            height=250,
            title="Komposisi Sentimen",
        )
        fig_sent.update_traces(textinfo="percent+label")
        fig_sent.update_layout(showlegend=False)
        st.plotly_chart(fig_sent, use_container_width=True)

    st.markdown("---")

    # ── Analisis Topik ─────────────────────────────────────
    st.subheader("🗣️ Analisis Topik Ulasan")

    topic_breakdown = get_topic_sentiment_breakdown(df)

    if not topic_breakdown.empty:
        fig_topic = px.bar(
            topic_breakdown,
            x="Jumlah", y="Topik",
            color="Sentimen",
            orientation="h",
            color_discrete_map={"Positif": "#2ecc71", "Netral": "#f39c12", "Negatif": "#e74c3c"},
            barmode="group",
            height=420,
            labels={"Jumlah": "Jumlah Sebutan", "Topik": "Topik"},
            title="Topik yang Paling Banyak Disinggung (per Sentimen)",
        )
        fig_topic.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_topic, use_container_width=True)

    st.markdown("---")

    # ── Word Frequency ─────────────────────────────────────
    st.subheader("🔤 Kata yang Paling Sering Muncul")
    wf_col1, wf_col2 = st.columns(2)

    with wf_col1:
        st.markdown("##### 👍 Dalam Ulasan Positif")
        wf_pos = get_word_frequency(df, sentimen="Positif", top_n=15)
        if not wf_pos.empty:
            fig_wf_pos = px.bar(
                wf_pos, x="Frekuensi", y="Kata", orientation="h",
                color="Frekuensi", color_continuous_scale="Greens",
                height=420,
            )
            fig_wf_pos.update_layout(yaxis=dict(autorange="reversed"), coloraxis_showscale=False)
            st.plotly_chart(fig_wf_pos, use_container_width=True)

    with wf_col2:
        st.markdown("##### 👎 Dalam Ulasan Negatif")
        wf_neg = get_word_frequency(df, sentimen="Negatif", top_n=15)
        if not wf_neg.empty:
            fig_wf_neg = px.bar(
                wf_neg, x="Frekuensi", y="Kata", orientation="h",
                color="Frekuensi", color_continuous_scale="Reds",
                height=420,
            )
            fig_wf_neg.update_layout(yaxis=dict(autorange="reversed"), coloraxis_showscale=False)
            st.plotly_chart(fig_wf_neg, use_container_width=True)
        else:
            st.info("Tidak cukup ulasan negatif untuk analisis kata.")

    st.markdown("---")

    # ── Ulasan Notable ─────────────────────────────────────
    st.subheader("📝 Ulasan Pilihan")
    notable = get_notable_reviews(df)

    tab_pos, tab_neg = st.tabs(["👍 Ulasan Positif Terpanjang", "👎 Ulasan Negatif / Kritik"])

    with tab_pos:
        for _, row in notable["positif"].iterrows():
            with st.container():
                st.markdown(f"**{row['Nama']}** — {'⭐' * int(row['Rating_Clean'])}")
                st.write(row["Ulasan_Clean"])
                st.divider()

    with tab_neg:
        if notable["negatif"].empty:
            st.success("Tidak ada ulasan negatif yang cukup panjang — pertanda baik!")
        else:
            for _, row in notable["negatif"].iterrows():
                with st.container():
                    st.markdown(f"**{row['Nama']}** — {'⭐' * int(row['Rating_Clean'])}")
                    st.write(row["Ulasan_Clean"])
                    st.divider()

    st.markdown("---")

    # ── Insight Otomatis ───────────────────────────────────
    st.header("💡 Insight & Rekomendasi")

    top_pos_topic = (
        topic_breakdown[topic_breakdown["Sentimen"] == "Positif"]
        .nlargest(1, "Jumlah")["Topik"].values[0]
        if not topic_breakdown[topic_breakdown["Sentimen"] == "Positif"].empty else "-"
    )
    top_neg_topic = (
        topic_breakdown[topic_breakdown["Sentimen"] == "Negatif"]
        .nlargest(1, "Jumlah")["Topik"].values[0]
        if not topic_breakdown[topic_breakdown["Sentimen"] == "Negatif"].empty else "-"
    )

    ic1, ic2, ic3 = st.columns(3)
    with ic1:
        st.subheader("🏆 Kekuatan")
        if nps["nps"] >= 50:
            st.success(f"NPS {nps['nps']:.1f} — Excellent! Pelanggan sangat puas.")
        elif nps["nps"] >= 0:
            st.info(f"NPS {nps['nps']:.1f} — Cukup baik, masih ada ruang peningkatan.")
        else:
            st.warning(f"NPS {nps['nps']:.1f} — Perlu perhatian serius.")
        st.write(f"Topik paling dipuji: **{top_pos_topic}**")

    with ic2:
        st.subheader("⚠️ Yang Perlu Diperbaiki")
        if top_neg_topic != "-":
            st.warning(f"Keluhan terbanyak pada: **{top_neg_topic}**")
        else:
            st.success("Tidak ada keluhan dominan yang terdeteksi.")
        low_rating = df[df["Rating_Clean"] <= 3]
        if not low_rating.empty:
            st.write(f"Total {len(low_rating)} ulasan rating ≤ 3 perlu ditindaklanjuti.")

    with ic3:
        st.subheader("📈 Peluang")
        passive_count = nps["passives"]
        if passive_count > 0:
            st.info(
                f"Ada **{passive_count} Passive** (rating 4) yang bisa dikonversi jadi "
                f"Promoter dengan sedikit peningkatan pengalaman."
            )
        if not wf_pos.empty:
            top_word = wf_pos.iloc[0]["Kata"]
            st.write(f"Kata paling positif: **'{top_word}'** — gunakan ini di materi promosi.")

    with st.expander("📄 Lihat Semua Data Ulasan"):
        cols_show = ["Nama", "Rating_Clean", "Sentimen", "NPS_Category", "Topik", "Ulasan_Clean"]
        st.dataframe(df[cols_show], use_container_width=True, hide_index=True)