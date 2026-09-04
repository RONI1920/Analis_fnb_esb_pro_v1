# ui/sidebar.py — Sidebar Upload & Filter Global

import pandas as pd
import streamlit as st

from config import TIPE_FILE_STANDAR
from data_loaders import (
    load_data_gmv, load_cogs_data, load_data_waiter,
    load_data_ulasan, load_data_purchase,
)


def build_sidebar():
    """Membangun sidebar dan mengembalikan semua file yang di-upload + use_db."""

    def on_checkbox_change():
        st.session_state.use_db = st.session_state.use_db_widget_key

    def on_file_change():
        load_data_gmv.clear()
        load_cogs_data.clear()
        load_data_waiter.clear()
        load_data_ulasan.clear()
        load_data_purchase.clear()
        # FIX: jangan matikan use_db saat file baru diupload.
        # Toggle tetap di posisi user terakhir kali set.
        # Tapi tandai widget_key sinkron dengan use_db agar tidak drift.
        st.session_state["use_db_widget_key"] = st.session_state.get("use_db", False)
        for key in ["gmv_saved_status", "cogs_saved_status", "waiter_saved_status",
                    "ulasan_saved_status", "purchase_saved_status"]:
            st.session_state[key] = False

    if "use_db" not in st.session_state:
        st.session_state.use_db = False

    with st.sidebar:
        st.markdown(
            """
            <div style='text-align:center;margin-bottom:20px;'>
                <h2>DATA DRIVEN</h2>
                <h2>SPECIALYST FNB</h2>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div style='font-size:12px;font-weight:700;color:#9ca3af;"
            "text-transform:uppercase;letter-spacing:.07em;"
            "margin-bottom:6px'>💾 Penyimpanan Data</div>",
            unsafe_allow_html=True,
        )

        _db_on = st.session_state.get("use_db", False)
        new_pref = st.toggle(
            "Simpan ke Database",
            value=_db_on,
            key="toggle_user_db",
            help=(
                "ON  → aktifkan penyimpanan permanen. Tombol simpan muncul di setiap file.\n"
                "OFF → data hanya sementara di sesi ini, tidak tersimpan ke database."
            ),
        )
        if new_pref != _db_on:
            st.session_state["use_db"] = new_pref
            st.session_state["use_db_widget_key"] = new_pref
            st.session_state["user_db_preference"] = new_pref

        if st.session_state.get("use_db", False):
            st.markdown(
                "<div style='background:linear-gradient(90deg,#064e3b,#065f46);"
                "border:1px solid #059669;color:#6ee7b7;border-radius:6px;"
                "padding:5px 10px;font-size:11px;font-weight:600;"
                "margin-top:4px'>🗄️ Database Aktif — klik Simpan di tiap file</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div style='background:#1a1f2e;border:1px solid #374151;"
                "color:#9ca3af;border-radius:6px;padding:5px 10px;"
                "font-size:11px;font-weight:600;margin-top:4px'>"
                "⚡ Mode Sementara — aktifkan toggle untuk simpan</div>",
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.header("📂 Upload Data")

        def _uploader_with_save(label, key, save_key, info_text, table_name):
            f = st.file_uploader(label, type=TIPE_FILE_STANDAR,
                                 key=key, on_change=on_file_change)
            if info_text:
                st.caption(info_text)

            if f is not None:
                sig          = f"{f.name}_{f.size}"
                already_saved = st.session_state.get(f"saved_sig_{table_name}") == sig
                db_aktif     = st.session_state.get("use_db", False)

                if already_saved:
                    # ── Sudah tersimpan ──────────────────────────────
                    st.markdown(
                        "<div style='background:#052e16;border:1px solid #166534;"
                        "border-radius:6px;padding:5px 10px;margin-top:4px'>"
                        "<span style='color:#4ade80;font-size:11px'>✅ Tersimpan di database</span>"
                        "</div>",
                        unsafe_allow_html=True,
                    )

                elif db_aktif:
                    # ── Toggle aktif — tampilkan tombol simpan ───────
                    st.markdown(
                        f"<div style='background:#1c1917;border:1px solid #44403c;"
                        f"border-radius:6px;padding:5px 10px;margin-top:4px'>"
                        f"<span style='color:#fbbf24;font-size:11px'>"
                        f"📄 {f.name[:28]}{'...' if len(f.name)>28 else ''} "
                        f"({f.size/1024:.0f} KB)</span></div>",
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "💾 Simpan ke Database",
                        key=f"save_btn_{table_name}",
                        use_container_width=True,
                        type="primary",
                        help=f"Simpan {f.name} ke database secara permanen",
                    ):
                        st.session_state[save_key] = True
                        st.session_state[f"pending_save_{table_name}"] = True
                        st.rerun()

                else:
                    # ── Toggle nonaktif — tombol disabled + petunjuk ─
                    st.markdown(
                        f"<div style='background:#1c1917;border:1px solid #44403c;"
                        f"border-radius:6px;padding:5px 10px;margin-top:4px'>"
                        f"<span style='color:#fbbf24;font-size:11px'>"
                        f"📄 {f.name[:28]}{'...' if len(f.name)>28 else ''} "
                        f"({f.size/1024:.0f} KB)</span></div>",
                        unsafe_allow_html=True,
                    )
                    st.button(
                        "🔒 Simpan ke Database",
                        key=f"save_btn_{table_name}",
                        use_container_width=True,
                        disabled=True,
                        help="Aktifkan toggle 'Gunakan data terakhir dari database' di atas untuk menyimpan",
                    )
                    st.caption("⬆️ Aktifkan toggle Database untuk menyimpan")

            return f

        gmv_file = _uploader_with_save(
            "1. 📊 Upload Laporan GMV (Operasional)", "uploader_gmv",
            "save_gmv_flag", "Header di baris ke-10", "gmv_data"
        )

        cogs_file = _uploader_with_save(
            "2. 💰 Upload Laporan COGS", "uploader_cogs",
            "save_cogs_flag", "Header di baris ke-13", "cogs_data"
        )

        waiter_file = _uploader_with_save(
            "3. 🧑‍🍳 Upload Sales Recapitulation Detail", "uploader_waiter",
            "save_waiter_flag", "Header di baris ke-12", "waiter_data"
        )

        ulasan_file = _uploader_with_save(
            "4. ❤️ Upload Laporan Ulasan Pelanggan", "uploader_ulasan",
            "save_ulasan_flag", "Kolom wajib: Nama, Rating, Ulasan", "ulasan_data"
        )

        purchase_file = _uploader_with_save(
            "5. 🛒 Upload Laporan Pembelian", "uploader_purchase",
            "save_purchase_flag", "Header di baris ke-12", "purchase_data"
        )

        pl_file = _uploader_with_save(
            "6. 📉 Upload Profit Loss Report", "uploader_pl",
            "save_pl_flag", "Format wide dengan kolom bulan", "pl_data"
        )

    # ── Render notifikasi simpan-ke-DB (dari queue di session_state) ──
    notif_queue = st.session_state.pop("notif_queue", [])
    for msg in notif_queue:
        st.toast(msg, icon="✅")

    return (
        gmv_file, cogs_file, waiter_file, ulasan_file,
        purchase_file, pl_file, st.session_state.use_db,
    )


def build_global_filters(data_gmv, data_cogs, data_waiter, data_purchase, data_pl):
    """Menggambar filter global dan mengembalikan data yang sudah difilter."""
    filtered_gmv = data_gmv
    filtered_cogs = data_cogs
    filtered_waiter = data_waiter
    filtered_purchase = data_purchase
    filtered_pl = data_pl

    # Tentukan sumber tanggal master
    master_min = master_max = pd.Timestamp.now().date()
    filter_source_df = date_col_ref = None

    try:
        if data_gmv is not None and not data_gmv.empty:
            master_min = data_gmv["Sales Date In"].min().date()
            master_max = data_gmv["Sales Date In"].max().date()
            filter_source_df, date_col_ref = data_gmv, "Sales Date In"
        elif data_cogs is not None and not data_cogs.empty:
            master_min = data_cogs["Sales Date"].min().date()
            master_max = data_cogs["Sales Date"].max().date()
            filter_source_df, date_col_ref = data_cogs, "Sales Date"
    except Exception as e:
        st.error(f"Gagal membaca rentang tanggal: {e}")

    if filter_source_df is None and data_pl is None:
        return filtered_gmv, filtered_cogs, filtered_waiter, filtered_purchase, filtered_pl

    st.subheader("Filter Analisis Global")

    # Filter Cabang
    if data_gmv is not None and "Branch" in data_gmv.columns:
        all_branches = sorted(data_gmv["Branch"].unique())
        sel_branches = st.multiselect(
            "Pilih Cabang (Branch):", options=all_branches,
            default=all_branches, key="branch_filter"
        )
        filtered_gmv = data_gmv[data_gmv["Branch"].isin(sel_branches)]
        if sel_branches:
            for df_ref, filtered_ref, col in [
                (data_cogs, "filtered_cogs", "Branch"),
                (data_waiter, "filtered_waiter", "Branch"),
                (data_purchase, "filtered_purchase", "Branch"),
                (data_pl, "filtered_pl", "Branch"),
            ]:
                if df_ref is not None and col in df_ref.columns:
                    locals()[filtered_ref] = df_ref[df_ref[col].isin(sel_branches)]

            # Apply branch filter manually (locals() workaround)
            if data_cogs is not None and "Branch" in data_cogs.columns:
                filtered_cogs = data_cogs[data_cogs["Branch"].isin(sel_branches)]
            if data_waiter is not None and "Branch" in data_waiter.columns:
                filtered_waiter = data_waiter[data_waiter["Branch"].isin(sel_branches)]
            if data_purchase is not None and "Branch" in data_purchase.columns:
                filtered_purchase = data_purchase[data_purchase["Branch"].isin(sel_branches)]
            if data_pl is not None and "Branch" in data_pl.columns:
                filtered_pl = data_pl[data_pl["Branch"].isin(sel_branches)]

    # Filter Waktu
    filter_type = st.radio(
        "Rentang waktu:",
        ["Semua Periode", "Harian", "Mingguan", "Bulanan", "Tahunan"],
        horizontal=True, key="filter_type_global",
    )

    def _apply_date_filter(df, col, condition_fn):
        if df is not None:
            return df[condition_fn(df[col])]
        return df

    if filter_type == "Harian":
        sel_date = st.date_input("Pilih Tanggal", value=master_max,
                                 min_value=master_min, max_value=master_max)
        filtered_gmv = _apply_date_filter(filtered_gmv, "Sales Date In",
                                          lambda c: c.dt.date == sel_date)
        filtered_cogs = _apply_date_filter(filtered_cogs, "Sales Date",
                                           lambda c: c.dt.date == sel_date)
        filtered_waiter = _apply_date_filter(filtered_waiter, "Order Time",
                                             lambda c: c.dt.date == sel_date)
        filtered_purchase = _apply_date_filter(filtered_purchase, "Purchase Date",
                                               lambda c: c.dt.date == sel_date)

    elif filter_type == "Mingguan":
        default_start = max(master_max - pd.to_timedelta(6, "d"), master_min)
        start = st.date_input("Tanggal Mulai (7 hari)", value=default_start,
                              min_value=master_min, max_value=master_max)
        end = start + pd.to_timedelta(6, "d")
        st.info(f"{start:%d-%m-%Y} s.d. {end:%d-%m-%Y}")

        filtered_gmv = _apply_date_filter(
            filtered_gmv, "Sales Date In", lambda c: (c.dt.date >= start) & (c.dt.date <= end)
        )
        filtered_cogs = _apply_date_filter(
            filtered_cogs, "Sales Date", lambda c: (c.dt.date >= start) & (c.dt.date <= end)
        )
        filtered_waiter = _apply_date_filter(
            filtered_waiter, "Order Time", lambda c: (c.dt.date >= start) & (c.dt.date <= end)
        )
        filtered_purchase = _apply_date_filter(
            filtered_purchase, "Purchase Date", lambda c: (c.dt.date >= start) & (c.dt.date <= end)
        )

    elif filter_type == "Bulanan":
        period_options, period_map = [], {}
        if filter_source_df is not None:
            temp = filter_source_df[[date_col_ref]].copy()
            temp["Period_Obj"] = temp[date_col_ref].dt.to_period("M")
            for p in sorted(temp["Period_Obj"].unique(), reverse=True):
                label = p.strftime("%B %Y")
                period_options.append(label)
                period_map[label] = (p.month, p.year)

        if not period_options:
            now = pd.Timestamp.now()
            period_options = [now.strftime("%B %Y")]
            period_map[period_options[0]] = (now.month, now.year)

        sel = st.selectbox("Pilih Bulan:", options=period_options)
        sel_month, sel_year = period_map[sel]

        filtered_gmv = _apply_date_filter(
            filtered_gmv, "Sales Date In",
            lambda c: (c.dt.month == sel_month) & (c.dt.year == sel_year)
        )
        filtered_cogs = _apply_date_filter(
            filtered_cogs, "Sales Date",
            lambda c: (c.dt.month == sel_month) & (c.dt.year == sel_year)
        )
        filtered_waiter = _apply_date_filter(
            filtered_waiter, "Order Time",
            lambda c: (c.dt.month == sel_month) & (c.dt.year == sel_year)
        )
        filtered_purchase = _apply_date_filter(
            filtered_purchase, "Purchase Date",
            lambda c: (c.dt.month == sel_month) & (c.dt.year == sel_year)
        )

    elif filter_type == "Tahunan":
        year_options = (
            sorted(filter_source_df[date_col_ref].dt.year.unique(), reverse=True)
            if filter_source_df is not None else [pd.Timestamp.now().year]
        )
        sel_year = st.selectbox("Pilih Tahun:", options=year_options)

        filtered_gmv = _apply_date_filter(
            filtered_gmv, "Sales Date In", lambda c: c.dt.year == sel_year
        )
        filtered_cogs = _apply_date_filter(
            filtered_cogs, "Sales Date", lambda c: c.dt.year == sel_year
        )
        filtered_waiter = _apply_date_filter(
            filtered_waiter, "Order Time", lambda c: c.dt.year == sel_year
        )
        filtered_purchase = _apply_date_filter(
            filtered_purchase, "Purchase Date", lambda c: c.dt.year == sel_year
        )

    return filtered_gmv, filtered_cogs, filtered_waiter, filtered_purchase, filtered_pl