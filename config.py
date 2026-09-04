# config.py — Konstanta & Konfigurasi Global

# ── Auto-load .env ────────────────────────────────────────────────
try:
    import load_env  # noqa: F401
except Exception:
    pass

import os

# DB_FILE: default ke ~/.fnb_data/ agar tidak di dalam web root
# Bisa di-override via env var FNB_DB_FILE
_db_default_name = os.environ.get("FNB_DB_FILE", "database_bisnis_saya.db")
if os.path.isabs(_db_default_name):
    # Path absolut → pakai apa adanya
    DB_FILE = _db_default_name
elif os.environ.get("FNB_ENV") == "production":
    # Production: simpan di home directory, bukan web root
    _data_dir = os.path.join(os.path.expanduser("~"), ".fnb_data")
    os.makedirs(_data_dir, exist_ok=True)
    DB_FILE = os.path.join(_data_dir, _db_default_name)
else:
    # Development: tetap di working dir (mudah untuk debug)
    DB_FILE = _db_default_name

PAGE_TITLE = "Data Driven Analyst Specialyst FnB"

DAY_MAP = {
    "Monday": "Senin",
    "Tuesday": "Selasa",
    "Wednesday": "Rabu",
    "Thursday": "Kamis",
    "Friday": "Jumat",
    "Saturday": "Sabtu",
    "Sunday": "Minggu",
}

WEEKDAYS = ["Senin", "Selasa", "Rabu", "Kamis"]
WEEKENDS = ["Jumat", "Sabtu", "Minggu"]

TIPE_FILE_STANDAR = [
    "xlsx",
    "csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
]

FILTER_REGEX_ADDON = r"ADDITIONAL|ADD[ -]?ON|New Add-ons|Level"
FILTER_REGEX_PACKAGE = r"PACKAGE|REFILL OCHA"

# Path absolut ke file kalender — tidak bergantung dari mana app.py dijalankan
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KALENDER_PATH = os.path.join(BASE_DIR, "kalender", "kalender_event1.csv")


# ──────────────────────────────────────────────────────────────────
# KONFIGURASI PEMBAYARAN (QRIS / WhatsApp Admin)
# Isi via environment variable atau .streamlit/secrets.toml:
#
#   Environment variable:
#     PAYMENT_MERCHANT_NAME="Nama Bisnis Anda"
#     PAYMENT_REKENING="08XXXXXXXXXX"
#     PAYMENT_CONFIRM_WA="08XXXXXXXXXX"
#     PAYMENT_BANK_NAME="GoPay / OVO / QRIS"
#     PAYMENT_QRIS_USE_IMAGE="true"
#
#   secrets.toml:
#     [payment]
#     merchant_name = "Nama Bisnis Anda"
#     rekening      = "08XXXXXXXXXX"
#     confirm_wa    = "08XXXXXXXXXX"
# ──────────────────────────────────────────────────────────────────


def _get_secret(env_key: str, secrets_key: str, default: str = "") -> str:
    """Baca nilai dari env var, lalu secrets.toml, lalu default."""
    val = os.environ.get(env_key, "")
    if val:
        return val
    try:
        import streamlit as _st

        return _st.secrets.get("payment", {}).get(secrets_key, default)
    except Exception:
        return default


# ──────────────────────────────────────────────────────────────────
# KONFIGURASI SESSION LOGIN
# Isi via environment variable atau .streamlit/secrets.toml:
#
#   Environment variable:
#     SESSION_HOURS=8          # durasi session tanpa "Ingat Saya" (default: 8 jam)
#     SESSION_REMEMBER_DAYS=30 # durasi session dengan "Ingat Saya" (default: 30 hari)
#
#   secrets.toml:
#     [session]
#     session_hours    = 8
#     remember_days    = 30
# ──────────────────────────────────────────────────────────────────


def _get_session_secret(env_key: str, secrets_key: str, default: int) -> int:
    val = os.environ.get(env_key, "")
    if val:
        try:
            return int(val)
        except ValueError:
            pass
    try:
        import streamlit as _st

        return int(_st.secrets.get("session", {}).get(secrets_key, default))
    except Exception:
        return default


SESSION_CONFIG: dict = {
    # Session pendek: expired setelah N jam (tanpa "Ingat Saya")
    "session_hours": _get_session_secret("SESSION_HOURS", "session_hours", 8),
    # Session panjang: expired setelah N hari (dengan "Ingat Saya")
    "remember_days": _get_session_secret("SESSION_REMEMBER_DAYS", "remember_days", 30),
}

PAYMENT_CONFIG: dict = {
    "merchant_name": _get_secret(
        "PAYMENT_MERCHANT_NAME", "merchant_name", "Data Driven Analyst FnB"
    ),
    "bank_name": _get_secret(
        "PAYMENT_BANK_NAME", "bank_name", "GoPay / OVO / Dana / QRIS"
    ),
    "rekening": _get_secret("PAYMENT_REKENING", "rekening", ""),
    "atas_nama": _get_secret("PAYMENT_ATAS_NAMA", "atas_nama", ""),
    "confirm_wa": _get_secret("PAYMENT_CONFIRM_WA", "confirm_wa", ""),
    "use_image": os.environ.get("PAYMENT_QRIS_USE_IMAGE", "false").lower() == "true",
    "qris_image_path": os.path.join(BASE_DIR, "asset", "qris.png"),
}
