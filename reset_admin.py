"""
Script reset password admin.
Jalankan SEKALI dari folder proyek:
    python reset_admin.py

Setelah berhasil, HAPUS file ini.
"""
import os, sys, sqlite3

DB_FILE = os.environ.get("FNB_DB_FILE", "database_bisnis_saya.db")

if not os.path.exists(DB_FILE):
    print(f"❌ Database '{DB_FILE}' tidak ditemukan.")
    print("   Pastikan script ini dijalankan dari folder yang sama dengan database.")
    sys.exit(1)

# Import hash function dari codebase ini sendiri
sys.path.insert(0, os.path.dirname(__file__))
from database import _hash_password, verify_password

NEW_PASSWORD = "Admin@2024"
hashed = _hash_password(NEW_PASSWORD)

conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()

cur.execute("SELECT id, username, role FROM users WHERE username='admin'")
row = cur.fetchone()

if row is None:
    # Buat admin baru
    cur.execute(
        "INSERT INTO users (username, email, password_hash, role, full_name) "
        "VALUES ('admin', 'admin@fnbdashboard.id', ?, 'admin', 'Super Admin')",
        (hashed,)
    )
    print("✅ Akun admin baru dibuat.")
else:
    cur.execute(
        "UPDATE users SET password_hash=? WHERE username='admin'",
        (hashed,)
    )
    print(f"✅ Password admin (id={row[0]}) berhasil direset.")

conn.commit()
conn.close()

# Verifikasi
conn2 = sqlite3.connect(DB_FILE)
stored = conn2.execute("SELECT password_hash FROM users WHERE username='admin'").fetchone()[0]
conn2.close()

ok = verify_password(NEW_PASSWORD, stored)
print()
print("=" * 40)
print(f"  Username : admin")
print(f"  Password : {NEW_PASSWORD}")
print(f"  Verifikasi hash: {'✅ OK' if ok else '❌ GAGAL'}")
print("=" * 40)
print()
print("⚠️  Segera ganti password ini setelah login pertama!")
print("⚠️  Hapus file reset_admin.py setelah digunakan!")
