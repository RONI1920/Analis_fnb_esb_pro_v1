"""
auth_password_helper.py — Helper Verifikasi Password (bcrypt-aware)

Ini adalah PATCH untuk auth.py yang sebelumnya pakai SHA-256.

CARA INTEGRASI ke auth.py:
  1. Letakkan file ini di folder yang sama dengan auth.py
  2. Di auth.py, ganti:
       import hashlib
       ...
       def _hash(p): return hashlib.sha256(p.encode()).hexdigest()
       ...
       if user["password_hash"] == _hash(password):  # verifikasi lama

     Dengan:
       from auth_password_helper import verify_password, hash_password
       ...
       if verify_password(password, user["password_hash"]):  # verifikasi baru

  3. Untuk user yang daftarkan baru / ganti password, gunakan hash_password():
       new_hash = hash_password(password)

BACKWARD COMPATIBILITY:
  - Akun lama (SHA-256, 64 char hex) tetap bisa login
  - Saat login berhasil, hash otomatis di-upgrade ke bcrypt
  - Tidak perlu reset semua password sekaligus
"""

import hashlib
import bcrypt
import sqlite3
import os
from typing import Optional

# ─────────────────────────────
# DETEKSI JENIS HASH
# ─────────────────────────────

def _is_bcrypt(stored_hash: str) -> bool:
    """Hash bcrypt selalu dimulai dengan $2b$ atau $2a$."""
    return stored_hash.startswith(("$2b$", "$2a$", "$2y$"))


def _is_sha256(stored_hash: str) -> bool:
    """Hash SHA-256 = tepat 64 karakter hexadecimal."""
    return (
        len(stored_hash) == 64
        and all(c in "0123456789abcdef" for c in stored_hash.lower())
    )


# ─────────────────────────────
# HASH PASSWORD (bcrypt)
# ─────────────────────────────

def hash_password(password: str, rounds: int = 12) -> str:
    """
    Hash password baru menggunakan bcrypt.
    Gunakan ini untuk registrasi & ganti password.

    Args:
        password: plaintext password
        rounds:   bcrypt cost factor (12 = rekomendasi 2024, ~300ms)

    Returns:
        str: bcrypt hash string (dimulai dengan $2b$)
    """
    salt   = bcrypt.gensalt(rounds=rounds)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


# ─────────────────────────────
# VERIFY PASSWORD (auto-detect)
# ─────────────────────────────

def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verifikasi password terhadap hash yang tersimpan.
    Otomatis mendeteksi bcrypt atau SHA-256 (legacy).

    Returns:
        True  jika password cocok
        False jika tidak cocok atau hash format tidak dikenal
    """
    if not password or not stored_hash:
        return False

    if _is_bcrypt(stored_hash):
        # Path modern — bcrypt
        return bcrypt.checkpw(
            password.encode("utf-8"),
            stored_hash.encode("utf-8"),
        )

    if _is_sha256(stored_hash):
        # Path legacy — SHA-256 (untuk akun lama yang belum di-upgrade)
        legacy_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return legacy_hash == stored_hash

    # Format tidak dikenal — tolak
    return False


# ─────────────────────────────
# AUTO-UPGRADE HASH
# ─────────────────────────────

def upgrade_hash_if_needed(
    password: str,
    stored_hash: str,
    db_path: str,
    username: str,
) -> bool:
    """
    Jika user berhasil login dengan hash SHA-256 lama,
    otomatis upgrade hash-nya ke bcrypt di database.

    Panggil ini SETELAH verify_password() berhasil.

    Args:
        password:    plaintext password yang sudah diverifikasi
        stored_hash: hash yang tersimpan di DB
        db_path:     path ke file SQLite auth_users.db
        username:    username untuk update query

    Returns:
        True jika upgrade dilakukan, False jika tidak perlu
    """
    if not _is_sha256(stored_hash):
        return False  # Sudah bcrypt atau format lain, tidak perlu upgrade

    try:
        new_hash = hash_password(password)
        conn = sqlite3.connect(db_path)
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (new_hash, username),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        # Gagal upgrade tidak boleh block login — user tetap masuk
        return False


# ─────────────────────────────
# CONTOH INTEGRASI DI auth.py
# ─────────────────────────────
#
# SEBELUM (auth.py lama):
# ──────────────────────────
#   import hashlib
#
#   def _check_login(username, password):
#       user = _get_user(username)
#       if not user:
#           return False
#       expected = hashlib.sha256(password.encode()).hexdigest()
#       return user["password_hash"] == expected
#
#
# SESUDAH (auth.py baru):
# ──────────────────────────
#   from auth_password_helper import verify_password, upgrade_hash_if_needed
#
#   _AUTH_DB = os.path.join(os.path.dirname(__file__), "auth_users.db")
#
#   def _check_login(username, password):
#       user = _get_user(username)
#       if not user:
#           return False
#
#       if not verify_password(password, user["password_hash"]):
#           return False
#
#       # Upgrade hash SHA-256 lama ke bcrypt secara transparan
#       upgrade_hash_if_needed(
#           password,
#           user["password_hash"],
#           _AUTH_DB,
#           username,
#       )
#
#       return True