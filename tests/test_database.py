"""
test_database.py
Unit test untuk database.py — fungsi-fungsi inti:
- Password hashing & verify
- CRUD user
- CRUD lisensi & payment
- Admin notifications
- Save/load GMV (dedup fix)
- SQL injection whitelist
"""
import pytest
import sqlite3
import pandas as pd
import numpy as np


# ═══════════════════════════════════════════════════════════════
# PASSWORD
# ═══════════════════════════════════════════════════════════════

class TestPassword:
    def test_hash_not_plaintext(self):
        from database import _hash_password
        h = _hash_password("rahasia123")
        assert h != "rahasia123"
        assert len(h) > 20

    def test_verify_correct(self):
        from database import _hash_password, verify_password
        h = _hash_password("test1234")
        assert verify_password("test1234", h) is True

    def test_verify_wrong(self):
        from database import _hash_password, verify_password
        h = _hash_password("test1234")
        assert verify_password("salah", h) is False

    def test_two_hashes_differ(self):
        """Setiap hash berbeda (salt random)."""
        from database import _hash_password
        h1 = _hash_password("sama")
        h2 = _hash_password("sama")
        assert h1 != h2

    def test_empty_password(self):
        from database import _hash_password, verify_password
        h = _hash_password("")
        assert verify_password("", h) is True
        assert verify_password("x", h) is False


# ═══════════════════════════════════════════════════════════════
# RESET TOKEN
# ═══════════════════════════════════════════════════════════════

class TestResetToken:
    def test_not_all_digits(self):
        """Setelah fix v3: token harus CSPRNG, bukan 6 digit angka."""
        from database import generate_reset_token
        token = generate_reset_token()
        assert not token.isdigit(), "Token masih pakai random.digits — belum difix!"

    def test_length_sufficient(self):
        from database import generate_reset_token
        token = generate_reset_token()
        assert len(token) >= 8

    def test_tokens_are_unique(self):
        from database import generate_reset_token
        tokens = {generate_reset_token() for _ in range(20)}
        assert len(tokens) == 20, "Ada token duplikat — CSPRNG bermasalah"


# ═══════════════════════════════════════════════════════════════
# CRUD USER
# ═══════════════════════════════════════════════════════════════

class TestUser:
    def test_create_user_success(self, tmp_db):
        from database import create_user, get_user_by_username
        ok, msg = create_user("roni", "roni@test.com", "pass123")
        assert ok, msg
        user = get_user_by_username("roni")
        assert user is not None
        assert user["email"] == "roni@test.com"
        assert user["role"] == "user"

    def test_create_duplicate_username(self, tmp_db):
        from database import create_user
        create_user("duplikat", "a@a.com", "pass")
        ok, msg = create_user("duplikat", "b@b.com", "pass")
        assert not ok
        assert "duplikat" in msg.lower() or "digunakan" in msg.lower()

    def test_create_duplicate_email(self, tmp_db):
        from database import create_user
        create_user("user1", "same@email.com", "pass")
        ok, msg = create_user("user2", "same@email.com", "pass")
        assert not ok

    def test_update_user_cannot_change_role(self, tmp_db):
        """FIX #006: update_user tidak boleh ubah role."""
        from database import create_user, update_user, get_user_by_username
        create_user("biasa", "biasa@test.com", "pass")
        user = get_user_by_username("biasa")
        uid = user["id"]
        update_user(uid, role="admin")  # seharusnya diabaikan
        refreshed = get_user_by_username("biasa")
        assert refreshed["role"] == "user", "FAIL: role berhasil diubah via update_user!"

    def test_admin_seed_not_admin123(self, tmp_db):
        """FIX #002: admin awal tidak boleh password 'admin123'."""
        from database import verify_password
        conn = sqlite3.connect(tmp_db)
        row = conn.execute(
            "SELECT password_hash FROM users WHERE username='admin'"
        ).fetchone()
        conn.close()
        assert row is not None, "Admin user tidak dibuat"
        assert not verify_password("admin123", row[0]), \
            "CRITICAL: Admin masih pakai password 'admin123'!"

    def test_get_user_not_found(self, tmp_db):
        from database import get_user_by_username
        assert get_user_by_username("tidak_ada") is None


# ═══════════════════════════════════════════════════════════════
# SQL INJECTION
# ═══════════════════════════════════════════════════════════════

class TestSQLInjection:
    def test_load_dataframe_blocks_injection(self, tmp_db):
        """FIX #001: table name injection harus diblok whitelist."""
        from database import load_dataframe_from_db
        result = load_dataframe_from_db(
            "gmv_data' UNION SELECT password_hash FROM users--",
            user_id=1
        )
        assert result is None, "CRITICAL: SQL injection tidak diblok!"

    def test_load_dataframe_valid_table(self, tmp_db):
        """Table name yang valid harus bisa diakses."""
        from database import load_dataframe_from_db
        result = load_dataframe_from_db("gmv_data", user_id=1)
        # Boleh None (kosong) tapi tidak boleh throw exception SQL injection
        assert result is None or isinstance(result, pd.DataFrame)

    def test_load_dataframe_unknown_table_blocked(self, tmp_db):
        """Table name sembarang harus diblok."""
        from database import load_dataframe_from_db
        result = load_dataframe_from_db("users", user_id=1)
        assert result is None, "Tabel 'users' seharusnya diblok!"


# ═══════════════════════════════════════════════════════════════
# SAVE / LOAD GMV — REVENUE INTEGRITY
# ═══════════════════════════════════════════════════════════════

class TestGMVRevenueIntegrity:
    """Test kritis: revenue di file harus = revenue di DB setelah save."""

    def _make_df(self, n=100, identical_menu=False):
        """Buat DataFrame GMV seperti export Ocha."""
        if identical_menu:
            # Skenario: 5 Ayam Goreng identik dalam 1 bill (yang dulu false-dedup)
            rows = []
            for i in range(n):
                rows.append({
                    'Sales Date In': pd.Timestamp('2024-01-15 12:00:00'),
                    'Bill Number':   'B00001',
                    'Sales Number':  'SN00001',
                    'Menu':          'Ayam Goreng',
                    'Menu Category': 'Main',
                    'Qty':           1.0,
                    'Price':         50000.0,
                    'Price (Net)':   45000.0,
                    'Subtotal':      50000.0,
                    'Discount':      0.0,
                    'Service Charge': 5000.0,
                    'Tax':           2500.0,
                    'VAT':           0.0,
                    'Total':         57500.0,
                    'Nett Sales':    45000.0,
                    'Total Nett Sales': 45000.0,
                    'Bill Discount': 0.0,
                    'Total Gross Sales': 57500.0,
                    'Total After Bill Discount': 57500.0,
                    'Waiter': 'John',
                    'Company': 'PT Test',
                    'Period': '2024',
                    'Branch': 'Jakarta',
                })
            return pd.DataFrame(rows)

        np.random.seed(42)
        return pd.DataFrame({
            'Sales Date In': pd.date_range('2024-01-01', periods=n, freq='5min'),
            'Bill Number':   [f'B{i//3:05d}' for i in range(n)],
            'Sales Number':  [f'SN{i//3:05d}' for i in range(n)],
            'Menu':          np.random.choice(['Ayam Goreng','Nasi','Soto'], n),
            'Menu Category': ['Main'] * n,
            'Qty':           np.random.choice([1.0, 2.0], n),
            'Price':         [50000.0] * n,
            'Price (Net)':   [45000.0] * n,
            'Subtotal':      [50000.0] * n,
            'Discount':      [0.0] * n,
            'Service Charge': [5000.0] * n,
            'Tax':           [2500.0] * n,
            'VAT':           [0.0] * n,
            'Total':         [57500.0] * n,
            'Nett Sales':    [45000.0] * n,
            'Total Nett Sales': [45000.0] * n,
            'Bill Discount': [0.0] * n,
            'Total Gross Sales': [57500.0] * n,
            'Total After Bill Discount': [57500.0] * n,
            'Waiter':        ['John'] * n,
            'Company':       ['PT Test'] * n,
            'Period':        ['2024'] * n,
            'Branch':        ['Jakarta'] * n,
        })

    def test_revenue_no_loss_normal(self, tmp_db):
        """Revenue tidak boleh berkurang setelah save ke DB."""
        from database import save_dataframe_smart_append
        df = self._make_df(200)
        rev_before = df['Total After Bill Discount'].sum()

        save_dataframe_smart_append(df.copy(), 'gmv_data', 'Sales Date In', user_id=1)

        conn = sqlite3.connect(tmp_db)
        df_db = pd.read_sql_query(
            "SELECT \"Total After Bill Discount\" FROM gmv_data WHERE user_id=1", conn
        )
        conn.close()
        rev_after = df_db['Total After Bill Discount'].sum()

        assert abs(rev_before - rev_after) < 1, \
            f"Revenue hilang! File={rev_before:,.0f}, DB={rev_after:,.0f}, " \
            f"Selisih={rev_before-rev_after:,.0f}"

    def test_revenue_no_loss_identical_menu_items(self, tmp_db):
        """FIX UTAMA: 5x Ayam Goreng identik harus SEMUA tersimpan."""
        from database import save_dataframe_smart_append
        df = self._make_df(5, identical_menu=True)
        rev_before = df['Total After Bill Discount'].sum()
        rows_before = len(df)

        save_dataframe_smart_append(df.copy(), 'gmv_data', 'Sales Date In', user_id=1)

        conn = sqlite3.connect(tmp_db)
        result = conn.execute(
            "SELECT COUNT(*), SUM(\"Total After Bill Discount\") FROM gmv_data WHERE user_id=1"
        ).fetchone()
        conn.close()

        rows_db, rev_db = result
        assert rows_db == rows_before, \
            f"Baris hilang! File={rows_before}, DB={rows_db} " \
            f"(DEDUP agresif masih aktif!)"
        assert abs(rev_before - (rev_db or 0)) < 1, \
            f"Revenue hilang! File={rev_before:,.0f}, DB={rev_db:,.0f}"

    def test_no_double_count_on_repeat_save(self, tmp_db):
        """Upload file yang sama 2x tidak boleh double-count revenue."""
        from database import save_dataframe_smart_append
        df = self._make_df(50)
        rev_once = df['Total After Bill Discount'].sum()

        save_dataframe_smart_append(df.copy(), 'gmv_data', 'Sales Date In', user_id=1)
        save_dataframe_smart_append(df.copy(), 'gmv_data', 'Sales Date In', user_id=1)

        conn = sqlite3.connect(tmp_db)
        rev_db = conn.execute(
            "SELECT SUM(\"Total After Bill Discount\") FROM gmv_data WHERE user_id=1"
        ).fetchone()[0] or 0
        conn.close()

        assert abs(rev_once - rev_db) < 1, \
            f"Double count! Seharusnya={rev_once:,.0f}, DB={rev_db:,.0f}"

    def test_user_isolation(self, tmp_db):
        """Data user A tidak boleh terlihat oleh user B."""
        from database import save_dataframe_smart_append
        df_a = self._make_df(30)
        df_b = self._make_df(20)
        # Beda revenue agar bisa dibedakan
        df_b['Total After Bill Discount'] = 99999.0

        save_dataframe_smart_append(df_a.copy(), 'gmv_data', 'Sales Date In', user_id=1)
        save_dataframe_smart_append(df_b.copy(), 'gmv_data', 'Sales Date In', user_id=2)

        conn = sqlite3.connect(tmp_db)
        rev_a = conn.execute(
            "SELECT SUM(\"Total After Bill Discount\") FROM gmv_data WHERE user_id=1"
        ).fetchone()[0]
        rev_b = conn.execute(
            "SELECT SUM(\"Total After Bill Discount\") FROM gmv_data WHERE user_id=2"
        ).fetchone()[0]
        conn.close()

        assert abs(rev_a - df_a['Total After Bill Discount'].sum()) < 1
        assert abs(rev_b - (99999.0 * 20)) < 1
        assert rev_a != rev_b, "Data user tercampur!"


# ═══════════════════════════════════════════════════════════════
# ADMIN NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════

class TestAdminNotifications:
    def test_push_and_get(self, tmp_db):
        from database import push_admin_notification, get_admin_notifications
        push_admin_notification(
            "enterprise_inquiry",
            "🏢 Test Enterprise",
            "Dari: test@test.com",
        )
        notifs = get_admin_notifications()
        assert len(notifs) == 1
        assert notifs[0]["title"] == "🏢 Test Enterprise"
        assert notifs[0]["is_read"] == 0

    def test_count_unread(self, tmp_db):
        from database import push_admin_notification, count_unread_notifications
        push_admin_notification("new_user", "User A", "")
        push_admin_notification("new_user", "User B", "")
        assert count_unread_notifications() == 2

    def test_mark_read(self, tmp_db):
        from database import (push_admin_notification, get_admin_notifications,
                               mark_notification_read, count_unread_notifications)
        push_admin_notification("new_payment", "Payment 1", "")
        push_admin_notification("new_payment", "Payment 2", "")
        nid = get_admin_notifications()[0]["id"]
        mark_notification_read(nid)
        assert count_unread_notifications() == 1

    def test_mark_all_read(self, tmp_db):
        from database import (push_admin_notification, mark_all_notifications_read,
                               count_unread_notifications)
        for i in range(5):
            push_admin_notification("system", f"Notif {i}", "")
        mark_all_notifications_read()
        assert count_unread_notifications() == 0

    def test_delete_notification(self, tmp_db):
        from database import (push_admin_notification, get_admin_notifications,
                               delete_notification)
        push_admin_notification("system", "Hapus ini", "")
        nid = get_admin_notifications()[0]["id"]
        delete_notification(nid)
        assert get_admin_notifications() == []

    def test_push_auto_creates_table(self, tmp_path):
        """push_admin_notification harus bisa buat tabel sendiri (DB lama)."""
        import database
        old = database.DB_FILE
        db_path = str(tmp_path / "old.db")
        database.DB_FILE = db_path

        # Buat DB tanpa tabel admin_notifications (simulasi DB lama)
        conn = sqlite3.connect(db_path)
        conn.close()

        # Push harus berhasil tanpa error
        try:
            database.push_admin_notification("system", "Test Old DB", "")
            notifs = database.get_admin_notifications()
            assert len(notifs) == 1
        finally:
            database.DB_FILE = old

    def test_unread_filter(self, tmp_db):
        from database import (push_admin_notification, get_admin_notifications,
                               mark_notification_read)
        push_admin_notification("system", "A", "")
        push_admin_notification("system", "B", "")
        notifs = get_admin_notifications()
        mark_notification_read(notifs[0]["id"])

        unread = get_admin_notifications(unread_only=True)
        assert len(unread) == 1
        assert unread[0]["title"] == "B"


# ═══════════════════════════════════════════════════════════════
# LISENSI & PAYMENT
# ═══════════════════════════════════════════════════════════════

class TestLicense:
    def _make_user(self, username="testuser"):
        from database import create_user, get_user_by_username
        create_user(username, f"{username}@test.com", "pass123")
        return get_user_by_username(username)["id"]

    def _today(self, delta_days=0):
        from datetime import date, timedelta
        return (date.today() + timedelta(days=delta_days)).isoformat()

    def test_create_license(self, tmp_db):
        from database import create_license, get_active_license
        uid = self._make_user()
        ok, msg = create_license(
            uid, "basic",
            start_date=self._today(),
            end_date=self._today(30),
        )
        assert ok, msg
        lic = get_active_license(uid)
        assert lic is not None
        assert lic["package_key"] == "basic"

    def test_license_isolation(self, tmp_db):
        """Lisensi user A tidak tampil untuk user B."""
        from database import create_license, get_active_license
        uid_a = self._make_user("userA")
        uid_b = self._make_user("userB")
        create_license(uid_a, "pro",
                       start_date=self._today(),
                       end_date=self._today(30))
        assert get_active_license(uid_b) is None

    def test_expired_license_not_returned(self, tmp_db):
        """Lisensi expired tidak boleh dikembalikan sebagai active."""
        from database import create_license, get_active_license
        uid = self._make_user("expireduser")
        create_license(uid, "basic",
                       start_date=self._today(-60),
                       end_date=self._today(-1),
                       status="expired")
        lic = get_active_license(uid)
        assert lic is None, "Lisensi expired seharusnya tidak dikembalikan!"

    def test_license_returns_correct_package(self, tmp_db):
        """Package key harus tersimpan dan terbaca dengan benar."""
        from database import create_license, get_active_license
        uid = self._make_user("prouser")
        create_license(uid, "pro_plus",
                       start_date=self._today(),
                       end_date=self._today(365))
        lic = get_active_license(uid)
        assert lic["package_key"] == "pro_plus"


# ═══════════════════════════════════════════════════════════════
# FORMATTERS
# ═══════════════════════════════════════════════════════════════

class TestFormatters:
    def test_safe_html_escapes_script(self):
        from formatters import safe_html
        result = safe_html('<script>alert(1)</script>')
        assert '<script>' not in result
        assert '&lt;script&gt;' in result

    def test_safe_html_escapes_quotes(self):
        from formatters import safe_html
        result = safe_html('"hello" & \'world\'')
        assert '"' not in result
        assert '&quot;' in result

    def test_safe_html_none(self):
        from formatters import safe_html
        assert safe_html(None) == ""

    def test_safe_html_normal_text(self):
        from formatters import safe_html
        assert safe_html("Warung Makan Enak") == "Warung Makan Enak"


# ═══════════════════════════════════════════════════════════════
# AI PROVIDER — mutable default arg fix
# ═══════════════════════════════════════════════════════════════

class TestAIProvider:
    def test_no_mutable_default_arg(self):
        """FIX #004: conversation_history default harus None, bukan []."""
        import inspect
        from services import ai_provider
        sig = inspect.signature(ai_provider.ask_ai)
        default = sig.parameters["conversation_history"].default
        assert default is None, \
            f"CRITICAL: conversation_history default adalah {default!r} " \
            f"— mutable default arg menyebabkan cross-tenant AI leak!"

    def test_separate_history_per_call(self):
        """Dua panggilan berbeda tidak boleh berbagi history."""
        from services.ai_provider import ask_ai
        import inspect
        sig = inspect.signature(ask_ai)
        # Jika default None, setiap call buat list baru
        assert sig.parameters["conversation_history"].default is None


# ═══════════════════════════════════════════════════════════════
# RELATIVE TIME (notifications)
# ═══════════════════════════════════════════════════════════════

class TestRelativeTime:
    def test_just_now(self):
        from ui.admin_notifications_tab import _relative_time
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        dt_str = now.strftime('%Y-%m-%d %H:%M:%S')
        assert _relative_time(dt_str) == "baru saja"

    def test_minutes_ago(self):
        from ui.admin_notifications_tab import _relative_time
        from datetime import datetime, timezone, timedelta
        dt = datetime.now(timezone.utc) - timedelta(minutes=15)
        result = _relative_time(dt.strftime('%Y-%m-%d %H:%M:%S'))
        assert "15 menit" in result

    def test_hours_ago(self):
        from ui.admin_notifications_tab import _relative_time
        from datetime import datetime, timezone, timedelta
        dt = datetime.now(timezone.utc) - timedelta(hours=3)
        result = _relative_time(dt.strftime('%Y-%m-%d %H:%M:%S'))
        assert "3 jam" in result

    def test_invalid_date(self):
        from ui.admin_notifications_tab import _relative_time
        # Tidak boleh crash untuk input tidak valid
        result = _relative_time("bukan-tanggal")
        assert isinstance(result, str)
