# database.py — Koneksi & Operasi Database SQLite
# VERSION: SaaS v7 — MULTI-TENANT ISOLATION ENFORCED
#
# PERUBAHAN KRITIS v7:
#   - Semua data table (gmv_data, cogs_data, dll) kini punya kolom user_id
#   - SETIAP query data WAJIB menyertakan WHERE user_id = ?
#   - Tanpa user_id yang valid, data tidak bisa dibaca/ditulis
#   - Isolasi total antar tenant / user SaaS

import os
try:
    from logger import capture_exception as _capture_exc, log as _log
except ImportError:
    def _capture_exc(e, ctx=""): pass
    class _log:
        @staticmethod
        def warning(m): pass
        @staticmethod  
        def info(m): pass
import secrets
import sqlite3
from datetime import datetime, date, timedelta

import pandas as pd
import streamlit as st

# ── Password hashing: bcrypt (production) dengan fallback PBKDF2 ──
try:
    import bcrypt as _bcrypt

    _USE_BCRYPT = True
except ImportError:
    import hashlib as _hashlib

    _USE_BCRYPT = False

from config import DB_FILE


def get_db_connection():
    """Membuat koneksi ke database SQLite dengan WAL mode untuk concurrency."""
    # FIX #022: WAL mode allows concurrent reads + non-blocking writes
    conn = sqlite3.connect(DB_FILE, check_same_thread=False, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Membuat skema tabel database jika belum ada."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # ── DATA TABLES: setiap tabel kini punya user_id (MULTI-TENANT) ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gmv_data (
                "user_id"               INTEGER NOT NULL,
                "Sales Date In"         DATETIME,
                "Sales Date Out"        DATETIME,
                "Sales Date"            DATETIME,
                "Order Time"            DATETIME,
                "Sales Number"          TEXT,
                "Bill Number"           TEXT,
                "Batch Order"           TEXT,
                "Table Section"         TEXT,
                "Table Name"            TEXT,
                "Brand"                 TEXT,
                "City"                  TEXT,
                "Area"                  TEXT,
                "Branch"                TEXT,
                "Sales Type"            TEXT,
                "Order Mode"            TEXT,
                "Visit Purpose"         TEXT,
                "Regular Member Code"   TEXT,
                "Regular Member Name"   TEXT,
                "Loyalty Member Code"   TEXT,
                "Loyalty Member Name"   TEXT,
                "Loyalty Member Type"   TEXT,
                "Employee Code"         TEXT,
                "Employee Name"         TEXT,
                "External Employee Code" TEXT,
                "External Employee Name" TEXT,
                "Customer Name"         TEXT,
                "Payment Method"        TEXT,
                "Menu Category"         TEXT,
                "Menu Category Detail"  TEXT,
                "Menu"                  TEXT,
                "Custom Menu Name"       TEXT,
                "Menu Code"             TEXT,
                "Menu Notes"            TEXT,
                "Qty"                   REAL,
                "Price"                 REAL,
                "Price (Net)"           REAL,
                "Subtotal"              REAL,
                "Discount"              REAL,
                "Service Charge"        REAL,
                "Tax"                   REAL,
                "VAT"                   REAL,
                "Total"                 REAL,
                "Nett Sales"            REAL,
                "Total Nett Sales"      REAL,
                "Bill Discount"         REAL,
                "Total Gross Sales"     REAL,
                "Total After Bill Discount" REAL,
                "Price (Pricelist)"     REAL,
                "Difference Price"      REAL,
                "Waiter"                TEXT,
                "Company"               TEXT,
                "Period"                TEXT
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cogs_data (
                "user_id"       INTEGER NOT NULL,
                "Sales Date"    DATETIME, "Branch" TEXT, "Menu Category" TEXT,
                "Menu"          TEXT, "Harga Jual" REAL, "COGS" REAL,
                "Qty"           REAL, "Total" REAL
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS waiter_data (
                "user_id"   INTEGER NOT NULL,
                "Bill Number" TEXT, "Waiter" TEXT, "Order Time" DATETIME,
                "Total After Bill Discount" REAL, "Branch" TEXT, "Sales Type" TEXT
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ulasan_data (
                "user_id"       INTEGER NOT NULL,
                "Nama"          TEXT, "Rating" TEXT, "Ulasan" TEXT, "Rating_Clean" INTEGER
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS purchase_data (
                "user_id"           INTEGER NOT NULL,
                "Purchase Date"     DATETIME, "Required Date" DATETIME,
                "Purchase Number"   TEXT, "Supplier Name" TEXT,
                "Category"          TEXT, "Sub Category" TEXT, "Product Name" TEXT,
                "PO Qty"            REAL, "Receipt Qty" REAL, "Pricelist Price" REAL,
                "Price"             REAL, "Discount" REAL, "VAT" REAL, "Total" REAL, "Branch" TEXT
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pl_data (
                "user_id"       INTEGER NOT NULL,
                "Account"       TEXT, "Description" TEXT, "Date" DATETIME,
                "Month_Name"    TEXT, "Year_Type" TEXT, "Value" REAL,
                "Branch"        TEXT, "Category" TEXT
            );
        """)

        # Index untuk performa multi-tenant query
        for tbl in [
            "gmv_data",
            "cogs_data",
            "waiter_data",
            "ulasan_data",
            "purchase_data",
            "pl_data",
        ]:
            cursor.execute(
                f'CREATE INDEX IF NOT EXISTS idx_{tbl}_user_id ON "{tbl}" (user_id)'
            )

        # ── TABEL SAAS: USER ACCOUNTS ─────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT UNIQUE NOT NULL,
                email       TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role        TEXT NOT NULL DEFAULT 'user',
                is_active   INTEGER NOT NULL DEFAULT 1,
                full_name   TEXT,
                phone       TEXT,
                company     TEXT,
                notes       TEXT,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login  DATETIME
            );
        """)

        # ── TABEL SAAS: PAKET ────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS packages (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                package_key     TEXT UNIQUE NOT NULL,
                name            TEXT NOT NULL,
                price_monthly   INTEGER NOT NULL DEFAULT 0,
                price_yearly    INTEGER NOT NULL DEFAULT 0,
                description     TEXT,
                is_active       INTEGER NOT NULL DEFAULT 1,
                use_database    INTEGER NOT NULL DEFAULT 1,
                created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # ── TABEL SAAS: LISENSI / LANGGANAN ──────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS licenses (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL REFERENCES users(id),
                package_key     TEXT NOT NULL,
                status          TEXT NOT NULL DEFAULT 'active',
                billing_cycle   TEXT NOT NULL DEFAULT 'monthly',
                start_date      DATE NOT NULL,
                end_date        DATE NOT NULL,
                price_paid      INTEGER NOT NULL DEFAULT 0,
                notes           TEXT,
                created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # ── TABEL SAAS: RIWAYAT PEMBAYARAN ───────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL REFERENCES users(id),
                license_id      INTEGER REFERENCES licenses(id),
                amount          INTEGER NOT NULL DEFAULT 0,
                method          TEXT,
                status          TEXT NOT NULL DEFAULT 'pending',
                proof_filename  TEXT,
                period_label    TEXT,
                confirmed_by    TEXT,
                confirmed_at    DATETIME,
                notes           TEXT,
                created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # ── TABEL SAAS: AUDIT LOG ─────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                actor       TEXT NOT NULL,
                role        TEXT,
                action      TEXT NOT NULL,
                target_type TEXT,
                target_id   TEXT,
                detail      TEXT,
                ip_address  TEXT,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # ── TABEL BARU: TAB ACCESS OVERRIDE ──────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS package_tab_access (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                package_key TEXT NOT NULL,
                tab_name    TEXT NOT NULL,
                is_enabled  INTEGER NOT NULL DEFAULT 1,
                updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(package_key, tab_name)
            );
        """)

        # ── TABEL: LOGIN ATTEMPTS (brute force protection) ────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS login_attempts (
                username     TEXT PRIMARY KEY,
                attempts     INTEGER NOT NULL DEFAULT 0,
                locked_until DATETIME,
                last_attempt DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # ── TABEL: SESSION TOKENS ─────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_tokens (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                token      TEXT    NOT NULL UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        # admin_notifications — dipisah karena SQLite tidak izinkan
        # multi-statement dalam satu cursor.execute()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_notifications (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                type       TEXT NOT NULL,
                title      TEXT NOT NULL,
                body       TEXT,
                ref_id     INTEGER,
                ref_table  TEXT,
                is_read    INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS otp_attempts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                username   TEXT NOT NULL,
                attempts   INTEGER DEFAULT 0,
                locked_until DATETIME,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ── MIGRASI: tambah user_id ke tabel data lama (v6→v7) ───
        for tbl in [
            "gmv_data",
            "cogs_data",
            "waiter_data",
            "ulasan_data",
            "purchase_data",
            "pl_data",
        ]:
            cursor.execute(f"PRAGMA table_info({tbl})")
            existing_cols = {row[1] for row in cursor.fetchall()}
            if "user_id" not in existing_cols:
                # Tambah kolom user_id, default 0 (admin) untuk data lama
                cursor.execute(
                    f'ALTER TABLE "{tbl}" ADD COLUMN user_id INTEGER NOT NULL DEFAULT 0'
                )
                cursor.execute(
                    f'CREATE INDEX IF NOT EXISTS idx_{tbl}_user_id ON "{tbl}" (user_id)'
                )

        # ── MIGRASI: tambah use_database jika DB lama belum punya ──
        cursor.execute("PRAGMA table_info(packages)")
        existing_cols = {row[1] for row in cursor.fetchall()}
        if "use_database" not in existing_cols:
            cursor.execute(
                "ALTER TABLE packages ADD COLUMN use_database INTEGER NOT NULL DEFAULT 1"
            )
            cursor.execute(
                "UPDATE packages SET use_database = 0 WHERE package_key = 'free'"
            )

        # ── MIGRASI: kolom baru tabel payments (v3) ───────────────
        cursor.execute("PRAGMA table_info(payments)")
        pay_cols = {row[1] for row in cursor.fetchall()}
        for col, typedef in [
            ("proof_image", "BLOB"),
            ("proof_mimetype", "TEXT"),
            ("rejected_reason", "TEXT"),
        ]:
            if col not in pay_cols:
                cursor.execute(f"ALTER TABLE payments ADD COLUMN {col} {typedef}")

        # ── MIGRASI: kolom baru tabel users (v3) ──────────────────
        cursor.execute("PRAGMA table_info(users)")
        user_cols = {row[1] for row in cursor.fetchall()}
        for col, typedef in [
            ("reset_token", "TEXT"),
            ("reset_token_expiry", "DATETIME"),
            ("username_hint", "TEXT"),
        ]:
            if col not in user_cols:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {typedef}")

        # ── SEED: Buat akun admin default jika belum ada ──────────
        cursor.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1;")
        if cursor.fetchone() is None:
            # Prioritas password seed:
            # 1. Env var FNB_ADMIN_PASSWORD (untuk deployment custom)
            # 2. Fallback: "Admin@2024" (mudah diingat, cukup kuat untuk dev/staging)
            # 
            # PENTING: segera ganti password ini via menu Profile setelah login pertama!
            # Untuk reset password jika lupa: jalankan script reset_admin.py
            import os as _os
            _tmp_pw = _os.environ.get("FNB_ADMIN_PASSWORD", "Admin@2024")
            default_hash = _hash_password(_tmp_pw)
            cursor.execute(
                """INSERT INTO users
                       (username, email, password_hash, role, full_name, notes)
                   VALUES (?, ?, ?, 'admin', 'Super Admin',
                           'Ganti password setelah login pertama!')""",
                ("admin", "admin@fnbdashboard.id", default_hash),
            )
            import logging as _log
            _log.info(
                "ADMIN SEED: username=admin | "
                "Password: " + _tmp_pw + " | "
                "Ganti segera via menu Profile!"
            )

        # ── SEED: Isi tabel packages dari PACKAGE_DEFINITIONS ─────
        try:
            from packages import PACKAGE_DEFINITIONS

            for key, cfg in PACKAGE_DEFINITIONS.items():
                cursor.execute("SELECT id FROM packages WHERE package_key = ?", (key,))
                if cursor.fetchone() is None:
                    cursor.execute(
                        """
                        INSERT INTO packages
                            (package_key, name, price_monthly, price_yearly,
                             description, use_database)
                        VALUES (?, ?, ?, ?, ?, ?);
                    """,
                        (
                            key,
                            cfg["name"],
                            cfg["price_monthly"],
                            cfg["price_yearly"],
                            cfg["description"],
                            int(cfg.get("use_database", False)),
                        ),
                    )
        except ImportError:
            pass

        # FIX #021: add indexes for frequently queried columns
        for idx_sql in [
            "CREATE INDEX IF NOT EXISTS idx_users_username   ON users(username)",
            "CREATE INDEX IF NOT EXISTS idx_users_email      ON users(email)",
            "CREATE INDEX IF NOT EXISTS idx_licenses_user_status ON licenses(user_id, status, end_date)",
            "CREATE INDEX IF NOT EXISTS idx_payments_status  ON payments(status)",
            "CREATE INDEX IF NOT EXISTS idx_payments_user    ON payments(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_created    ON audit_log(created_at)",
        ]:
            cursor.execute(idx_sql)

        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        st.error(f"Gagal inisialisasi database: {e}")
    finally:
        if conn:
            conn.close()


def _get_current_user_id_safe() -> int | None:
    """
    Ambil user_id dari session state secara aman.
    Harus dipanggil dalam konteks Streamlit runtime.
    Return None jika tidak ada sesi aktif.
    """
    try:
        return st.session_state.get("auth_user_id")
    except Exception:
        return None


def _filter_columns_to_schema(df: pd.DataFrame, table_name: str, conn) -> pd.DataFrame:
    """Helper: filter kolom DataFrame agar sesuai skema tabel DB (kecuali user_id)."""
    db_columns = pd.read_sql_query(
        f'SELECT * FROM "{table_name}" LIMIT 0', conn
    ).columns.tolist()

    # Hapus user_id dari daftar kolom yang di-filter — user_id diisi manual
    schema_cols = [c for c in db_columns if c != "user_id"]
    keep = [c for c in df.columns if c in schema_cols]
    return df[keep]


def save_dataframe_to_db(df: pd.DataFrame, table_name: str, user_id: int = None):
    """Simpan DataFrame ke tabel (mode replace untuk user ini)."""
    if df is None or df.empty:
        st.error(f"DataFrame {table_name} kosong, tidak disimpan.")
        return

    uid = user_id or _get_current_user_id_safe()
    if not uid:
        st.error("Tidak ada sesi pengguna aktif. Silakan login ulang.")
        return

    conn = None
    try:
        conn = get_db_connection()
        df_clean = _filter_columns_to_schema(df, table_name, conn)
        df_clean = df_clean.copy()
        df_clean.insert(0, "user_id", uid)

        # Hapus data lama user ini, lalu insert baru
        conn.execute(f'DELETE FROM "{table_name}" WHERE user_id = ?', (uid,))
        df_clean.to_sql(table_name, conn, if_exists="append", index=False)
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        st.error(f"Gagal simpan {table_name}: {e}")
    finally:
        if conn:
            conn.close()


# ── Anti-duplikat strategy ────────────────────────────────────────
#
# ROOT CAUSE ANALYSIS (versi final):
# Dedup berbasis SUBSET KOLOM (misal Sales Number+Bill Number+Menu+Qty)
# TERLALU AGRESIF dan menyebabkan REVENUE HILANG karena:
#   → Restoran sering pesan menu yang SAMA berkali-kali dalam 1 bill
#   → 5x Ayam Goreng = 5 baris identik di kolom dedup key
#   → 4 dari 5 baris dihapus → revenue hilang ~5-10%
#
# SOLUSI BENAR: 
#   - TIDAK pakai dedup berbasis subset kolom
#   - Untuk gmv_data: TIDAK dedup sama sekali (data POS sudah final & akurat)
#   - Untuk data lain: dedup hanya jika SEMUA kolom string/numeric identik
#   - Anti-duplikat upload berulang sudah dihandle oleh DELETE BETWEEN range tanggal
#
# Kosongkan _DEDUP_KEYS untuk gmv_data agar tidak ada false-positive dedup:
_DEDUP_KEYS: dict[str, list[str]] = {
    "gmv_data": [],          # ← SENGAJA KOSONG: data POS sudah final, jangan dedup
    "cogs_data": ["Sales Date", "Branch", "Menu", "Menu Category"],
    "waiter_data": ["Bill Number", "Waiter", "Order Time"],
    "ulasan_data": ["Nama", "Ulasan", "Rating"],
    "purchase_data": ["Purchase Number", "Product Name", "Purchase Date"],
    "pl_data": ["Account", "Date", "Branch"],
}


def save_dataframe_smart_append(
    df: pd.DataFrame, table_name: str, date_col_name: str, user_id: int = None
):
    """
    Simpan DataFrame ke DB dengan anti-duplikat + isolasi per user_id.

    FIX BUG: Fungsi ini menerima df LANGSUNG dari loader (tanpa filter dashboard).
    Filter periode/cabang/menu hanya diterapkan di dashboard (tab1_sales, dll),
    TIDAK di sini. Semua data dari file disimpan ke DB secara lengkap.
    """
    if isinstance(df, tuple):
        df = df[0] if df else None

    if df is None or df.empty:
        st.error(f"DataFrame {table_name} kosong, tidak disimpan.")
        return

    uid = user_id or _get_current_user_id_safe()
    if not uid:
        st.error("Tidak ada sesi pengguna aktif. Silakan login ulang.")
        return

    conn_schema = None
    try:
        conn_schema = get_db_connection()
        df_clean = _filter_columns_to_schema(df, table_name, conn_schema)
    except Exception as e:
        st.error(f"Gagal mencocokkan skema: {e}")
        return
    finally:
        if conn_schema:
            conn_schema.close()

    if date_col_name not in df_clean.columns:
        st.error(f"Kolom tanggal '{date_col_name}' tidak ditemukan.")
        return

    # ── 1. Parse & sort by date ───────────────────────────────────
    try:
        df_clean[date_col_name] = pd.to_datetime(df_clean[date_col_name])
        df_clean = df_clean.sort_values(date_col_name).reset_index(drop=True)
        min_date = df_clean[date_col_name].min().strftime("%Y-%m-%d %H:%M:%S")
        max_date = df_clean[date_col_name].max().strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        st.error(f"Gagal proses kolom tanggal '{date_col_name}': {e}")
        return

    # ── 2. Dedup di level DataFrame ───────────────────────────────
    # PENTING: jika _DEDUP_KEYS[table] = [] → SKIP dedup sepenuhnya.
    # Untuk gmv_data: tidak dedup karena data POS sudah final.
    # DROP_DUPLICATES berbasis subset kolom menyebabkan false-positive
    # (misal: 5x Ayam Goreng dalam 1 bill → 4 baris dihapus → revenue hilang).
    _configured_keys = _DEDUP_KEYS.get(table_name, None)  # None = belum dikonfigurasi
    if _configured_keys is None:
        # Tabel belum ada di _DEDUP_KEYS → dedup semua kolom (aman)
        dedup_keys = None
        rows_before = len(df_clean)
        df_clean = df_clean.drop_duplicates(keep="last")
        dupes_removed = rows_before - len(df_clean)
    elif len(_configured_keys) == 0:
        # Dikonfigurasi eksplisit kosong → SKIP dedup sama sekali
        dedup_keys = []
        dupes_removed = 0
    else:
        # Ada dedup keys dikonfigurasi → filter ke kolom yang ada di df
        dedup_keys = [k for k in _configured_keys if k in df_clean.columns]
        rows_before = len(df_clean)
        df_clean = (
            df_clean.drop_duplicates(subset=dedup_keys, keep="last")
            if dedup_keys
            else df_clean
        )
        dupes_removed = rows_before - len(df_clean)

    # ── 3. Tambahkan user_id ──────────────────────────────────────
    df_clean = df_clean.copy()
    df_clean.insert(0, "user_id", uid)

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # ── 4. Hapus range yang sama MILIK USER INI saja ──────────
        cursor.execute(
            f'DELETE FROM "{table_name}" WHERE user_id = ? AND "{date_col_name}" BETWEEN ? AND ?',
            (uid, min_date, max_date),
        )
        deleted = cursor.rowcount

        df_clean.to_sql(table_name, conn, if_exists="append", index=False)
        conn.commit()

        # FIX 3: verifikasi jumlah rows yang benar-benar tersimpan
        cursor.execute(
            f'SELECT COUNT(*) FROM "{table_name}" WHERE user_id = ? AND "{date_col_name}" BETWEEN ? AND ?',
            (uid, min_date, max_date)
        )
        verified_rows = cursor.fetchone()[0]

        # Notifikasi
        parts = [f"✅ {len(df_clean):,} baris data {table_name} disimpan"]
        if verified_rows != len(df_clean):
            parts.append(f"⚠️ Terverifikasi: {verified_rows:,} baris (ada {len(df_clean)-verified_rows:,} baris tidak tersimpan)")
        parts.append(f"📅 {min_date[:10]} → {max_date[:10]}")
        if deleted > 0:
            parts.append(f"🔄 {deleted:,} baris lama diganti")
        if dupes_removed > 0:
            parts.append(f"🧹 {dupes_removed:,} duplikat dihapus")
        msg_text = " · ".join(parts)

        notif_sig_key = f"last_upload_sig_{table_name}"
        notif_sig = f"{table_name}_{len(df_clean)}_{min_date[:10]}_{max_date[:10]}"
        if st.session_state.get(notif_sig_key) != notif_sig:
            st.session_state[notif_sig_key] = notif_sig
            queue = st.session_state.setdefault("notif_queue", [])
            queue.append(msg_text)

        # Email notif (opsional)
        try:
            from services.notifier import notify_upload_success
            from auth import get_current_username

            username = get_current_username() or "user"
            user_email = st.session_state.get("user_email")
            notify_upload_success(
                to_email=user_email,
                username=username,
                table=table_name,
                rows=len(df_clean),
                min_date=min_date[:10],
                max_date=max_date[:10],
                dupes=dupes_removed,
            )
        except Exception:
            pass

    except Exception as e:
        st.error(f"Gagal simpan {table_name}: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


@st.cache_data(ttl=30)
def load_dataframe_from_db(
    table_name: str,
    date_cols: list | None = None,
    numeric_cols_config: dict | None = None,
    sort_by: str = "",
    user_id: int = None,  # ← WAJIB diisi untuk isolasi data
) -> pd.DataFrame | None:
    """
    Muat DataFrame dari tabel DB, diurutkan ascending by date.
    HANYA mengembalikan data milik user_id yang diberikan.
    """
    if not os.path.exists(DB_FILE):
        return None

    uid = user_id or _get_current_user_id_safe()
    if not uid:
        return None

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # FIX #001: parameterise sqlite_master; whitelist table_name for PRAGMA
        _ALLOWED_TABLES_LD = {
            "gmv_data","cogs_data","waiter_data",
            "ulasan_data","purchase_data","pl_data",
        }
        if table_name not in _ALLOWED_TABLES_LD:
            return None
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        if cursor.fetchone() is None:
            return None

        # Pastikan kolom user_id ada (table_name whitelisted above)
        cursor.execute(f"PRAGMA table_info({table_name})")
        cols = {row[1] for row in cursor.fetchall()}
        if "user_id" not in cols:
            return None

        order_col = sort_by or (
            (date_cols[0] if date_cols else "") if date_cols else ""
        )
        if order_col:
            query = f'SELECT * FROM "{table_name}" WHERE user_id = ? ORDER BY "{order_col}" ASC'
        else:
            query = f'SELECT * FROM "{table_name}" WHERE user_id = ?'

        df = pd.read_sql_query(query, conn, params=(uid,))
        if df.empty:
            return None

        # Drop user_id dari output (tidak perlu tampil ke user)
        if "user_id" in df.columns:
            df = df.drop(columns=["user_id"])

        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        for col_name, col_type in (numeric_cols_config or {}).items():
            if col_name in df.columns:
                if col_type == "int":
                    df[col_name] = (
                        pd.to_numeric(df[col_name], errors="coerce")
                        .fillna(0)
                        .astype(int)
                    )
                else:
                    df[col_name] = pd.to_numeric(df[col_name], errors="coerce").fillna(
                        0
                    )

        return df
    except Exception:
        return None
    finally:
        if conn:
            conn.close()


# ══════════════════════════════════════════════════════════════════
# DATABASE MANAGEMENT FUNCTIONS
# ══════════════════════════════════════════════════════════════════

DATA_TABLES = [
    "gmv_data",
    "cogs_data",
    "waiter_data",
    "ulasan_data",
    "purchase_data",
    "pl_data",
]

_DATE_COL_MAP = {
    "gmv_data": "Sales Date In",
    "cogs_data": "Sales Date",
    "waiter_data": "Order Time",
    "ulasan_data": None,
    "purchase_data": "Purchase Date",
    "pl_data": "Date",
}


def get_db_table_info(user_id: int = None) -> dict:
    """
    Kembalikan info tiap tabel data untuk user tertentu.
    Return: {table_name: {rows, min_date, max_date, size_kb, exists}}
    """
    uid = user_id or _get_current_user_id_safe() or 0
    result = {}
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        for tbl in DATA_TABLES:
            info = {
                "rows": 0,
                "min_date": None,
                "max_date": None,
                "size_kb": 0,
                "exists": False,
            }
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (tbl,)
            )
            if cursor.fetchone() is None:
                result[tbl] = info
                continue
            info["exists"] = True
            cursor.execute(f'SELECT COUNT(*) FROM "{tbl}" WHERE user_id = ?', (uid,))
            info["rows"] = cursor.fetchone()[0]
            date_col = _DATE_COL_MAP.get(tbl)
            if date_col:
                try:
                    cursor.execute(
                        f'SELECT MIN("{date_col}"), MAX("{date_col}") FROM "{tbl}" WHERE user_id = ?',
                        (uid,),
                    )
                    row = cursor.fetchone()
                    if row:
                        info["min_date"] = str(row[0])[:10] if row[0] else None
                        info["max_date"] = str(row[1])[:10] if row[1] else None
                except Exception:
                    pass
            try:
                cursor.execute("PRAGMA page_count")
                pc = cursor.fetchone()[0]
                cursor.execute("PRAGMA page_size")
                ps = cursor.fetchone()[0]
                info["size_kb"] = round(pc * ps / 1024 / len(DATA_TABLES), 1)
            except Exception:
                pass
            result[tbl] = info
    except Exception:
        for tbl in DATA_TABLES:
            result.setdefault(
                tbl,
                {
                    "rows": 0,
                    "min_date": None,
                    "max_date": None,
                    "size_kb": 0,
                    "exists": False,
                },
            )
    finally:
        if conn:
            conn.close()
    return result


def clear_table(table_name: str, user_id: int = None) -> tuple[bool, str]:
    """Hapus semua data dari satu tabel MILIK USER INI SAJA."""
    if table_name not in DATA_TABLES:
        return False, f"Tabel '{table_name}' tidak dikenali."
    uid = user_id or _get_current_user_id_safe()
    if not uid:
        return False, "Sesi tidak valid."
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f'DELETE FROM "{table_name}" WHERE user_id = ?', (uid,))
        deleted = cursor.rowcount
        conn.commit()
        load_dataframe_from_db.clear()
        return True, f"{deleted:,} baris dihapus dari {table_name}."
    except Exception as e:
        if conn:
            conn.rollback()
        return False, str(e)
    finally:
        if conn:
            conn.close()


def clear_all_data_tables(user_id: int = None) -> tuple[bool, str, dict]:
    """
    Hapus SEMUA tabel data bisnis milik USER INI SAJA.
    Tabel auth (users, sessions, dll) TIDAK tersentuh.
    """
    uid = user_id or _get_current_user_id_safe()
    if not uid:
        return False, "Sesi tidak valid.", {}
    conn = None
    report = {}
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        for tbl in DATA_TABLES:
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (tbl,)
            )
            if cursor.fetchone() is None:
                report[tbl] = 0
                continue
            cursor.execute(f'DELETE FROM "{tbl}" WHERE user_id = ?', (uid,))
            report[tbl] = cursor.rowcount
        conn.commit()
        load_dataframe_from_db.clear()
        total_deleted = sum(report.values())
        return (
            True,
            f"Semua data dihapus. Total {total_deleted:,} baris dihapus.",
            report,
        )
    except Exception as e:
        if conn:
            conn.rollback()
        return False, str(e), report
    finally:
        if conn:
            conn.close()


def sync_dataframe_to_db(
    df, table_name: str, user_id: int = None
) -> tuple[bool, str, dict]:
    """
    Sinkronisasi penuh: REPLACE seluruh data tabel user ini dengan data upload baru.
    """
    if df is None or (hasattr(df, "empty") and df.empty):
        return False, f"Data {table_name} kosong.", {}

    if isinstance(df, tuple):
        df = df[0] if df else None
    if df is None:
        return False, "Data tidak valid.", {}

    uid = user_id or _get_current_user_id_safe()
    if not uid:
        return False, "Sesi tidak valid.", {}

    conn = None
    try:
        conn = get_db_connection()
        df_clean = _filter_columns_to_schema(df, table_name, conn)

        _cfg2 = _DEDUP_KEYS.get(table_name, None)
        if _cfg2 is None:
            rows_before = len(df_clean)
            df_clean = df_clean.drop_duplicates(keep="last")
            dupes_removed = rows_before - len(df_clean)
        elif len(_cfg2) == 0:
            dupes_removed = 0  # skip dedup (misal gmv_data)
        else:
            dedup_keys = [k for k in _cfg2 if k in df_clean.columns]
            rows_before = len(df_clean)
            df_clean = df_clean.drop_duplicates(subset=dedup_keys, keep="last") if dedup_keys else df_clean
            dupes_removed = rows_before - len(df_clean)

        cursor = conn.cursor()
        cursor.execute(f'SELECT COUNT(*) FROM "{table_name}" WHERE user_id = ?', (uid,))
        old_rows = cursor.fetchone()[0]

        # Hapus data lama user ini
        cursor.execute(f'DELETE FROM "{table_name}" WHERE user_id = ?', (uid,))

        # Insert baru dengan user_id
        df_clean = df_clean.copy()
        df_clean.insert(0, "user_id", uid)
        df_clean.to_sql(table_name, conn, if_exists="append", index=False)
        conn.commit()

        load_dataframe_from_db.clear()

        stats = {
            "rows_new": len(df_clean),
            "rows_old": old_rows,
            "dupes_removed": dupes_removed,
        }
        msg = (
            f"✅ Sinkronisasi {table_name} selesai. "
            f"{len(df_clean):,} baris baru (lama: {old_rows:,}, duplikat dihapus: {dupes_removed:,})"
        )
        queue = st.session_state.setdefault("notif_queue", [])
        queue.append(msg)
        return True, msg, stats
    except Exception as e:
        if conn:
            conn.rollback()
        return False, str(e), {}
    finally:
        if conn:
            conn.close()


# ══════════════════════════════════════════════════════════════════
# SAAS HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════


def _hash_password(password: str) -> str:
    if _USE_BCRYPT:
        return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt(rounds=12)).decode()
    else:
        salt = secrets.token_hex(16)
        dk = _hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000)
        return f"pbkdf2${salt}${dk.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    if not hashed:
        return False
    if hashed.startswith(("$2b$", "$2a$", "$2y$")):
        if _USE_BCRYPT:
            try:
                return _bcrypt.checkpw(password.encode(), hashed.encode())
            except Exception:
                return False
        return False
    if hashed.startswith("pbkdf2$"):
        try:
            _, salt, stored_hex = hashed.split("$", 2)
            dk = _hashlib.pbkdf2_hmac(
                "sha256", password.encode(), salt.encode(), 260_000
            )
            return dk.hex() == stored_hex
        except Exception:
            return False
    _OLD_SALT = "fnb_dashboard_salt_v1"
    import hashlib as _hl

    old_hash = _hl.sha256(f"{_OLD_SALT}{password}".encode()).hexdigest()
    return old_hash == hashed


def generate_temp_password() -> str:
    return secrets.token_urlsafe(10)


# ──────────────────────────────────────────────────────────────────
# USER CRUD
# ──────────────────────────────────────────────────────────────────


def get_user_by_username(username: str) -> dict | None:
    conn = get_db_connection()
    try:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> dict | None:
    conn = get_db_connection()
    try:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_all_users() -> list[dict]:
    conn = get_db_connection()
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def create_user(
    username: str,
    email: str,
    password: str,
    role: str = "user",
    full_name: str = "",
    phone: str = "",
    company: str = "",
    notes: str = "",
) -> tuple[bool, str]:
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO users
                (username, email, password_hash, role, full_name, phone, company, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                username,
                email,
                _hash_password(password),
                role,
                full_name,
                phone,
                company,
                notes,
            ),
        )
        conn.commit()

        # Notifikasi admin: user baru
        try:
            push_admin_notification(
                type="new_user",
                title=f"👤 User Baru — {username}",
                body=f"Email: {email} | Nama: {full_name or '-'} | Perusahaan: {company or '-'}",
                ref_table="users",
            )
        except Exception:
            pass

        return True, f"User '{username}' berhasil dibuat."
    except sqlite3.IntegrityError as e:
        if "username" in str(e):
            return False, f"Username '{username}' sudah digunakan."
        if "email" in str(e):
            return False, f"Email '{email}' sudah terdaftar."
        return False, str(e)
    finally:
        conn.close()


def update_user(user_id: int, **fields) -> tuple[bool, str]:
    # FIX #006: 'role' removed from allowed — use admin_update_user() for role changes
    allowed = {"full_name", "email", "phone", "company", "notes", "is_active"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False, "Tidak ada field valid untuk diupdate."
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [user_id]
    conn = get_db_connection()
    try:
        conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
        conn.commit()
        return True, "Data user berhasil diupdate."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def admin_update_user(user_id: int, **fields) -> tuple[bool, str]:
    """Admin-only: can change role, is_active, and all user fields."""
    # FIX #006: separate function that explicitly requires admin role
    try:
        import streamlit as _st
        from auth import is_admin as _is_admin
        if not _is_admin():
            return False, "Akses ditolak — hanya admin."
    except Exception:
        pass  # allow in non-Streamlit context (tests, CLI)
    allowed = {"full_name", "email", "phone", "company", "notes", "is_active", "role"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False, "Tidak ada field valid untuk diupdate."
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [user_id]
    conn = get_db_connection()
    try:
        conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
        conn.commit()
        return True, "Data user berhasil diupdate."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def update_user_password(user_id: int, new_password: str) -> tuple[bool, str]:
    conn = get_db_connection()
    try:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (_hash_password(new_password), user_id),
        )
        conn.commit()
        return True, "Password berhasil diperbarui."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def update_last_login(user_id: int) -> None:
    conn = get_db_connection()
    try:
        conn.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user_id,)
        )
        conn.commit()
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────
# LICENSE CRUD
# ──────────────────────────────────────────────────────────────────


def get_active_license(user_id: int) -> dict | None:
    conn = get_db_connection()
    try:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT l.*, u.username, u.email
            FROM   licenses l
            JOIN   users    u ON u.id = l.user_id
            WHERE  l.user_id = ?
              AND  l.status IN ('active', 'trial')
              AND  l.end_date >= date('now')
            ORDER  BY l.end_date DESC
            LIMIT  1
        """,
            (user_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_all_licenses() -> list[dict]:
    conn = get_db_connection()
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT l.*,
                   u.username, u.email, u.full_name, u.company,
                   p.name AS package_name
            FROM   licenses l
            JOIN   users    u ON u.id = l.user_id
            LEFT JOIN packages p ON p.package_key = l.package_key
            ORDER  BY l.end_date ASC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_expiring_soon(days: int = 7) -> list[dict]:
    conn = get_db_connection()
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT l.*, u.username, u.email, u.full_name
            FROM   licenses l
            JOIN   users    u ON u.id = l.user_id
            WHERE  l.status IN ('active', 'trial')
              AND  l.end_date BETWEEN date('now') AND date('now', ? || ' days')
            ORDER  BY l.end_date ASC
        """,
            (str(days),),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def create_license(
    user_id: int,
    package_key: str,
    start_date: str,
    end_date: str,
    status: str = "active",
    billing_cycle: str = "monthly",
    price_paid: int = 0,
    notes: str = "",
) -> tuple[bool, str]:
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO licenses
                (user_id, package_key, status, billing_cycle,
                 start_date, end_date, price_paid, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                user_id,
                package_key,
                status,
                billing_cycle,
                start_date,
                end_date,
                price_paid,
                notes,
            ),
        )
        conn.commit()
        return True, "Lisensi berhasil dibuat."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def update_license(license_id: int, **fields) -> tuple[bool, str]:
    allowed = {
        "package_key",
        "status",
        "billing_cycle",
        "start_date",
        "end_date",
        "price_paid",
        "notes",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False, "Tidak ada field valid."
    updates["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [license_id]
    conn = get_db_connection()
    try:
        conn.execute(f"UPDATE licenses SET {set_clause} WHERE id = ?", values)
        conn.commit()
        return True, "Lisensi berhasil diupdate."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────
# PAYMENT CRUD
# ──────────────────────────────────────────────────────────────────


def create_payment(
    user_id: int,
    amount: int,
    method: str = "QRIS",
    status: str = "pending",
    license_id: int | None = None,
    period_label: str = "",
    notes: str = "",
    proof_filename: str = "",
    package_key: str = "",
    billing_cycle: str = "monthly",
) -> tuple[bool, str, int | None]:
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO payments
                (user_id, license_id, amount, method, status,
                 period_label, notes, proof_filename)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                user_id,
                license_id,
                amount,
                method,
                status,
                period_label,
                notes,
                proof_filename,
            ),
        )
        conn.commit()
        return True, "Pembayaran berhasil dicatat.", cursor.lastrowid
    except Exception as e:
        return False, str(e), None
    finally:
        conn.close()


def confirm_payment(
    payment_id: int, confirmed_by: str
) -> tuple[bool, str, dict | None]:
    conn = get_db_connection()
    try:
        conn.row_factory = sqlite3.Row
        payment = conn.execute(
            "SELECT * FROM payments WHERE id = ?", (payment_id,)
        ).fetchone()
        if not payment:
            return False, f"Payment ID {payment_id} tidak ditemukan.", None
        payment = dict(payment)
        conn.execute(
            """
            UPDATE payments
            SET status       = 'confirmed',
                confirmed_by = ?,
                confirmed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (confirmed_by, payment_id),
        )
        license_row = None
        if payment.get("license_id"):
            license_row = conn.execute(
                "SELECT * FROM licenses WHERE id = ?", (payment["license_id"],)
            ).fetchone()
        if not license_row:
            license_row = conn.execute(
                """
                SELECT * FROM licenses
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT 1
            """,
                (payment["user_id"],),
            ).fetchone()
        license_info = None
        if license_row:
            license_row = dict(license_row)
            billing_cycle = license_row.get("billing_cycle", "monthly")
            today = date.today()
            try:
                current_end = date.fromisoformat(str(license_row["end_date"]))
                start_date = current_end if current_end >= today else today
            except Exception:
                start_date = today
            if billing_cycle == "yearly":
                end_date = start_date + timedelta(days=365)
            elif billing_cycle == "lifetime":
                end_date = start_date + timedelta(days=36500)
            else:
                end_date = start_date + timedelta(days=30)
            conn.execute(
                """
                UPDATE licenses
                SET status     = 'active',
                    start_date = ?,
                    end_date   = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """,
                (str(start_date), str(end_date), license_row["id"]),
            )
            license_info = {
                "license_id": license_row["id"],
                "user_id": payment["user_id"],
                "package_key": license_row["package_key"],
                "billing_cycle": billing_cycle,
                "start_date": str(start_date),
                "end_date": str(end_date),
            }
        conn.commit()
        if license_info:
            return (
                True,
                f"Pembayaran dikonfirmasi & lisensi diaktifkan hingga {license_info['end_date']}.",
                license_info,
            )
        else:
            return (
                True,
                "Pembayaran dikonfirmasi. ⚠️ Lisensi tidak ditemukan — aktifkan manual di tab Lisensi.",
                None,
            )
    except Exception as e:
        if conn:
            conn.rollback()
        return False, str(e), None
    finally:
        conn.close()


def get_all_payments() -> list[dict]:
    conn = get_db_connection()
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT p.*, u.username, u.full_name, u.email
            FROM   payments p
            JOIN   users    u ON u.id = p.user_id
            ORDER  BY p.created_at DESC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────
# AUDIT LOG
# ──────────────────────────────────────────────────────────────────


def write_audit_log(
    actor: str,
    action: str,
    role: str = "",
    target_type: str = "",
    target_id: str = "",
    detail: str = "",
    ip_address: str = "",
) -> None:
    conn = None
    try:
        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO audit_log
                (actor, role, action, target_type, target_id, detail, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (actor, role, action, target_type, str(target_id), detail, ip_address),
        )
        conn.commit()
    except Exception:
        pass
    finally:
        if conn:
            conn.close()


def get_audit_log(limit: int = 200) -> list[dict]:
    conn = get_db_connection()
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────
# PACKAGE DB CRUD
# ──────────────────────────────────────────────────────────────────


def get_all_packages_from_db() -> list[dict]:
    conn = get_db_connection()
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM packages ORDER BY id ASC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_packages_merged() -> dict[str, dict]:
    from packages import PACKAGE_DEFINITIONS, PACKAGE_ORDER

    db_rows = get_all_packages_from_db()
    db_map = {r["package_key"]: r for r in db_rows}
    merged = {}
    for key in PACKAGE_ORDER:
        if key not in PACKAGE_DEFINITIONS:
            continue
        static = PACKAGE_DEFINITIONS[key].copy()
        db_row = db_map.get(key, {})
        if db_row.get("name"):
            static["name"] = db_row["name"]
        if db_row.get("price_monthly") is not None:
            static["price_monthly"] = db_row["price_monthly"]
        if db_row.get("price_yearly") is not None:
            static["price_yearly"] = db_row["price_yearly"]
        if db_row.get("description"):
            static["description"] = db_row["description"]
        static["is_active"] = bool(db_row.get("is_active", 1))
        if "use_database" in db_row and db_row["use_database"] is not None:
            static["use_database"] = bool(db_row["use_database"])
        merged[key] = static
    return merged


def get_package_use_database(package_key: str) -> bool:
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT use_database FROM packages WHERE package_key = ?",
            (package_key,),
        ).fetchone()
        if row is not None:
            return bool(row[0])
    except Exception:
        pass
    finally:
        conn.close()
    try:
        from packages import PACKAGE_DEFINITIONS

        return bool(PACKAGE_DEFINITIONS.get(package_key, {}).get("use_database", False))
    except Exception:
        return False


def update_package_in_db(package_key: str, **fields) -> tuple[bool, str]:
    allowed = {
        "name",
        "price_monthly",
        "price_yearly",
        "description",
        "is_active",
        "use_database",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False, "Tidak ada field valid."
    updates["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [package_key]
    conn = get_db_connection()
    try:
        conn.execute(f"UPDATE packages SET {set_clause} WHERE package_key = ?", values)
        conn.commit()
        return True, "Paket berhasil diupdate."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────
# PACKAGE TAB ACCESS OVERRIDE
# ──────────────────────────────────────────────────────────────────


def get_package_tab_access(package_key: str) -> dict[str, bool]:
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT tab_name, is_enabled FROM package_tab_access WHERE package_key = ?",
            (package_key,),
        ).fetchall()
        return {row[0]: bool(row[1]) for row in rows}
    except Exception:
        return {}
    finally:
        conn.close()


def set_package_tab_access(
    package_key: str, tab_name: str, is_enabled: bool
) -> tuple[bool, str]:
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO package_tab_access (package_key, tab_name, is_enabled, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(package_key, tab_name) DO UPDATE SET
                is_enabled = excluded.is_enabled,
                updated_at = excluded.updated_at
        """,
            (package_key, tab_name, int(is_enabled), datetime.now().isoformat()),
        )
        conn.commit()
        status = "aktif" if is_enabled else "nonaktif"
        return True, f"Tab '{tab_name}' pada paket '{package_key}' sekarang {status}."
    except Exception as e:
        return False, f"Gagal update tab access: {e}"
    finally:
        conn.close()


def reset_package_tab_access(package_key: str) -> tuple[bool, str]:
    conn = get_db_connection()
    try:
        conn.execute(
            "DELETE FROM package_tab_access WHERE package_key = ?", (package_key,)
        )
        conn.commit()
        return True, f"Override tab untuk paket '{package_key}' direset ke default."
    except Exception as e:
        return False, f"Gagal reset: {e}"
    finally:
        conn.close()


def get_all_package_tab_access() -> dict[str, dict[str, bool]]:
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT package_key, tab_name, is_enabled FROM package_tab_access"
        ).fetchall()
        result: dict[str, dict[str, bool]] = {}
        for pkg, tab, enabled in rows:
            result.setdefault(pkg, {})[tab] = bool(enabled)
        return result
    except Exception:
        return {}
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────
# DASHBOARD STATS
# ──────────────────────────────────────────────────────────────────


def get_admin_dashboard_stats() -> dict:
    conn = get_db_connection()
    try:
        stats = {}
        stats["total_users"] = conn.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'user'"
        ).fetchone()[0]
        stats["active_users"] = conn.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'user' AND is_active = 1"
        ).fetchone()[0]
        stats["active_licenses"] = conn.execute(
            "SELECT COUNT(*) FROM licenses WHERE status IN ('active','trial') AND end_date >= date('now')"
        ).fetchone()[0]
        stats["expired_licenses"] = conn.execute(
            "SELECT COUNT(*) FROM licenses WHERE status = 'expired' OR end_date < date('now')"
        ).fetchone()[0]
        stats["expiring_soon"] = conn.execute(
            "SELECT COUNT(*) FROM licenses WHERE status IN ('active','trial') "
            "AND end_date BETWEEN date('now') AND date('now', '7 days')"
        ).fetchone()[0]
        stats["pending_payments"] = conn.execute(
            "SELECT COUNT(*) FROM payments WHERE status = 'pending'"
        ).fetchone()[0]
        stats["revenue_this_month"] = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM payments "
            "WHERE status = 'confirmed' "
            "AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')"
        ).fetchone()[0]
        rows = conn.execute("""
            SELECT l.package_key, COALESCE(SUM(p.amount), 0) as total
            FROM payments p
            JOIN licenses l ON l.id = p.license_id
            WHERE p.status = 'confirmed'
            GROUP BY l.package_key
        """).fetchall()
        stats["revenue_by_package"] = {r[0]: r[1] for r in rows}
        return stats
    except Exception:
        return {}
    finally:
        conn.close()




# ══════════════════════════════════════════════════════════════════
# ADMIN NOTIFICATIONS
# ══════════════════════════════════════════════════════════════════


def push_admin_notification(
    type: str,
    title: str,
    body: str = "",
    ref_id: int | None = None,
    ref_table: str | None = None,
) -> None:
    """Tambah notifikasi baru untuk admin. Dipanggil dari mana saja."""
    try:
        conn = get_db_connection()
        # Auto-create tabel jika DB lama belum punya (migrasi aman)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS admin_notifications (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                type       TEXT NOT NULL,
                title      TEXT NOT NULL,
                body       TEXT,
                ref_id     INTEGER,
                ref_table  TEXT,
                is_read    INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS otp_attempts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                username   TEXT NOT NULL,
                attempts   INTEGER DEFAULT 0,
                locked_until DATETIME,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute(
            """INSERT INTO admin_notifications (type, title, body, ref_id, ref_table)
               VALUES (?, ?, ?, ?, ?)""",
            (type, title, body, ref_id, ref_table),
        )
        conn.commit()
        conn.close()
    except Exception as _e:
        _capture_exc(_e, "push_admin_notification")  # log tapi tidak crash


def get_admin_notifications(
    unread_only: bool = False,
    limit: int = 50,
) -> list[dict]:
    """Ambil notifikasi admin, terbaru di atas."""
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        where = "WHERE is_read = 0" if unread_only else ""
        rows = conn.execute(
            f"""SELECT id, type, title, body, ref_id, ref_table, is_read, created_at
                FROM admin_notifications
                {where}
                ORDER BY created_at DESC
                LIMIT ?""",
            (limit,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def count_unread_notifications() -> int:
    """Hitung notifikasi yang belum dibaca. Ringan — aman dipanggil tiap render."""
    try:
        conn = get_db_connection()
        n = conn.execute(
            "SELECT COUNT(*) FROM admin_notifications WHERE is_read = 0"
        ).fetchone()[0]
        conn.close()
        return n
    except Exception:
        return 0


def mark_notification_read(notif_id: int) -> None:
    try:
        conn = get_db_connection()
        conn.execute("UPDATE admin_notifications SET is_read=1 WHERE id=?", (notif_id,))
        conn.commit()
        conn.close()
    except Exception:
        pass


def mark_all_notifications_read() -> None:
    try:
        conn = get_db_connection()
        conn.execute("UPDATE admin_notifications SET is_read=1")
        conn.commit()
        conn.close()
    except Exception:
        pass


def delete_notification(notif_id: int) -> None:
    try:
        conn = get_db_connection()
        conn.execute("DELETE FROM admin_notifications WHERE id=?", (notif_id,))
        conn.commit()
        conn.close()
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════
# RESET PASSWORD
# ══════════════════════════════════════════════════════════════════


def generate_reset_token() -> str:
    # FIX #003: use CSPRNG (secrets module already imported at top)
    # 8-char alphanumeric URL-safe = 2.8 trillion combinations
    return secrets.token_urlsafe(8)


def set_reset_token(user_id: int, token: str, expiry_minutes: int = 30) -> bool:
    from datetime import datetime, timedelta

    expiry = (datetime.utcnow() + timedelta(minutes=expiry_minutes)).isoformat()
    conn = get_db_connection()
    try:
        conn.execute(
            "UPDATE users SET reset_token=?, reset_token_expiry=? WHERE id=?",
            (token, expiry, user_id),
        )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def verify_reset_token(username: str, token: str) -> tuple[bool, str, dict | None]:
    from datetime import datetime

    conn = get_db_connection()
    try:
        conn.row_factory = sqlite3.Row
        user = conn.execute(
            "SELECT * FROM users WHERE username=?", (username.strip().lower(),)
        ).fetchone()
        if not user:
            return False, "Username tidak ditemukan.", None
        if not user["reset_token"] or user["reset_token"] != token:
            return False, "Kode verifikasi salah.", None
        expiry = user["reset_token_expiry"]
        if not expiry or datetime.utcnow() > datetime.fromisoformat(expiry):
            return False, "Kode sudah kedaluwarsa. Minta kode baru.", None
        return True, "Token valid.", dict(user)
    finally:
        conn.close()


def clear_reset_token(user_id: int) -> None:
    conn = get_db_connection()
    try:
        conn.execute(
            "UPDATE users SET reset_token=NULL, reset_token_expiry=NULL WHERE id=?",
            (user_id,),
        )
        conn.commit()
    finally:
        conn.close()


def find_user_by_email_or_phone(query: str) -> list[dict]:
    conn = get_db_connection()
    try:
        conn.row_factory = sqlite3.Row
        q = f"%{query.strip()}%"
        rows = conn.execute(
            "SELECT id, username, email, phone, full_name FROM users WHERE email LIKE ? OR phone LIKE ?",
            (q, q),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════
# BUKTI TRANSFER
# ══════════════════════════════════════════════════════════════════


def save_payment_proof(
    payment_id: int, image_bytes: bytes, mimetype: str, filename: str
) -> bool:
    conn = get_db_connection()
    try:
        conn.execute(
            "UPDATE payments SET proof_image=?, proof_mimetype=?, proof_filename=? WHERE id=?",
            (image_bytes, mimetype, filename, payment_id),
        )
        conn.commit()

        # Notifikasi admin: bukti pembayaran baru
        try:
            push_admin_notification(
                type="new_payment",
                title="💳 Bukti Pembayaran Baru",
                body=f"Payment ID #{payment_id} telah mengirim bukti — menunggu konfirmasi.",
                ref_id=payment_id,
                ref_table="payments",
            )
        except Exception:
            pass

        return True
    except Exception:
        return False
    finally:
        conn.close()


def get_payment_proof(payment_id: int) -> dict | None:
    conn = get_db_connection()
    try:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT proof_image, proof_mimetype, proof_filename FROM payments WHERE id=?",
            (payment_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def reject_payment(
    payment_id: int, reason: str, admin_username: str
) -> tuple[bool, str]:
    from datetime import datetime

    conn = get_db_connection()
    try:
        conn.execute(
            """UPDATE payments
               SET status='rejected', rejected_reason=?, confirmed_by=?, confirmed_at=?
               WHERE id=?""",
            (reason, admin_username, datetime.utcnow().isoformat(), payment_id),
        )
        conn.commit()
        return True, "Pembayaran ditolak."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def get_users_full(search: str = "") -> list[dict]:
    conn = get_db_connection()
    try:
        conn.row_factory = sqlite3.Row
        q = f"%{search}%"
        rows = conn.execute(
            """
            SELECT
                u.id, u.username, u.email, u.full_name, u.phone, u.company,
                u.role, u.is_active, u.last_login, u.created_at, u.notes,
                l.id        AS license_id,
                l.package_key,
                l.status    AS license_status,
                l.end_date,
                l.billing_cycle
            FROM users u
            LEFT JOIN licenses l
                ON l.user_id = u.id
                AND l.status IN ('active','trial')
                AND l.end_date >= date('now')
            WHERE u.username LIKE ? OR u.email LIKE ? OR u.full_name LIKE ?
            ORDER BY u.id
            """,
            (q, q, q),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def bulk_update_license_status(
    user_ids: list[int], new_status: str
) -> tuple[bool, str]:
    if not user_ids:
        return False, "Tidak ada user dipilih."
    conn = get_db_connection()
    try:
        placeholders = ",".join("?" * len(user_ids))
        conn.execute(
            f"UPDATE licenses SET status=? WHERE user_id IN ({placeholders}) AND status IN ('active','trial','suspended')",
            [new_status, *user_ids],
        )
        conn.commit()
        return True, f"Status {len(user_ids)} user diperbarui ke '{new_status}'."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def bulk_update_package(
    user_ids: list[int], package_key: str, extend_days: int = 30
) -> tuple[bool, str]:
    from datetime import date, timedelta

    if not user_ids:
        return False, "Tidak ada user dipilih."
    conn = get_db_connection()
    try:
        new_end = (date.today() + timedelta(days=extend_days)).isoformat()
        placeholders = ",".join("?" * len(user_ids))
        conn.execute(
            f"""UPDATE licenses SET package_key=?, end_date=?, status='active'
                WHERE user_id IN ({placeholders})""",
            [package_key, new_end, *user_ids],
        )
        conn.commit()
        return True, f"Paket {len(user_ids)} user diperbarui ke '{package_key}'."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def get_all_payments_with_proof() -> list[dict]:
    conn = get_db_connection()
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT p.*, u.username, u.full_name, u.email,
                   CASE WHEN p.proof_image IS NOT NULL THEN 1 ELSE 0 END AS has_proof
            FROM payments p
            JOIN users u ON u.id = p.user_id
            ORDER BY p.created_at DESC
            """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════
# ADMIN: DATA OVERVIEW ACROSS ALL USERS
# ══════════════════════════════════════════════════════════════════


def get_all_users_data_stats() -> list[dict]:
    """Admin only: statistik data per user untuk semua tabel.
    FIX #020: from N*6 queries -> 6+1 queries via GROUP BY.
    """
    conn = get_db_connection()
    try:
        conn.row_factory = sqlite3.Row

        # Single query per table — collect counts grouped by user
        stats_map: dict[int, dict[str, int]] = {}
        for tbl in DATA_TABLES:
            try:
                rows = conn.execute(
                    f'SELECT user_id, COUNT(*) FROM "{tbl}" GROUP BY user_id'
                ).fetchall()
                for uid, cnt in rows:
                    stats_map.setdefault(uid, {})[tbl] = cnt
            except Exception:
                pass

        users = conn.execute(
            "SELECT id, username, email, full_name FROM users WHERE role = 'user'"
        ).fetchall()

        return [
            {
                "user_id":  u["id"],
                "username": u["username"],
                "email":    u["email"],
                "full_name": u["full_name"],
                **{tbl: stats_map.get(u["id"], {}).get(tbl, 0) for tbl in DATA_TABLES},
            }
            for u in users
        ]
    finally:
        conn.close()
