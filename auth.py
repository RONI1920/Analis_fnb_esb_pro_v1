# auth.py
# JWT AUTH + LOCAL STORAGE
# pip install PyJWT
# pip install streamlit-local-storage

from __future__ import annotations

# ── Auto-load .env SEBELUM import lain ───────────────────────────
# Wajib di baris paling atas agar FNB_JWT_SECRET terbaca sebelum
# konfigurasi JWT di bawah dieksekusi
try:
    import load_env  # noqa: F401 — side-effect: populate os.environ from .env
except Exception:
    pass

import os
import jwt
import streamlit as st

from datetime import datetime, timedelta

from streamlit_local_storage import LocalStorage

from database import (
    get_user_by_username,
    get_user_by_id,
    verify_password,
    update_last_login,
    update_user_password,
    get_active_license,
    write_audit_log,
)

from packages import (
    get_allowed_tabs,
    get_upgrade_suggestion,
    ADMIN_TAB,
)

# ─────────────────────────────────────────────
# LOCAL STORAGE — lazy init (harus di dalam runtime Streamlit)
# ─────────────────────────────────────────────

_localS = None

def _get_local_storage():
    global _localS
    if _localS is None:
        _localS = LocalStorage()
    return _localS

# ─────────────────────────────────────────────
# JWT CONFIG
# ─────────────────────────────────────────────

_secret_from_env = os.environ.get("FNB_JWT_SECRET", "")
if not _secret_from_env:
    try:
        _secret_from_env = st.secrets.get("FNB_JWT_SECRET", "")
    except Exception:
        # secrets.toml tidak ada — normal di lokal dev tanpa file tersebut
        _secret_from_env = ""

if not _secret_from_env or len(_secret_from_env) < 32:
    import warnings, os as _os
    _env_mode = _os.environ.get("FNB_ENV", "development")
    if _env_mode == "production":
        raise RuntimeError(
            "FATAL: FNB_JWT_SECRET tidak disetel atau <32 karakter di production. "
            "Jalankan: export FNB_JWT_SECRET=$(python -c 'import secrets; print(secrets.token_hex(32))')"
        )
    warnings.warn(
        "FNB_JWT_SECRET tidak disetel — menggunakan fallback DEV ONLY. "
        "Set FNB_ENV=production untuk enforcement.",
        stacklevel=2,
    )
    # FIX #005: Fallback development-only — TIDAK BOLEH di production
    _secret_from_env = "dev-only-secret-not-for-production-use-min32!"

SECRET_KEY = _secret_from_env
ALGORITHM  = "HS256"

# Baca durasi session dari config (bukan hardcoded)
from config import SESSION_CONFIG
_SESSION_HOURS   = SESSION_CONFIG["session_hours"]   # default 8 jam
_REMEMBER_DAYS   = SESSION_CONFIG["remember_days"]   # default 30 hari

# ─────────────────────────────────────────────
# SECURITY
# ─────────────────────────────────────────────

_MAX_LOGIN_ATTEMPTS = 5
_LOCKOUT_MINUTES = 15

# ─────────────────────────────────────────────
# SESSION KEYS
# ─────────────────────────────────────────────

_KEY_LOGGED_IN  = "auth_logged_in"
_KEY_USER_ID    = "auth_user_id"
_KEY_USERNAME   = "auth_username"
_KEY_ROLE       = "auth_role"
_KEY_FULL_NAME  = "auth_full_name"
_KEY_PKG_KEY    = "auth_package_key"
_KEY_LICENSE_ID = "auth_license_id"
_KEY_END_DATE   = "auth_license_end_date"
_KEY_STATUS     = "auth_license_status"
_KEY_TOKEN      = "auth_jwt_token"

# ─────────────────────────────────────────────
# JWT
# ─────────────────────────────────────────────

def create_token(user: dict, remember_me: bool = False) -> str:
    if remember_me:
        duration = timedelta(days=_REMEMBER_DAYS)
    else:
        duration = timedelta(hours=_SESSION_HOURS)
    payload = {
        "user_id"    : user["id"],
        "username"   : user["username"],
        "role"       : user["role"],
        "remember_me": remember_me,
        "exp"        : datetime.utcnow() + duration,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except Exception:
        return None


# ─────────────────────────────────────────────
# BRUTE FORCE PROTECTION
# ─────────────────────────────────────────────

def _get_login_attempts(username: str):
    """Baca jumlah attempt dan waktu lockout dari DB (persisten lintas tab/browser)."""
    try:
        from database import get_db_connection
        conn = get_db_connection()
        row = conn.execute(
            "SELECT attempts, locked_until FROM login_attempts WHERE username=?",
            (username.lower(),)
        ).fetchone()
        conn.close()
        if row:
            locked_until = datetime.fromisoformat(row[1]) if row[1] else None
            return int(row[0]), locked_until
    except Exception:
        pass
    # Fallback ke session state
    return (
        st.session_state.get(f"_login_attempts_{username}", 0),
        st.session_state.get(f"_login_lockout_{username}", None),
    )


def _record_failed_attempt(username: str):
    attempts = _get_login_attempts(username)[0] + 1
    lockout_until = None
    is_locked = False
    if attempts >= _MAX_LOGIN_ATTEMPTS:
        lockout_until = (datetime.now() + timedelta(minutes=_LOCKOUT_MINUTES)).isoformat()
        is_locked = True
    try:
        from database import get_db_connection
        conn = get_db_connection()
        conn.execute(
            """INSERT INTO login_attempts (username, attempts, locked_until, last_attempt)
               VALUES (?,?,?,datetime('now'))
               ON CONFLICT(username) DO UPDATE SET
                 attempts=excluded.attempts,
                 locked_until=excluded.locked_until,
                 last_attempt=excluded.last_attempt""",
            (username.lower(), attempts, lockout_until)
        )
        conn.commit()
        conn.close()
    except Exception:
        # Fallback ke session state
        key_attempts = f"_login_attempts_{username}"
        key_lockout  = f"_login_lockout_{username}"
        st.session_state[key_attempts] = attempts
        if is_locked:
            st.session_state[key_lockout] = datetime.now() + timedelta(minutes=_LOCKOUT_MINUTES)
    return attempts, is_locked


def _reset_login_attempts(username: str):
    try:
        from database import get_db_connection
        conn = get_db_connection()
        conn.execute("DELETE FROM login_attempts WHERE username=?", (username.lower(),))
        conn.commit()
        conn.close()
    except Exception:
        pass
    st.session_state.pop(f"_login_attempts_{username}", None)
    st.session_state.pop(f"_login_lockout_{username}", None)


def _is_locked_out(username: str):
    _, lockout_until = _get_login_attempts(username)
    if lockout_until is None:
        return False, 0
    if datetime.now() < lockout_until:
        sisa = int((lockout_until - datetime.now()).total_seconds())
        return True, sisa
    _reset_login_attempts(username)
    return False, 0


# ─────────────────────────────────────────────
# SESSION HELPERS
# ─────────────────────────────────────────────

def _init_session():
    defaults = {
        _KEY_LOGGED_IN : False,
        _KEY_USER_ID   : None,
        _KEY_USERNAME  : None,
        _KEY_ROLE      : None,
        _KEY_FULL_NAME : None,
        _KEY_PKG_KEY   : None,
        _KEY_LICENSE_ID: None,
        _KEY_END_DATE  : None,
        _KEY_STATUS    : None,
        _KEY_TOKEN     : None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _set_session(user: dict, license_info: dict | None, token: str = ""):
    st.session_state[_KEY_LOGGED_IN] = True
    st.session_state[_KEY_USER_ID]   = user["id"]
    st.session_state[_KEY_USERNAME]  = user["username"]
    st.session_state[_KEY_ROLE]      = user["role"]
    st.session_state[_KEY_FULL_NAME] = user.get("full_name") or user["username"]
    st.session_state[_KEY_TOKEN]     = token
    st.session_state["user_email"]   = user.get("email") or ""  # Untuk notifikasi

    if license_info:
        st.session_state[_KEY_PKG_KEY]    = license_info["package_key"]
        st.session_state[_KEY_LICENSE_ID] = license_info["id"]
        st.session_state[_KEY_END_DATE]   = license_info["end_date"]
        st.session_state[_KEY_STATUS]     = license_info["status"]
    else:
        st.session_state[_KEY_PKG_KEY]    = None
        st.session_state[_KEY_LICENSE_ID] = None
        st.session_state[_KEY_END_DATE]   = None
        st.session_state[_KEY_STATUS]     = "no_license"


def clear_session():
    # FIX #010: completely wipe session state on logout to prevent
    # data leakage between users sharing the same browser tab.
    try:
        _get_local_storage().deleteItem("fnb_jwt_token")
    except Exception:
        pass
    st.session_state.clear()
    st.session_state["auth_page"] = "pricing"


# ─────────────────────────────────────────────
# GETTERS
# ─────────────────────────────────────────────

def is_logged_in():
    return st.session_state.get(_KEY_LOGGED_IN, False)

def get_current_user_id():
    return st.session_state.get(_KEY_USER_ID)

def get_current_username():
    return st.session_state.get(_KEY_USERNAME, "")

def get_current_role():
    return st.session_state.get(_KEY_ROLE, "")

def get_current_full_name():
    return st.session_state.get(_KEY_FULL_NAME, "")

def get_current_package_key():
    return st.session_state.get(_KEY_PKG_KEY)

def get_current_license_end_date():
    return st.session_state.get(_KEY_END_DATE)

def get_current_license_status():
    return st.session_state.get(_KEY_STATUS)

def is_admin():
    return get_current_role() == "admin"


# ─────────────────────────────────────────────
# FIX 1: REFRESH LICENSE FROM DB
# Panggil ini di setiap app load agar session selalu sinkron dengan DB.
# Solusi untuk: "paket tidak update di dashboard setelah admin edit"
# ─────────────────────────────────────────────

def refresh_user_license():
    """
    Re-fetch lisensi aktif user dari DB dan update session state.
    Dipanggil di awal setiap render _build_main_app() agar perubahan
    yang dilakukan admin (ganti paket, perpanjang, suspend, dll.)
    langsung terlihat di dashboard user tanpa perlu logout-login ulang.
    """
    user_id = get_current_user_id()
    if not user_id or is_admin():
        return  # Admin tidak punya lisensi, skip

    try:
        license_info = get_active_license(user_id)
        if license_info:
            st.session_state[_KEY_PKG_KEY]    = license_info["package_key"]
            st.session_state[_KEY_LICENSE_ID] = license_info["id"]
            st.session_state[_KEY_END_DATE]   = license_info["end_date"]
            st.session_state[_KEY_STATUS]     = license_info["status"]
        else:
            # Lisensi tidak aktif / expired / tidak ada
            st.session_state[_KEY_PKG_KEY]    = None
            st.session_state[_KEY_LICENSE_ID] = None
            st.session_state[_KEY_END_DATE]   = None
            st.session_state[_KEY_STATUS]     = "no_license"
    except Exception:
        pass  # Jangan crash app jika DB error saat refresh


# ─────────────────────────────────────────────
# FIX 2: ACCESS CONTROL — pakai DB override
# Solusi untuk: "update tab access admin tidak berpengaruh ke user"
# ─────────────────────────────────────────────

def can_access_tab(tab_name: str):
    if is_admin():
        return True
    if tab_name == ADMIN_TAB:
        return False
    pkg = get_current_package_key()
    if pkg is None:
        return False

    # FIX: Ambil override dari DB agar perubahan admin panel langsung berlaku
    try:
        from database import get_package_tab_access
        db_overrides = get_package_tab_access(pkg)
    except Exception:
        db_overrides = {}

    return tab_name in get_allowed_tabs(pkg, db_overrides if db_overrides else None)


def get_tab_lock_message(tab_name: str):
    suggestion = get_upgrade_suggestion(tab_name)
    if suggestion:
        return f"Fitur tersedia mulai paket {suggestion}"
    return "Anda tidak memiliki akses"


# ─────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────

def attempt_login(username: str, password: str, remember_me: bool = False):
    if not username or not password:
        return False, "Username dan password wajib diisi."

    username = username.strip().lower()

    locked, sisa = _is_locked_out(username)
    if locked:
        menit = sisa // 60
        detik = sisa % 60
        return False, f"Terlalu banyak percobaan. Coba lagi {menit}m {detik}d"

    user = get_user_by_username(username)

    if user is None or not verify_password(password, user["password_hash"]):
        attempts, locked_now = _record_failed_attempt(username)
        try:
            write_audit_log(username, "login_failed", detail=f"attempt={attempts}")
        except Exception:
            pass
        if locked_now:
            return False, f"Akun terkunci {_LOCKOUT_MINUTES} menit"
        sisa = _MAX_LOGIN_ATTEMPTS - attempts
        return False, f"Username/password salah. Sisa percobaan: {sisa}"

    if not user.get("is_active", 1):
        return False, "Akun dinonaktifkan"

    _reset_login_attempts(username)

    # ── Auto-rehash: upgrade hash SHA256 lama → bcrypt/PBKDF2 ────
    # Jika hash yang tersimpan masih format lama (64-char hex SHA256),
    # perbarui ke format aman setelah login berhasil — transparan ke user.
    stored_hash = user["password_hash"]
    if not stored_hash.startswith(("$2b$", "$2a$", "$2y$", "pbkdf2$")):
        try:
            update_user_password(user["id"], password)
        except Exception:
            pass  # Jangan blokir login jika rehash gagal

    license_info = None
    if user["role"] != "admin":
        license_info = get_active_license(user["id"])

    token = create_token(user, remember_me=remember_me)

    # SAVE TOKEN TO LOCAL STORAGE
    _get_local_storage().setItem("fnb_jwt_token", token)

    _set_session(user, license_info, token=token)
    update_last_login(user["id"])

    try:
        write_audit_log(username, "login_success", role=user["role"])
    except Exception:
        pass

    return True, "Login berhasil"


# ─────────────────────────────────────────────
# UI — HALAMAN PRICING (landing page)
# ─────────────────────────────────────────────

def _build_pricing_gate():
    """
    Halaman pertama yang dilihat user yang belum login.
    Menampilkan paket + tombol Login dari ui/pricing.py.

    FIX 3: Proses return value dari build_pricing_page() agar tombol
    "Pilih Paket" berfungsi dan mengarahkan user ke halaman register/login.
    Sebelumnya return value dibuang sehingga tombol tidak bereaksi.
    """
    try:
        from ui.pricing import build_pricing_page
        chosen_package = build_pricing_page()

        # FIX: Tangani pilihan paket dari pricing page
        if chosen_package:
            st.session_state["selected_package"] = chosen_package
            if chosen_package == "enterprise":
                # Enterprise → halaman kontak khusus, bukan register biasa
                st.session_state["auth_page"] = "enterprise_contact"
            else:
                # Free & berbayar → register
                st.session_state["auth_page"] = "register"
            st.rerun()

    except Exception as e:
        # Fallback jika pricing page gagal load
        st.title("📊 FnB Analytics")
        st.subheader("Pilih paket yang sesuai kebutuhan bisnis Anda")
        st.divider()
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button("🔐 Login", use_container_width=True, type="primary"):
                st.session_state["auth_page"] = "login"
                st.rerun()


# ─────────────────────────────────────────────
# UI — HALAMAN LOGIN
# ─────────────────────────────────────────────

def _build_login_page(show_back_button: bool = True):
    """
    Form login.
    show_back_button=False digunakan oleh admin_app agar
    tidak ada tombol kembali ke pricing.
    """
    if show_back_button:
        if st.button("← Kembali ke Halaman Paket"):
            st.session_state["auth_page"] = "pricing"
            st.rerun()
        st.markdown(
            "<h2 style='text-align:center;margin-bottom:4px'>📊 FnB Analytics</h2>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='text-align:center;color:#9ca3af;margin-bottom:20px'>Masuk ke akun Anda</p>",
            unsafe_allow_html=True,
        )
    else:
        # Admin login — tampilan khusus
        st.markdown(
            """
            <div style='text-align:center;padding:20px 0 10px'>
                <div style='font-size:2.5rem'>🛡️</div>
                <h2 style='color:#f59e0b;margin:8px 0 4px;font-size:1.6rem'>
                    FnB Analytics Admin Login
                </h2>
                <p style='color:#6b7280;font-size:0.85rem'>
                    Halaman ini hanya untuk administrator sistem
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.form("login_form"):
        username    = st.text_input("Username")
        password    = st.text_input("Password", type="password")
        remember_me = st.checkbox(
            f"🔒 Ingat Saya selama {_REMEMBER_DAYS} hari",
            value=False,
            help=f"Tanpa centang: session berakhir dalam {_SESSION_HOURS} jam. "
                 f"Dengan centang: tetap login selama {_REMEMBER_DAYS} hari."
        )
        submitted = st.form_submit_button("Masuk", use_container_width=True)

    if submitted:
        with st.spinner("Memverifikasi..."):
            success, msg = attempt_login(username, password, remember_me=remember_me)
        if success:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

    # ── Link lupa password / username ────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔑 Lupa Password?", use_container_width=True):
            st.session_state["auth_page"] = "forgot_password"
            st.rerun()
    with col_b:
        if st.button("👤 Lupa Username?", use_container_width=True):
            st.session_state["auth_page"] = "forgot_username"
            st.rerun()


# ─────────────────────────────────────────────
# UI — HALAMAN REGISTER
# ─────────────────────────────────────────────

def _build_register_gate():
    """
    Halaman register. Flow:
    - Paket free  → buat akun + lisensi trial → redirect login
    - Paket bayar → buat akun + lisensi pending + payment record
                  → simpan registration_data ke session → redirect payment
    """
    from datetime import date, timedelta

    pkg_key = st.session_state.get("selected_package", "free")

    try:
        from ui.register import build_register_page
        reg_data = build_register_page(selected_package_key=pkg_key)
    except Exception as e:
        st.error(f"Halaman registrasi error: {e}")
        if st.button("← Kembali ke Halaman Paket"):
            st.session_state["auth_page"] = "pricing"
            st.session_state.pop("selected_package", None)
            st.rerun()
        return

    if reg_data is None:
        return

    from database import (
        create_user,
        create_license,
        create_payment,
        get_user_by_username,
    )

    username = reg_data["username"]

    if pkg_key == "free":
        # ── Paket gratis: buat akun + lisensi trial → login ───────
        ok, msg = create_user(
            username=username,
            email=reg_data["email"],
            password=reg_data["password"],
            role="user",
            full_name=reg_data["full_name"],
            phone=reg_data.get("phone", ""),
            company=reg_data.get("company", ""),
        )
        if not ok:
            st.error(f"Gagal membuat akun: {msg}")
            return

        user = get_user_by_username(username)
        if user:
            start = date.today()
            create_license(
                user_id=user["id"],
                package_key="free",
                status="trial",
                billing_cycle="trial",
                start_date=start.isoformat(),
                end_date=(start + timedelta(days=30)).isoformat(),
            )

        st.success(f"✅ Akun trial gratis berhasil dibuat! Selamat datang, {reg_data['full_name']}!")
        st.info("Silakan login menggunakan username dan password yang sudah dibuat.")
        st.session_state.pop("selected_package", None)
        st.session_state.pop("registration_data", None)
        st.session_state["auth_page"] = "login"
        st.rerun()

    elif pkg_key == "enterprise":
        # ── Enterprise: tidak langsung bayar, buat akun + arahkan ke halaman kontak ─
        ok, msg = create_user(
            username=username,
            email=reg_data["email"],
            password=reg_data["password"],
            role="user",
            full_name=reg_data["full_name"],
            phone=reg_data.get("phone", ""),
            company=reg_data.get("company", ""),
            notes="Enterprise — menunggu diskusi dengan admin",
        )
        if not ok:
            st.error(f"Gagal membuat akun: {msg}")
            return

        user = get_user_by_username(username)
        if user:
            start = date.today()
            create_license(
                user_id=user["id"],
                package_key="enterprise",
                status="pending",
                billing_cycle="custom",
                start_date=start.isoformat(),
                end_date=(start + timedelta(days=30)).isoformat(),
            )

        st.session_state["registration_data"] = reg_data
        st.session_state["auth_page"] = "enterprise_contact"
        st.rerun()

    else:
        # ── Paket berbayar: JANGAN buat akun/lisensi dulu sampai pembayaran dikonfirmasi ─
        # Data hanya disimpan di session state, belum masuk ke DB agar admin panel bersih
        from packages import PACKAGE_DEFINITIONS
        billing = st.session_state.get("billing_cycle", "monthly")
        try:
            from database import get_packages_merged
            cfg = get_packages_merged().get(pkg_key, PACKAGE_DEFINITIONS.get(pkg_key, {}))
        except Exception:
            cfg = PACKAGE_DEFINITIONS.get(pkg_key, {})
        amount = cfg.get("price_yearly" if billing == "yearly" else "price_monthly", 0)

        # Simpan data registrasi ke session SAJA (belum ke DB)
        reg_data["_amount"]  = amount
        reg_data["_billing"] = billing
        st.session_state["registration_data"] = reg_data
        st.session_state["pending_payment_id"] = None   # akan diisi setelah bukti dikirim
        st.session_state["auth_page"] = "payment"
        st.rerun()


def _build_payment_gate():
    """
    Halaman pembayaran setelah registrasi paket berbayar.
    Menampilkan QRIS + form upload bukti bayar.
    Setelah bukti dikirim → tampilkan success page → redirect login.
    """
    reg_data   = st.session_state.get("registration_data", {})
    pkg_key    = st.session_state.get("selected_package", "starter")
    billing    = st.session_state.get("billing_cycle", "monthly")
    payment_id = st.session_state.get("pending_payment_id")

    # Jika tidak ada data registrasi (misal akses langsung), kembali ke pricing
    if not reg_data:
        st.session_state["auth_page"] = "pricing"
        st.rerun()
        return

    try:
        from ui.payment import build_payment_page, build_payment_success_page
    except Exception as e:
        st.error(f"Halaman pembayaran error: {e}")
        if st.button("← Kembali ke Login"):
            st.session_state["auth_page"] = "login"
            st.rerun()
        return

    # Cek apakah bukti sudah dikirim sebelumnya
    if st.session_state.get("payment_submitted"):
        build_payment_success_page(pkg_key, reg_data.get("username", ""))
        return

    result = build_payment_page(
        user_data=reg_data,
        package_key=pkg_key,
        billing_cycle=billing,
        payment_id=payment_id,
    )

    if result and result.get("pending"):
        # ── Bukti pembayaran berhasil dikirim → BARU simpan user/lisensi/payment ke DB ──
        from datetime import date, timedelta
        from database import create_user, create_license, create_payment, get_user_by_username

        amount  = reg_data.get("_amount", 0)
        billing = reg_data.get("_billing", "monthly")

        ok, msg = create_user(
            username=reg_data["username"],
            email=reg_data["email"],
            password=reg_data["password"],
            role="user",
            full_name=reg_data["full_name"],
            phone=reg_data.get("phone", ""),
            company=reg_data.get("company", ""),
            notes=f"Paket {pkg_key} — menunggu konfirmasi pembayaran",
        )

        if not ok:
            st.error(f"Gagal menyimpan akun: {msg}")
            return

        user = get_user_by_username(reg_data["username"])
        if user:
            start = date.today()
            end = start + timedelta(days=365 if billing == "yearly" else 30)
            create_license(
                user_id=user["id"],
                package_key=pkg_key,
                status="pending",
                billing_cycle=billing,
                start_date=start.isoformat(),
                end_date=end.isoformat(),
            )
            pay_ok, _, pay_id = create_payment(
                user_id=user["id"],
                amount=amount,
                notes=result.get("notes", f"Registrasi baru paket {pkg_key} ({billing})"),
            )
            if pay_ok:
                st.session_state["pending_payment_id"] = pay_id

        st.session_state["payment_submitted"] = True
        st.rerun()


# ─────────────────────────────────────────────
# UI — PERINGATAN LISENSI
# ─────────────────────────────────────────────

_LICENSE_CSS = """
<style>
.lic-page {
    min-height: 80vh;
    display: flex;
    align-items: center;
    justify-content: center;
}
.lic-card {
    background: #0f1420;
    border: 1px solid #2d3348;
    border-radius: 20px;
    padding: 48px 40px 40px;
    max-width: 480px;
    width: 100%;
    text-align: center;
}
.lic-icon {
    font-size: 3.5rem;
    margin-bottom: 16px;
    line-height: 1;
}
.lic-title {
    font-size: 1.4rem;
    font-weight: 800;
    color: #f0f2f5;
    margin-bottom: 10px;
}
.lic-desc {
    font-size: 0.9rem;
    color: #9ca3af;
    line-height: 1.6;
    margin-bottom: 28px;
}
.lic-badge {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
    margin-bottom: 28px;
    letter-spacing: .04em;
}
.lic-badge-pending  { background:#3d2900; color:#fcd34d; border:1px solid #92400e; }
.lic-badge-expired  { background:#451a1a; color:#fca5a5; border:1px solid #7f1d1d; }
.lic-badge-no       { background:#1e3a5f; color:#93c5fd; border:1px solid #1e40af; }
.lic-badge-suspended{ background:#2d1b00; color:#fb923c; border:1px solid #92400e; }
.lic-divider {
    border: none;
    border-top: 1px solid #2d3348;
    margin: 24px 0;
}
.lic-username {
    font-size: 0.82rem;
    color: #6b7280;
    margin-top: 20px;
}
</style>
"""

def _build_license_warning():
    # Selalu refresh dari DB sebelum cek status.
    # Ini memastikan perubahan admin (aktifkan, suspend, ganti paket)
    # langsung terlihat tanpa user perlu logout-login ulang.
    refresh_user_license()

    status   = get_current_license_status()
    end_date = get_current_license_end_date()

    # Jika setelah refresh status sudah valid, langsung return — lanjut ke app.
    if status in ("active", "trial"):
        return

    _configs = {
        "no_license": {
            "icon": "🔑",
            "badge_class": "lic-badge-no",
            "badge_text": "BELUM ADA LISENSI",
            "title": "Akun Belum Aktif",
            "desc": (
                "Akun Anda belum memiliki lisensi aktif. "
                "Silakan hubungi admin atau pilih paket untuk mulai menggunakan layanan."
            ),
            "action_label": "🚀 Lihat Paket",
            "action": "pricing",
        },
        "expired": {
            "icon": "⏰",
            "badge_class": "lic-badge-expired",
            "badge_text": f"EXPIRED {end_date or ''}",
            "title": "Lisensi Anda Telah Berakhir",
            "desc": (
                "Masa aktif langganan Anda sudah habis. "
                "Perpanjang sekarang untuk melanjutkan akses ke semua fitur analitik."
            ),
            "action_label": "🔄 Perpanjang Sekarang",
            "action": "pricing",
        },
        "pending": {
            "icon": "⏳",
            "badge_class": "lic-badge-pending",
            "badge_text": "MENUNGGU KONFIRMASI",
            "title": "Pembayaran Sedang Diverifikasi",
            "desc": (
                "Bukti pembayaran Anda sudah diterima dan sedang diverifikasi oleh admin. "
                "Akses akan aktif otomatis setelah konfirmasi, biasanya dalam &lt;15 menit."
            ),
            "action_label": None,
            "action": None,
        },
        "suspended": {
            "icon": "🚫",
            "badge_class": "lic-badge-suspended",
            "badge_text": "AKUN DISUSPEND",
            "title": "Akun Anda Dinonaktifkan",
            "desc": (
                "Akun Anda sementara dinonaktifkan oleh administrator. "
                "Silakan hubungi admin untuk informasi lebih lanjut."
            ),
            "action_label": None,
            "action": None,
        },
    }

    cfg = _configs.get(status)
    if cfg is None:
        return

    st.markdown(_LICENSE_CSS, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown(f"""
        <div class="lic-card">
            <div class="lic-icon">{cfg["icon"]}</div>
            <div class="lic-badge {cfg["badge_class"]}">{cfg["badge_text"]}</div>
            <div class="lic-title">{cfg["title"]}</div>
            <div class="lic-desc">{cfg["desc"]}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if cfg["action_label"] and cfg["action"]:
            if st.button(cfg["action_label"], use_container_width=True, type="primary"):
                clear_session()
                st.session_state["auth_page"] = cfg["action"]
                st.rerun()

        if st.button("← Keluar", use_container_width=True, type="secondary"):
            clear_session()
            st.rerun()

    st.stop()

# ─────────────────────────────────────────────
# AUTH GUARD
# ─────────────────────────────────────────────

def require_auth(skip_pricing: bool = False):
    """
    Guard utama autentikasi.

    skip_pricing=True  → langsung tampil form login (untuk admin_app.py)
    skip_pricing=False → tampil halaman pricing dulu, lalu login (untuk app.py)
    """
    _init_session()

    # ── 1. Session aktif (sudah login) ───────────────────────────
    if is_logged_in():
        if not is_admin():
            _build_license_warning()
        return

    # ── 2. Coba pulihkan dari JWT di local storage ────────────────
    token = _get_local_storage().getItem("fnb_jwt_token")
    if token:
        payload = verify_token(token)
        if payload:
            user = get_user_by_id(payload["user_id"])
            if user and user.get("is_active", 1):
                license_info = None
                if user["role"] != "admin":
                    license_info = get_active_license(user["id"])
                _set_session(user, license_info, token=token)
                if not is_admin():
                    _build_license_warning()
                return

    # ── 3. Belum login ────────────────────────────────────────────
    if skip_pricing:
        # admin_app: langsung login, tanpa tombol kembali ke pricing
        _build_login_page(show_back_button=False)
    else:
        # app.py: pricing → register → login
        auth_page = st.session_state.get("auth_page", "pricing")

        if auth_page == "login":
            _build_login_page(show_back_button=True)

        elif auth_page == "register":
            _build_register_gate()

        elif auth_page == "payment":
            # Halaman pembayaran setelah register paket berbayar
            _build_payment_gate()

        elif auth_page == "forgot_password":
            from ui.forgot_password import build_forgot_password_page
            build_forgot_password_page()

        elif auth_page == "forgot_username":
            from ui.forgot_password import build_forgot_username_page
            build_forgot_username_page()

        elif auth_page == "enterprise_contact":
            # Enterprise contact page — premium UI/UX
            from ui.enterprise_contact import build_enterprise_contact_page
            build_enterprise_contact_page()

        else:
            # Default: tampilkan pricing page
            _build_pricing_gate()

    st.stop()