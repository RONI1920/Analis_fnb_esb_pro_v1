#!/usr/bin/env python3
"""
backup.py — Script backup database otomatis.

Cara pakai:
  Manual     : python backup.py
  Windows Task Scheduler: Jalankan setiap hari jam 02:00
  Linux cron : 0 2 * * * cd /path/to/app && python backup.py

Env vars (di .env):
  FNB_DB_FILE    = path ke database SQLite
  FNB_BACKUP_DIR = folder tujuan backup (default: ./backups)
  FNB_BACKUP_MAX = jumlah backup yang disimpan (default: 30)
"""

from __future__ import annotations
import os
import sys
import shutil
from datetime import datetime
from pathlib import Path

# ── Auto-load .env ────────────────────────────────────────────────
try:
    _base = Path(__file__).parent
    _env  = _base / ".env"
    if _env.exists():
        with open(_env, encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if not _line or _line.startswith("#") or "=" not in _line:
                    continue
                _k, _, _v = _line.partition("=")
                _k = _k.strip(); _v = _v.strip()
                if _k and _k not in os.environ:
                    os.environ[_k] = _v
except Exception:
    pass


def run_backup() -> bool:
    db_file    = os.environ.get("FNB_DB_FILE", "database_bisnis_saya.db")
    backup_dir = os.environ.get("FNB_BACKUP_DIR", "backups")
    max_keep   = int(os.environ.get("FNB_BACKUP_MAX", "30"))

    # Resolve relative DB path — cek di ~/.fnb_data/ juga (production)
    if not os.path.isabs(db_file):
        prod_path = Path.home() / ".fnb_data" / db_file
        local_path = Path(__file__).parent / db_file
        if prod_path.exists():
            db_file = str(prod_path)
        elif local_path.exists():
            db_file = str(local_path)

    if not os.path.exists(db_file):
        print(f"❌ Database tidak ditemukan: {db_file}")
        print(f"   Coba set FNB_DB_FILE di .env ke path yang benar.")
        return False

    # Buat folder backup (Windows path OK)
    try:
        Path(backup_dir).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"❌ Tidak bisa membuat folder backup '{backup_dir}': {e}")
        return False

    # Nama file backup dengan timestamp
    ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
    db_name = Path(db_file).stem
    dest    = str(Path(backup_dir) / f"{db_name}_backup_{ts}.db")

    # Backup dengan SQLite API (aman untuk DB yang sedang dipakai)
    try:
        import sqlite3
        src_conn = sqlite3.connect(db_file)
        dst_conn = sqlite3.connect(dest)
        src_conn.backup(dst_conn)
        dst_conn.close()
        src_conn.close()
        size_kb = os.path.getsize(dest) / 1024
        print(f"✅ Backup berhasil: {dest} ({size_kb:.1f} KB)")
    except Exception as e:
        print(f"❌ Backup gagal: {e}")
        # Fallback: simple file copy
        try:
            shutil.copy2(db_file, dest)
            size_kb = os.path.getsize(dest) / 1024
            print(f"✅ Backup (copy) berhasil: {dest} ({size_kb:.1f} KB)")
        except Exception as e2:
            print(f"❌ Backup copy juga gagal: {e2}")
            return False

    # Hapus backup lama, simpan max_keep terbaru
    backups = sorted(Path(backup_dir).glob(f"{db_name}_backup_*.db"))
    if len(backups) > max_keep:
        for old in backups[:-max_keep]:
            old.unlink(missing_ok=True)
            print(f"🗑  Hapus backup lama: {old.name}")

    return True


if __name__ == "__main__":
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Menjalankan backup...")
    success = run_backup()
    sys.exit(0 if success else 1)
