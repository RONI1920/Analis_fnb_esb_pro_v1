# admin_panel.py — Dashboard Admin Modern

from __future__ import annotations
from ui.admin_notifications_tab import build_notifications_tab, count_unread_notifications

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from auth import (
    get_current_username,
    get_current_full_name,
    is_admin,
    clear_session,
    write_audit_log,
)
from database import (
    get_all_users,
    create_user,
    update_user,
    update_user_password,
    generate_temp_password,
    get_all_licenses,
    create_license,
    update_license,
    get_expiring_soon,
    get_all_payments,
    get_all_payments_with_proof,
    create_payment,
    confirm_payment,
    reject_payment,
    get_payment_proof,
    save_payment_proof,
    get_all_packages_from_db,
    update_package_in_db,
    get_admin_dashboard_stats,
    get_audit_log,
    get_users_full,
    bulk_update_license_status,
    bulk_update_package,
)
from packages import (
    PACKAGE_DEFINITIONS,
    PACKAGE_ORDER,
    ALL_TABS,
    format_price,
    get_allowed_tabs,
)

_ADMIN_CSS = """
<style>
.ap-metric {
    background: #1a1f2e;
    border: 1px solid #2d3348;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 8px;
}
.ap-metric .label {
    font-size: 12px;
    color: #8892a4;
    text-transform: uppercase;
    letter-spacing: .08em;
    margin-bottom: 6px;
}
.ap-metric .value {
    font-size: 28px;
    font-weight: 700;
    color: #f0f2f5;
    line-height: 1;
}
.ap-metric .sub {
    font-size: 12px;
    color: #64d68a;
    margin-top: 4px;
}
.ap-metric .sub.warn { color: #f59e0b; }
.ap-metric .sub.danger { color: #f87171; }
.ap-section {
    font-size: 13px;
    font-weight: 600;
    color: #8892a4;
    text-transform: uppercase;
    letter-spacing: .1em;
    padding: 4px 0 12px;
    border-bottom: 1px solid #2d3348;
    margin-bottom: 20px;
}
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: .04em;
}
.badge-active   { background:#064e3b; color:#6ee7b7; }
.badge-trial    { background:#1e3a5f; color:#93c5fd; }
.badge-expired  { background:#451a1a; color:#fca5a5; }
.badge-suspended{ background:#3d2900; color:#fcd34d; }
.badge-pending  { background:#3d2900; color:#fcd34d; }
.badge-confirmed{ background:#064e3b; color:#6ee7b7; }
.badge-rejected { background:#451a1a; color:#fca5a5; }
.badge-admin    { background:#3b0764; color:#d8b4fe; }
.badge-user     { background:#1e3a5f; color:#93c5fd; }
.ap-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #0f1420;
    border: 1px solid #2d3348;
    border-radius: 12px;
    padding: 14px 20px;
    margin-bottom: 24px;
}
.ap-topbar .title { font-size: 18px; font-weight: 700; color: #f0f2f5; }
.ap-topbar .user  { font-size: 13px; color: #8892a4; }
.pkg-card {
    border: 1px solid #2d3348;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 12px;
    background: #131929;
}
.pkg-card .pkg-name  { font-size: 16px; font-weight: 700; color: #f0f2f5; margin-bottom: 4px; }
.pkg-card .pkg-price { font-size: 22px; font-weight: 700; margin-bottom: 8px; }
.pkg-card .pkg-tabs  { font-size: 12px; color: #8892a4; }
</style>
"""


def _badge(text: str, kind: str) -> str:
    return f'<span class="badge badge-{kind}">{text}</span>'


def _metric_card(label: str, value: str, sub: str = "", sub_class: str = "") -> None:
    st.markdown(
        f"""<div class="ap-metric">
            <div class="label">{label}</div>
            <div class="value">{value}</div>
            {"" if not sub else f'<div class="sub {sub_class}">{sub}</div>'}
        </div>""",
        unsafe_allow_html=True,
    )


def _section(title: str) -> None:
    st.markdown(f'<div class="ap-section">{title}</div>', unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────
# TAB: OVERVIEW
# ──────────────────────────────────────────────────────────────────

def _tab_overview() -> None:
    stats = get_admin_dashboard_stats()

    _section("Ringkasan hari ini")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _metric_card("Total User", str(stats.get("total_users", 0)),
                     f"{stats.get('active_users', 0)} aktif", "")
    with c2:
        _metric_card("Lisensi Aktif", str(stats.get("active_licenses", 0)),
                     f"{stats.get('expired_licenses', 0)} expired", "warn")
    with c3:
        exp_soon = stats.get("expiring_soon", 0)
        _metric_card("Hampir Expired", str(exp_soon),
                     "dalam 7 hari" if exp_soon == 0 else f"⚠️ {exp_soon} user perlu renewal",
                     "warn" if exp_soon > 0 else "")
    with c4:
        pending = stats.get("pending_payments", 0)
        _metric_card("Pembayaran Pending", str(pending),
                     "perlu dikonfirmasi" if pending > 0 else "semua bersih",
                     "warn" if pending > 0 else "")

    st.markdown("<br>", unsafe_allow_html=True)
    _section("Revenue bulan ini")

    rev        = stats.get("revenue_this_month", 0)
    rev_by_pkg = stats.get("revenue_by_package", {})

    c1, c2 = st.columns([1, 2])
    with c1:
        _metric_card("Total Revenue", f"Rp {rev:,}".replace(",", "."), "pembayaran terkonfirmasi")
    with c2:
        if rev_by_pkg:
            df_rev = pd.DataFrame([{"Paket": k.title(), "Revenue": v} for k, v in rev_by_pkg.items()])
            st.dataframe(df_rev, use_container_width=True, hide_index=True)
        else:
            st.info("Belum ada pembayaran terkonfirmasi bulan ini.")

    expiring = get_expiring_soon(days=7)
    if expiring:
        st.markdown("<br>", unsafe_allow_html=True)
        _section(f"⚠️ {len(expiring)} User Hampir Expired (≤7 hari)")
        df_exp = pd.DataFrame([{
            "Username": r["username"],
            "Nama"    : r.get("full_name") or "-",
            "Email"   : r["email"],
            "Paket"   : r["package_key"].title(),
            "Expired" : r["end_date"],
        } for r in expiring])
        st.dataframe(df_exp, use_container_width=True, hide_index=True)


# ──────────────────────────────────────────────────────────────────
# TAB: USER
# ──────────────────────────────────────────────────────────────────

def _tab_users() -> None:
    _section("Daftar User")

    users = get_all_users()

    q = st.text_input("🔍 Cari username / email / nama", placeholder="ketik untuk filter...")
    if q:
        q_low = q.lower()
        users = [u for u in users if
                 q_low in (u.get("username") or "").lower() or
                 q_low in (u.get("email") or "").lower() or
                 q_low in (u.get("full_name") or "").lower()]

    if not users:
        st.info("Tidak ada user ditemukan.")
    else:
        df = pd.DataFrame([{
            "ID"           : u["id"],
            "Username"     : u["username"],
            "Nama"         : u.get("full_name") or "-",
            "Email"        : u["email"],
            "Role"         : u["role"],
            "Status"       : "Aktif" if u.get("is_active", 1) else "Nonaktif",
            "Login Terakhir": u.get("last_login") or "-",
            "Dibuat"       : (u.get("created_at") or "")[:10],
        } for u in users])
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()

    with st.expander("➕ Buat User Baru", expanded=False):
        with st.form("form_create_user"):
            c1, c2 = st.columns(2)
            with c1:
                new_username = st.text_input("Username*")
                new_email    = st.text_input("Email*")
                new_fullname = st.text_input("Nama Lengkap")
                new_phone    = st.text_input("No. HP")
            with c2:
                new_company  = st.text_input("Nama Restoran / Bisnis")
                new_role     = st.selectbox("Role", ["user", "admin"])
                new_password = st.text_input("Password (kosongkan = auto-generate)", type="password")
                new_notes    = st.text_area("Catatan", height=68)

            if st.form_submit_button("Buat User", type="primary"):
                if not new_username or not new_email:
                    st.error("Username dan Email wajib diisi.")
                else:
                    pwd = new_password.strip() or generate_temp_password()
                    ok, msg = create_user(
                        username=new_username.strip().lower(),
                        email=new_email.strip().lower(),
                        password=pwd,
                        role=new_role,
                        full_name=new_fullname,
                        phone=new_phone,
                        company=new_company,
                        notes=new_notes,
                    )
                    if ok:
                        write_audit_log(get_current_username(), "create_user",
                                        role="admin", target_type="user", target_id=new_username)
                        if not new_password.strip():
                            st.success(f"{msg} Password sementara: **{pwd}**")
                        else:
                            st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

    with st.expander("✏️ Edit / Suspend User", expanded=False):
        if not users:
            st.info("Tidak ada user.")
        else:
            user_options = {
                f"{u['username']} ({u.get('full_name') or u['email']})": u
                for u in users if u["role"] != "admin"
            }
            if not user_options:
                st.info("Tidak ada user biasa untuk diedit.")
            else:
                selected_label = st.selectbox("Pilih User", list(user_options.keys()))
                sel_user = user_options[selected_label]

                with st.form("form_edit_user"):
                    c1, c2 = st.columns(2)
                    with c1:
                        edit_fullname = st.text_input("Nama Lengkap", value=sel_user.get("full_name") or "")
                        edit_email    = st.text_input("Email", value=sel_user.get("email") or "")
                        edit_phone    = st.text_input("No. HP", value=sel_user.get("phone") or "")
                    with c2:
                        edit_company = st.text_input("Bisnis", value=sel_user.get("company") or "")
                        edit_active  = st.selectbox("Status", [1, 0],
                                                    index=0 if sel_user.get("is_active", 1) else 1,
                                                    format_func=lambda x: "Aktif" if x else "Nonaktif")
                        edit_notes   = st.text_area("Catatan", value=sel_user.get("notes") or "", height=68)

                    col_a, col_b = st.columns(2)
                    with col_a:
                        save_edit = st.form_submit_button("Simpan Perubahan", type="primary")
                    with col_b:
                        reset_pwd = st.form_submit_button("Reset Password (auto-generate)")

                if save_edit:
                    ok, msg = update_user(sel_user["id"],
                                          full_name=edit_fullname,
                                          email=edit_email.strip().lower(),
                                          phone=edit_phone,
                                          company=edit_company,
                                          is_active=edit_active,
                                          notes=edit_notes)
                    if ok:
                        write_audit_log(get_current_username(), "update_user",
                                        role="admin", target_type="user", target_id=str(sel_user["id"]))
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

                if reset_pwd:
                    new_pwd = generate_temp_password()
                    ok, msg = update_user_password(sel_user["id"], new_pwd)
                    if ok:
                        write_audit_log(get_current_username(), "reset_password",
                                        role="admin", target_type="user", target_id=str(sel_user["id"]))
                        st.success(f"Password baru untuk **{sel_user['username']}**: `{new_pwd}`")
                    else:
                        st.error(msg)


    # ── Lupa Password / Lupa Username (bantu user dari admin) ────
    with st.expander("🔑 Bantu User: Lupa Password / Lupa Username", expanded=False):
        st.caption(
            "Gunakan fitur ini untuk membantu user yang lupa password atau username mereka. "
            "Admin bisa cari user berdasarkan email / No. HP, lalu reset password langsung."
        )

        from database import find_user_by_email_or_phone

        search_fp = st.text_input(
            "Cari user berdasarkan Email atau No. HP",
            placeholder="email@bisnis.com atau 08xxx",
            key="admin_fp_search",
        )

        if search_fp:
            found = find_user_by_email_or_phone(search_fp.strip())
            if not found:
                st.warning("Tidak ada user ditemukan dengan email / No. HP tersebut.")
            else:
                for u in found:
                    with st.container(border=True):
                        ci1, ci2, ci3 = st.columns([2, 2, 1])
                        with ci1:
                            st.markdown(f"👤 **{u['username']}**")
                            st.caption(f"Nama : {u.get('full_name') or '-'}")
                            st.caption(f"Email: {u.get('email') or '-'}")
                            st.caption(f"HP   : {u.get('phone') or '-'}")
                        with ci2:
                            new_pw_key = f"new_pw_{u['id']}"
                            new_pw = st.text_input(
                                "Password baru (kosong = auto-generate)",
                                type="password",
                                key=new_pw_key,
                                placeholder="minimal 6 karakter",
                            )
                        with ci3:
                            st.markdown("<br>", unsafe_allow_html=True)
                            if st.button("🔑 Reset", key=f"admin_reset_{u['id']}", use_container_width=True, type="primary"):
                                from database import generate_temp_password as gtp
                                pwd_to_set = new_pw.strip() if new_pw.strip() and len(new_pw.strip()) >= 6 else gtp()
                                ok, msg = update_user_password(u["id"], pwd_to_set)
                                if ok:
                                    write_audit_log(
                                        get_current_username(), "reset_password",
                                        role="admin", target_type="user",
                                        target_id=u["username"],
                                        detail="reset via admin panel (lupa password)",
                                    )
                                    st.success(
                                        f"✅ Password **{u['username']}** berhasil direset. "
                                        f"Password baru: `{pwd_to_set}` — "
                                        f"Sampaikan ke user secara langsung."
                                    )
                                else:
                                    st.error(msg)

    # ── Enterprise pending — notifikasi & tindak lanjut ──────────
    with st.expander("🤝 Enterprise Pending — Perlu Follow-up", expanded=False):
        from database import get_all_licenses

        ent_pending = [
            l for l in get_all_licenses()
            if l.get("package_key") == "enterprise" and l.get("status") == "pending"
        ]

        if not ent_pending:
            st.success("Tidak ada pendaftaran Enterprise yang menunggu tindak lanjut.")
        else:
            st.warning(f"Ada **{len(ent_pending)} pendaftaran Enterprise** yang perlu dihubungi.")
            all_u = {u["id"]: u for u in get_all_users()}
            for lic in ent_pending:
                u = all_u.get(lic["user_id"], {})
                with st.container(border=True):
                    e1, e2, e3 = st.columns([2, 2, 1])
                    with e1:
                        st.markdown(f"👤 **{u.get('username', '-')}**")
                        st.markdown(f"**{u.get('full_name') or '-'}**")
                        st.caption(f"📧 {u.get('email') or '-'}")
                        st.caption(f"📱 {u.get('phone') or '-'}")
                        st.caption(f"🏢 {u.get('company') or '-'}")
                        st.caption(f"📅 Daftar: {(lic.get('start_date') or '')[:10]}")
                    with e2:
                        st.markdown("**Catatan / Kesepakatan:**")
                        note_key = f"ent_note_{lic['id']}"
                        note_val = st.text_area(
                            "Tulis catatan atau detail harga yang disepakati",
                            key=note_key, height=100,
                            placeholder="Misal: Harga Rp 800.000/bulan, 3 outlet, contract 1 tahun...",
                            label_visibility="collapsed",
                        )
                    with e3:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if u.get("id") and st.button("✅ Aktifkan", key=f"ent_act_{lic['id']}", type="primary", use_container_width=True):
                            from database import update_license
                            import datetime
                            end = (datetime.date.today() + datetime.timedelta(days=365)).isoformat()
                            ok1, _ = update_license(lic["id"], status="active", end_date=end)
                            if note_val.strip():
                                update_user(u["id"], notes=f"Enterprise aktif — {note_val.strip()}")
                            if ok1:
                                write_audit_log(
                                    get_current_username(), "confirm_payment",
                                    role="admin", target_type="license",
                                    target_id=u.get("username", ""),
                                    detail=f"enterprise activated amount=custom note={note_val[:50]}",
                                )
                                st.success(f"✅ Akun Enterprise **{u.get('username')}** diaktifkan hingga {end}!")
                                st.rerun()
                            else:
                                st.error("Gagal mengaktifkan lisensi.")

                        if st.button("❌ Tolak", key=f"ent_rej_{lic['id']}", use_container_width=True):
                            from database import update_license
                            ok2, _ = update_license(lic["id"], status="rejected")
                            if ok2:
                                write_audit_log(
                                    get_current_username(), "reject_payment",
                                    role="admin", target_type="license",
                                    target_id=u.get("username",""),
                                    detail="enterprise registration rejected",
                                )
                                st.warning(f"Pendaftaran Enterprise '{u.get('username')}' ditolak.")
                                st.rerun()


# ──────────────────────────────────────────────────────────────────
# TAB: USER ACTIONS (bulk operations)
# ──────────────────────────────────────────────────────────────────

def _tab_user_actions() -> None:
    _section("Manajemen & Aksi User")

    users_full = get_users_full()

    if not users_full:
        st.info("Tidak ada user.")
        return

    # ── Tabel user dengan info lisensi ────────────────────────────
    st.markdown("#### 📋 Semua User + Status Lisensi")

    search = st.text_input("🔍 Cari user", placeholder="username / email / nama", key="ua_search")
    if search:
        users_full = get_users_full(search)

    df = pd.DataFrame([{
        "ID"          : u["id"],
        "Username"    : u["username"],
        "Nama"        : u.get("full_name") or "-",
        "Email"       : u.get("email") or "-",
        "Role"        : u["role"],
        "Aktif"       : "✅" if u.get("is_active") else "❌",
        "Paket"       : (u.get("package_key") or "-").title(),
        "Lic. Status" : u.get("license_status") or "Tidak ada",
        "Expired"     : u.get("end_date") or "-",
    } for u in users_full if u["role"] == "user"])

    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    st.divider()

    # ── Pilih user untuk diaksi ───────────────────────────────────
    st.markdown("#### ⚡ Aksi Cepat per User")

    non_admin = [u for u in users_full if u["role"] == "user"]
    user_opts = {
        f"{u['username']} | {(u.get('package_key') or '-').title()} | {u.get('license_status') or 'no lic'}": u
        for u in non_admin
    }

    if not user_opts:
        st.info("Tidak ada user.")
        return

    sel_label = st.selectbox("Pilih User", list(user_opts.keys()), key="ua_sel_user")
    sel_user  = user_opts[sel_label]

    c1, c2, c3, c4 = st.columns(4)

    # ── Toggle aktif / nonaktif ───────────────────────────────────
    with c1:
        is_active = bool(sel_user.get("is_active", 1))
        label_toggle = "🔴 Nonaktifkan" if is_active else "🟢 Aktifkan"
        if st.button(label_toggle, use_container_width=True, key="ua_toggle_active"):
            ok, msg = update_user(sel_user["id"], is_active=0 if is_active else 1)
            if ok:
                write_audit_log(get_current_username(), "toggle_user_active",
                                role="admin", target_type="user",
                                target_id=sel_user["username"],
                                detail=f"is_active={'0' if is_active else '1'}")
                st.success(f"User **{sel_user['username']}** {'dinonaktifkan' if is_active else 'diaktifkan'}.")
                st.rerun()
            else:
                st.error(msg)

    # ── Suspend lisensi ───────────────────────────────────────────
    with c2:
        if sel_user.get("license_id"):
            lic_status = sel_user.get("license_status","")
            label_lic = "⏸️ Suspend" if lic_status not in ("suspended",) else "▶️ Aktifkan Lic"
            new_lic_status = "suspended" if lic_status not in ("suspended",) else "active"
            if st.button(label_lic, use_container_width=True, key="ua_toggle_lic"):
                ok, msg = update_license(sel_user["license_id"], status=new_lic_status)
                if ok:
                    write_audit_log(get_current_username(), "toggle_license_status",
                                    role="admin", target_type="license",
                                    target_id=str(sel_user["license_id"]),
                                    detail=f"status={new_lic_status}")
                    st.success(msg)
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(msg)
        else:
            st.button("Belum ada lisensi", disabled=True, use_container_width=True)

    # ── Reset password ────────────────────────────────────────────
    with c3:
        if st.button("🔑 Reset Password", use_container_width=True, key="ua_reset_pw"):
            new_pwd = generate_temp_password()
            ok, msg = update_user_password(sel_user["id"], new_pwd)
            if ok:
                write_audit_log(get_current_username(), "reset_password",
                                role="admin", target_type="user",
                                target_id=sel_user["username"])
                st.success(f"Password baru **{sel_user['username']}**: `{new_pwd}`")
            else:
                st.error(msg)

    # ── Ganti paket langsung ──────────────────────────────────────
    with c4:
        from packages import PACKAGE_DEFINITIONS, PACKAGE_ORDER, format_price
        new_pkg = st.selectbox(
            "Ganti Paket",
            PACKAGE_ORDER,
            index=PACKAGE_ORDER.index(sel_user.get("package_key","starter"))
                  if sel_user.get("package_key") in PACKAGE_ORDER else 0,
            key="ua_new_pkg",
        )
        extend_days = st.number_input("Extend (hari)", min_value=1, value=30, step=1, key="ua_days")
        if st.button("Simpan Paket", use_container_width=True, key="ua_save_pkg", type="primary"):
            ok, msg = bulk_update_package([sel_user["id"]], new_pkg, int(extend_days))
            if ok:
                write_audit_log(get_current_username(), "change_package",
                                role="admin", target_type="license",
                                target_id=sel_user["username"],
                                detail=f"pkg={new_pkg} days={extend_days}")
                st.success(msg)
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(msg)

    st.divider()

    # ── Bulk actions ──────────────────────────────────────────────
    st.markdown("#### 🔀 Bulk Action (multi user)")
    st.caption("Pilih beberapa user sekaligus untuk diaksi secara massal.")

    all_usernames = [f"{u['username']} ({(u.get('package_key') or '-').title()})"
                     for u in non_admin]
    sel_bulk = st.multiselect("Pilih User", all_usernames, key="ua_bulk_sel")
    sel_ids  = [non_admin[all_usernames.index(s)]["id"] for s in sel_bulk]

    if sel_ids:
        bc1, bc2, bc3 = st.columns(3)
        with bc1:
            if st.button("⏸️ Suspend Semua", use_container_width=True, key="bulk_suspend"):
                ok, msg = bulk_update_license_status(sel_ids, "suspended")
                if ok:
                    write_audit_log(get_current_username(), "bulk_suspend",
                                    role="admin", detail=f"user_ids={sel_ids}")
                    st.success(msg)
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(msg)
        with bc2:
            if st.button("▶️ Aktifkan Semua", use_container_width=True, key="bulk_activate"):
                ok, msg = bulk_update_license_status(sel_ids, "active")
                if ok:
                    write_audit_log(get_current_username(), "bulk_activate",
                                    role="admin", detail=f"user_ids={sel_ids}")
                    st.success(msg)
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(msg)
        with bc3:
            bulk_pkg  = st.selectbox("Ganti Paket Bulk", PACKAGE_ORDER, key="ua_bulk_pkg")
            bulk_days = st.number_input("Extend (hari)", min_value=1, value=30, key="ua_bulk_days")
            if st.button("Ganti Paket Semua", use_container_width=True, key="bulk_pkg_save", type="primary"):
                ok, msg = bulk_update_package(sel_ids, bulk_pkg, int(bulk_days))
                if ok:
                    write_audit_log(get_current_username(), "bulk_change_package",
                                    role="admin", detail=f"user_ids={sel_ids} pkg={bulk_pkg}")
                    st.success(msg)
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(msg)
    else:
        st.caption("Pilih minimal 1 user untuk bulk action.")


# ──────────────────────────────────────────────────────────────────
# TAB: LISENSI
# ──────────────────────────────────────────────────────────────────

def _tab_licenses() -> None:
    _section("Semua Lisensi")

    licenses = get_all_licenses()

    status_filter = st.selectbox("Filter status", ["Semua", "active", "trial", "expired", "suspended"])
    if status_filter != "Semua":
        today = str(date.today())
        if status_filter == "expired":
            licenses = [l for l in licenses if l["status"] == "expired" or l["end_date"] < today]
        else:
            licenses = [l for l in licenses if l["status"] == status_filter]

    if not licenses:
        st.info("Tidak ada lisensi ditemukan.")
    else:
        df = pd.DataFrame([{
            "ID"        : l["id"],
            "Username"  : l["username"],
            "Nama"      : l.get("full_name") or "-",
            "Paket"     : l["package_key"].title(),
            "Status"    : l["status"],
            "Mulai"     : l["start_date"],
            "Expired"   : l["end_date"],
            "Sisa Hari" : max(0, (date.fromisoformat(l["end_date"]) - date.today()).days),
            "Harga Bayar": f"Rp {l.get('price_paid', 0):,}".replace(",", "."),
        } for l in licenses])
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()

    with st.expander("➕ Buat Lisensi Baru / Perpanjang", expanded=False):
        all_users    = get_all_users()
        user_options = {
            f"{u['username']} ({u.get('full_name') or u['email']})": u
            for u in all_users if u["role"] == "user"
        }
        if not user_options:
            st.info("Belum ada user. Buat user dulu di tab User.")
        else:
            with st.form("form_create_license"):
                c1, c2 = st.columns(2)
                with c1:
                    sel_user_label = st.selectbox("Pilih User", list(user_options.keys()))
                    sel_pkg        = st.selectbox(
                        "Paket", PACKAGE_ORDER,
                        format_func=lambda k: f"{PACKAGE_DEFINITIONS[k]['name']} — {format_price(PACKAGE_DEFINITIONS[k]['price_monthly'])}/bln"
                    )
                    sel_status = st.selectbox("Status", ["active", "trial", "suspended"])
                with c2:
                    sel_billing = st.selectbox("Siklus Billing", ["monthly", "yearly", "lifetime", "custom"])
                    sel_start   = st.date_input("Tanggal Mulai", value=date.today())
                    default_end = date.today() + timedelta(days=30)
                    sel_end     = st.date_input("Tanggal Expired", value=default_end)
                    sel_price   = st.number_input("Harga Dibayar (Rp)", min_value=0,
                                                  value=PACKAGE_DEFINITIONS[sel_pkg]["price_monthly"], step=10_000)
                sel_notes = st.text_input("Catatan (opsional)")

                if st.form_submit_button("Buat Lisensi", type="primary"):
                    sel_user_data = user_options[sel_user_label]
                    if sel_end <= sel_start:
                        st.error("Tanggal expired harus setelah tanggal mulai.")
                    else:
                        ok, msg = create_license(
                            user_id=sel_user_data["id"],
                            package_key=sel_pkg,
                            start_date=str(sel_start),
                            end_date=str(sel_end),
                            status=sel_status,
                            billing_cycle=sel_billing,
                            price_paid=int(sel_price),
                            notes=sel_notes,
                        )
                        if ok:
                            write_audit_log(get_current_username(), "create_license",
                                            role="admin", target_type="license",
                                            target_id=sel_user_data["username"],
                                            detail=f"pkg={sel_pkg} end={sel_end}")
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

    with st.expander("✏️ Edit Lisensi", expanded=False):
        if not licenses:
            st.info("Tidak ada lisensi.")
        else:
            lic_opts = {
                f"#{l['id']} — {l['username']} ({l['package_key']}, exp: {l['end_date']})": l
                for l in get_all_licenses()
            }
            sel_lic_label = st.selectbox("Pilih Lisensi", list(lic_opts.keys()))
            sel_lic       = lic_opts[sel_lic_label]

            with st.form("form_edit_license"):
                c1, c2 = st.columns(2)
                with c1:
                    ed_pkg    = st.selectbox("Paket", PACKAGE_ORDER,
                                             index=PACKAGE_ORDER.index(sel_lic["package_key"])
                                             if sel_lic["package_key"] in PACKAGE_ORDER else 0)
                    ed_status = st.selectbox("Status",
                                             ["active", "trial", "expired", "suspended"],
                                             index=["active","trial","expired","suspended"].index(sel_lic["status"])
                                             if sel_lic["status"] in ["active","trial","expired","suspended"] else 0)
                with c2:
                    ed_end   = st.date_input("Expired", value=date.fromisoformat(sel_lic["end_date"]))
                    ed_price = st.number_input("Harga Bayar", min_value=0,
                                               value=sel_lic.get("price_paid", 0), step=10_000)
                ed_notes = st.text_input("Catatan", value=sel_lic.get("notes") or "")

                if st.form_submit_button("Simpan", type="primary"):
                    ok, msg = update_license(sel_lic["id"],
                                             package_key=ed_pkg,
                                             status=ed_status,
                                             end_date=str(ed_end),
                                             price_paid=int(ed_price),
                                             notes=ed_notes)
                    if ok:
                        write_audit_log(get_current_username(), "update_license",
                                        role="admin", target_type="license",
                                        target_id=str(sel_lic["id"]))
                        st.cache_data.clear()  # user ybs langsung dapat paket/status baru
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)


# ──────────────────────────────────────────────────────────────────
# TAB: PEMBAYARAN
# ──────────────────────────────────────────────────────────────────

def _render_proof_image(payment_id: int, filename: str = "") -> None:
    """Render preview bukti transfer dari blob DB menggunakan st.image."""
    proof = get_payment_proof(payment_id)
    if proof and proof.get("proof_image"):
        import io
        img_bytes = proof["proof_image"]
        fname     = proof.get("proof_filename") or filename or "bukti.jpg"
        st.image(io.BytesIO(img_bytes), caption=f"📎 {fname}", use_container_width=True)
    else:
        st.markdown(
            "<div style='background:#1a1f2e;border:1px dashed #374151;"
            "border-radius:8px;padding:24px;text-align:center;"
            "color:#6b7280;font-size:12px'>📭 Belum ada bukti transfer</div>",
            unsafe_allow_html=True,
        )


def _tab_payments() -> None:
    _section("Riwayat Pembayaran")

    payments = get_all_payments_with_proof()
    pending  = [p for p in payments if p["status"] == "pending"]

    if pending:
        st.warning(f"⚠️ Ada **{len(pending)} pembayaran pending** yang perlu dikonfirmasi.")

    # ── Filter ────────────────────────────────────────────────────
    fc1, fc2 = st.columns([2, 1])
    with fc1:
        status_f = st.selectbox(
            "Filter status", ["Semua", "pending", "confirmed", "rejected"], key="pay_status_f"
        )
    with fc2:
        bukti_f = st.selectbox(
            "Filter bukti", ["Semua", "Ada bukti", "Belum ada bukti"], key="pay_bukti_f"
        )

    filtered = payments
    if status_f != "Semua":
        filtered = [p for p in filtered if p["status"] == status_f]
    if bukti_f == "Ada bukti":
        filtered = [p for p in filtered if p.get("has_proof")]
    elif bukti_f == "Belum ada bukti":
        filtered = [p for p in filtered if not p.get("has_proof")]

    if not filtered:
        st.info("Belum ada pembayaran.")
    else:
        df = pd.DataFrame([{
            "ID"          : p["id"],
            "Username"    : p["username"],
            "Nama"        : p.get("full_name") or "-",
            "Jumlah"      : f"Rp {p['amount']:,}".replace(",", "."),
            "Metode"      : p.get("method") or "-",
            "Status"      : p["status"],
            "Bukti"       : "✅ Ada" if p.get("has_proof") else "❌ Tidak",
            "Periode"     : p.get("period_label") or "-",
            "Dikonfirmasi": p.get("confirmed_by") or "-",
            "Tanggal"     : (p.get("created_at") or "")[:10],
        } for p in filtered])
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()

    # ══════════════════════════════════════════════════════════════
    # SECTION 1 — PENDING: preview bukti + konfirmasi / tolak
    # ══════════════════════════════════════════════════════════════
    pending_all = [p for p in get_all_payments_with_proof() if p["status"] == "pending"]
    label_pending = f"⏳ Pembayaran Pending — perlu tindakan ({len(pending_all)})" if pending_all else "⏳ Tidak ada pembayaran pending"
    with st.expander(label_pending, expanded=bool(pending_all)):
        if not pending_all:
            st.info("Semua pembayaran sudah ditangani.")
        for p in pending_all:
            with st.container(border=True):
                col_info, col_img = st.columns([1, 1])

                with col_info:
                    st.markdown(f"### {p['username']}")
                    st.markdown(f"**{p.get('full_name') or '-'}**")
                    st.markdown(
                        f"💰 **Rp {p['amount']:,}**".replace(",", ".")
                        + f"  via **{p.get('method') or '-'}**"
                    )
                    st.caption(f"📅 Periode: {p.get('period_label') or '-'}")
                    st.caption(f"🕐 Dikirim: {(p.get('created_at') or '')[:16]}")
                    if p.get("notes"):
                        st.info(f"📝 {p['notes']}")

                with col_img:
                    st.markdown("**📷 Bukti Transfer**")
                    _render_proof_image(p["id"], p.get("proof_filename", ""))

                st.markdown("---")
                act1, act2, act3 = st.columns([2, 1, 3])

                with act1:
                    if st.button("✅ Konfirmasi Pembayaran", key=f"conf_{p['id']}", type="primary", use_container_width=True):
                        ok, msg, lic_info = confirm_payment(p["id"], get_current_username())
                        if ok:
                            write_audit_log(get_current_username(), "confirm_payment",
                                            role="admin", target_type="payment",
                                            target_id=str(p["id"]),
                                            detail=f"user={p['username']} amount={p['amount']}")
                            if lic_info:
                                st.success(
                                    f"✅ Dikonfirmasi! Lisensi **{lic_info['package_key'].title()}** "
                                    f"aktif hingga **{lic_info['end_date']}**"
                                )
                            else:
                                st.success("✅ Pembayaran dikonfirmasi.")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(msg)

                with act2:
                    reject_key = f"reject_toggle_{p['id']}"
                    if st.button("❌ Tolak", key=f"rej_btn_{p['id']}", use_container_width=True):
                        st.session_state[reject_key] = not st.session_state.get(reject_key, False)

                with act3:
                    if st.session_state.get(reject_key, False):
                        reason = st.text_input(
                            "Alasan penolakan:",
                            key=f"rej_reason_{p['id']}",
                            placeholder="contoh: Nominal tidak sesuai, bukti tidak jelas...",
                        )
                        if st.button("Kirim Penolakan", key=f"rej_send_{p['id']}", type="primary"):
                            if not reason.strip():
                                st.error("Alasan wajib diisi.")
                            else:
                                ok, msg2 = reject_payment(p["id"], reason, get_current_username())
                                if ok:
                                    write_audit_log(get_current_username(), "reject_payment",
                                                    role="admin", target_type="payment",
                                                    target_id=str(p["id"]),
                                                    detail=f"reason={reason}")
                                    st.warning("❌ Pembayaran ditolak.")
                                    st.session_state.pop(reject_key, None)
                                    st.rerun()
                                else:
                                    st.error(msg2)

    # ══════════════════════════════════════════════════════════════
    # SECTION 2 — LIHAT BUKTI SEMUA PEMBAYARAN (confirmed / rejected)
    # ══════════════════════════════════════════════════════════════
    st.divider()
    _section("🖼️ Lihat Bukti Transfer")

    all_with_proof = [p for p in get_all_payments_with_proof() if p.get("has_proof")]

    if not all_with_proof:
        st.info("Belum ada pembayaran dengan bukti transfer tersimpan.")
    else:
        opts = {
            f"#{p['id']} — {p['username']} | Rp {p['amount']:,} | {p['status']} | {(p.get('created_at') or '')[:10]}".replace(",", "."): p
            for p in all_with_proof
        }
        sel_label = st.selectbox("Pilih pembayaran untuk lihat bukti:", list(opts.keys()), key="proof_viewer_sel")
        sel_p     = opts[sel_label]

        vi1, vi2 = st.columns([1, 1])
        with vi1:
            st.markdown(f"**User:** {sel_p['username']} ({sel_p.get('full_name') or '-'})")
            st.markdown(f"**Jumlah:** Rp {sel_p['amount']:,}".replace(",", "."))
            st.markdown(f"**Metode:** {sel_p.get('method') or '-'}")
            st.markdown(f"**Status:** `{sel_p['status']}`")
            st.markdown(f"**Periode:** {sel_p.get('period_label') or '-'}")
            st.markdown(f"**Tanggal kirim:** {(sel_p.get('created_at') or '')[:16]}")
            if sel_p.get("confirmed_by"):
                st.markdown(f"**Dikonfirmasi oleh:** {sel_p['confirmed_by']}")
            if sel_p.get("rejected_reason"):
                st.error(f"Alasan ditolak: {sel_p['rejected_reason']}")
            if sel_p.get("notes"):
                st.info(f"Catatan user: {sel_p['notes']}")

        with vi2:
            st.markdown("**📷 Bukti Transfer**")
            _render_proof_image(sel_p["id"], sel_p.get("proof_filename", ""))

            proof = get_payment_proof(sel_p["id"])
            if proof and proof.get("proof_image"):
                st.download_button(
                    "⬇️ Download Bukti",
                    data=proof["proof_image"],
                    file_name=proof.get("proof_filename") or f"bukti_{sel_p['id']}.jpg",
                    mime=proof.get("proof_mimetype") or "image/jpeg",
                    use_container_width=True,
                )

    st.divider()

    # ══════════════════════════════════════════════════════════════
    # SECTION 3 — CATAT PEMBAYARAN BARU (manual oleh admin)
    # ══════════════════════════════════════════════════════════════
    with st.expander("➕ Catat Pembayaran Baru", expanded=False):
        all_users = get_all_users()
        user_opts = {
            f"{u['username']} ({u.get('full_name') or u['email']})": u
            for u in all_users if u["role"] == "user"
        }
        licenses = get_all_licenses()
        if not user_opts:
            st.info("Belum ada user.")
        else:
            with st.form("form_create_payment"):
                c1, c2 = st.columns(2)
                with c1:
                    pay_user_label = st.selectbox("User", list(user_opts.keys()))
                    pay_amount     = st.number_input("Jumlah (Rp)", min_value=0, step=10_000)
                    pay_method     = st.text_input("Metode", placeholder="Transfer BCA, QRIS, ...")
                with c2:
                    pay_period = st.text_input("Periode", placeholder="Mei 2026")
                    pay_status = st.selectbox("Status Awal", ["pending", "confirmed"])
                    pay_notes  = st.text_area("Catatan", height=68)

                if st.form_submit_button("Catat Pembayaran", type="primary"):
                    sel_u     = user_opts[pay_user_label]
                    user_lics = [l for l in licenses if l["user_id"] == sel_u["id"]]
                    lic_id    = user_lics[0]["id"] if user_lics else None
                    ok, msg, pay_id = create_payment(
                        user_id=sel_u["id"], amount=int(pay_amount),
                        method=pay_method, status=pay_status,
                        license_id=lic_id, period_label=pay_period, notes=pay_notes,
                    )
                    if ok:
                        if pay_status == "confirmed" and pay_id:
                            c_ok, _, c_lic = confirm_payment(pay_id, get_current_username())
                            if c_ok and c_lic:
                                st.info(
                                    f"🔑 Lisensi **{sel_u['username']}** diaktifkan "
                                    f"hingga **{c_lic['end_date']}**"
                                )
                        write_audit_log(get_current_username(), "create_payment",
                                        role="admin", target_type="payment",
                                        target_id=sel_u["username"])
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)


def _tab_packages() -> None:
    from database import (
        get_package_tab_access,
        set_package_tab_access,
        reset_package_tab_access,
        get_all_package_tab_access,
        update_package_in_db,
    )

    _section("Paket & Harga")

    packages_db = get_all_packages_from_db()
    pkg_map     = {p["package_key"]: p for p in packages_db}

    # ══════════════════════════════════════════════════════════════
    # KARTU RINGKASAN PAKET — satu baris, rapi
    # ══════════════════════════════════════════════════════════════
    cols = st.columns(len(PACKAGE_ORDER))
    for i, key in enumerate(PACKAGE_ORDER):
        cfg        = PACKAGE_DEFINITIONS[key]
        db_row     = pkg_map.get(key, {})
        price_m    = db_row.get("price_monthly", cfg["price_monthly"])
        is_active  = bool(db_row.get("is_active", 1))
        use_db     = bool(db_row.get("use_database", cfg.get("use_database", False)))
        grade      = cfg.get("grade")
        label      = f"Grade {grade}" if grade else cfg["name"]
        color      = cfg["color"]

        with cols[i]:
            st.markdown(
                f"""<div style="
                    border:1px solid {color}44;
                    border-top:3px solid {color};
                    border-radius:10px;
                    padding:12px 14px;
                    background:#0f1420;
                    margin-bottom:4px;
                ">
                    <div style="font-size:13px;font-weight:700;color:#f0f2f5;
                                margin-bottom:6px;">{label}</div>
                    <div style="font-size:11px;color:#8892a4;margin-bottom:4px;">
                        {'🟢 Aktif' if is_active else '🔴 Nonaktif'}
                    </div>
                    <div style="font-size:11px;color:#8892a4;margin-bottom:4px;">
                        {'🗄️ Pakai DB' if use_db else '⚡ In-Memory'}
                    </div>
                    <div style="font-size:12px;font-weight:600;color:{color};">
                        {format_price(price_m)}/bln
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )

    st.divider()

    # ══════════════════════════════════════════════════════════════
    # TOGGLE DATABASE — Grid rapi semua paket sekaligus
    # ══════════════════════════════════════════════════════════════
    _section("🗄️ Fitur Database per Paket")
    st.caption(
        "Toggle **Pakai Database** mengontrol apakah data yang diupload user "
        "disimpan permanen ke SQLite atau hanya in-memory (hilang saat refresh)."
    )
    st.write("")

    # Header grid
    hdr = st.columns([3, 1, 1, 1])
    with hdr[0]:
        st.markdown("<div style='font-size:11px;font-weight:700;color:#8892a4;"
                    "text-transform:uppercase;letter-spacing:.08em'>Paket</div>",
                    unsafe_allow_html=True)
    with hdr[1]:
        st.markdown("<div style='font-size:11px;font-weight:700;color:#8892a4;"
                    "text-transform:uppercase;letter-spacing:.08em;text-align:center'>"
                    "Status</div>", unsafe_allow_html=True)
    with hdr[2]:
        st.markdown("<div style='font-size:11px;font-weight:700;color:#8892a4;"
                    "text-transform:uppercase;letter-spacing:.08em;text-align:center'>"
                    "Pakai Database</div>", unsafe_allow_html=True)
    with hdr[3]:
        st.markdown("<div style='font-size:11px;font-weight:700;color:#8892a4;"
                    "text-transform:uppercase;letter-spacing:.08em;text-align:center'>"
                    "Harga/Bln</div>", unsafe_allow_html=True)

    st.markdown("<hr style='margin:4px 0 8px;border-color:#2d3348'>",
                unsafe_allow_html=True)

    db_changed: dict[str, bool] = {}

    for key in PACKAGE_ORDER:
        cfg       = PACKAGE_DEFINITIONS[key]
        db_row    = pkg_map.get(key, {})
        is_active = bool(db_row.get("is_active", 1))
        use_db    = bool(db_row.get("use_database", cfg.get("use_database", False)))
        grade     = cfg.get("grade")
        label     = f"Grade {grade} — {cfg['name']}" if grade else cfg["name"]
        color     = cfg["color"]
        price_m   = db_row.get("price_monthly", cfg["price_monthly"])

        row = st.columns([3, 1, 1, 1])

        with row[0]:
            st.markdown(
                f"<div style='padding:8px 0;'>"
                f"<span style='font-size:13px;font-weight:600;color:#f0f2f5'>{label}</span>"
                f"<br><span style='font-size:11px;color:{color}'>{cfg['description'][:50]}...</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

        with row[1]:
            st.markdown(
                f"<div style='text-align:center;padding:12px 0'>"
                f"{'🟢 Aktif' if is_active else '🔴 Nonaktif'}"
                f"</div>",
                unsafe_allow_html=True,
            )

        with row[2]:
            new_use_db = st.toggle(
                "",
                value=use_db,
                key=f"usedb_{key}",
                label_visibility="collapsed",
                help=(
                    "ON  → upload user disimpan ke SQLite, data persisten antar session\n"
                    "OFF → upload hanya in-memory, hilang saat user refresh"
                ),
            )
            if new_use_db != use_db:
                db_changed[key] = new_use_db

        with row[3]:
            st.markdown(
                f"<div style='text-align:center;padding:12px 0;"
                f"font-size:13px;font-weight:600;color:{color}'>"
                f"{format_price(price_m)}</div>",
                unsafe_allow_html=True,
            )

        st.markdown("<div style='border-bottom:1px solid #1e2535;margin:2px 0'></div>",
                    unsafe_allow_html=True)

    st.write("")
    if db_changed:
        summary = ", ".join(
            f"**{k}** → {'🗄️ DB' if v else '⚡ In-Memory'}"
            for k, v in db_changed.items()
        )
        st.info(f"Perubahan belum disimpan: {summary}")

    col_save_db, _ = st.columns([2, 3])
    with col_save_db:
        if st.button(
            f"💾 Simpan Pengaturan Database ({len(db_changed)} perubahan)",
            type="primary",
            use_container_width=True,
            disabled=len(db_changed) == 0,
            key="save_use_db_btn",
        ):
            for pkg_key, val in db_changed.items():
                update_package_in_db(pkg_key, use_database=int(val))
                write_audit_log(
                    get_current_username(), "update_package_use_database",
                    role="admin", target_type="package", target_id=pkg_key,
                    detail=f"use_database={'true' if val else 'false'}",
                )
            st.cache_data.clear()
            st.success(f"✅ {len(db_changed)} paket diperbarui. Berlaku segera untuk semua user.")
            st.rerun()

    st.divider()

    # ══════════════════════════════════════════════════════════════
    # EDIT HARGA & DETAIL PAKET
    # ══════════════════════════════════════════════════════════════
    with st.expander("✏️ Edit Harga & Detail Paket", expanded=False):
        sel_pkg_edit = st.selectbox(
            "Pilih Paket", PACKAGE_ORDER,
            format_func=lambda k: (
                f"Grade {PACKAGE_DEFINITIONS[k]['grade']}"
                if PACKAGE_DEFINITIONS[k].get("grade")
                else PACKAGE_DEFINITIONS[k]["name"]
            ),
            key="pkg_edit_select",
        )
        db_row = pkg_map.get(sel_pkg_edit, {})
        cfg    = PACKAGE_DEFINITIONS[sel_pkg_edit]

        with st.form("form_edit_package"):
            c1, c2 = st.columns(2)
            with c1:
                ep_name = st.text_input("Nama Paket", value=db_row.get("name", cfg["name"]))
                ep_pm   = st.number_input("Harga Bulanan (Rp)", min_value=0,
                                          value=db_row.get("price_monthly", cfg["price_monthly"]), step=10_000)
            with c2:
                ep_py     = st.number_input("Harga Tahunan (Rp)", min_value=0,
                                            value=db_row.get("price_yearly", cfg["price_yearly"]), step=100_000)
                ep_active = st.selectbox("Status Paket", [1, 0],
                                         index=0 if db_row.get("is_active", 1) else 1,
                                         format_func=lambda x: "🟢 Aktif" if x else "🔴 Nonaktif")
            ep_desc = st.text_area("Deskripsi", value=db_row.get("description", cfg["description"]))

            if st.form_submit_button("💾 Simpan", type="primary"):
                ok, msg = update_package_in_db(
                    sel_pkg_edit,
                    name=ep_name,
                    price_monthly=int(ep_pm),
                    price_yearly=int(ep_py),
                    description=ep_desc,
                    is_active=ep_active,
                )
                if ok:
                    write_audit_log(get_current_username(), "update_package",
                                    role="admin", target_type="package", target_id=sel_pkg_edit)
                    st.cache_data.clear()
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    st.divider()

    _section("🔧 Kontrol Akses Tab per Paket")
    st.info("Switch on/off akses tab untuk setiap paket. Perubahan berlaku langsung.")

    sel_pkg_access = st.selectbox(
        "Pilih Paket", PACKAGE_ORDER,
        format_func=lambda k: (
            f"Grade {PACKAGE_DEFINITIONS[k]['grade']}"
            if PACKAGE_DEFINITIONS[k].get("grade")
            else PACKAGE_DEFINITIONS[k]["name"]
        ),
        key="pkg_access_select",
    )

    cfg_access   = PACKAGE_DEFINITIONS[sel_pkg_access]
    db_overrides = get_package_tab_access(sel_pkg_access)
    default_tabs = set(cfg_access["tabs"])

    grade_label = (
        f"Grade {cfg_access['grade']}" if cfg_access.get("grade") else cfg_access["name"]
    )
    st.markdown(f"**{grade_label}** — {cfg_access['description']}")
    st.write("")

    changed = {}
    for tab in ALL_TABS:
        in_default = tab in default_tabs
        db_val     = db_overrides.get(tab)
        current    = db_val if db_val is not None else in_default

        source = ""
        if db_val is not None:
            source = " *(override)*"
        elif in_default:
            source = " *(default)*"

        col_sw, col_lbl = st.columns([1, 8])
        with col_sw:
            new_val = st.toggle("", value=current,
                                key=f"toggle_{sel_pkg_access}_{tab}",
                                label_visibility="collapsed")
        with col_lbl:
            st.markdown(f"{tab}{source}")

        if new_val != current:
            changed[tab] = new_val

    st.write("")
    col_save, col_reset = st.columns([2, 1])
    with col_save:
        if st.button(f"💾 Simpan Perubahan ({len(changed)} tab diubah)",
                     type="primary", use_container_width=True, disabled=len(changed) == 0):
            for tab, enabled in changed.items():
                set_package_tab_access(sel_pkg_access, tab, enabled)
            write_audit_log(get_current_username(), "update_tab_access",
                            role="admin", target_type="package", target_id=sel_pkg_access,
                            detail=str(changed))
            st.cache_data.clear()  # paksa semua user session baca ulang tab access dari DB
            st.success(f"✅ {len(changed)} perubahan disimpan.")
            st.rerun()

    with col_reset:
        if st.button("🔄 Reset ke Default", use_container_width=True):
            ok, msg = reset_package_tab_access(sel_pkg_access)
            if ok:
                # BUG FIX: Hapus session_state keys semua toggle paket ini
                # agar widget ikut reset tampilan ke nilai default,
                # bukan tetap menampilkan nilai lama dari session_state.
                for k in list(st.session_state.keys()):
                    if k.startswith(f"toggle_{sel_pkg_access}_") or \
                       k.startswith(f"bulk_{sel_pkg_access}_"):
                        del st.session_state[k]
                write_audit_log(get_current_username(), "reset_tab_access",
                                role="admin", target_type="package", target_id=sel_pkg_access)
                st.cache_data.clear()  # paksa user dashboard baca ulang dari DB
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    st.divider()

    # ══════════════════════════════════════════════════════════════
    # DASHBOARD PENGATURAN DEFAULT — Semua Paket Sekaligus
    # ══════════════════════════════════════════════════════════════
    _section("⚙️ Dashboard Pengaturan Default Semua Paket")
    st.info(
        "Atur akses tab untuk **semua paket sekaligus** dalam satu tampilan. "
        "Perubahan langsung terlihat di dashboard user setelah disimpan."
    )

    all_overrides_bulk = get_all_package_tab_access()

    # Header kolom
    pkg_labels = []
    for k in PACKAGE_ORDER:
        c = PACKAGE_DEFINITIONS[k]
        pkg_labels.append(f"Grade {c['grade']}" if c.get("grade") else c["name"])

    hdr_cols = st.columns([3] + [1] * len(PACKAGE_ORDER))
    with hdr_cols[0]:
        st.markdown("<div style='font-size:12px;font-weight:700;color:#8892a4;"
                    "text-transform:uppercase;letter-spacing:.08em'>Tab / Fitur</div>",
                    unsafe_allow_html=True)
    for i, label in enumerate(pkg_labels):
        with hdr_cols[i + 1]:
            st.markdown(f"<div style='font-size:11px;font-weight:700;color:#8892a4;"
                        f"text-transform:uppercase;letter-spacing:.06em;text-align:center'>"
                        f"{label}</div>", unsafe_allow_html=True)

    st.markdown("<hr style='margin:4px 0 10px;border-color:#2d3348'>", unsafe_allow_html=True)

    bulk_changed: dict[str, dict[str, bool]] = {}

    for tab in ALL_TABS:
        row_cols = st.columns([3] + [1] * len(PACKAGE_ORDER))
        with row_cols[0]:
            st.markdown(f"<div style='padding:5px 0;font-size:13px;color:#d1d5db'>{tab}</div>",
                        unsafe_allow_html=True)
        for i, pkg_key in enumerate(PACKAGE_ORDER):
            in_default = tab in PACKAGE_DEFINITIONS[pkg_key]["tabs"]
            db_val     = all_overrides_bulk.get(pkg_key, {}).get(tab)
            current    = db_val if db_val is not None else in_default
            with row_cols[i + 1]:
                new_val = st.toggle(
                    "",
                    value=current,
                    key=f"bulk_{pkg_key}_{tab}",
                    label_visibility="collapsed",
                )
            if new_val != current:
                bulk_changed.setdefault(pkg_key, {})[tab] = new_val

    st.write("")
    total_bulk = sum(len(v) for v in bulk_changed.values())
    col_bsave, col_breset = st.columns([2, 1])

    with col_bsave:
        if st.button(
            f"💾 Simpan Semua ({total_bulk} perubahan)",
            type="primary",
            use_container_width=True,
            disabled=total_bulk == 0,
            key="bulk_save_btn",
        ):
            for pkg_key, tab_changes in bulk_changed.items():
                for tab, enabled in tab_changes.items():
                    set_package_tab_access(pkg_key, tab, enabled)
            write_audit_log(
                get_current_username(), "bulk_update_tab_access",
                role="admin", target_type="package", target_id="all",
                detail=str(bulk_changed),
            )
            st.success(f"✅ {total_bulk} perubahan disimpan untuk {len(bulk_changed)} paket.")
            st.rerun()

    with col_breset:
        if st.button(
            "🔄 Reset Semua Paket",
            use_container_width=True,
            key="bulk_reset_btn",
        ):
            for pkg_key in PACKAGE_ORDER:
                reset_package_tab_access(pkg_key)
            # BUG FIX: Hapus semua toggle session_state bulk & per-paket
            for k in list(st.session_state.keys()):
                if k.startswith("bulk_") or any(
                    k.startswith(f"toggle_{p}_") for p in PACKAGE_ORDER
                ):
                    del st.session_state[k]
            write_audit_log(
                get_current_username(), "bulk_reset_all_tab_access",
                role="admin", target_type="package", target_id="all",
            )
            st.success("✅ Semua paket direset ke pengaturan default.")
            st.rerun()

    st.divider()

    _section("📋 Overview Akses Tab — Semua Paket")
    all_overrides = get_all_package_tab_access()

    header_names = []
    for k in PACKAGE_ORDER:
        c = PACKAGE_DEFINITIONS[k]
        header_names.append(f"Grade {c['grade']}" if c.get("grade") else c["name"])

    tab_data = []
    for tab in ALL_TABS:
        row = {"Tab": tab}
        for i, key in enumerate(PACKAGE_ORDER):
            cfg_k      = PACKAGE_DEFINITIONS[key]
            in_default = tab in cfg_k["tabs"]
            db_val     = all_overrides.get(key, {}).get(tab)
            effective  = db_val if db_val is not None else in_default

            if effective:
                icon = "✅🔧" if db_val is True else "✅"
            else:
                icon = "🔴" if db_val is False else "—"

            row[header_names[i]] = icon
        tab_data.append(row)

    st.dataframe(pd.DataFrame(tab_data), use_container_width=True, hide_index=True)
    st.caption("✅ = aktif (default)  ·  ✅🔧 = aktif (override)  ·  🔴 = dinonaktifkan admin  ·  — = tidak termasuk paket")


# ──────────────────────────────────────────────────────────────────
# TAB: AUDIT LOG
# ──────────────────────────────────────────────────────────────────

def _fmt_audit_action(action: str) -> str:
    """Terjemahkan kode aksi teknis → kalimat Indonesia yang mudah dibaca."""
    _map = {
        # Auth
        "login_success"               : "🟢 Login berhasil",
        "login_failed"                : "🔴 Gagal login",
        "logout"                      : "🚪 Logout",
        # User
        "create_user"                 : "👤 Buat user baru",
        "update_user"                 : "✏️ Ubah data user",
        "toggle_user_active"          : "🔁 Aktifkan / nonaktifkan user",
        "reset_password"              : "🔑 Reset password",
        "change_password"             : "🔒 Ganti password",
        # Lisensi
        "create_license"              : "📋 Buat lisensi baru",
        "update_license"              : "📋 Ubah lisensi",
        "toggle_license_status"       : "🔁 Ubah status lisensi",
        "bulk_suspend"                : "⏸️ Suspend banyak user sekaligus",
        "bulk_activate"               : "▶️ Aktifkan banyak user sekaligus",
        # Paket
        "change_package"              : "📦 Ganti paket user",
        "bulk_change_package"         : "📦 Ganti paket banyak user sekaligus",
        "update_package"              : "📦 Ubah konfigurasi paket",
        "update_package_use_database" : "🗄️ Ubah akses database paket",
        "update_tab_access"           : "🔧 Ubah akses tab paket",
        "bulk_update_tab_access"      : "🔧 Ubah akses tab banyak paket sekaligus",
        "reset_tab_access"            : "🔄 Reset akses tab ke default",
        "bulk_reset_all_tab_access"   : "🔄 Reset semua akses tab ke default",
        # Pembayaran
        "create_payment"              : "💳 Catat pembayaran baru",
        "confirm_payment"             : "✅ Konfirmasi pembayaran",
        "reject_payment"              : "❌ Tolak pembayaran",
        # Sistem
        "run_init_db"                 : "🛠️ Jalankan ulang init database",
        "export_data"                 : "⬇️ Export data",
    }
    return _map.get(action, f"⚙️ {action.replace('_', ' ').title()}")


def _fmt_audit_detail(action: str, detail: str, target_type: str, target_id: str) -> str:
    """
    Ubah raw detail + target → kalimat deskriptif yang mudah dipahami.
    Tidak ada lagi kode teknis, tanda #, atau dict Python mentah.
    """
    if not detail and not target_id:
        return "-"

    d = detail or ""

    # ── Helper ambil nilai dari format "key=value key2=value2" ──
    def _get(key):
        import re
        m = re.search(rf"{key}=([^\s]+)", d)
        return m.group(1) if m else None

    # ── Per aksi ────────────────────────────────────────────────
    if action == "login_success":
        return f"User '{target_id or _get('actor') or ''}' berhasil masuk ke sistem."

    if action == "login_failed":
        attempt = _get("attempt")
        return f"Percobaan login gagal" + (f" (percobaan ke-{attempt})" if attempt else "") + "."

    if action == "create_user":
        return f"Akun baru '{target_id}' berhasil dibuat."

    if action == "update_user":
        uid = target_id
        return f"Data profil user ID {uid} diperbarui (nama, email, status, atau catatan)."

    if action == "toggle_user_active":
        active = _get("is_active")
        status = "diaktifkan" if active == "1" else "dinonaktifkan"
        return f"User '{target_id}' {status}."

    if action == "reset_password":
        return f"Password user '{target_id}' direset oleh admin."

    if action == "change_password":
        return f"User '{target_id}' mengganti password sendiri."

    if action == "create_license":
        pkg  = _get("pkg") or ""
        end  = _get("end") or ""
        return f"Lisensi paket '{pkg.title()}' dibuat untuk '{target_id}'" + (f", berlaku hingga {end}" if end else "") + "."

    if action == "update_license":
        lid = target_id
        return f"Lisensi ID {lid} diperbarui (paket, status, atau tanggal expired)."

    if action == "toggle_license_status":
        status = _get("status") or "diubah"
        return f"Status lisensi ID {target_id} diubah menjadi '{status}'."

    if action == "bulk_suspend":
        ids = d.replace("user_ids=", "").strip("[]").replace(" ", "")
        count = len(ids.split(",")) if ids else "?"
        return f"{count} user disuspend sekaligus."

    if action == "bulk_activate":
        ids = d.replace("user_ids=", "").strip("[]").replace(" ", "")
        count = len(ids.split(",")) if ids else "?"
        return f"{count} user diaktifkan sekaligus."

    if action == "change_package":
        pkg  = _get("pkg") or "?"
        days = _get("days") or "?"
        return f"Paket user '{target_id}' diganti ke '{pkg.title()}', diperpanjang {days} hari."

    if action == "bulk_change_package":
        ids  = d.replace("user_ids=", "").strip("[]").replace(" ", "")
        pkg  = _get("pkg") or "?"
        count = len(ids.split(",")) if ids else "?"
        return f"{count} user dipindah ke paket '{pkg.title()}'."

    if action == "update_package":
        return f"Konfigurasi paket '{target_id}' diperbarui (nama, harga, atau deskripsi)."

    if action == "update_package_use_database":
        val = _get("use_database") or d
        status = "diaktifkan" if val in ("true", "1", "True") else "dinonaktifkan"
        return f"Akses database untuk paket '{target_id}' {status}."

    if action in ("update_tab_access", "bulk_update_tab_access"):
        # Parse dict sederhana dari detail
        import re, ast
        try:
            parsed = ast.literal_eval(d)
            lines = []
            for pkg, tabs in parsed.items():
                for tab, enabled in tabs.items():
                    status = "diaktifkan" if enabled else "dinonaktifkan"
                    lines.append(f"Tab '{tab}' pada paket '{pkg.title()}' {status}")
            return ". ".join(lines) + "." if lines else d
        except Exception:
            return f"Akses tab diperbarui untuk paket '{target_id}'."

    if action in ("reset_tab_access", "bulk_reset_all_tab_access"):
        return f"Semua pengaturan akses tab direset ke default untuk paket '{target_id}'."

    if action == "create_payment":
        return f"Pembayaran baru dicatat untuk user '{target_id}'."

    if action == "confirm_payment":
        user   = _get("user") or target_id
        amount = _get("amount")
        amt_str = f"Rp {int(amount):,}".replace(",", ".") if amount and amount.isdigit() else amount or ""
        return f"Pembayaran {amt_str} dari '{user}' dikonfirmasi dan lisensi diaktifkan."

    if action == "reject_payment":
        reason = _get("reason") or d
        return f"Pembayaran ID {target_id} ditolak. Alasan: {reason}."

    if action == "run_init_db":
        return "Struktur database diinisialisasi ulang oleh admin."

    # Fallback — bersihkan tanpa kode teknis
    clean = d.replace("user_ids=", "User ID: ").replace("pkg=", "paket: ").replace("days=", "hari: ")
    clean = clean.replace("=", ": ").replace("_", " ")
    return clean.strip() or "-"


def _tab_audit_log() -> None:
    _section("Riwayat Aktivitas (Audit Log)")

    st.caption(
        "Semua aktivitas penting di sistem tercatat di sini — login, perubahan user, "
        "lisensi, paket, dan pembayaran. Log tidak bisa dihapus."
    )

    # ── Filter ────────────────────────────────────────────────────
    fc1, fc2, fc3 = st.columns([3, 2, 1])
    with fc1:
        log_q = st.text_input("🔍 Cari berdasarkan nama user atau jenis aktivitas",
                              placeholder="contoh: admin, login, nadhira, paket...")
    with fc2:
        aksi_opts = [
            "Semua Aktivitas",
            "🟢 Login & Logout",
            "👤 Manajemen User",
            "📋 Lisensi",
            "💳 Pembayaran",
            "📦 Paket & Tab",
            "🛠️ Sistem",
        ]
        aksi_filter = st.selectbox("Kategori", aksi_opts)
    with fc3:
        log_limit = st.selectbox("Maks baris", [50, 100, 200, 500], index=1)

    logs = get_audit_log(limit=log_limit)

    # ── Filter kategori ───────────────────────────────────────────
    _kategori_map = {
        "🟢 Login & Logout" : {"login_success", "login_failed", "logout"},
        "👤 Manajemen User" : {"create_user", "update_user", "toggle_user_active",
                               "reset_password", "change_password",
                               "bulk_suspend", "bulk_activate"},
        "📋 Lisensi"        : {"create_license", "update_license", "toggle_license_status",
                               "change_package", "bulk_change_package"},
        "💳 Pembayaran"     : {"create_payment", "confirm_payment", "reject_payment"},
        "📦 Paket & Tab"    : {"update_package", "update_package_use_database",
                               "update_tab_access", "bulk_update_tab_access",
                               "reset_tab_access", "bulk_reset_all_tab_access"},
        "🛠️ Sistem"         : {"run_init_db", "export_data"},
    }
    if aksi_filter != "Semua Aktivitas":
        allowed = _kategori_map.get(aksi_filter, set())
        logs = [l for l in logs if l.get("action") in allowed]

    # ── Filter teks ───────────────────────────────────────────────
    if log_q:
        q = log_q.lower()
        logs = [l for l in logs if
                q in (l.get("actor") or "").lower() or
                q in _fmt_audit_action(l.get("action","")).lower() or
                q in (l.get("detail") or "").lower() or
                q in (l.get("target_id") or "").lower()]

    if not logs:
        st.info("Tidak ada aktivitas ditemukan untuk filter yang dipilih.")
        return

    # ── Statistik ringkas ─────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    logins = sum(1 for l in logs if l.get("action") == "login_success")
    failed = sum(1 for l in logs if l.get("action") == "login_failed")
    actors = len({l.get("actor") for l in logs if l.get("actor")})
    with m1:
        st.metric("Total Aktivitas", len(logs))
    with m2:
        st.metric("Login Berhasil", logins)
    with m3:
        st.metric("Login Gagal", failed)
    with m4:
        st.metric("User Terlibat", actors)

    st.divider()

    # ── Tabel log ─────────────────────────────────────────────────
    rows = []
    for l in logs:
        action = l.get("action", "")
        waktu_raw = l.get("created_at", "")

        # Format tanggal lebih ramah
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(waktu_raw)
            waktu = dt.strftime("%d %b %Y  %H:%M")
        except Exception:
            waktu = waktu_raw[:16]

        rows.append({
            "Waktu"      : waktu,
            "Dilakukan oleh" : l.get("actor") or "-",
            "Peran"      : "Admin" if l.get("role") == "admin" else "User",
            "Aktivitas"  : _fmt_audit_action(action),
            "Keterangan" : _fmt_audit_detail(
                action,
                l.get("detail") or "",
                l.get("target_type") or "",
                l.get("target_id") or "",
            ),
        })

    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Waktu"          : st.column_config.TextColumn(width="medium"),
            "Dilakukan oleh" : st.column_config.TextColumn(width="small"),
            "Peran"          : st.column_config.TextColumn(width="small"),
            "Aktivitas"      : st.column_config.TextColumn(width="medium"),
            "Keterangan"     : st.column_config.TextColumn(width="large"),
        },
    )

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Export ke CSV",
        csv,
        f"audit_log_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
        "text/csv",
    )


# ──────────────────────────────────────────────────────────────────
# TAB: DATABASE TOOLS
# ──────────────────────────────────────────────────────────────────

def _tab_database() -> None:
    _section("Alat Database")

    st.warning("⚠️ Operasi di halaman ini bersifat permanen. Pastikan kamu tahu apa yang dilakukan.")

    from config import DB_FILE
    import os

    if os.path.exists(DB_FILE):
        size_kb = os.path.getsize(DB_FILE) / 1024
        st.info(f"📁 Database: `{DB_FILE}` — {size_kb:.1f} KB")
    else:
        st.error("Database tidak ditemukan.")
        return

    st.subheader("Backup Database")
    if st.button("⬇️ Download Backup Database"):
        with open(DB_FILE, "rb") as f:
            st.download_button("Klik untuk download .db", f,
                               file_name=f"backup_{DB_FILE}",
                               mime="application/octet-stream")

    st.divider()

    st.subheader("Perbaiki Struktur Database")
    st.caption("Jalankan init_db() ulang — aman, hanya membuat tabel yang belum ada.")
    if st.button("🔧 Jalankan init_db()"):
        from database import init_db
        init_db()
        write_audit_log(get_current_username(), "run_init_db", role="admin")
        st.success("init_db() selesai dijalankan.")


# ──────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────

def build_admin_panel() -> None:
    if not is_admin():
        st.error("⛔ Akses ditolak. Halaman ini hanya untuk administrator.")
        return

    st.markdown(_ADMIN_CSS, unsafe_allow_html=True)

    st.markdown(
        f"""<div class="ap-topbar">
            <div class="title">🛠️ Admin Panel</div>
            <div class="user">Login sebagai <strong>{get_current_full_name()}</strong>
            &nbsp;|&nbsp;
            <span style="color:#8892a4">{get_current_username()}</span></div>
        </div>""",
        unsafe_allow_html=True,
    )

    # Hitung unread untuk badge di tab title
    _unread = count_unread_notifications()
    _notif_label = f"🔔 Notifikasi ({_unread})" if _unread > 0 else "🔔 Notifikasi"

    tabs = st.tabs([
        "📊 Overview",
        "👥 User",
        "⚡ User Actions",
        "🔑 Lisensi",
        "💳 Pembayaran",
        "📦 Paket & Harga",
        "📋 Audit Log",
        "🗄️ Database",
        _notif_label,
    ])

    with tabs[0]: _tab_overview()
    with tabs[1]: _tab_users()
    with tabs[2]: _tab_user_actions()
    with tabs[3]: _tab_licenses()
    with tabs[4]: _tab_payments()
    with tabs[5]: _tab_packages()
    with tabs[6]: _tab_audit_log()
    with tabs[7]: _tab_database()
    with tabs[8]: build_notifications_tab()