# supa_sync.py — Persistensi file SQLite via Supabase Storage
#
# TUJUAN:
#   Streamlit Cloud (dan platform PaaS sejenis) punya filesystem EPHEMERAL:
#   setiap kali container di-restart (idle sleep, redeploy, realokasi resource),
#   semua file lokal (termasuk database_bisnis_saya.db) direset ke isi Git repo.
#   Modul ini menitipkan file SQLite ke Supabase Storage (bucket private) supaya
#   data tetap ada walau container restart — TANPA mengubah satu pun query SQL
#   yang sudah ada di database.py.
#
# CARA KERJA:
#   1) restore_db_if_needed()  -> dipanggil sekali saat app start (di database.py).
#      Kalau file .db lokal belum ada/kosong, download versi terakhir dari
#      Supabase Storage. Kalau lokal sudah ada isinya, JANGAN ditimpa.
#   2) schedule_upload()       -> dipanggil setiap kali conn.commit() terjadi.
#      Snapshot file .db (pakai SQLite backup API, aman walau WAL mode aktif)
#      lalu upload ke Supabase Storage secara async (thread terpisah, di-debounce
#      supaya tidak upload berkali-kali dalam hitungan detik yang sama).
#
# KONFIGURASI (isi di .env lokal ATAU Streamlit Secrets):
#   SUPABASE_URL          = https://xxxxxxxx.supabase.co
#   SUPABASE_SERVICE_KEY  = (service_role key, BUKAN anon key)
#   SUPABASE_DB_BUCKET    = db-backup   (default kalau tidak diisi)
#
#   Jika variabel di atas tidak diisi / library `supabase` belum terinstall,
#   modul ini otomatis nonaktif (silent) dan aplikasi tetap jalan 100% dengan
#   SQLite lokal seperti biasa — tidak ada breaking change.

from __future__ import annotations

import os
import sqlite3
import tempfile
import threading
import time
from pathlib import Path

try:
    from logger import capture_exception as _capture_exc
except ImportError:
    def _capture_exc(e, ctx=""):
        pass

_MIN_UPLOAD_INTERVAL_SEC = 5  # debounce: minimal jeda antar-upload
_last_upload_ts = 0.0
_upload_lock = threading.Lock()
_client = None
_client_checked = False


def _get_secret(key: str, default: str = "") -> str:
    """Baca konfigurasi dari env var dulu, lalu fallback ke st.secrets['supabase']."""
    val = os.environ.get(key, "")
    if val:
        return val
    try:
        import streamlit as _st
        return _st.secrets.get("supabase", {}).get(key.lower().replace("supabase_", ""), default) \
            or _st.secrets.get(key, default)
    except Exception:
        return default


def _get_client():
    """Lazy singleton client Supabase. Return None kalau belum dikonfigurasi."""
    global _client, _client_checked
    if _client_checked:
        return _client
    _client_checked = True

    url = _get_secret("SUPABASE_URL")
    key = _get_secret("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("[supa_sync] SUPABASE_URL / SUPABASE_SERVICE_KEY belum diisi — "
              "sync ke Supabase Storage nonaktif, pakai SQLite lokal saja.")
        return None

    try:
        from supabase import create_client
        _client = create_client(url, key)
        print("[supa_sync] Supabase Storage sync AKTIF.")
    except Exception as e:
        print(f"[supa_sync] Gagal init Supabase client: {e}")
        _capture_exc(e, "supa_sync._get_client")
        _client = None

    return _client


def _bucket_name() -> str:
    return _get_secret("SUPABASE_DB_BUCKET", "db-backup")


def _snapshot_to_temp(db_path: str) -> str | None:
    """Ambil snapshot konsisten dari DB (aman walau WAL mode aktif) ke file temp."""
    fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        src = sqlite3.connect(db_path)
        dst = sqlite3.connect(tmp_path)
        src.backup(dst)
        dst.close()
        src.close()
        return tmp_path
    except Exception as e:
        print(f"[supa_sync] Snapshot DB gagal: {e}")
        _capture_exc(e, "supa_sync._snapshot_to_temp")
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        return None


def restore_db_if_needed(db_path: str) -> None:
    """
    Dipanggil SEKALI saat app start (dari database.py, saat module di-import).
    Kalau file DB lokal belum ada / masih 0 byte -> download dari Supabase Storage.
    Kalau file lokal sudah ada isinya -> dibiarkan (tidak ditimpa).
    """
    client = _get_client()
    if client is None:
        return

    try:
        if os.path.exists(db_path) and os.path.getsize(db_path) > 0:
            # Sudah ada data lokal (container belum restart / masih sesi lama) — skip.
            return

        object_name = os.path.basename(db_path)
        bucket = _bucket_name()
        data = client.storage.from_(bucket).download(object_name)

        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        with open(db_path, "wb") as f:
            f.write(data)
        print(f"[supa_sync] DB berhasil di-restore dari Supabase Storage "
              f"({bucket}/{object_name}, {len(data)/1024:.1f} KB).")
    except Exception as e:
        # Wajar terjadi saat pertama kali pakai (belum pernah ada backup tersimpan).
        print(f"[supa_sync] Tidak ada backup di Supabase Storage (mungkin pertama kali): {e}")


def schedule_upload(db_path: str) -> None:
    """
    Dipanggil setiap kali conn.commit() terjadi (lihat database.py).
    Upload snapshot terbaru ke Supabase Storage secara ASYNC + DEBOUNCED,
    supaya tidak membebani setiap single commit dengan I/O jaringan.
    """
    client = _get_client()
    if client is None:
        return

    global _last_upload_ts
    now = time.time()
    with _upload_lock:
        if now - _last_upload_ts < _MIN_UPLOAD_INTERVAL_SEC:
            return
        _last_upload_ts = now

    def _do_upload():
        tmp_path = _snapshot_to_temp(db_path)
        if not tmp_path:
            return
        try:
            object_name = os.path.basename(db_path)
            bucket = _bucket_name()
            with open(tmp_path, "rb") as f:
                data = f.read()
            client.storage.from_(bucket).upload(
                path=object_name,
                file=data,
                file_options={"content-type": "application/octet-stream", "upsert": "true"},
            )
        except Exception as e:
            print(f"[supa_sync] Upload ke Supabase Storage gagal: {e}")
            _capture_exc(e, "supa_sync.schedule_upload")
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    threading.Thread(target=_do_upload, daemon=True, name="supa-sync-upload").start()


def force_upload_now(db_path: str) -> bool:
    """
    Upload SEKARANG JUGA, tanpa debounce dan tanpa background thread (blocking).
    Berguna untuk dipanggil manual dari admin panel ('Backup ke Supabase sekarang')
    atau sebelum app dimatikan secara terkontrol.
    """
    client = _get_client()
    if client is None:
        return False

    tmp_path = _snapshot_to_temp(db_path)
    if not tmp_path:
        return False
    try:
        object_name = os.path.basename(db_path)
        bucket = _bucket_name()
        with open(tmp_path, "rb") as f:
            data = f.read()
        client.storage.from_(bucket).upload(
            path=object_name,
            file=data,
            file_options={"content-type": "application/octet-stream", "upsert": "true"},
        )
        global _last_upload_ts
        _last_upload_ts = time.time()
        return True
    except Exception as e:
        print(f"[supa_sync] force_upload_now gagal: {e}")
        _capture_exc(e, "supa_sync.force_upload_now")
        return False
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass
