# packages.py — Definisi Paket, Harga, dan Permission Map
#
# Versi gabungan fnb_project + fnb_project1:
#   - Paket "free" (trial terbatas, tanpa kartu kredit)
#   - Grade A = Starter, Grade B = Growth, Grade C = Pro
#   - Tab-level access bisa di-toggle dari Admin Panel (DB override)
#   - use_database per paket (dari fnb_project)
#   - Tab baru: RFM, Inventori, Operasional, PL Advanced (dari fnb_project1)

from __future__ import annotations

# ──────────────────────────────────────────────────────────────────
# DAFTAR SEMUA TAB
# ──────────────────────────────────────────────────────────────────

ALL_TABS: list[str] = [
    "📊 Penjualan (GMV)",
    "💰 COGS & Profit",
    "🧑‍🍳 SDM & Waktu Sibuk",
    "🛒 Pembelian",
    "⚖️ A/B Comparison",
    "🎯 Target",
    "🔮 Forecast (AI)",
    "❤️ Ulasan",
    "💡 Rekomendasi",
    "💸 Analisis Promo",
    "✨ Analisis Musiman",
    "🧪 Lab Strategi",
    "📉 Laporan Laba Rugi (P&L)",
    "👥 RFM & Loyalitas",
    "📦 Inventori Lanjutan",
    "⚙️ Operasional Lanjutan",
    "🔧 Menu Engineering",
    "🍽️ Klarifikasi Section",
    "🤖 Enterprise AI Assistant",
]


# Tab khusus admin — tidak masuk paket manapun
ADMIN_TAB = "🛠️ Admin Panel"


# ──────────────────────────────────────────────────────────────────
# DEFINISI PAKET
# ──────────────────────────────────────────────────────────────────

PACKAGE_DEFINITIONS: dict[str, dict] = {
    # ── Gratis / Trial ──────────────────────────────────────────
    "free": {
        "name": "Gratis",
        "grade": None,
        "price_monthly": 0,
        "price_yearly": 0,
        "trial_days": 30,
        "description": "Coba fitur dasar tanpa biaya. Akun trial 30 hari.",
        "color": "#6B7280",
        "badge_color": "#374151",
        "use_database": False,   # Data hanya in-memory, tidak disimpan ke DB
        "highlight": False,
        "tabs": [
            "📊 Penjualan (GMV)",
        ],
    },

    # ── Grade A — Starter ────────────────────────────────────────
    "starter": {
        "name": "Grade A",
        "grade": "A",
        "price_monthly": 149_000,
        "price_yearly": 1_490_000,
        "trial_days": 7,
        "description": "Cocok untuk bisnis F&B yang baru mulai tracking data.",
        "color": "#1D9E75",
        "badge_color": "#064e3b",
        "use_database": True,    # Data tersimpan permanen di SQLite
        "highlight": False,
        "tabs": [
            "📊 Penjualan (GMV)",
            "💰 COGS & Profit",
            "🧑‍🍳 SDM & Waktu Sibuk",
        ],
    },

    # ── Grade B — Growth ─────────────────────────────────────────
    "growth": {
        "name": "Grade B",
        "grade": "B",
        "price_monthly": 299_000,
        "price_yearly": 2_990_000,
        "trial_days": 7,
        "description": "Kontrol penuh atas operasional harian bisnis Anda.",
        "color": "#185FA5",
        "badge_color": "#1e3a5f",
        "use_database": True,    # Data tersimpan permanen di SQLite
        "highlight": True,   # Most popular
        "tabs": [
            "📊 Penjualan (GMV)",
            "💰 COGS & Profit",
            "🧑‍🍳 SDM & Waktu Sibuk",
            "🛒 Pembelian",
            "⚖️ A/B Comparison",
            "🎯 Target",
            "🍽️ Klarifikasi Section",
        ],
    },

    # ── Grade C — Pro ────────────────────────────────────────────
    "pro": {
        "name": "Grade C",
        "grade": "C",
        "price_monthly": 499_000,
        "price_yearly": 4_990_000,
        "trial_days": 14,
        "description": "Analitik lengkap dengan AI Forecast dan Market Basket.",
        "color": "#534AB7",
        "badge_color": "#2e1065",
        "use_database": True,    # Data tersimpan permanen di SQLite
        "highlight": False,
        "tabs": [
            "📊 Penjualan (GMV)",
            "💰 COGS & Profit",
            "🧑‍🍳 SDM & Waktu Sibuk",
            "🛒 Pembelian",
            "⚖️ A/B Comparison",
            "🎯 Target",
            "🔮 Forecast (AI)",
            "❤️ Ulasan",
            "💡 Rekomendasi",
            "💸 Analisis Promo",
            "🍽️ Klarifikasi Section",
        ],
    },

    # ── Enterprise — semua fitur + AI Assistant ──────────────────
    "enterprise": {
        "name": "Enterprise",
        "grade": None,
        "price_monthly": 0,
        "price_yearly": 0,
        "trial_days": 30,
        "description": "Akses semua fitur + AI Assistant interaktif + prioritas support. Harga negosiasi.",
        "color": "#993C1D",
        "badge_color": "#431407",
        "use_database": True,    # Data tersimpan permanen di SQLite
        "highlight": False,
        "tabs": ALL_TABS,
    },
}

# Urutan tampil di halaman pricing
PACKAGE_ORDER: list[str] = ["free", "starter", "growth", "pro", "enterprise"]

# Urutan tampil di pricing page publik
PRICING_DISPLAY_ORDER: list[str] = ["free", "starter", "growth", "pro", "enterprise"]


# ──────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ──────────────────────────────────────────────────────────────────

def can_use_database(package_key: str, db_override: bool | None = None) -> bool:
    """
    Apakah paket ini boleh menyimpan/membaca data dari SQLite database.

    Args:
        package_key:  kunci paket user
        db_override:  nilai dari kolom use_database di tabel packages DB.
                      Jika None, pakai default dari PACKAGE_DEFINITIONS.

    Returns:
        True  → upload disimpan ke DB, data persisten antar session
        False → upload hanya in-memory, hilang saat refresh
    """
    if db_override is not None:
        return bool(db_override)
    cfg = PACKAGE_DEFINITIONS.get(package_key, PACKAGE_DEFINITIONS["free"])
    return bool(cfg.get("use_database", False))


def get_all_package_keys() -> list[str]:
    return list(PACKAGE_DEFINITIONS.keys())


def get_package_config(package_key: str) -> dict:
    return PACKAGE_DEFINITIONS.get(package_key, PACKAGE_DEFINITIONS["starter"])


def get_allowed_tabs(package_key: str, db_overrides: dict | None = None) -> list[str]:
    """
    Kembalikan list tab yang diizinkan untuk paket tertentu.
    db_overrides: dict {tab_name: bool} dari tabel package_tab_access di DB.
    Jika db_overrides tersedia, gunakan itu sebagai sumber kebenaran.
    """
    config = get_package_config(package_key)
    default_tabs = config.get("tabs", [])

    if db_overrides is None:
        return default_tabs

    # Gabungkan: default tabs + override dari DB
    # DB bisa menambah (True) atau menonaktifkan (False) tab
    result = []
    for tab in ALL_TABS:
        if tab in db_overrides:
            if db_overrides[tab]:  # Admin explicitly enabled
                result.append(tab)
        elif tab in default_tabs:  # Pakai default paket
            result.append(tab)

    return result


def is_tab_allowed(tab_name: str, package_key: str, db_overrides: dict | None = None) -> bool:
    return tab_name in get_allowed_tabs(package_key, db_overrides)


def get_upgrade_suggestion(tab_name: str) -> str | None:
    """Kembalikan nama paket terendah yang bisa akses tab ini."""
    for key in PACKAGE_ORDER:
        if tab_name in PACKAGE_DEFINITIONS[key]["tabs"]:
            return PACKAGE_DEFINITIONS[key]["name"]
    return None


def format_price(amount: int) -> str:
    if amount == 0:
        return "Gratis"
    return f"Rp {amount:,}".replace(",", ".")


def get_package_display_info(package_key: str) -> dict:
    cfg = get_package_config(package_key)
    return {
        "key": package_key,
        "name": cfg["name"],
        "grade": cfg.get("grade"),
        "price_monthly_fmt": format_price(cfg["price_monthly"]),
        "price_yearly_fmt": format_price(cfg["price_yearly"]),
        "price_monthly": cfg["price_monthly"],
        "price_yearly": cfg["price_yearly"],
        "description": cfg["description"],
        "color": cfg["color"],
        "badge_color": cfg.get("badge_color", "#1a1f2e"),
        "highlight": cfg.get("highlight", False),
        "tab_count": len(cfg["tabs"]),
        "tabs": cfg["tabs"],
        "trial_days": cfg["trial_days"],
    }
