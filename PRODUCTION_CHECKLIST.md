# 🚀 Production Checklist — FnB SaaS Dashboard
**Update: Juni 2026 | Score: 62/100 → target 80/100**

---

## ✅ STATUS KEAMANAN (sudah difix)
- [x] SQL Injection — whitelist + parameterized query
- [x] Password hashing — bcrypt rounds=12
- [x] JWT secret — RuntimeError jika tidak diset di production
- [x] CSPRNG reset token — secrets.token_urlsafe
- [x] Role escalation — diblok di update_user()
- [x] XSS — html.escape di semua output user
- [x] File upload — magic byte validation
- [x] Multi-tenant — WHERE user_id di semua query
- [x] Session — clear penuh saat logout
- [x] Revenue integrity — DEDUP agresif dihapus

---

## 🔴 P0 — WAJIB sebelum deploy (30 menit)

### P0-1: Set JWT Secret
```bash
# Generate secret kuat
python -c "import secrets; print(secrets.token_hex(32))"

# Set di .env
FNB_JWT_SECRET=hasil_dari_command_di_atas
FNB_ENV=production
```

### P0-2: DB path aman
```bash
# Set path absolut di luar web root
FNB_DB_FILE=/var/data/fnb/database_bisnis_saya.db

# Atau biarkan default — production mode otomatis simpan di ~/.fnb_data/
FNB_ENV=production  # cukup ini
```

### P0-3: Jangan commit/kirim .env
```bash
# .env TIDAK boleh ada di ZIP atau git
# Kirim ke client hanya .env.example
# Client isi sendiri nilai nyata sebelum jalankan
echo ".env" >> .gitignore
```

---

## 🟠 P1 — Fix dalam 1 minggu setelah launch

### P1-1: Backup otomatis
```bash
# Jalankan manual dulu, cek berhasil
python backup.py

# Setup cron harian jam 02:00
crontab -e
# Tambah baris ini:
0 2 * * * cd /path/to/app && python backup.py >> /var/log/fnb_backup.log 2>&1

# Set folder backup di .env
FNB_BACKUP_DIR=/var/backup/fnb
FNB_BACKUP_MAX=30  # simpan 30 hari terakhir
```

### P1-2: Error monitoring (Sentry — GRATIS)
```bash
# 1. Daftar di sentry.io (free tier 5000 error/bulan)
# 2. Buat project Python
# 3. Install SDK
pip install sentry-sdk

# 4. Set DSN di .env
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx

# Sekarang semua error otomatis terkirim ke Sentry dashboard
```

### P1-3: Monitoring uptime (UptimeRobot — GRATIS)
```
1. Daftar di uptimerobot.com
2. Tambah monitor HTTP ke URL app (misal: https://app.client.com)
3. Set alert ke email/WhatsApp jika down
4. Gratis untuk 50 monitor, interval 5 menit
```

### P1-4: PIN Dependencies
```bash
# requirements.txt sudah di-pin — deploy pakai versi exact
pip install -r requirements.txt
```

---

## 🟡 P2 — Monitor dan fix bertahap

- [ ] Migrasi PostgreSQL saat user > 20 simultan (P1-1)
- [ ] Session token revocation server-side (P2-2)
- [ ] Rate limit OTP persistent di DB — tabel otp_attempts sudah ada (P2-3)
- [ ] Analytics graceful error — gunakan tab_error_guard() dari formatters.py (P2-4)

---

## 📋 Checklist Deploy Cepat

```bash
# 1. Clone / extract app
cd /path/to/app

# 2. Copy dan isi .env
cp .env.example .env
nano .env  # isi FNB_JWT_SECRET, FNB_ENV=production, dll

# 3. Install dependencies
pip install -r requirements.txt

# 4. Test startup checks
python -c "from startup_check import run_startup_checks; print(run_startup_checks(show_in_ui=False))"
# Harus print: True

# 5. Backup script test
python backup.py

# 6. Jalankan
streamlit run app.py --server.port 8501

# 7. Pasang UptimeRobot monitor ke URL
# 8. Setup cron backup harian
```

---

## 📊 Scoring Progress

| Area | Sebelum Audit | Setelah Patch | Target |
|---|---|---|---|
| Security | 52/100 | 72/100 | 85/100 |
| Data Integrity | 60/100 | 90/100 | 95/100 |
| Stability | 40/100 | 68/100 | 80/100 |
| Scalability | 45/100 | 45/100 | 70/100* |
| Observability | 20/100 | 50/100 | 75/100 |
| Test Coverage | 0/100 | 65/100 | 80/100 |
| **Overall** | **36/100** | **65/100** | **80/100** |

*Perlu migrasi PostgreSQL untuk capai 70+

---

*Generated: Juni 2026 | fnb_saas_v7_12_patched*
