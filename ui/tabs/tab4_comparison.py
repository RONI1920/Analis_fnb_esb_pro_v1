# ui/tabs/tab4_comparison.py — Tab 4: A/B Executive Comparison Dashboard

import pandas as pd
import streamlit as st

from analytics.gmv import calculate_sales_kpi
from formatters import format_rupiah, format_angka_bulat


def build_tab4_comparison(data_gmv, data_cogs, data_waiter):
    st.header("⚖️ Executive Comparison Dashboard")

    # Pastikan datetime
    for df, col in [(data_gmv, "Sales Date In"), (data_cogs, "Sales Date"), (data_waiter, "Order Time")]:
        if df is not None and not df.empty and col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Helper functions
    def safe_get(d, k): return d.get(k, 0) if d else 0
    def pct_change(a, b): return ((a - b) / b * 100) if b != 0 else (100 if a != 0 else 0)
    def get_severity(v): v=abs(v); return "🔴 Critical" if v>=30 else ("🟠 High" if v>=15 else ("🟡 Medium" if v>=5 else "🟢 Normal"))
    def classify_trend(v): return "🚀 Strong Growth" if v>=20 else ("📈 Growth" if v>=5 else ("➡️ Stable" if v>-5 else ("📉 Decline" if v>-20 else "💥 Critical Decline")))

    # Deteksi data range
    master_min = master_max = pd.Timestamp.now().date()
    has_data = False
    for df, col in [(data_gmv, "Sales Date In"), (data_cogs, "Sales Date"), (data_waiter, "Order Time")]:
        if df is not None and not df.empty and col in df.columns:
            master_min = df[col].min().date()
            master_max = df[col].max().date()
            has_data = True
            break

    if not has_data:
        st.warning("Upload data terlebih dahulu.")
        return

    # Slice helper
    def slice_data(df, date_col, ref_date, ctype):
        if df is None or df.empty or date_col not in df.columns:
            return pd.DataFrame(columns=df.columns if df is not None else []), "-"
        if ctype == "Harian":
            return df[df[date_col].dt.date == ref_date], ref_date.strftime('%d %b %Y')
        elif ctype == "Mingguan":
            end = ref_date + pd.to_timedelta(6, "d")
            return df[(df[date_col].dt.date >= ref_date) & (df[date_col].dt.date <= end)], f"{ref_date:%d %b} – {end:%d %b %Y}"
        elif ctype == "Bulanan":
            return df[(df[date_col].dt.month == ref_date.month) & (df[date_col].dt.year == ref_date.year)], ref_date.strftime('%B %Y')
        elif ctype == "Tahunan":
            return df[df[date_col].dt.year == ref_date.year], f"Tahun {ref_date.year}"
        return df, "-"

    # Filter UI
    ctype = st.selectbox("Tipe Perbandingan", ["Harian", "Mingguan", "Bulanan", "Tahunan"])
    st.markdown("---")

    dA = master_max
    try:
        offset = {"Harian": pd.to_timedelta(1, "d"), "Mingguan": pd.to_timedelta(7, "d"),
                  "Bulanan": pd.DateOffset(months=1), "Tahunan": pd.DateOffset(years=1)}
        dB = (pd.Timestamp(dA) - offset[ctype]).date()
        if pd.Timestamp(dB) < pd.Timestamp(master_min):
            dB = master_min
    except Exception:
        dB = master_min

    c1, c2, c3 = st.columns([0.38, 0.24, 0.38])
    with c1:
        st.markdown("### 📌 Periode A")
        date_A = st.date_input("A", value=dA, key="cmp_A")
    with c3:
        st.markdown("### 📊 Periode B")
        date_B = st.date_input("B", value=dB, key="cmp_B")
    with c2:
        st.markdown("### Δ")
        if date_A > date_B: st.success("A lebih baru")
        elif date_A < date_B: st.warning("A lebih lama")
        else: st.info("Periode sama")

    st.markdown("---")

    # Slice data
    gmvA, _ = slice_data(data_gmv, "Sales Date In", date_A, ctype)
    gmvB, _ = slice_data(data_gmv, "Sales Date In", date_B, ctype)

    kA = calculate_sales_kpi(gmvA) if not gmvA.empty else {}
    kB = calculate_sales_kpi(gmvB) if not gmvB.empty else {}

    rev_A = safe_get(kA, "Total Pendapatan Kotor"); rev_B = safe_get(kB, "Total Pendapatan Kotor")
    trx_A = safe_get(kA, "Total Transaksi");       trx_B = safe_get(kB, "Total Transaksi")
    atv_A = safe_get(kA, "Rata-rata Nilai Transaksi (ATV)"); atv_B = safe_get(kB, "Rata-rata Nilai Transaksi (ATV)")
    ipb_A = safe_get(kA, "Item per Transaksi (IPB)"); ipb_B = safe_get(kB, "Item per Transaksi (IPB)")
    disc_A = safe_get(kA, "Total Diskon"); disc_B = safe_get(kB, "Total Diskon")

    d_rev = pct_change(rev_A, rev_B); d_trx = pct_change(trx_A, trx_B)
    d_atv = pct_change(atv_A, atv_B); d_ipb = pct_change(ipb_A, ipb_B)
    d_disc = pct_change(disc_A, disc_B)

    # Executive Summary
    st.header("📌 Executive Summary")
    with st.container(border=True):
        st.markdown(f"""
        ### Revenue Performance
        Status: {get_severity(d_rev)} | Trend: {classify_trend(d_rev)}
        # {d_rev:+.1f}%
        ({format_rupiah(rev_A)} vs {format_rupiah(rev_B)})
        """)
        impact = rev_A - rev_B
        if impact < 0:
            st.error(f"💸 Estimasi kehilangan revenue: {format_rupiah(abs(impact))}")
        else:
            st.success(f"💰 Tambahan revenue: {format_rupiah(impact)}")

    # Revenue Driver
    st.header("📈 Revenue Driver Analysis")
    with st.container(border=True):
        factors = {"Transaction": abs(d_trx), "ATV": abs(d_atv), "IPB": abs(d_ipb), "Discount": abs(d_disc)}
        top_driver = max(factors, key=factors.get)
        st.warning(f"🚨 Faktor terbesar: **{top_driver}** ({factors[top_driver]:.1f}%)")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Revenue", format_rupiah(rev_A), f"{d_rev:+.1f}%")
        c2.metric("Transaction", format_angka_bulat(trx_A), f"{d_trx:+.1f}%")
        c3.metric("ATV", format_rupiah(atv_A), f"{d_atv:+.1f}%")
        c4.metric("IPB", f"{ipb_A:.2f}", f"{d_ipb:+.1f}%")

    # Root Cause
    st.header("🔍 Root Cause Analysis")
    with st.container(border=True):
        if d_trx < -5:
            st.error(f"🔴 Traffic customer turun {abs(d_trx):.1f}%\n- Promo kurang efektif\n- Kompetitor lebih agresif")
        if d_atv < -5 and d_ipb < -5:
            st.warning(f"⚠️ Customer beli lebih sedikit item.\nATV turun {abs(d_atv):.1f}%, IPB turun {abs(d_ipb):.1f}%")
        if d_disc > 15:
            st.warning(f"🏷️ Diskon meningkat {d_disc:.1f}% — margin bisa tertekan.")
        if d_atv > 10:
            st.success("✅ ATV meningkat signifikan. Upselling berjalan baik.")

    # Recommendations
    st.header("✅ Recommended Actions")
    recs = []
    if d_trx < -10: recs.append("Evaluasi traffic customer dan efektivitas promosi.")
    if d_atv < -10: recs.append("Tingkatkan upselling dan bundling menu.")
    if d_disc > 15: recs.append("Audit efektivitas program diskon.")
    if d_ipb < -10: recs.append("Evaluasi strategi add-on dan cross-selling.")
    if not recs: recs.append("Performa relatif stabil. Fokus menjaga konsistensi operasional.")
    with st.container(border=True):
        for r in recs:
            st.markdown(f"• {r}")

    # Conclusion
    st.header("💡 Executive Conclusion")
    with st.container(border=True):
        summary = []
        summary.append(f"Revenue {'naik' if d_rev > 0 else 'turun'} {abs(d_rev):.1f}% dibanding periode sebelumnya.")
        summary.append("Perubahan utama dipengaruhi " + ("volume transaksi." if abs(d_trx) > abs(d_atv) else "nilai transaksi pelanggan."))
        if d_disc > 10: summary.append("Diskon meningkat signifikan dan perlu dikontrol.")
        if d_ipb < -10: summary.append("Item per transaksi turun — upselling perlu diperkuat.")
        elif d_ipb > 10: summary.append("Cross-selling dan add-on berjalan efektif.")
        for s in summary:
            st.markdown(f"• {s}")
