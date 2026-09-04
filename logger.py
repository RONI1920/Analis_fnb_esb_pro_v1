# logger.py — Centralized logging untuk FnB SaaS
# Semua error dari except: pass seharusnya lewat sini

from __future__ import annotations
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

_LOG_LEVEL = os.environ.get("FNB_LOG_LEVEL", "INFO").upper()
_LOG_FILE  = os.environ.get("FNB_LOG_FILE", "fnb_app.log")
_SENTRY_DSN = os.environ.get("SENTRY_DSN", "")

def _setup() -> logging.Logger:
    logger = logging.getLogger("fnb_saas")
    if logger.handlers:
        return logger  # sudah di-setup sebelumnya

    logger.setLevel(getattr(logging, _LOG_LEVEL, logging.INFO))
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File handler (rotating 5MB × 3 file)
    try:
        fh = RotatingFileHandler(_LOG_FILE, maxBytes=5*1024*1024, backupCount=3,
                                  encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception:
        pass  # jika tidak bisa tulis file, tetap log ke console

    # Sentry (opsional) — aktif jika SENTRY_DSN di-set di .env
    if _SENTRY_DSN:
        try:
            import sentry_sdk
            sentry_sdk.init(dsn=_SENTRY_DSN, traces_sample_rate=0.1)
            logger.info("Sentry error tracking aktif")
        except ImportError:
            logger.warning("SENTRY_DSN diset tapi sentry-sdk tidak terinstall. "
                          "Jalankan: pip install sentry-sdk")

    return logger

log = _setup()


def capture_exception(exc: Exception, context: str = "") -> None:
    """Log exception + kirim ke Sentry jika aktif."""
    msg = f"{context}: {type(exc).__name__}: {exc}" if context else str(exc)
    log.error(msg, exc_info=True)
    if _SENTRY_DSN:
        try:
            import sentry_sdk
            sentry_sdk.capture_exception(exc)
        except Exception:
            pass


def capture_message(message: str, level: str = "info") -> None:
    """Log pesan + kirim ke Sentry jika aktif."""
    getattr(log, level.lower(), log.info)(message)
    if _SENTRY_DSN:
        try:
            import sentry_sdk
            sentry_sdk.capture_message(message, level=level)
        except Exception:
            pass
