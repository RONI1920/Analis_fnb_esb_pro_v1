# ui/register.py — Form Registrasi Akun Baru (Trial / Berbayar)

from __future__ import annotations

import streamlit as st
from packages import PACKAGE_DEFINITIONS, format_price


_REG_CSS = """
<style>
.reg-wrap {
    max-width: 520px;
    margin: 0 auto;
}
.reg-header {
    text-align: center;
    padding: 32px 0 24px;
}
.reg-header h2 {
    font-size: 1.8rem;
    font-weight: 800;
    color: #f0f2f5;
    margin: 0 0 8px;
}
.reg-header p {
    color: #9ca3af;
    font-size: 0.9rem;
}
.reg-pkg-banner {
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border: 1px solid;
}
.reg-pkg-name {
    font-size: 1.1rem;
    font-weight: 700;
}
.reg-pkg-price {
    font-size: 0.9rem;
    opacity: .8;
}
</style>
"""


def build_register_page(selected_package_key: str) -> dict | None:
    try:
        from database import get_packages_merged
        _pkg_data = get_packages_merged()
        cfg = _pkg_data.get(selected_package_key, PACKAGE_DEFINITIONS.get(selected_package_key, PACKAGE_DEFINITIONS["free"]))
    except Exception:
        cfg = PACKAGE_DEFINITIONS.get(selected_package_key, PACKAGE_DEFINITIONS["free"])
    is_free = selected_package_key == "free"

    st.markdown(_REG_CSS, unsafe_allow_html=True)

    # ── Header ────────────────────────────────────────────────────
    icon = "🎉" if is_free else "📝"
    title = "Daftar Akun Trial Gratis" if is_free else f"Daftar — {cfg['name']}"
    st.markdown(f"""
    <div class="reg-header">
        <h2>{icon} {title}</h2>
        <p>{"Nikmati akses 30 hari tanpa biaya, tanpa kartu kredit." if is_free
            else "Isi data di bawah, lalu lanjut ke pembayaran."}</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Paket banner ──────────────────────────────────────────────
    price_str = "GRATIS" if is_free else f"{format_price(cfg['price_monthly'])}/bulan"
    st.markdown(f"""
    <div class="reg-pkg-banner" style="border-color:{cfg['color']};background:{cfg.get('badge_color','#1a1f2e')}20">
        <div>
            <div class="reg-pkg-name" style="color:{cfg['color']}">{cfg['name']}</div>
            <div class="reg-pkg-price" style="color:{cfg['color']}">{cfg['description']}</div>
        </div>
        <div style="font-size:1.2rem;font-weight:800;color:{cfg['color']}">{price_str}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Form ─────────────────────────────────────────────────────
    with st.form("form_register", clear_on_submit=False):
        col1, col2 = st.columns(2)

        with col1:
            username = st.text_input(
                "Username *",
                placeholder="contoh: warung_budi",
                help="Hanya huruf kecil, angka, dan underscore"
            )
            email = st.text_input("Email *", placeholder="email@bisnis.com")
            full_name = st.text_input("Nama Lengkap *", placeholder="Budi Santoso")

        with col2:
            phone = st.text_input("No. HP / WhatsApp", placeholder="08123456789")
            company = st.text_input("Nama Restoran / Bisnis", placeholder="Warung Makan Budi")
            password = st.text_input("Password *", type="password", placeholder="minimal 6 karakter")

        confirm_password = st.text_input(
            "Konfirmasi Password *",
            type="password",
            placeholder="ulangi password"
        )

        agree = st.checkbox("Saya menyetujui syarat & ketentuan layanan")

        st.markdown("<br>", unsafe_allow_html=True)

        btn_label = "🚀 Buat Akun Trial Gratis" if is_free else "➡️ Lanjut ke Pembayaran"
        submitted = st.form_submit_button(btn_label, type="primary", use_container_width=True)

    # ── Validasi ──────────────────────────────────────────────────
    if submitted:
        errors = []

        import re
        if not username:
            errors.append("Username wajib diisi.")
        elif not re.match(r'^[a-z0-9_]{3,30}$', username.strip().lower()):
            errors.append("Username hanya boleh huruf kecil, angka, dan underscore (3–30 karakter).")

        if not email or "@" not in email:
            errors.append("Email tidak valid.")
        if not full_name:
            errors.append("Nama lengkap wajib diisi.")
        import re
        pw_errors = []
        if not password or len(password) < 8:
            pw_errors.append('minimal 8 karakter')
        if not re.search(r'[A-Z]', password or ''):
            pw_errors.append('minimal 1 huruf kapital')
        if not re.search(r'[0-9]', password or ''):
            pw_errors.append('minimal 1 angka')
        if pw_errors:
            errors.append('Password harus: ' + ', '.join(pw_errors) + '.')
        if False:  # placeholder agar blok lama tidak error
            errors.append("Password minimal 6 karakter.")
        if password != confirm_password:
            errors.append("Password dan konfirmasi password tidak cocok.")
        if not agree:
            errors.append("Anda harus menyetujui syarat & ketentuan.")

        if errors:
            for e in errors:
                st.error(e)
            return None

        return {
            "username": username.strip().lower(),
            "email": email.strip().lower(),
            "full_name": full_name.strip(),
            "phone": phone.strip(),
            "company": company.strip(),
            "password": password,
            "package_key": selected_package_key,
        }
        
    # ── Tombol kembali ────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    col_x, col_y, col_z = st.columns([1, 2, 1])
    with col_y:
        if st.button("← Kembali ke Pilihan Paket", use_container_width=True):
            st.session_state["auth_page"] = "pricing"
            st.session_state.pop("selected_package", None)
            st.rerun()

    # ── Sudah punya akun? Login ───────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        st.markdown(
            "<p style='text-align:center; color:#9ca3af; font-size:0.88rem;'>Sudah punya akun?</p>",
            unsafe_allow_html=True,
        )
        if st.button("🔐 Login di sini", use_container_width=True):
            st.session_state["auth_page"] = "login"
            st.session_state.pop("selected_package", None)
            st.rerun()

    return None