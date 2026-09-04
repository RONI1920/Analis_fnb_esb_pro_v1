#!/usr/bin/env python3
"""
health_check.py — Cek kesehatan aplikasi sebelum/sesudah deployment.
Jalankan: python health_check.py

Exit code: 0 = sehat, 1 = ada masalah
"""
from __future__ import annotations
import os, sys
from pathlib import Path

# Load .env
_env = Path(__file__).parent / ".env"
if _env.exists():
    with open(_env, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip(); v = v.strip()
            if k and k not in os.environ:
                os.environ[k] = v

issues = []
warnings = []

print("=" * 50)
print("  FnB Dashboard — Health Check")
print("=" * 50)

# 1. JWT Secret
jwt = os.environ.get("FNB_JWT_SECRET", "")
if not jwt:
    issues.append("❌ FNB_JWT_SECRET tidak diset")
elif len(jwt) < 32:
    issues.append(f"❌ FNB_JWT_SECRET terlalu pendek ({len(jwt)} chars)")
else:
    print(f"✅ JWT Secret: OK ({len(jwt)} chars)")

# 2. Database
db_file = os.environ.get("FNB_DB_FILE", "database_bisnis_saya.db")
if not os.path.isabs(db_file):
    prod_path = Path.home() / ".fnb_data" / db_file
    local_path = Path(__file__).parent / db_file
    if prod_path.exists():
        db_file = str(prod_path)
    elif local_path.exists():
        db_file = str(local_path)

if os.path.exists(db_file):
    size_kb = os.path.getsize(db_file) / 1024
    print(f"✅ Database: {db_file} ({size_kb:.1f} KB)")
else:
    warnings.append(f"⚠️  Database belum ada (akan dibuat otomatis saat pertama run): {db_file}")

# 3. Backup dir
backup_dir = os.environ.get("FNB_BACKUP_DIR", "")
if not backup_dir:
    warnings.append("⚠️  FNB_BACKUP_DIR belum diset — backup otomatis tidak aktif")
else:
    print(f"✅ Backup dir: {backup_dir}")

# 4. Payment config
rekening = os.environ.get("PAYMENT_REKENING", "")
confirm_wa = os.environ.get("PAYMENT_CONFIRM_WA", "")
if rekening and confirm_wa:
    print(f"✅ Payment: rekening {rekening}, WA {confirm_wa}")
else:
    warnings.append("⚠️  Konfigurasi pembayaran belum lengkap (rekening/WA)")

# 5. Python packages
required = ["streamlit", "jwt", "bcrypt", "pandas", "plotly"]
for pkg in required:
    try:
        __import__(pkg)
        print(f"✅ Package {pkg}: OK")
    except ImportError:
        issues.append(f"❌ Package {pkg} tidak terinstall — jalankan: pip install -r requirements.txt")

# 6. Required files
for fname in ["app.py", "auth.py", "database.py", "config.py", "load_env.py"]:
    fpath = Path(__file__).parent / fname
    if fpath.exists():
        print(f"✅ {fname}: OK")
    else:
        issues.append(f"❌ File {fname} tidak ditemukan")

print()
if warnings:
    for w in warnings:
        print(w)
    print()

if issues:
    print("=" * 50)
    print("  ❌ ADA MASALAH — Perbaiki sebelum production!")
    print("=" * 50)
    for i in issues:
        print(i)
    sys.exit(1)
else:
    print("=" * 50)
    print(f"  ✅ SIAP PRODUCTION ({len(warnings)} peringatan minor)")
    print("=" * 50)
    sys.exit(0)
