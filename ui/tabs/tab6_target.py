# ui/tabs/tab6_target.py — Tab 6: Pencapaian Target & Proyeksi

import pandas as pd
import streamlit as st

from analytics.forecast import get_prophet_projection
from insights.generators import generate_target_insights
from config import DAY_MAP, WEEKDAYS, WEEKENDS
from formatters import format_rupiah


def build_tab6_target(data_gmv):
    st.header("🎯 Pencapaian Target & Proyeksi (Dinamis)")

    if data_gmv is None or data_gmv.empty:
        st.warning("Silakan upload file Laporan GMV (File 1) di sidebar.")
        return

    st.subheader("Pengaturan Analisis")

    # Pilih bulan
    try:
        tmp = data_gmv.copy()
        tmp["Bulan-Tahun"] = tmp["Sales Date In"].dt.to_period("M")
        available = sorted(tmp["Bulan-Tahun"].unique(), reverse=True)
        month_opts = {p: p.strftime("%B %Y") for p in available}

        sel_str = st.selectbox("Pilih Bulan:", options=month_opts.values())
        sel_period = [p for p, s in month_opts.items() if s == sel_str][0]
        active_month, active_year = sel_period.month, sel_period.year
        active_month_name = sel_str
    except Exception as e:
        st.error(f"Gagal memproses tanggal: {e}")
        return

    with st.container(border=True):
        target_juta = st.number_input(
            f"Target {active_month_name} (dalam Juta Rp)",
            min_value=1, value=500, step=10,
            key=f"target_{active_month_name}",
        )
        target_bulanan = target_juta * 1_000_000
        st.metric("Target diatur ke:", format_rupiah(target_bulanan))

    st.markdown("---")

    kpi_dict = {}

    try:
        data_bulan = data_gmv[
            (data_gmv["Sales Date In"].dt.month == active_month) &
            (data_gmv["Sales Date In"].dt.year == active_year)
        ].copy()

        if data_bulan.empty:
            st.error(f"Tidak ada data untuk {active_month_name}.")
            return

        latest_in_full = data_gmv["Sales Date In"].max()
        max_date_sel = data_bulan["Sales Date In"].max()
        total_days = pd.Period(f"{active_year}-{active_month}", freq="M").days_in_month

        is_current = (active_year == latest_in_full.year) and (active_month == latest_in_full.month)
        hari_berjalan = max_date_sel.day if is_current else total_days
        sisa_hari = total_days - hari_berjalan
        kpi_dict["sisa_hari"] = sisa_hari

        if is_current:
            st.info(f"Bulan berjalan — data terdeteksi sampai tanggal {hari_berjalan}.")
        else:
            st.success(f"Menampilkan ulasan performa bulan lalu ({active_month_name}) yang telah selesai.")

        penjualan = data_bulan["Total After Bill Discount"].sum()
        kpi_dict["penjualan_saat_ini"] = penjualan
        pencapaian_pct = penjualan / target_bulanan if target_bulanan > 0 else 0
        kpi_dict["pencapaian_persen"] = pencapaian_pct
        sales_dibutuhkan = max(target_bulanan - penjualan, 0)
        rata_harian = penjualan / hari_berjalan if hari_berjalan > 0 else 0

        data_bulan["Nama Hari"] = data_bulan["Sales Date In"].dt.day_name().map(DAY_MAP)
        data_bulan["Tipe Hari"] = data_bulan["Nama Hari"].apply(
            lambda x: "Weekend" if x in WEEKENDS else "Weekday"
        )

        daily_agg = (
            data_bulan.groupby(["Sales Date In", "Tipe Hari"])["Total After Bill Discount"]
            .sum().reset_index()
        )
        avg_wd = daily_agg[daily_agg["Tipe Hari"] == "Weekday"]["Total After Bill Discount"].mean()
        avg_we = daily_agg[daily_agg["Tipe Hari"] == "Weekend"]["Total After Bill Discount"].mean()
        avg_wd = 0 if pd.isna(avg_wd) else avg_wd
        avg_we = 0 if pd.isna(avg_we) else avg_we
        kpi_dict.update({"avg_sales_weekday": avg_wd, "avg_sales_weekend": avg_we})

        weekend_weight = (avg_we / avg_wd) if avg_wd > 0 else (1000.0 if avg_we > 0 else 1.0)

        proyeksi = penjualan
        rdr_wd = rdr_we = 0
        proyeksi_prophet = penjualan

        if sisa_hari > 0:
            end_bulan = max_date_sel.replace(day=total_days)
            sisa_tgl = pd.DataFrame(
                pd.date_range(start=max_date_sel + pd.Timedelta(days=1), end=end_bulan),
                columns=["Tanggal"]
            )
            sisa_tgl["Nama Hari"] = sisa_tgl["Tanggal"].dt.day_name().map(DAY_MAP)
            n_wd = sisa_tgl["Nama Hari"].isin(WEEKDAYS).sum()
            n_we = sisa_tgl["Nama Hari"].isin(WEEKENDS).sum()

            proyeksi += (n_wd * avg_wd) + (n_we * avg_we)
            pembagi = n_wd + (n_we * weekend_weight)
            if pembagi > 0 and sales_dibutuhkan > 0:
                rdr_wd = sales_dibutuhkan / pembagi
                rdr_we = rdr_wd * weekend_weight

            kpi_dict.update({"rdr_weekday": rdr_wd, "rdr_weekend": rdr_we})

            prophet_data = (
                data_bulan.groupby(data_bulan["Sales Date In"].dt.date)["Total After Bill Discount"]
                .sum().reset_index()
                .rename(columns={"Sales Date In": "ds", "Total After Bill Discount": "y"})
            )
            ramalan = get_prophet_projection(prophet_data, sisa_hari)
            proyeksi_prophet = penjualan + ramalan if ramalan is not None else proyeksi

        proyeksi_vs_target = proyeksi / target_bulanan if target_bulanan > 0 else 0
        kekurangan = target_bulanan - proyeksi

        kpi_dict.update({
            "proyeksi_vs_target_persen": proyeksi_vs_target,
            "proyeksi_akhir_bulan": proyeksi,
            "proyeksi_prophet": proyeksi_prophet,
            "target_bulanan": target_bulanan,
        })

        status_color = "normal" if proyeksi_vs_target > 1.05 else ("off" if proyeksi_vs_target >= 0.98 else "inverse")

    except Exception as e:
        st.error(f"Gagal mengkalkulasi KPI Target: {e}")
        st.exception(e)
        return

    # ── Tampilan KPI ───────────────────────────────────────
    st.subheader("📈 Gambaran Besar")
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Pencapaian per {max_date_sel.strftime('%d-%m-%Y')}",
              f"{pencapaian_pct*100:,.1f}%",
              help=f"{format_rupiah(penjualan)} dari {format_rupiah(target_bulanan)}")

    if sisa_hari > 0:
        c2.metric("Penjualan Dibutuhkan", format_rupiah(sales_dibutuhkan),
                  help=f"Sisa {sisa_hari} hari")
        c3.metric("Proyeksi Kekurangan", format_rupiah(kekurangan))
    else:
        c2.metric("Hasil Akhir Bulan", format_rupiah(penjualan),
                  delta=f"{pencapaian_pct*100:,.1f}% dari Target", delta_color=status_color)
        c3.metric("Selisih Target", format_rupiah(penjualan - target_bulanan))

    # ── Insight ────────────────────────────────────────────
    st.markdown("---")
    st.header("💡 Insight Otomatis (Analisis Target)")
    insights = generate_target_insights(kpi_dict)
    with st.expander("Rangkuman & Rencana Aksi Target", expanded=True):
        for item in insights:
            fn = {"success": st.success, "warning": st.warning,
                  "error": st.error, "info": st.info}.get(item["type"], st.info)
            fn(item["text"])
