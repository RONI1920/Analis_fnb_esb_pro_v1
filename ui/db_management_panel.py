# ui/db_management_panel.py
# Panel Manajemen Database — Flash, Sinkronisasi, Status Real-time
# Dipanggil dari sidebar.py setelah upload section

import streamlit as st
import datetime

_TABLE_LABELS = {
    "gmv_data":      ("📊", "GMV / Penjualan",    "Sales Date In"),
    "cogs_data":     ("💰", "COGS",               "Sales Date"),
    "waiter_data":   ("🧑‍🍳", "Waiter / SDM",     "Order Time"),
    "ulasan_data":   ("❤️",  "Ulasan Pelanggan",  None),
    "purchase_data": ("🛒",  "Pembelian",          "Purchase Date"),
    "pl_data":       ("📉",  "Profit & Loss",      "Date"),
}

_CONFIRM_KEYS = {
    "flash_all":  "confirm_flash_all",
    "flash_gmv":  "confirm_flash_gmv",
    "flash_cogs": "confirm_flash_cogs",
}


def _badge(text: str, color: str, bg: str) -> str:
    return (
        f"<span style='background:{bg};color:{color};border:1px solid {color}40;"
        f"border-radius:6px;padding:1px 8px;font-size:11px;font-weight:700;"
        f"white-space:nowrap'>{text}</span>"
    )


def _status_row(icon, label, info: dict):
    if not info.get("exists") or info["rows"] == 0:
        st.markdown(
            f"{icon} **{label}** &nbsp; {_badge('Kosong', '#ef4444', '#450a0a')}",
            unsafe_allow_html=True,
        )
        return

    rows  = f"{info['rows']:,}"
    d_min = info.get("min_date") or "—"
    d_max = info.get("max_date") or "—"
    period = f"{d_min} → {d_max}" if d_min != "—" else "—"

    st.markdown(
        f"{icon} **{label}** &nbsp; "
        f"{_badge(f'{rows} baris', '#34d399', '#064e3b')} &nbsp;"
        f"<span style='font-size:11px;color:#6b7280'>{period}</span>",
        unsafe_allow_html=True,
    )


def build_db_management_panel(
    df_gmv=None, df_cogs=None, df_waiter=None,
    df_ulasan=None, df_purchase=None, df_pl=None,
):
    """
    Panel manajemen database lengkap:
    - Status tiap tabel (baris, range tanggal)
    - Tombol Flash per-tabel dan Flash All
    - Tombol Sinkronisasi (replace total dari file upload)
    - Konfirmasi sebelum aksi destruktif
    """
    from database import (
        get_db_table_info, clear_table, clear_all_data_tables,
        sync_dataframe_to_db, load_dataframe_from_db, DATA_TABLES,
    )

    with st.expander("🗄️ Manajemen Database", expanded=False):

        # ── Status tabel ─────────────────────────────────────────
        st.markdown(
            "<p style='font-size:12px;font-weight:700;color:#93c5fd;"
            "text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px'>"
            "📋 Status Tabel Data</p>",
            unsafe_allow_html=True,
        )

        from auth import get_current_user_id as _get_uid
        info = get_db_table_info(user_id=_get_uid())
        for tbl in DATA_TABLES:
            icon, label, _ = _TABLE_LABELS[tbl]
            _status_row(icon, label, info.get(tbl, {}))

        # Total DB size
        import os
        from config import DB_FILE
        if os.path.exists(DB_FILE):
            size_kb = os.path.getsize(DB_FILE) / 1024
            size_label = f"{size_kb:.0f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
            st.markdown(
                f"<p style='font-size:11px;color:#6b7280;margin-top:4px'>"
                f"💾 Ukuran database: <b style='color:#9ca3af'>{size_label}</b></p>",
                unsafe_allow_html=True,
            )

        st.divider()

        # ── SINKRONISASI — Replace total per tabel ───────────────
        st.markdown(
            "<p style='font-size:12px;font-weight:700;color:#6ee7b7;"
            "text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px'>"
            "🔄 Sinkronisasi Database</p>",
            unsafe_allow_html=True,
        )
        st.caption(
            "**Sinkronisasi** mengganti SELURUH isi tabel dengan data file yang baru diupload. "
            "Pastikan file sudah diupload di atas sebelum klik."
        )

        upload_map = {
            "gmv_data":      ("GMV",        df_gmv),
            "cogs_data":     ("COGS",       df_cogs),
            "waiter_data":   ("Waiter",     df_waiter),
            "ulasan_data":   ("Ulasan",     df_ulasan),
            "purchase_data": ("Pembelian",  df_purchase),
            "pl_data":       ("P&L",        df_pl),
        }

        # Sinkronisasi individual per tabel
        cols_sync = st.columns(3)
        col_idx = 0
        for tbl, (label, df_data) in upload_map.items():
            icon = _TABLE_LABELS[tbl][0]
            has_data = df_data is not None and (
                not hasattr(df_data, "empty") or not df_data.empty
            )
            with cols_sync[col_idx % 3]:
                btn_disabled = not has_data
                if st.button(
                    f"{icon} Sync {label}",
                    key=f"sync_{tbl}",
                    disabled=btn_disabled,
                    help=f"Ganti seluruh tabel {tbl} dengan file yang diupload"
                         if has_data else "Upload file terlebih dahulu",
                    use_container_width=True,
                ):
                    with st.spinner(f"Sinkronisasi {label}..."):
                        from auth import get_current_user_id as _get_uid
                        ok, msg, stats = sync_dataframe_to_db(df_data, tbl, user_id=_get_uid())
                    if ok:
                        st.success(
                            f"✅ {label}: {stats['rows_new']:,} baris "
                            f"(lama: {stats['rows_old']:,}, duplikat: {stats['dupes_removed']:,})"
                        )
                        st.rerun()
                    else:
                        st.error(f"❌ Gagal: {msg}")
            col_idx += 1

        # Sinkronisasi semua sekaligus
        st.markdown("<br>", unsafe_allow_html=True)
        any_data = any(
            d is not None and (not hasattr(d, "empty") or not d.empty)
            for d in [df_gmv, df_cogs, df_waiter, df_ulasan, df_purchase, df_pl]
        )
        if st.button(
            "🔄 Sinkronisasi Semua Sekaligus",
            key="sync_all",
            disabled=not any_data,
            type="primary",
            use_container_width=True,
            help="Sync semua tabel yang ada file-nya sekaligus",
        ):
            results = []
            for tbl, (label, df_data) in upload_map.items():
                if df_data is None or (hasattr(df_data, "empty") and df_data.empty):
                    continue
                with st.spinner(f"Sync {label}..."):
                    from auth import get_current_user_id as _get_uid
                    ok, msg, stats = sync_dataframe_to_db(df_data, tbl, user_id=_get_uid())
                if ok:
                    results.append(
                        f"✅ **{label}**: {stats['rows_new']:,} baris "
                        f"(lama: {stats['rows_old']:,})"
                    )
                else:
                    results.append(f"❌ **{label}**: {msg}")
            for r in results:
                st.markdown(r)
            st.rerun()

        st.divider()

        # ── FLASH / HAPUS ─────────────────────────────────────────
        st.markdown(
            "<p style='font-size:12px;font-weight:700;color:#fca5a5;"
            "text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px'>"
            "⚠️ Hapus Data</p>",
            unsafe_allow_html=True,
        )
        st.caption(
            "Hapus data dari database. Data yang belum diupload ulang akan hilang. "
            "**Akun & login tidak terpengaruh.**"
        )

        # Flash per tabel
        cols_flash = st.columns(3)
        col_idx = 0
        for tbl in DATA_TABLES:
            icon, label, _ = _TABLE_LABELS[tbl]
            tbl_info = info.get(tbl, {})
            has_rows = tbl_info.get("rows", 0) > 0
            confirm_key = f"confirm_del_{tbl}"

            with cols_flash[col_idx % 3]:
                if not st.session_state.get(confirm_key):
                    if st.button(
                        f"🗑️ {label}",
                        key=f"del_btn_{tbl}",
                        disabled=not has_rows,
                        use_container_width=True,
                        help=f"Hapus {tbl_info.get('rows',0):,} baris dari {tbl}"
                             if has_rows else "Tabel sudah kosong",
                    ):
                        st.session_state[confirm_key] = True
                        st.rerun()
                else:
                    st.warning(f"Hapus **{label}**?")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ Ya", key=f"del_yes_{tbl}", use_container_width=True):
                            from auth import get_current_user_id as _get_uid
                            ok, msg = clear_table(tbl, user_id=_get_uid())
                            st.session_state.pop(confirm_key, None)
                            if ok:
                                st.success(f"🗑️ {label} dihapus.")
                            else:
                                st.error(msg)
                            st.rerun()
                    with c2:
                        if st.button("❌ Batal", key=f"del_no_{tbl}", use_container_width=True):
                            st.session_state.pop(confirm_key, None)
                            st.rerun()
            col_idx += 1

        st.markdown("<br>", unsafe_allow_html=True)

        # ── FLASH ALL — tombol paling berbahaya ───────────────────
        st.markdown(
            """<div style="background:#1c0a0a;border:1px solid #7f1d1d;
            border-radius:10px;padding:12px 16px;margin-top:4px">
            <p style="color:#fca5a5;font-weight:700;font-size:13px;margin:0 0 6px 0">
            ⚡ Flash Database — Hapus SEMUA Data Bisnis</p>
            <p style="color:#9ca3af;font-size:12px;margin:0">
            Menghapus GMV, COGS, Waiter, Ulasan, Pembelian, dan P&L sekaligus.
            Data akun & login <b>aman</b>. Tidak bisa di-undo.</p>
            </div>""",
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)

        FLASH_ALL_KEY = "confirm_flash_all_db"

        if not st.session_state.get(FLASH_ALL_KEY):
            if st.button(
                "⚡ FLASH ALL — Hapus Semua Data",
                key="flash_all_btn",
                use_container_width=True,
                help="Hapus semua data bisnis dari database. Akun tetap aman.",
            ):
                st.session_state[FLASH_ALL_KEY] = True
                st.rerun()
        else:
            st.error(
                "⚠️ **KONFIRMASI** — Semua data GMV, COGS, Waiter, Ulasan, "
                "Pembelian & P&L akan dihapus permanen dari database. Lanjutkan?"
            )
            # Ketik konfirmasi manual untuk keamanan extra
            konfirm_text = st.text_input(
                'Ketik **"HAPUS SEMUA"** untuk konfirmasi:',
                key="flash_all_confirm_text",
                placeholder="HAPUS SEMUA",
            )
            c1, c2 = st.columns(2)
            with c1:
                flash_ok = konfirm_text.strip().upper() == "HAPUS SEMUA"
                if st.button(
                    "⚡ Ya, Flash Semua",
                    key="flash_all_yes",
                    type="primary",
                    disabled=not flash_ok,
                    use_container_width=True,
                ):
                    with st.spinner("Menghapus semua data..."):
                        from auth import get_current_user_id as _get_uid
                        ok, msg, report = clear_all_data_tables(user_id=_get_uid())
                    st.session_state.pop(FLASH_ALL_KEY, None)
                    st.session_state.pop("flash_all_confirm_text", None)
                    # Clear session data juga
                    for key in ["last_upload_sig_gmv_data", "last_upload_sig_cogs_data",
                                "last_upload_sig_waiter_data", "last_upload_sig_ulasan_data",
                                "last_upload_sig_purchase_data", "last_upload_sig_pl_data"]:
                        st.session_state.pop(key, None)
                    if ok:
                        total = sum(report.values())
                        st.success(f"⚡ Flash selesai! {total:,} baris dihapus dari database.")
                    else:
                        st.error(f"❌ Gagal: {msg}")
                    st.rerun()
            with c2:
                if st.button("❌ Batal", key="flash_all_no", use_container_width=True):
                    st.session_state.pop(FLASH_ALL_KEY, None)
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Tips ──────────────────────────────────────────────────
        st.markdown(
            """<div style="background:#0d1b2e;border-left:3px solid #3b82f6;
            border-radius:0 8px 8px 0;padding:10px 14px">
            <p style="color:#93c5fd;font-size:11px;font-weight:700;margin:0 0 4px 0">
            💡 Kapan pakai apa?</p>
            <ul style="color:#6b7280;font-size:11px;margin:0;padding-left:16px;line-height:1.8">
            <li><b style="color:#6ee7b7">Sinkronisasi</b> — Upload file baru → klik Sync → data DB = file upload (aman, anti-duplikat)</li>
            <li><b style="color:#fbbf24">Hapus per tabel</b> — Bersihkan 1 tabel saja tanpa ganggu tabel lain</li>
            <li><b style="color:#fca5a5">Flash All</b> — Reset total database bisnis (mulai dari nol)</li>
            </ul>
            </div>""",
            unsafe_allow_html=True,
        )
