# ui/forgot_password.py — Halaman Lupa Password & Lupa Username

import os
import streamlit as st
from database import (
    get_user_by_username,
    find_user_by_email_or_phone,
    generate_reset_token,
    set_reset_token,
    verify_reset_token,
    clear_reset_token,
    update_user_password,
)

_CSS = """
<style>
.fp-card {
    background: #0f1420;
    border: 1px solid #2d3348;
    border-radius: 16px;
    padding: 36px 32px;
    max-width: 440px;
    margin: 0 auto;
}
.fp-title { font-size:1.3rem; font-weight:800; color:#f0f2f5; margin-bottom:6px; }
.fp-sub   { font-size:0.88rem; color:#9ca3af; margin-bottom:24px; line-height:1.5; }
.fp-token-box {
    background:#1a1f2e; border:1px solid #374151;
    border-radius:8px; padding:14px 18px;
    font-size:1.6rem; font-weight:700; letter-spacing:.25em;
    color:#34d399; text-align:center; margin:16px 0;
}
.fp-hint { font-size:0.8rem; color:#6b7280; text-align:center; }
</style>
"""


def _mask_email(email: str) -> str:
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    return local[:2] + "***@" + domain


def _mask_phone(phone: str) -> str:
    if not phone or len(phone) < 6:
        return "***"
    return phone[:3] + "****" + phone[-2:]


def build_forgot_password_page():
    """
    Flow lupa password:
    Step 1 → masukkan username
    Step 2 → tampilkan token (simulasi kirim kode)
    Step 3 → verifikasi token → set password baru
    """
    st.markdown(_CSS, unsafe_allow_html=True)

    step = st.session_state.get("fp_step", 1)

    # ── Header ───────────────────────────────────────────────────
    if st.button("← Kembali ke Login", key="fp_back"):
        _reset_flow()
        st.session_state["auth_page"] = "login"
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2, 1])
    with col:
        # ─────────────────────────────────────────────
        # STEP 1 — Input username
        # ─────────────────────────────────────────────
        if step == 1:
            st.markdown("""
            <div class="fp-card">
                <div class="fp-title">🔑 Lupa Password</div>
                <div class="fp-sub">Masukkan username akun Anda. Kami akan membuat kode verifikasi reset password.</div>
            </div>""", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            with st.form("fp_step1"):
                username = st.text_input("Username", placeholder="username Anda")
                submitted = st.form_submit_button("Kirim Kode Verifikasi", type="primary", use_container_width=True)

            if submitted:
                if not username.strip():
                    st.error("Username wajib diisi.")
                else:
                    user = get_user_by_username(username.strip().lower())
                    if not user:
                        st.error("Username tidak ditemukan.")
                    else:
                        token = generate_reset_token()
                        set_reset_token(user["id"], token, expiry_minutes=15)
                        st.session_state["fp_username"] = user["username"]
                        st.session_state["fp_user_email"] = user.get("email", "")

                        # Kirim token ke email user (jika email & SMTP dikonfigurasi)
                        user_email = user.get("email", "")
                        if user_email:
                            try:
                                from services.notifier import send_email_notification, _email_template
                                subject = "🔑 Kode Reset Password — FnB Analyst"
                                body = f"""
                                <p>Halo <b>{user.get('full_name') or user.get('username','')}</b>,</p>
                                <p>Kode verifikasi reset password Anda adalah:</p>
                                <div style="background:#1a1f2e;border:1px solid #374151;border-radius:8px;
                                            padding:20px;text-align:center;margin:16px 0">
                                    <span style="font-size:2rem;font-weight:700;letter-spacing:.3em;color:#34d399">{token}</span>
                                </div>
                                <p style="color:#9ca3af;font-size:0.85rem">
                                    Kode berlaku <b style="color:#f0f2f5">15 menit</b>.<br>
                                    Jika Anda tidak meminta reset password, abaikan email ini.
                                </p>
                                """
                                send_email_notification(user_email, subject, _email_template("Reset Password 🔑", body))
                            except Exception:
                                pass  # Email opsional — flow tetap berjalan meski SMTP belum dikonfigurasi

                        # DEV fallback: simpan token di session agar bisa dilihat di UI dev mode
                        if os.environ.get("FNB_ENV", "production").lower() == "development":
                            st.session_state["fp_debug_token"] = token

                        st.session_state["fp_step"] = 2
                        st.rerun()

        # ─────────────────────────────────────────────
        # STEP 2 — Tampilkan token & input verifikasi
        # ─────────────────────────────────────────────
        elif step == 2:
            username   = st.session_state.get("fp_username", "")
            email_raw  = st.session_state.get("fp_user_email", "")
            dev_token  = st.session_state.get("fp_debug_token", "")

            st.markdown(f"""
            <div class="fp-card">
                <div class="fp-title">📩 Kode Verifikasi</div>
                <div class="fp-sub">
                    Kode reset dikirim ke <b>{_mask_email(email_raw)}</b>.<br>
                    Kode berlaku <b>15 menit</b>.
                </div>
            </div>""", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            # DEV MODE hanya aktif jika env FNB_ENV=development
            if dev_token and os.environ.get("FNB_ENV", "production").lower() == "development":
                st.info(f"🛠️ **Dev mode** — Kode reset: `{dev_token}`")

            with st.form("fp_step2"):
                kode = st.text_input("Masukkan Kode 6 Digit", placeholder="123456", max_chars=6)
                submitted = st.form_submit_button("Verifikasi Kode", type="primary", use_container_width=True)

            if submitted:
                ok, msg, user = verify_reset_token(username, kode.strip())
                if ok:
                    st.session_state["fp_verified_user"] = user
                    st.session_state["fp_step"] = 3
                    st.rerun()
                else:
                    st.error(msg)

            if st.button("Kirim ulang kode", key="fp_resend"):
                user = get_user_by_username(username)
                if user:
                    new_token = generate_reset_token()
                    set_reset_token(user["id"], new_token, expiry_minutes=15)
                    if os.environ.get("FNB_ENV","production").lower() == "development":
                        st.session_state["fp_debug_token"] = new_token
                    st.success("Kode baru sudah dikirim.")
                    st.rerun()

        # ─────────────────────────────────────────────
        # STEP 3 — Set password baru
        # ─────────────────────────────────────────────
        elif step == 3:
            user = st.session_state.get("fp_verified_user", {})
            st.markdown(f"""
            <div class="fp-card">
                <div class="fp-title">🔒 Buat Password Baru</div>
                <div class="fp-sub">Halo <b>{user.get('full_name') or user.get('username','')}</b>, buat password baru untuk akun Anda.</div>
            </div>""", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            with st.form("fp_step3"):
                pw1 = st.text_input("Password Baru", type="password")
                pw2 = st.text_input("Konfirmasi Password Baru", type="password")
                submitted = st.form_submit_button("Simpan Password Baru", type="primary", use_container_width=True)

            if submitted:
                import re
                pw_ok = len(pw1) >= 8 and re.search(r'[A-Z]', pw1) and re.search(r'[0-9]', pw1)
                if not pw_ok:
                    st.error("Password minimal 8 karakter, mengandung huruf kapital dan angka.")
                elif pw1 != pw2:
                    st.error("Password tidak cocok.")
                else:
                    ok, msg = update_user_password(user["id"], pw1)
                    if ok:
                        clear_reset_token(user["id"])
                        # Kirim notifikasi email konfirmasi ganti password
                        user_email = st.session_state.get("fp_user_email", "")
                        if user_email:
                            try:
                                from services.notifier import notify_password_changed, show_wa_button
                                wa_msg = notify_password_changed(
                                    to_email=user_email,
                                    username=user.get("username", ""),
                                    full_name=user.get("full_name") or user.get("username", ""),
                                )
                                show_wa_button(wa_msg, label="Kirim Konfirmasi ke WhatsApp")
                            except Exception:
                                pass
                        st.success("✅ Password berhasil diubah! Silakan login dengan password baru.")
                        _reset_flow()
                        st.session_state["auth_page"] = "login"
                        st.rerun()
                    else:
                        st.error(f"Gagal: {msg}")


def build_forgot_username_page():
    """
    Flow lupa username:
    Masukkan email atau nomor HP → tampilkan username yang terdaftar (di-mask sebagian).
    """
    st.markdown(_CSS, unsafe_allow_html=True)

    if st.button("← Kembali ke Login", key="fu_back"):
        st.session_state["auth_page"] = "login"
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("""
        <div class="fp-card">
            <div class="fp-title">👤 Lupa Username</div>
            <div class="fp-sub">Masukkan email atau nomor HP yang terdaftar. Kami akan menampilkan username Anda.</div>
        </div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        with st.form("fu_form"):
            query = st.text_input("Email atau No. HP", placeholder="email@bisnis.com atau 08xxx")
            submitted = st.form_submit_button("Cari Username", type="primary", use_container_width=True)

        if submitted:
            if not query.strip():
                st.error("Wajib diisi.")
            else:
                results = find_user_by_email_or_phone(query.strip())
                if not results:
                    st.error("Tidak ada akun yang terdaftar dengan email/HP tersebut.")
                else:
                    st.success(f"Ditemukan **{len(results)}** akun:")
                    for u in results:
                        # Tampilkan username sebagian (privacy)
                        uname = u["username"]
                        masked = uname[:2] + "*" * max(0, len(uname) - 3) + uname[-1:]
                        email_hint = _mask_email(u.get("email",""))
                        phone_hint = _mask_phone(u.get("phone",""))
                        st.info(
                            f"👤 Username: **`{masked}`**\n\n"
                            f"📧 {email_hint}  |  📱 {phone_hint}"
                        )
                    st.caption("Hubungi admin jika membutuhkan bantuan lebih lanjut.")


def _reset_flow():
    for k in ["fp_step", "fp_username", "fp_user_email", "fp_debug_token", "fp_verified_user"]:
        st.session_state.pop(k, None)
