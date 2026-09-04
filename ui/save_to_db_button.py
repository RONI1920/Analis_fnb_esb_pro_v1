# ui/save_to_db_button.py

from __future__ import annotations
import streamlit as st

_TABLE_MAP = {
    "gmv":      ("gmv_data",      "📊 GMV / Penjualan"),
    "cogs":     ("cogs_data",     "💰 COGS"),
    "waiter":   ("waiter_data",   "🧑‍🍳 Waiter / SDM"),
    "ulasan":   ("ulasan_data",   "❤️ Ulasan"),
    "purchase": ("purchase_data", "🛒 Pembelian"),
    "pl":       ("pl_data",       "📉 Profit & Loss"),
}


def build_save_to_db_banner(uploads: dict, pkg_supports_db: bool = True):
    # Kumpulkan file yang sudah diupload tapi belum tersimpan
    unsaved = []
    for up_key, (table, label) in _TABLE_MAP.items():
        f = uploads.get(up_key)
        if f is None:
            continue
        sig = f"{f.name}_{f.size}"
        if st.session_state.get(f"saved_sig_{table}") != sig:
            unsaved.append((up_key, label, table, f))

    if not unsaved:
        return

    use_db_on = st.session_state.get("user_db_preference", False)

    # ── Toggle DB nonaktif — jangan tampilkan apapun ──
    if not use_db_on:
        return  # STOP — tidak ada notifikasi, tidak ada tombol

    # ── Paket tidak support DB ────────────────────────────────────
    if not pkg_supports_db:
        st.info(
            "⚡ Penyimpanan database memerlukan paket **Starter** ke atas. "
            "Data ditampilkan langsung dari file (mode sementara)."
        )
        return

    # ── Toggle aktif + paket support → tampilkan banner simpan ───
    st.markdown(
        """<div style="background:linear-gradient(135deg,#1c2a1c,#0d2b0d);
            border:1.5px solid #22c55e;border-radius:14px;
            padding:16px 22px;margin:12px 0 14px 0">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
                <span style="font-size:1.4rem">💾</span>
                <div>
                    <div style="font-size:14px;font-weight:800;color:#4ade80">
                        Data Siap Disimpan ke Database
                    </div>
                    <div style="font-size:11px;color:#86efac;margin-top:2px">
                        File sudah diupload. Klik tombol di bawah agar data tersimpan permanen.
                    </div>
                </div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    cols = st.columns(min(len(unsaved), 3))
    for i, (up_key, label, table, f) in enumerate(unsaved):
        with cols[i % len(cols)]:
            if st.button(
                f"💾 Simpan {label}",
                key=f"main_save_{table}",
                type="primary",
                use_container_width=True,
                help=f"Simpan {f.name} ({f.size/1024:.0f} KB) ke database",
            ):
                st.session_state[f"pending_save_{table}"] = True
                st.rerun()

    if len(unsaved) > 1:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button(
            f"💾 Simpan Semua ({len(unsaved)} file) ke Database",
            key="main_save_all",
            type="primary",
            use_container_width=True,
        ):
            for (_, __, table, ___) in unsaved:
                st.session_state[f"pending_save_{table}"] = True
            st.rerun()

    st.markdown("---")


def build_upload_status_indicator(uploads: dict, use_db: bool):
    if use_db:
        color, icon, text = "#4ade80", "🗄️", "Data dari Database (Permanen)"
    else:
        files = [lbl for k, (_, lbl) in _TABLE_MAP.items() if uploads.get(k)]
        if files:
            color, icon = "#fbbf24", "⚡"
            text = f"Data Sementara: {', '.join(files[:3])}{'...' if len(files) > 3 else ''}"
        else:
            color, icon, text = "#6b7280", "📭", "Belum ada data — upload file di sidebar"

    st.markdown(
        f"""<div style="background:{color}18;border:1px solid {color}40;
            border-radius:8px;padding:6px 14px;margin-bottom:8px;
            display:inline-flex;align-items:center;gap:8px;font-size:12px;
            color:{color};font-weight:600">{icon} {text}</div>""",
        unsafe_allow_html=True,
    )
