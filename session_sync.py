
# session_sync.py — Sinkronisasi Session State dengan Database
#
# FIXED VERSION
# ------------------------------------------------------------
# Perbaikan:
#   ✅ Sinkron package dari DB
#   ✅ Sinkron tabs dari package terbaru
#   ✅ Refresh otomatis setelah admin ubah paket
#   ✅ Support invalidasi session
#   ✅ Auto logout jika akun dinonaktifkan
#
# Integrasi:
#
# app.py
# ------------------------------------------------------------
# from session_sync import refresh_user_session
#
# def main():
#     refresh_user_session()
#     ...
#
#
# admin_panel.py
# ------------------------------------------------------------
# from session_sync import invalidate_user_session
#
# setelah update package/license:
# invalidate_user_session(username)
#

from __future__ import annotations

import logging
import os
import sqlite3
import time
from typing import Optional

import streamlit as st

from packages import get_allowed_tabs

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────

_log = logging.getLogger(__name__)

_HERE = os.path.dirname(os.path.abspath(__file__))
_AUTH_DB = os.path.join(_HERE, "auth_users.db")


# ─────────────────────────────────────────────────────────────
# DB MIGRATION
# ─────────────────────────────────────────────────────────────

def _ensure_invalidation_column() -> None:
    """
    Tambah kolom session_invalidated jika belum ada.
    Aman dijalankan berkali-kali.
    """

    try:
        conn = sqlite3.connect(_AUTH_DB)

        cursor = conn.execute("PRAGMA table_info(users)")
        cols = {row[1] for row in cursor.fetchall()}

        if "session_invalidated" not in cols:
            conn.execute(
                """
                ALTER TABLE users
                ADD COLUMN session_invalidated INTEGER DEFAULT 0
                """
            )

            conn.commit()

            _log.info(
                "Kolom session_invalidated berhasil ditambahkan."
            )

        conn.close()

    except Exception as e:
        _log.warning(
            f"_ensure_invalidation_column gagal: {e}"
        )


# ─────────────────────────────────────────────────────────────
# FETCH USER
# ─────────────────────────────────────────────────────────────

def _fetch_user_from_db(username: str) -> Optional[dict]:
    """
    Ambil data terbaru user dari DB.
    """

    try:
        conn = sqlite3.connect(_AUTH_DB)
        conn.row_factory = sqlite3.Row

        cursor = conn.execute(
            """
            SELECT
                username,
                role,
                package,
                is_active,
                trial_end,
                session_invalidated
            FROM users
            WHERE username = ?
            """,
            (username,),
        )

        row = cursor.fetchone()

        conn.close()

        return dict(row) if row else None

    except Exception as e:
        _log.warning(
            f"_fetch_user_from_db gagal untuk {username!r}: {e}"
        )

        return None


# ─────────────────────────────────────────────────────────────
# REFRESH SESSION
# ─────────────────────────────────────────────────────────────

def refresh_user_session() -> None:
    """
    Sinkronisasi session_state dengan DB.

    Dipanggil di setiap load dashboard.

    Yang di-refresh:
        - role
        - package
        - tabs
        - trial_end
        - status aktif user
    """

    username = st.session_state.get("username")

    if not username:
        return

    # interval check
    last_check = st.session_state.get("_last_db_check", 0)
    now = time.time()

    force_check = st.session_state.get("_force_recheck", False)

    # hemat query DB
    if not force_check and (now - last_check) < 60:
        return

    st.session_state["_last_db_check"] = now
    st.session_state["_force_recheck"] = False

    # fetch terbaru dari DB
    db_user = _fetch_user_from_db(username)

    if not db_user:
        _log.warning(
            f"User {username!r} tidak ditemukan di DB."
        )
        return

    # ─────────────────────────────────────────────────────────
    # CEK USER AKTIF
    # ─────────────────────────────────────────────────────────

    if not db_user.get("is_active", 1):

        _log.info(
            f"User {username!r} dinonaktifkan admin."
        )

        _force_logout(
            "Akun Anda telah dinonaktifkan administrator."
        )

        return

    # ─────────────────────────────────────────────────────────
    # DATA BARU DARI DB
    # ─────────────────────────────────────────────────────────

    db_role = db_user.get("role", "")
    db_package = db_user.get("package", "")

    current_role = st.session_state.get("role", "")
    current_package = st.session_state.get("package", "")

    was_invalidated = bool(
        db_user.get("session_invalidated", 0)
    )

    # ─────────────────────────────────────────────────────────
    # DETEKSI PERUBAHAN
    # ─────────────────────────────────────────────────────────

    changed = (
        current_role != db_role
        or current_package != db_package
        or was_invalidated
    )

    if not changed:
        return

    _log.info(
        f"Session user {username!r} diperbarui | "
        f"role: {current_role} -> {db_role} | "
        f"package: {current_package} -> {db_package}"
    )

    # ─────────────────────────────────────────────────────────
    # UPDATE SESSION
    # ─────────────────────────────────────────────────────────

    st.session_state["role"] = db_role

    st.session_state["package"] = db_package

    st.session_state["tabs"] = get_allowed_tabs(
        db_package
    )

    st.session_state["trial_end"] = db_user.get(
        "trial_end",
        "",
    )

    # reset invalidation flag
    if was_invalidated:
        _clear_invalidation_flag(username)

    # refresh UI
    st.rerun()


# ─────────────────────────────────────────────────────────────
# INVALIDATE SINGLE USER
# ─────────────────────────────────────────────────────────────

def invalidate_user_session(username: str) -> bool:
    """
    Tandai session user agar refresh pada request berikutnya.
    """

    _ensure_invalidation_column()

    try:
        conn = sqlite3.connect(_AUTH_DB)

        conn.execute(
            """
            UPDATE users
            SET session_invalidated = 1
            WHERE username = ?
            """,
            (username,),
        )

        conn.commit()
        conn.close()

        _log.info(
            f"Session user {username!r} berhasil diinvalidasi."
        )

        return True

    except Exception as e:

        _log.error(
            f"invalidate_user_session gagal: {e}"
        )

        return False


# ─────────────────────────────────────────────────────────────
# INVALIDATE ALL
# ─────────────────────────────────────────────────────────────

def invalidate_all_sessions() -> int:
    """
    Paksa semua session refresh.
    """

    _ensure_invalidation_column()

    try:
        conn = sqlite3.connect(_AUTH_DB)

        cursor = conn.execute(
            """
            UPDATE users
            SET session_invalidated = 1
            """
        )

        count = cursor.rowcount

        conn.commit()
        conn.close()

        _log.info(
            f"Semua session berhasil diinvalidasi ({count})."
        )

        return count

    except Exception as e:

        _log.error(
            f"invalidate_all_sessions gagal: {e}"
        )

        return 0


# ─────────────────────────────────────────────────────────────
# CLEAR INVALIDATION FLAG
# ─────────────────────────────────────────────────────────────

def _clear_invalidation_flag(username: str) -> None:
    """
    Reset session_invalidated = 0
    """

    try:
        conn = sqlite3.connect(_AUTH_DB)

        conn.execute(
            """
            UPDATE users
            SET session_invalidated = 0
            WHERE username = ?
            """,
            (username,),
        )

        conn.commit()
        conn.close()

    except Exception as e:

        _log.warning(
            f"_clear_invalidation_flag gagal: {e}"
        )


# ─────────────────────────────────────────────────────────────
# FORCE LOGOUT
# ─────────────────────────────────────────────────────────────

def _force_logout(message: str) -> None:
    """
    Bersihkan session dan stop aplikasi.
    """

    for key in list(st.session_state.keys()):
        del st.session_state[key]

    st.error(f"🔒 {message}")

    st.stop()