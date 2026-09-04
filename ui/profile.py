# ui/profile.py — Halaman Profil User & Admin

import streamlit as st
from database import (
    get_user_by_username,
    get_active_license,
    get_all_payments,
    update_user,
    update_user_password,
    verify_password,
    write_audit_log,
)
from auth import get_current_username, get_current_role, get_current_full_name
from packages import get_package_config


_CSS = """
<style>
.prof-card {
    background: #0f1420;
    border: 1px solid #2d3348;
    border-radius: 14px;
    padding: 28px 24px;
    margin-bottom: 16px;
}
.prof-avatar {
    width: 72px; height: 72px;
    background: linear-gradient(135deg, #1d4ed8, #7c3aed);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 2rem; margin: 0 auto 12px;
    text-align: center;
}
.prof-name {
    font-size: 1.4rem; font-weight: 800;
    color: #f0f2f5; text-align: center; margin-bottom: 4px;
}
.prof-role {
    font-size: 0.82rem; text-align: center;
    color: #6b7280; margin-bottom: 16px;
}
.prof-badge {
    display: inline-block;
    padding: 3px 10px; border-radius: 20px;
    font-size: 11px; font-weight: 700;
    margin: 2px;
}
.prof-field { margin-bottom: 12px; }
.prof-label {
    font-size: 11px; font-weight: 700;
    color: #6b7280; text-transform: uppercase;
    letter-spacing: .07em; margin-bottom: 3px;
}
.prof-value { font-size: 0.95rem; color: #e5e7eb; }
</style>
"""


def _field(label: str, value: str, icon: str = ""):
    val = value if value and str(value).strip() and value != "None" else "—"
    st.markdown(
        f"""<div class="prof-field">
            <div class="prof-label">{icon} {label}</div>
            <div class="prof-value">{val}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def build_profile_page():
    """Halaman profil lengkap — user & admin bisa akses."""
    st.markdown(_CSS, unsafe_allow_html=True)

    username = get_current_username()
    role     = get_current_role()
    user     = get_user_by_username(username)

    if not user:
        st.error("Gagal memuat data profil.")
        return

    # ── Avatar & nama ─────────────────────────────────────────────
    full_name = user.get("full_name") or username
    initials  = "".join([w[0].upper() for w in full_name.split()[:2]])

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown(
            f"""<div class="prof-card">
                <div class="prof-avatar">{initials}</div>
                <div class="prof-name">{full_name}</div>
                <div class="prof-role">@{username} · {"Administrator" if role == "admin" else "User"}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabs ─────────────────────────────────────────────────────
    if role == "admin":
        tab_info, tab_pw = st.tabs(["📋 Informasi Akun", "🔒 Ganti Password"])
    else:
        tab_info, tab_lic, tab_pay, tab_pw = st.tabs([
            "📋 Informasi Akun",
            "🎫 Lisensi & Paket",
            "💳 Riwayat Pembayaran",
            "🔒 Ganti Password",
        ])

    # ────────────────────────────────────────────────────────────
    # TAB 1 — INFORMASI AKUN
    # ────────────────────────────────────────────────────────────
    with tab_info:
        c1, c2 = st.columns(2)

        with c1:
            st.markdown("#### 👤 Data Diri")
            with st.form("form_update_profile"):
                new_name  = st.text_input("Nama Lengkap", value=user.get("full_name") or "")
                new_email = st.text_input("Email", value=user.get("email") or "")
                new_phone = st.text_input("No. HP", value=user.get("phone") or "")
                new_co    = st.text_input("Perusahaan / Nama Warung",
                                           value=user.get("company") or "")

                if st.form_submit_button("💾 Simpan Perubahan", type="primary",
                                         use_container_width=True):
                    ok, msg = update_user(
                        user["id"],
                        full_name=new_name.strip(),
                        email=new_email.strip().lower(),
                        phone=new_phone.strip(),
                        company=new_co.strip(),
                    )
                    if ok:
                        write_audit_log(username, "update_profile", role=role,
                                        target_type="user", target_id=username)
                        st.success("✅ Profil diperbarui!")
                        st.rerun()
                    else:
                        st.error(f"Gagal: {msg}")

        with c2:
            st.markdown("#### 🔍 Info Akun")
            _field("Username",   username,                            "🔑")
            _field("Role",       "Administrator" if role == "admin" else "User", "🛡️")
            _field("Status",     "Aktif" if user.get("is_active") else "Nonaktif", "🟢")
            _field("Bergabung",  (user.get("created_at") or "")[:10], "📅")
            _field("Login Terakhir", (user.get("last_login") or "")[:16], "🕐")
            if user.get("notes"):
                _field("Catatan", user["notes"], "📝")

    # ────────────────────────────────────────────────────────────
    # TAB 2 — LISENSI & PAKET (user only)
    # ────────────────────────────────────────────────────────────
    if role != "admin":
        with tab_lic:
            lic = get_active_license(user["id"])

            if not lic:
                st.warning("⚠️ Tidak ada lisensi aktif.")
                st.info("Hubungi admin atau upgrade paket Anda.")
            else:
                from datetime import date
                pkg_key  = lic.get("package_key", "free")
                pkg_cfg  = get_package_config(pkg_key)
                end_date = lic.get("end_date", "")

                # Hitung sisa hari
                try:
                    sisa = (date.fromisoformat(str(end_date)) - date.today()).days
                    sisa_str = f"{sisa} hari lagi"
                    sisa_color = "#ef4444" if sisa <= 7 else "#f59e0b" if sisa <= 30 else "#34d399"
                except Exception:
                    sisa_str, sisa_color = "—", "#6b7280"

                # Card lisensi
                st.markdown(
                    f"""<div style="background:linear-gradient(135deg,{pkg_cfg.get('badge_color','#1a1f2e')},#0f1420);
                        border:1px solid {pkg_cfg.get('color','#374151')}44;border-radius:12px;
                        padding:24px;margin-bottom:16px">
                        <div style="font-size:1.4rem;font-weight:800;color:{pkg_cfg.get('color','#f0f2f5')}">
                            {pkg_cfg.get('name','?')}
                        </div>
                        <div style="color:#9ca3af;font-size:0.85rem;margin-top:4px">
                            {pkg_cfg.get('description','')}
                        </div>
                        <div style="margin-top:16px;display:flex;gap:20px;flex-wrap:wrap">
                            <div>
                                <div style="font-size:10px;color:#6b7280;text-transform:uppercase">Status</div>
                                <div style="font-weight:700;color:#34d399">{lic.get('status','').title()}</div>
                            </div>
                            <div>
                                <div style="font-size:10px;color:#6b7280;text-transform:uppercase">Berlaku Hingga</div>
                                <div style="font-weight:700;color:#f0f2f5">{str(end_date)[:10]}</div>
                            </div>
                            <div>
                                <div style="font-size:10px;color:#6b7280;text-transform:uppercase">Sisa</div>
                                <div style="font-weight:700;color:{sisa_color}">{sisa_str}</div>
                            </div>
                            <div>
                                <div style="font-size:10px;color:#6b7280;text-transform:uppercase">Billing</div>
                                <div style="font-weight:700;color:#f0f2f5">{lic.get('billing_cycle','').title()}</div>
                            </div>
                        </div>
                    </div>""",
                    unsafe_allow_html=True,
                )

                # Daftar fitur / tab yang bisa diakses
                from packages import get_allowed_tabs
                from database import get_package_tab_access
                db_overrides = get_package_tab_access(pkg_key)
                allowed = get_allowed_tabs(pkg_key, db_overrides if db_overrides else None)

                st.markdown(f"**Fitur yang dapat diakses ({len(allowed)} tab):**")
                cols = st.columns(3)
                for i, tab in enumerate(allowed):
                    with cols[i % 3]:
                        st.markdown(f"✅ {tab}")

                if sisa <= 30:
                    st.divider()
                    st.warning(
                        f"⏰ Lisensi Anda berakhir dalam **{sisa_str}**. "
                        f"Hubungi admin untuk perpanjangan."
                    )

    # ────────────────────────────────────────────────────────────
    # TAB 3 — RIWAYAT PEMBAYARAN (user only)
    # ────────────────────────────────────────────────────────────
    if role != "admin":
        with tab_pay:
            all_pays = get_all_payments()
            my_pays  = [p for p in all_pays if p.get("user_id") == user["id"]]

            if not my_pays:
                st.info("Belum ada riwayat pembayaran.")
            else:
                import pandas as pd
                df = pd.DataFrame([{
                    "Tanggal" : (p.get("created_at") or "")[:10],
                    "Jumlah"  : f"Rp {p['amount']:,}".replace(",", "."),
                    "Metode"  : p.get("method") or "—",
                    "Periode" : p.get("period_label") or "—",
                    "Status"  : p.get("status", "—").title(),
                    "Dikonfirmasi": p.get("confirmed_by") or "—",
                } for p in my_pays])
                st.dataframe(df, use_container_width=True, hide_index=True)

    # ────────────────────────────────────────────────────────────
    # TAB GANTI PASSWORD
    # ────────────────────────────────────────────────────────────
    pw_tab = tab_pw
    with pw_tab:
        st.markdown("#### 🔒 Ganti Password")
        st.caption("Password baru minimal 8 karakter, mengandung huruf kapital dan angka.")

        with st.form("form_change_password"):
            pw_old = st.text_input("Password Lama", type="password")
            pw_new = st.text_input("Password Baru", type="password")
            pw_cfm = st.text_input("Konfirmasi Password Baru", type="password")

            if st.form_submit_button("🔒 Simpan Password Baru", type="primary",
                                     use_container_width=True):
                import re as _re
                if not pw_old or not pw_new:
                    st.error("Semua field wajib diisi.")
                elif not verify_password(pw_old, user["password_hash"]):
                    st.error("❌ Password lama salah.")
                elif len(pw_new) < 8 or not _re.search(r'[A-Z]', pw_new) \
                        or not _re.search(r'[0-9]', pw_new):
                    st.error("Password baru harus minimal 8 karakter, "
                              "mengandung huruf kapital dan angka.")
                elif pw_new != pw_cfm:
                    st.error("Konfirmasi password tidak cocok.")
                else:
                    ok, msg = update_user_password(user["id"], pw_new)
                    if ok:
                        write_audit_log(username, "change_password", role=role,
                                        target_type="user", target_id=username)
                        # ── Notifikasi sukses 5 detik (dismissible) ────────
                        notif_pw = st.empty()
                        notif_pw.success("✅ Password berhasil diubah!")
                        st.markdown(
                            """<script>
                            setTimeout(function() {
                                var alerts = window.parent.document.querySelectorAll(
                                    '[data-testid="stAlert"]'
                                );
                                alerts.forEach(function(el) { el.style.display = 'none'; });
                            }, 5000);
                            </script>""",
                            unsafe_allow_html=True,
                        )
                        # ── Kirim notifikasi email + WA ────────────────────
                        try:
                            from services.notifier import notify_password_changed, show_wa_button
                            user_email = user.get("email")
                            full = user.get("full_name") or username
                            wa_msg = notify_password_changed(user_email, username, full)
                            show_wa_button(wa_msg, label="Kirim Notif Password ke WhatsApp")
                        except Exception:
                            pass
                    else:
                        st.error(f"Gagal: {msg}")
