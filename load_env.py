# load_env.py — Auto-load .env file ke os.environ
# Di-import di awal app.py dan startup_check.py
# Kompatibel Windows & Linux tanpa perlu shell script

from __future__ import annotations
import os
from pathlib import Path


def load_dotenv_manual(env_file: str = ".env") -> dict[str, str]:
    """
    Load .env file ke os.environ secara manual.
    Tidak butuh library python-dotenv — pure stdlib.
    Return: dict key-value yang berhasil di-load.
    """
    loaded = {}

    # Cari .env di folder yang sama dengan script ini (root project)
    base_dir = Path(__file__).parent
    env_path = base_dir / env_file

    if not env_path.exists():
        return loaded

    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip komentar dan baris kosong
            if not line or line.startswith("#"):
                continue
            # Skip baris tanpa =
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key   = key.strip()
            value = value.strip()
            # Hapus quote jika ada
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            # Jangan override jika sudah di-set di environment sistem
            if key and key not in os.environ:
                os.environ[key] = value
                loaded[key] = value

    return loaded


# Auto-load saat diimport
_loaded = load_dotenv_manual()
