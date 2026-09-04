# admin_app.py — Entry Point ADMIN PANEL (Terisolasi)
#
# ═══════════════════════════════════════════════════════════════════
#  CARA MENJALANKAN:
#    streamlit run admin_app.py --server.port 8502
#
#  INSTALL DEPENDENCY (wajib, jika belum):
#    pip install streamlit-cookies-controller
#
#  KEAMANAN:
#    - Jangan expose port 8502 ke publik. Hanya bisa diakses via:
#        a) localhost saja  → jalankan dengan --server.address localhost
#        b) VPN / SSH tunnel → akses dari mesin admin saja
#        c) Reverse proxy (nginx) dengan IP whitelist
#
#  CONTOH PALING AMAN:
#    streamlit run admin_app.py \
#        --server.port 8502 \
#        --server.address localhost \
#        --server.headless true
#
#  Kemudian akses via SSH tunnel dari laptop admin:
#    ssh -L 8502:localhost:8502 user@server_ip
#    Buka di browser: http://localhost:8502
# ═══════════════════════════════════════════════════════════════════

import os
import sys
import ipaddress

import streamlit as st

# ── Tambahkan root project ke sys.path ──────────────────────────────
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from auth import (
    require_auth,
    is_admin,
    get_current_full_name,
    get_current_username,
    clear_session,
)
from admin_panel import build_admin_panel
from database import init_db

# ── Konfigurasi halaman ──────────────────────────────────────────────
st.set_page_config(
    page_title="FnB Analytics Admin Login",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── LAPISAN KEAMANAN 1: IP Whitelist ────────────────────────────────
ALLOWED_IPS: list[str] = [
    # "127.0.0.1",
    # "192.168.1.0/24",
    # "203.0.113.10",
]


def _check_ip_whitelist() -> None:
    if not ALLOWED_IPS:
        return

    headers = st.context.headers if hasattr(st, "context") else {}
    client_ip_str = (
        headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or headers.get("X-Real-IP", "")
        or "127.0.0.1"
    )

    try:
        client_ip = ipaddress.ip_address(client_ip_str)
    except ValueError:
        _block_access(f"IP tidak valid: {client_ip_str}")
        return

    for allowed in ALLOWED_IPS:
        try:
            if "/" in allowed:
                if client_ip in ipaddress.ip_network(allowed, strict=False):
                    return
            else:
                if client_ip == ipaddress.ip_address(allowed):
                    return
        except ValueError:
            continue

    _block_access(f"Akses ditolak dari IP: {client_ip_str}")


def _block_access(reason: str) -> None:
    st.error(f"🚫 {reason}")
    st.warning("Halaman ini hanya dapat diakses dari jaringan yang diizinkan.")
    st.stop()


# ── LAPISAN KEAMANAN 2: Harus login sebagai admin ───────────────────
def _require_admin() -> None:
    """
    skip_pricing=True → langsung ke form login, tanpa halaman pricing.
    Setelah login, cek role harus admin.
    """
    require_auth(skip_pricing=True)  # ← langsung login, skip pricing

    if not is_admin():
        st.error("🚫 Akses Ditolak")
        st.warning(
            f"Halaman Admin Panel hanya dapat diakses oleh **Administrator**.\n\n"
            f"Anda login sebagai: `{get_current_username()}` (bukan admin)."
        )
        st.info("Silakan hubungi administrator jika Anda membutuhkan akses ini.")
        if st.button("🚪 Logout"):
            clear_session()
            st.rerun()
        st.stop()


# ── Header admin ─────────────────────────────────────────────────────
def _render_admin_header() -> None:
    name = get_current_full_name()
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #1a1f2e 0%, #0d1117 100%);
            border: 1px solid #f59e0b55;
            border-left: 4px solid #f59e0b;
            border-radius: 8px;
            padding: 12px 20px;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 12px;
        ">
            <span style="font-size:24px;">🛡️</span>
            <div>
                <div style="color:#f59e0b; font-weight:700; font-size:13px;
                            text-transform:uppercase; letter-spacing:.08em;">
                    Admin Panel Terisolasi
                </div>
                <div style="color:#8892a4; font-size:12px; margin-top:2px;">
                    Login sebagai <strong style="color:#f0f2f5;">{name}</strong>
                    &nbsp;·&nbsp; Semua tindakan dicatat di audit log
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Tombol logout di sidebar
    with st.sidebar:
        st.markdown(f"**👤 {name}**")
        st.caption(f"`{get_current_username()}` · admin")
        st.divider()
        if st.button("👤 Profil Saya", use_container_width=True, key="admin_profile"):
            st.session_state["admin_show_profile"] = True
            st.rerun()
        if st.button("🚪 Logout", use_container_width=True, type="secondary"):
            clear_session()
            st.rerun()


# ── MAIN ─────────────────────────────────────────────────────────────
def main() -> None:
    init_db()

    _check_ip_whitelist()  # 1. IP check (opsional)
    _require_admin()       # 2. Cookie restore / login form / role check

    _render_admin_header()

    if st.session_state.get("admin_show_profile"):
        from ui.profile import build_profile_page
        if st.button("← Kembali ke Admin Panel", key="back_admin_profile"):
            st.session_state["admin_show_profile"] = False
            st.rerun()
        build_profile_page()
        return

    build_admin_panel()


if __name__ == "__main__":
    main()