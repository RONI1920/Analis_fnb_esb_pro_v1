# startup_check.py
# Dijalankan otomatis oleh app.py saat start.
# Cek semua konfigurasi wajib sebelum app bisa digunakan.

from __future__ import annotations
import os, sys

# ── Auto-load .env SEBELUM cek apapun ────────────────────────────
try:
    import load_env  # noqa: F401
except Exception:
    pass

_ERRORS   = []
_WARNINGS = []


def _check() -> tuple[list[str], list[str]]:
    errors   = []
    warnings = []

    # ── P0-1: JWT Secret ──────────────────────────────────────────
    jwt_secret = os.environ.get("FNB_JWT_SECRET", "")
    if not jwt_secret:
        errors.append(
            "❌ FNB_JWT_SECRET belum diset!\n"
            "   Jalankan: python -c \"import secrets; print(secrets.token_hex(32))\"\n"
            "   Lalu set di .env atau environment variable server."
        )
    elif jwt_secret in (
        "ganti-dengan-random-string-minimal-32-karakter",
        "dev-only-secret-not-for-production-use-min32!",
    ):
        env_mode = os.environ.get("FNB_ENV", "development")
        if env_mode == "production":
            errors.append(
                "❌ FNB_JWT_SECRET masih nilai default/placeholder!\n"
                "   Ganti dengan string acak minimal 32 karakter."
            )
        else:
            warnings.append("⚠️  FNB_JWT_SECRET masih placeholder — OK untuk development.")
    elif len(jwt_secret) < 32:
        errors.append(
            f"❌ FNB_JWT_SECRET terlalu pendek ({len(jwt_secret)} karakter, minimal 32)."
        )

    # ── P0-2: DB path ─────────────────────────────────────────────
    from config import DB_FILE
    db_name = os.path.basename(DB_FILE)
    if db_name.endswith(".db") and DB_FILE == db_name:
        env_mode = os.environ.get("FNB_ENV", "development")
        if env_mode == "production":
            warnings.append(
                f"⚠️  Database ({DB_FILE}) ada di working directory.\n"
                "   Set FNB_DB_FILE ke path absolut di luar web root untuk keamanan ekstra."
            )

    # ── P0-3: .env placeholder check ─────────────────────────────
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            content = f.read()
        if "ganti-dengan-random" in content or "XXXXXXXXXX" in content:
            warnings.append(
                "⚠️  File .env berisi nilai placeholder.\n"
                "   Pastikan sudah diisi dengan nilai nyata sebelum production."
            )

    # ── P1-1: Payment config check ───────────────────────────────
    rekening   = os.environ.get("PAYMENT_REKENING", "")
    confirm_wa = os.environ.get("PAYMENT_CONFIRM_WA", "")
    # Fallback ke secrets.toml
    if not rekening or not confirm_wa:
        try:
            import streamlit as _st
            pay = _st.secrets.get("payment", {})
            rekening   = rekening   or pay.get("rekening", "")
            confirm_wa = confirm_wa or pay.get("confirm_wa", "")
        except Exception:
            pass
    if not rekening or not confirm_wa:
        warnings.append(
            "⚠️  Konfigurasi pembayaran belum lengkap.\n"
            "   Set PAYMENT_REKENING dan PAYMENT_CONFIRM_WA di .env atau secrets.toml."
        )

# Hilangkan warning sementara 

    # ── P1-2: Backup dir ─────────────────────────────────────────
    # env_mode = os.environ.get("FNB_ENV", "development")
    # if env_mode == "production":
    #     backup_dir = os.environ.get("FNB_BACKUP_DIR", "")
    #     if not backup_dir:
    #         warnings.append(
    #             "⚠️  FNB_BACKUP_DIR belum diset.\n"
    #             "   Backup otomatis tidak aktif — data berisiko hilang jika server crash.\n"
    #             "   Set FNB_BACKUP_DIR=C:\\Users\\RoniAlHidayat\\fnb_backups di .env."
    #         )
    #     else:
    #         # Pastikan folder backup bisa dibuat / sudah ada
    #         try:
    #             import pathlib
    #             pathlib.Path(backup_dir).mkdir(parents=True, exist_ok=True)
    #         except Exception as e:
    #             warnings.append(f"⚠️  FNB_BACKUP_DIR tidak bisa dibuat: {e}")


    # ── P1-3: Email placeholder check ────────────────────────────
    email_sender = os.environ.get("NOTIFY_EMAIL_SENDER", "")
    email_pass   = os.environ.get("NOTIFY_EMAIL_APP_PASSWORD", "")
    if email_sender == "email_anda@gmail.com" or "xxxx" in email_pass:
        # Ini warning ringan — email notifikasi opsional
        pass  # Tidak perlu warning di UI, cukup diam

    return errors, warnings


def run_startup_checks(show_in_ui: bool = True) -> bool:
    errors, warnings = _check()

    if not show_in_ui:
        if errors:
            for e in errors:
                print(f"[STARTUP ERROR] {e}", file=sys.stderr)
        return len(errors) == 0

    try:
        import streamlit as st
        if errors:
            st.error("### 🚨 Konfigurasi Wajib Belum Lengkap")
            for e in errors:
                st.error(e)
            st.info(
                "Setelah memperbaiki konfigurasi, **restart** aplikasi.\n\n"
                "Panduan lengkap ada di file **PRODUCTION_CHECKLIST.md**"
            )
            st.stop()

        if warnings:
            for w in warnings:
                st.warning(w)
    except Exception:
        pass

    return len(errors) == 0
