# insights/generators.py — Generator Insight Otomatis untuk Semua Tab

import pandas as pd
import streamlit as st

from formatters import format_rupiah, format_persen, format_angka_bulat


# ──────────────────────────────────────────────
# TAB 1 — GMV
# ──────────────────────────────────────────────

@st.cache_data
def generate_gmv_insights(kpi, top_selling, bottom_selling, peak_hours, peak_days_of_week):
    insights = []
    try:
        if not top_selling.empty:
            top = top_selling.iloc[0]
            insights.append(
                f"**🚀 Menu Paling Laris:** `{top['Menu']}` terjual "
                f"**{top['Qty']:,.0f} porsi** pada periode ini."
            )
    except Exception:
        pass

    try:
        if not bottom_selling.empty:
            bot = bottom_selling.iloc[0]
            insights.append(
                f"**📉 Menu Jarang Laku:** `{bot['Menu']}` hanya terjual "
                f"**{bot['Qty']:,.0f} porsi**."
            )
    except Exception:
        pass

    try:
        if not peak_days_of_week.empty:
            peak_day = peak_days_of_week.sort_values("Bill Number", ascending=False).iloc[0]
            insights.append(
                f"**🗓️ Hari Paling Ramai:** **{peak_day['Day Name']}** dengan "
                f"**{peak_day['Bill Number']:,.0f} transaksi**."
            )
    except Exception:
        pass

    try:
        if not peak_hours.empty:
            peak_hr = peak_hours.sort_values("Bill Number", ascending=False).iloc[0]
            insights.append(
                f"**🕒 Jam Paling Ramai:** Pukul **{peak_hr['Hour']}:00** dengan "
                f"**{peak_hr['Bill Number']:,.0f} transaksi**."
            )
    except Exception:
        pass

    try:
        atv = kpi.get("Rata-rata Nilai Transaksi (ATV)", 0)
        ipb = kpi.get("Item per Transaksi (IPB)", 0)
        insights.append(
            f"**💸 Pola Belanja:** Rata-rata pelanggan menghabiskan **{format_rupiah(atv)}** "
            f"dengan **{ipb:.2f} item** per transaksi."
        )
    except Exception:
        pass

    insights.append(
        "**💡 Catatan:** Untuk melihat menu paling *profit*, cek tab **'💰 COGS & Profit'**."
    )
    return insights


# ──────────────────────────────────────────────
# TAB 2 — COGS
# ──────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def generate_cogs_insights(profit_df):
    insights = []
    if profit_df is None or profit_df.empty:
        return ["Tidak ada data profit untuk dianalisis."]

    try:
        total_revenue = profit_df["Total Revenue (Rp)"].sum()
        total_profit = profit_df["Total Profit (Rp)"].sum()
        avg_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0

        insights.append(
            f"**💰 Profitabilitas Umum:** Revenue **{format_rupiah(total_revenue)}**, "
            f"profit **{format_rupiah(total_profit)}**, margin rata-rata **{avg_margin:,.1f}%**."
        )

        df_valid = profit_df[profit_df["Qty"] > 0]
        if not df_valid.empty:
            top = df_valid.nlargest(1, "Total Profit (Rp)").iloc[0]
            insights.append(
                f"**🏆 Bintang Profit:** `{top['Menu']}` menghasilkan "
                f"**{format_rupiah(top['Total Profit (Rp)'])}**."
            )

            best_margin = df_valid.nlargest(1, "Margin (%)").iloc[0]
            insights.append(
                f"**📈 Efisiensi Terbaik:** `{best_margin['Menu']}` dengan margin "
                f"**{format_persen(best_margin['Margin (%)'])}**."
            )

            worst = df_valid.nsmallest(1, "Total Profit (Rp)").iloc[0]
            insights.append(
                f"**💸 Perlu Perhatian:** `{worst['Menu']}` hanya profit "
                f"**{format_rupiah(worst['Total Profit (Rp)'])}** dari "
                f"**{worst['Qty']:,.0f} porsi**."
            )
    except Exception as e:
        insights.append(f"Gagal membuat insight: {e}")

    return insights


# ──────────────────────────────────────────────
# TAB 3 — HR & Fraud
# ──────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def generate_hr_insights(time_data, waiter_data):
    insights = []

    try:
        if time_data is not None and not time_data.empty:
            peak_sales = time_data.nlargest(1, "Total_Penjualan").iloc[0]
            insights.append(
                f"**🕒 Waktu Emas:** Sesi **{peak_sales['Waktu Kunjungan']}** "
                f"menghasilkan **{format_rupiah(peak_sales['Total_Penjualan'])}**."
            )
            peak_trx = time_data.nlargest(1, "Jumlah_Transaksi").iloc[0]
            insights.append(
                f"**🏃 Tersibuk:** Sesi **{peak_trx['Waktu Kunjungan']}** dengan "
                f"**{format_angka_bulat(peak_trx['Jumlah_Transaksi'])}** transaksi."
            )
    except Exception:
        pass

    try:
        if waiter_data is not None and not waiter_data.empty:
            top_w = waiter_data.nlargest(1, "Total_Penjualan").iloc[0]
            insights.append(
                f"**🏆 Waiter Terbaik:** **{top_w['Waiter']}** menghasilkan "
                f"**{format_rupiah(top_w['Total_Penjualan'])}** dari "
                f"**{format_angka_bulat(top_w['Jumlah_Transaksi'])}** transaksi."
            )
    except Exception:
        pass

    return insights


def generate_fraud_insights(fraud_result: dict) -> list:
    insights = []
    if not fraud_result:
        return ["Analisis deteksi anomali gagal."]

    res_void = fraud_result["void"]
    res_ns = fraud_result["nonsales"]

    if not res_void["suspects"].empty:
        names = ", ".join(res_void["suspects"].index.tolist()[:3])
        insights.append(
            f"⚠️ **{len(res_void['suspects'])} karyawan** (cth: {names}) terindikasi anomali Void "
            f"(threshold: {res_void['threshold']:.0f}x)."
        )
    else:
        insights.append("✅ **Void:** Tidak ada anomali yang terdeteksi.")

    if not res_ns["suspects"].empty:
        names = ", ".join(res_ns["suspects"].index.tolist()[:3])
        insights.append(
            f"🟠 **{len(res_ns['suspects'])} karyawan** (cth: {names}) terindikasi anomali Non-Sales "
            f"(threshold: {res_ns['threshold']:.0f}x)."
        )
    else:
        insights.append("✅ **Non-Sales:** Tidak ada anomali yang terdeteksi.")

    return insights


# ──────────────────────────────────────────────
# TAB 5 — Forecast
# ──────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def generate_forecast_insights(forecast_df, last_date):
    insights = []
    if forecast_df is None or forecast_df.empty:
        return ["Tidak ada data ramalan."]

    try:
        trend_now = forecast_df[forecast_df["ds"] <= last_date]["trend"].iloc[-1]
        trend_end = forecast_df["trend"].iloc[-1]
        trend_pct = (trend_end - trend_now) / trend_now if trend_now != 0 else 0

        if trend_pct > 0.01:
            insights.append(f"**📈 Tren NAIK** ({trend_pct:+.1%}) untuk periode ke depan.")
        elif trend_pct < -0.01:
            insights.append(f"**📉 Tren TURUN** ({trend_pct:+.1%}). Waspadai perlambatan.")
        else:
            insights.append(f"**⚖️ Tren STABIL** (perubahan {trend_pct:+.1%}).")

        future = forecast_df[forecast_df["ds"] > last_date]
        if len(future) >= 7:
            insights.append(
                f"**🔮 Ramalan 7 Hari:** estimasi penjualan "
                f"**{format_rupiah(future.iloc[:7]['yhat'].sum())}**."
            )
    except Exception as e:
        insights.append(f"Gagal membuat insight: {e}")

    insights.append(
        "**🗓️ Pola Mingguan:** Periksa grafik 'Komponen Tren & Musiman' untuk detail hari terkuat."
    )
    return insights


# ──────────────────────────────────────────────
# TAB 6 — Target
# ──────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def generate_target_insights(kpi_dict: dict) -> list:
    insights = []

    try:
        sisa_hari = kpi_dict.get("sisa_hari", 0)

        if sisa_hari <= 0:
            pct = kpi_dict.get("penjualan_saat_ini", 0) / max(kpi_dict.get("target_bulanan", 1), 1)
            t = "success" if pct >= 1 else "warning"
            insights.append({"type": t, "text": f"Bulan selesai dengan pencapaian **{pct*100:,.1f}%**."})
            return insights

        proyeksi_pct = kpi_dict.get("proyeksi_vs_target_persen", 0)
        if proyeksi_pct > 1.05:
            insights.append({"type": "success", "text": f"**SANGAT ON TRACK:** Proyeksi **{proyeksi_pct*100:,.1f}%** dari target!"})
        elif proyeksi_pct >= 0.98:
            insights.append({"type": "info", "text": f"**ON TRACK:** Proyeksi **{proyeksi_pct*100:,.1f}%** dari target."})
        else:
            insights.append({"type": "error", "text": f"**OFF TRACK:** Proyeksi hanya **{proyeksi_pct*100:,.1f}%**. Rencana aksi diperlukan!"})

        rdr_wd = kpi_dict.get("rdr_weekday", 0)
        avg_wd = kpi_dict.get("avg_sales_weekday", 0)
        delta_wd = rdr_wd - avg_wd
        if delta_wd > 0:
            insights.append({
                "type": "warning",
                "text": f"**FOKUS WEEKDAY:** Perlu tambahan **{format_rupiah(delta_wd)}/hari** "
                        f"(dari {format_rupiah(avg_wd)} → {format_rupiah(rdr_wd)}).",
            })

        proj = kpi_dict.get("proyeksi_akhir_bulan", 0)
        prophet = kpi_dict.get("proyeksi_prophet", 0)
        if prophet > proj * 1.05:
            insights.append({"type": "info", "text": f"**AI lebih optimis:** Prophet ({format_rupiah(prophet)}) vs Proyeksi Cerdas ({format_rupiah(proj)})."})
        elif prophet < proj * 0.95:
            insights.append({"type": "warning", "text": f"**AI lebih pesimis:** Prophet ({format_rupiah(prophet)}) vs Proyeksi Cerdas ({format_rupiah(proj)})."})

    except Exception as e:
        insights.append({"type": "error", "text": f"Gagal membuat insight: {e}"})

    return insights


# ──────────────────────────────────────────────
# TAB 7 — Ulasan
# ──────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def generate_review_insights(total_ulasan, avg_rating, nps_score, df_positive, df_negative):
    insights = []
    if total_ulasan == 0:
        return ["Belum ada data ulasan."]

    try:
        status = "BAIK" if nps_score > 20 else ("PERLU PERHATIAN" if nps_score < 0 else "NETRAL")
        insights.append(
            f"**❤️ Sentimen:** {total_ulasan} ulasan, rating rata-rata **{avg_rating:.1f}/5**, "
            f"NPS **{nps_score:.1f}** ({status})."
        )

        if not df_positive.empty:
            top = df_positive.iloc[0]
            insights.append(
                f"**👍 Kekuatan:** **{top['Topik']}** disebut **{top['Jumlah']} kali** dalam ulasan positif."
            )

        if not df_negative.empty:
            top = df_negative.iloc[0]
            insights.append(
                f"**👎 Perlu Perbaikan:** **{top['Topik']}** disebut **{top['Jumlah']} kali** dalam ulasan negatif."
            )
    except Exception as e:
        insights.append(f"Gagal membuat insight: {e}")

    return insights


# ──────────────────────────────────────────────
# TAB 8 — Purchase
# ──────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def generate_purchase_insights(total_cost, cost_by_category, cost_by_supplier, top_items, fcp):
    insights = []

    if fcp > 0:
        insights.append(
            f"💰 **Food Cost %:** **{fcp:.1f}%** (ideal F&B: 25–35%)."
        )

    if total_cost == 0 or top_items.empty:
        return insights or ["Belum ada data pembelian."]

    try:
        insights.append(f"**🛒 Total Biaya:** **{format_rupiah(total_cost)}**.")

        if not cost_by_category.empty:
            top_cat = cost_by_category.iloc[0]
            insights.append(
                f"**🍔 Terbesar:** Kategori `{top_cat['Category']}` menghabiskan "
                f"**{format_rupiah(top_cat['Total'])}**."
            )

        if not cost_by_supplier.empty:
            top_sup = cost_by_supplier.iloc[0]
            insights.append(
                f"**🚚 Supplier Utama:** `{top_sup['Supplier Name']}` — "
                f"**{format_rupiah(top_sup['Total'])}**."
            )

        if not top_items.empty:
            top_item = top_items.iloc[0]
            insights.append(
                f"**💸 Item Termahal:** `{top_item['Product Name']}` — "
                f"**{format_rupiah(top_item['Total'])}**."
            )
    except Exception as e:
        insights.append(f"Gagal membuat insight: {e}")

    return insights


# ──────────────────────────────────────────────
# TAB 9 — Rekomendasi
# ──────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def generate_recommendation_insights(rules_df):
    insights = []
    if rules_df is None or rules_df.empty:
        return ["Tidak ada aturan rekomendasi yang cukup kuat."]

    try:
        top_ev = rules_df.nlargest(1, "expected_value").iloc[0]
        insights.append(
            f"**💸 Potensi Tertinggi:** Jika beli `{top_ev['antecedents']}`, "
            f"tawarkan `{top_ev['consequents']}` — expected value **{format_rupiah(top_ev['expected_value'])}**."
        )

        top_conf = rules_df.nlargest(1, "confidence").iloc[0]
        insights.append(
            f"**🤝 Paling Pasti:** `{top_conf['antecedents']}` → `{top_conf['consequents']}` "
            f"dengan confidence **{top_conf['confidence']:.1%}**."
        )

        top_lift = rules_df.nlargest(1, "lift").iloc[0]
        insights.append(
            f"**🔗 Koneksi Terkuat:** `{top_lift['antecedents']}` & `{top_lift['consequents']}` "
            f"— **{top_lift['lift']:.1f}x** lebih mungkin dibeli bersamaan."
        )

        insights.append("**💡 Aksi:** Gunakan filter 'JIKA Beli' untuk eksplorasi spesifik.")
    except Exception as e:
        insights.append(f"Gagal membuat insight: {e}")

    return insights


# ──────────────────────────────────────────────
# TAB 13 — P&L
# ──────────────────────────────────────────────

@st.cache_data
def generate_pl_insights(df_pl):
    insights = []
    if df_pl is None or df_pl.empty:
        return ["Data P&L kosong."]

    df_curr = df_pl[df_pl["Year_Type"] == "Current Year"]
    total_rev = df_curr[df_curr["Category"] == "Revenue"]["Value"].sum()
    total_exp = df_curr[df_curr["Category"] == "Expense"]["Value"].sum()
    total_cogs = df_curr[df_curr["Category"] == "COGS"]["Value"].sum()
    net_profit = total_rev - total_cogs - total_exp
    npm = (net_profit / total_rev * 100) if total_rev else 0

    if npm > 15:
        insights.append(f"**💰 Sehat:** Net Profit Margin **{npm:.1f}%** — sangat baik untuk F&B.")
    elif npm > 0:
        insights.append(f"**⚠️ Profit Tipis:** Margin **{npm:.1f}%** — perlu efisiensi biaya.")
    else:
        insights.append(f"**🚨 Merugi:** Kerugian bersih **{format_rupiah(abs(net_profit))}**.")

    exp_ratio = (total_exp / total_rev * 100) if total_rev else 0
    insights.append(f"**💸 Beban Operasional:** Memakan **{exp_ratio:.1f}%** dari omzet.")

    return insights
