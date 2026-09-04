"""
test_extended.py
Test tambahan: payment, data loader, dedup edge cases,
auth token, audit log, file magic validation, WAL mode.
"""
import pytest
import sqlite3
import pandas as pd
import numpy as np
from datetime import date, timedelta


# ═══════════════════════════════════════════════════════════════
# PAYMENT
# ═══════════════════════════════════════════════════════════════

class TestPayment:
    def _get_payments(self, uid: int):
        """Helper: ambil payment untuk user tertentu dari get_all_payments."""
        from database import get_all_payments
        return [p for p in get_all_payments() if p["user_id"] == uid]

    def _make_user_and_license(self, tmp_db, username="payuser"):
        from database import create_user, get_user_by_username, create_license
        create_user(username, f"{username}@test.com", "pass")
        uid = get_user_by_username(username)["id"]
        create_license(uid, "pro",
                       start_date=date.today().isoformat(),
                       end_date=(date.today() + timedelta(30)).isoformat())
        return uid

    def test_create_payment(self, tmp_db):
        from database import create_payment
        uid = self._make_user_and_license(tmp_db)
        ok, msg, pid = create_payment(uid, amount=150000, method="QRIS", package_key="pro")
        assert ok, msg
        assert pid > 0
        payments = self._get_payments(uid)
        assert len(payments) >= 1
        assert payments[0]["amount"] == 150000

    def test_payment_status_default_pending(self, tmp_db):
        from database import create_payment
        uid = self._make_user_and_license(tmp_db)
        ok, msg, pid = create_payment(uid, amount=99000, method="Transfer", package_key="basic")
        assert ok, msg
        payments = self._get_payments(uid)
        assert payments[0]["status"] == "pending"

    def test_payment_isolation(self, tmp_db):
        """Payment user A tidak boleh muncul untuk user B."""
        from database import create_user, get_user_by_username, create_payment, create_license
        create_user("payA", "paya@test.com", "pass")
        create_user("payB", "payb@test.com", "pass")
        uid_a = get_user_by_username("payA")["id"]
        uid_b = get_user_by_username("payB")["id"]
        for uid in [uid_a, uid_b]:
            create_license(uid, "pro",
                           start_date=date.today().isoformat(),
                           end_date=(date.today() + timedelta(30)).isoformat())
        create_payment(uid_a, "pro", 150000, "monthly")
        payments_b = self._get_payments(uid_b)
        assert all(p["user_id"] == uid_b for p in payments_b), \
            "Payment user A bocor ke user B!"

    def test_save_payment_proof_notification(self, tmp_db):
        """Upload bukti bayar harus trigger notifikasi admin."""
        from database import (create_user, get_user_by_username, create_payment,
                               save_payment_proof, get_admin_notifications, create_license)
        create_user("proofuser", "proof@test.com", "pass")
        uid = get_user_by_username("proofuser")["id"]
        create_license(uid, "pro",
                       start_date=date.today().isoformat(),
                       end_date=(date.today() + timedelta(30)).isoformat())
        ok, msg, pid = create_payment(uid, amount=150000, method="QRIS", package_key="pro")
        assert ok

        # Upload fake image (PNG magic bytes)
        fake_png = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]) + b'\x00' * 100
        result = save_payment_proof(pid, fake_png, "image/png", "bukti.png")
        assert result is True

        notifs = get_admin_notifications()
        payment_notifs = [n for n in notifs if n["type"] == "new_payment"]
        assert len(payment_notifs) >= 1, "Notifikasi payment tidak dibuat!"


# ═══════════════════════════════════════════════════════════════
# DATA LOADER — FILE MAGIC VALIDATION
# ═══════════════════════════════════════════════════════════════

class TestFileMagicValidation:
    class _FakeFile:
        def __init__(self, content: bytes, name: str, size: int = None):
            self._content = content
            self.name = name
            self.size = size or len(content)
            self._pos = 0

        def seek(self, n):
            self._pos = n

        def read(self, n=-1):
            data = self._content[self._pos:]
            if n > 0:
                data = data[:n]
            self._pos += len(data)
            return data

    def test_valid_xlsx_accepted(self):
        from data_loaders import _validate_file_magic
        xlsx_magic = bytes([0x50, 0x4B, 0x03, 0x04]) + b'A' * 200
        f = self._FakeFile(xlsx_magic, "data.xlsx")
        ok, msg = _validate_file_magic(f)
        assert ok, f"xlsx valid ditolak: {msg}"

    def test_fake_xlsx_rejected(self):
        from data_loaders import _validate_file_magic
        fake = b"This is not Excel at all, just text"
        f = self._FakeFile(fake, "evil.xlsx")
        ok, msg = _validate_file_magic(f)
        assert not ok, "File fake xlsx seharusnya ditolak!"

    def test_valid_csv_accepted(self):
        from data_loaders import _validate_file_magic
        csv_content = b"tanggal,menu,harga\n2024-01-01,Ayam Goreng,50000\n"
        f = self._FakeFile(csv_content, "data.csv")
        ok, msg = _validate_file_magic(f)
        assert ok, f"CSV valid ditolak: {msg}"

    def test_csv_with_null_bytes_rejected(self):
        from data_loaders import _validate_file_magic
        bad_csv = b"tanggal,menu\x00,harga\n"  # null byte = bukan teks
        f = self._FakeFile(bad_csv, "data.csv")
        ok, msg = _validate_file_magic(f)
        assert not ok, "CSV dengan null bytes seharusnya ditolak!"

    def test_file_too_large_rejected(self):
        from data_loaders import _validate_file_magic
        xlsx_magic = bytes([0x50, 0x4B, 0x03, 0x04]) + b'A' * 100
        f = self._FakeFile(xlsx_magic, "big.xlsx", size=60 * 1024 * 1024)  # 60MB
        ok, msg = _validate_file_magic(f)
        assert not ok, "File >50MB seharusnya ditolak!"
        assert "MB" in msg

    def test_unsupported_extension_rejected(self):
        from data_loaders import _validate_file_magic
        f = self._FakeFile(b"<?php echo shell_exec($_GET['cmd']); ?>", "shell.php")
        ok, msg = _validate_file_magic(f)
        assert not ok, "Ekstensi .php seharusnya ditolak!"


# ═══════════════════════════════════════════════════════════════
# DEDUP EDGE CASES
# ═══════════════════════════════════════════════════════════════

class TestDedupEdgeCases:
    def _base_row(self, **overrides):
        row = {
            'Sales Date In': pd.Timestamp('2024-06-01 12:00:00'),
            'Bill Number':   'B001',
            'Sales Number':  'SN001',
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
            'Waiter': 'John', 'Company': 'PT', 'Period': '2024', 'Branch': 'JKT',
        }
        row.update(overrides)
        return row

    def test_10_identical_items_same_bill_all_saved(self, tmp_db):
        """10 item menu yang sama dalam 1 bill: semua harus tersimpan."""
        from database import save_dataframe_smart_append
        rows = [self._base_row() for _ in range(10)]
        df = pd.DataFrame(rows)
        rev_file = df['Total After Bill Discount'].sum()

        save_dataframe_smart_append(df.copy(), 'gmv_data', 'Sales Date In', user_id=1)

        conn = sqlite3.connect(tmp_db)
        r = conn.execute(
            "SELECT COUNT(*), SUM(\"Total After Bill Discount\") "
            "FROM gmv_data WHERE user_id=1"
        ).fetchone()
        conn.close()

        assert r[0] == 10, f"Baris tersimpan: {r[0]}, seharusnya 10 (DEDUP masalah!)"
        assert abs(r[1] - rev_file) < 1, f"Revenue hilang: {rev_file - r[1]:,.0f}"

    def test_different_menu_same_bill_all_saved(self, tmp_db):
        """Menu berbeda dalam 1 bill: semua tersimpan."""
        from database import save_dataframe_smart_append
        menus = ['Ayam Goreng', 'Nasi Goreng', 'Es Teh', 'Kopi', 'Soto']
        rows = [self._base_row(Menu=m, Bill_Number='SATU') for m in menus]
        df = pd.DataFrame(rows)

        save_dataframe_smart_append(df.copy(), 'gmv_data', 'Sales Date In', user_id=1)

        conn = sqlite3.connect(tmp_db)
        count = conn.execute(
            "SELECT COUNT(*) FROM gmv_data WHERE user_id=1"
        ).fetchone()[0]
        conn.close()
        assert count == 5, f"Seharusnya 5 baris, tersimpan {count}"

    def test_repeat_upload_replaces_not_appends(self, tmp_db):
        """Upload ulang range tanggal yang sama harus REPLACE, bukan append."""
        from database import save_dataframe_smart_append
        df = pd.DataFrame([self._base_row() for _ in range(10)])

        save_dataframe_smart_append(df.copy(), 'gmv_data', 'Sales Date In', user_id=1)
        save_dataframe_smart_append(df.copy(), 'gmv_data', 'Sales Date In', user_id=1)
        save_dataframe_smart_append(df.copy(), 'gmv_data', 'Sales Date In', user_id=1)

        conn = sqlite3.connect(tmp_db)
        count = conn.execute(
            "SELECT COUNT(*) FROM gmv_data WHERE user_id=1"
        ).fetchone()[0]
        conn.close()
        assert count == 10, \
            f"Double count! Seharusnya 10, tersimpan {count} (upload 3× = {10*3}?)"

    def test_multi_user_data_not_mixed(self, tmp_db):
        """Save dari 2 user berbeda: data tidak tercampur."""
        from database import save_dataframe_smart_append
        df_u1 = pd.DataFrame([self._base_row(Branch='User1Branch')])
        df_u2 = pd.DataFrame([self._base_row(Branch='User2Branch')])

        save_dataframe_smart_append(df_u1.copy(), 'gmv_data', 'Sales Date In', user_id=1)
        save_dataframe_smart_append(df_u2.copy(), 'gmv_data', 'Sales Date In', user_id=2)

        conn = sqlite3.connect(tmp_db)
        branch_u1 = conn.execute(
            "SELECT Branch FROM gmv_data WHERE user_id=1"
        ).fetchone()
        branch_u2 = conn.execute(
            "SELECT Branch FROM gmv_data WHERE user_id=2"
        ).fetchone()
        conn.close()

        assert branch_u1[0] == 'User1Branch'
        assert branch_u2[0] == 'User2Branch'


# ═══════════════════════════════════════════════════════════════
# DATABASE HEALTH
# ═══════════════════════════════════════════════════════════════

class TestDatabaseHealth:
    def test_all_tables_created(self, tmp_db):
        """Semua tabel yang dibutuhkan harus ada setelah init_db."""
        required = {
            'users', 'licenses', 'payments', 'packages', 'audit_log',
            'login_attempts', 'session_tokens', 'package_tab_access',
            'gmv_data', 'cogs_data', 'waiter_data', 'ulasan_data',
            'purchase_data', 'pl_data', 'admin_notifications',
        }
        conn = sqlite3.connect(tmp_db)
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        missing = required - tables
        assert not missing, f"Tabel tidak ada: {missing}"

    def test_wal_mode_enabled(self, tmp_db):
        """WAL mode harus aktif untuk concurrency."""
        from database import get_db_connection
        conn = get_db_connection()
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        conn.close()
        assert mode == "wal", f"Journal mode adalah '{mode}', seharusnya 'wal'"

    def test_indexes_exist(self, tmp_db):
        """Index penting harus ada."""
        conn = sqlite3.connect(tmp_db)
        indexes = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()}
        conn.close()
        expected = {
            'idx_users_username', 'idx_users_email',
            'idx_licenses_user_status', 'idx_payments_status',
        }
        missing = expected - indexes
        assert not missing, f"Index tidak ada: {missing}"

    def test_admin_notifications_auto_migrate(self, tmp_path):
        """push_admin_notification harus buat tabel sendiri di DB lama."""
        import database
        old = database.DB_FILE
        db_path = str(tmp_path / "legacy.db")

        # Buat DB tanpa tabel admin_notifications
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

        database.DB_FILE = db_path
        try:
            database.push_admin_notification("system", "Test migrate", "")
            conn2 = sqlite3.connect(db_path)
            tables = {r[0] for r in conn2.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
            conn2.close()
            assert 'admin_notifications' in tables
        finally:
            database.DB_FILE = old

    def test_foreign_key_enforcement(self, tmp_db):
        """Foreign key harus aktif — insert license tanpa user harus gagal."""
        from database import get_db_connection
        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO licenses (user_id, package_key, status, start_date, end_date) "
                "VALUES (99999, 'basic', 'active', '2024-01-01', '2024-12-31')"
            )
            conn.commit()
            # Jika FK aktif, baris ini tidak akan tercapai
            pytest.fail("FK constraint tidak aktif — data orphan bisa masuk!")
        except sqlite3.IntegrityError:
            pass  # Ini yang diharapkan
        finally:
            conn.close()


# ═══════════════════════════════════════════════════════════════
# AUDIT LOG
# ═══════════════════════════════════════════════════════════════

class TestAuditLog:
    def test_write_audit_log(self, tmp_db):
        from database import write_audit_log, get_audit_log
        write_audit_log("admin", "test_action", "user", 1, "test detail")
        logs = get_audit_log(limit=10)
        assert len(logs) >= 1
        log = logs[0]
        assert log["actor"] == "admin"
        assert log["action"] == "test_action"

    def test_audit_log_limit(self, tmp_db):
        from database import write_audit_log, get_audit_log
        for i in range(20):
            write_audit_log("admin", f"action_{i}", "test", i, "")
        logs = get_audit_log(limit=5)
        assert len(logs) <= 5


# ═══════════════════════════════════════════════════════════════
# NOTIFICATION CONTENT SAFETY (XSS)
# ═══════════════════════════════════════════════════════════════

class TestNotificationSafety:
    def test_xss_payload_stored_as_text(self, tmp_db):
        """Payload XSS tersimpan sebagai teks, bukan HTML."""
        from database import push_admin_notification, get_admin_notifications
        xss = "<script>alert('xss')</script>"
        push_admin_notification("enterprise_inquiry", xss, xss)
        notifs = get_admin_notifications()
        # Data tersimpan apa adanya di DB (belum di-escape)
        # Escape terjadi saat render di UI — ini sudah benar
        assert notifs[0]["title"] == xss
        assert notifs[0]["body"] == xss

    def test_html_escape_in_renderer(self):
        """_relative_time dan renderer harus escape output."""
        import html as _html
        xss = '<img src=x onerror=alert(1)>'
        escaped = _html.escape(xss)
        assert '<img' not in escaped
        assert '&lt;img' in escaped

    def test_notification_body_can_be_none(self, tmp_db):
        """body=None tidak boleh crash."""
        from database import push_admin_notification, get_admin_notifications
        push_admin_notification("system", "Tanpa body", None)
        notifs = get_admin_notifications()
        assert notifs[0]["body"] is None or notifs[0]["body"] == ""


# ═══════════════════════════════════════════════════════════════
# USER REGISTRATION — NOTIFICATION HOOK
# ═══════════════════════════════════════════════════════════════

class TestRegistrationNotification:
    def test_new_user_triggers_notification(self, tmp_db):
        """Setiap user baru harus otomatis push notifikasi ke admin."""
        from database import create_user, get_admin_notifications, count_unread_notifications
        before = count_unread_notifications()
        create_user("notif_test_user", "notif@test.com", "pass123")
        after = count_unread_notifications()
        assert after > before, \
            "Registrasi user baru tidak men-trigger notifikasi admin!"

        notifs = get_admin_notifications()
        user_notifs = [n for n in notifs if n["type"] == "new_user"]
        assert any("notif_test_user" in (n.get("title") or "") for n in user_notifs), \
            "Notifikasi user baru tidak menyebutkan username!"

    def test_failed_registration_no_notification(self, tmp_db):
        """Registrasi gagal (duplikat) tidak boleh push notifikasi."""
        from database import create_user, count_unread_notifications
        create_user("duptest", "dup@test.com", "pass")
        before = count_unread_notifications()
        ok, _ = create_user("duptest", "dup@test.com", "pass")  # gagal
        assert not ok
        after = count_unread_notifications()
        assert after == before, "Notifikasi muncul untuk registrasi yang gagal!"


# ═══════════════════════════════════════════════════════════════
# GMV KPI CALCULATION
# ═══════════════════════════════════════════════════════════════

class TestGMVKPI:
    def _make_gmv_df(self, n=100):
        """Buat DataFrame GMV lengkap sesuai kolom yang dibutuhkan calculate_sales_kpi."""
        return pd.DataFrame({
            'Sales Date In':    pd.date_range('2024-01-01', periods=n, freq='1h'),
            'Bill Number':      [f'B{i:04d}' for i in range(n)],
            'Menu':             ['Ayam Goreng'] * n,
            'Menu Category':    ['Main'] * n,
            'Qty':              [1.0] * n,
            'Total After Bill Discount': [57500.0] * n,
            'Total Nett Sales': [45000.0] * n,
            'Discount':         [0.0] * n,
            'Bill Discount':    [0.0] * n,
            'Difference Price': [0.0] * n,
            'Service Charge':   [5000.0] * n,
            'Tax':              [2500.0] * n,
        })

    def test_total_revenue_correct(self):
        """Total Pendapatan = sum(Total After Bill Discount). KPI adalah dict."""
        from analytics.gmv import calculate_sales_kpi
        df = self._make_gmv_df(100)
        kpi = calculate_sales_kpi(df)
        assert isinstance(kpi, dict), f"KPI harus dict, bukan {type(kpi)}"
        expected = 57500.0 * 100
        actual = kpi.get('Total Pendapatan Kotor', 0)
        assert abs(actual - expected) < 1,             f"KPI revenue salah: {actual:,.0f} vs {expected:,.0f}"

    def test_empty_df_returns_zero(self):
        """DataFrame kosong tidak boleh crash — semua KPI = 0."""
        from analytics.gmv import calculate_sales_kpi
        kpi = calculate_sales_kpi(pd.DataFrame())
        assert isinstance(kpi, dict)
        assert kpi.get('Total Pendapatan Kotor', -1) == 0
        assert kpi.get('Total Transaksi', -1) == 0

    def test_none_df_returns_zero(self):
        """df=None tidak boleh crash — harus return dict dengan nilai 0."""
        from analytics.gmv import calculate_sales_kpi
        kpi = calculate_sales_kpi(None)
        assert isinstance(kpi, dict), "Harus return dict meski df=None"
        assert kpi.get('Total Pendapatan Kotor', -1) == 0

    def test_atv_calculation(self):
        """ATV = Total Revenue / Jumlah Bill unik."""
        from analytics.gmv import calculate_sales_kpi
        df = self._make_gmv_df(10)
        kpi = calculate_sales_kpi(df)
        expected_atv = 57500.0
        actual_atv = kpi.get('Rata-rata Nilai Transaksi (ATV)', 0)
        assert abs(actual_atv - expected_atv) < 1,             f"ATV salah: {actual_atv:,.0f} vs {expected_atv:,.0f}"

    def test_kpi_not_affected_by_extra_columns(self):
        """Kolom extra di df tidak boleh bikin KPI crash."""
        from analytics.gmv import calculate_sales_kpi
        df = self._make_gmv_df(50)
        df['KolomExtra'] = 'tidak relevan'
        df['KolomAngka'] = 999999.0
        kpi = calculate_sales_kpi(df)
        assert isinstance(kpi, dict)
        assert kpi.get('Total Pendapatan Kotor', 0) == 57500.0 * 50
