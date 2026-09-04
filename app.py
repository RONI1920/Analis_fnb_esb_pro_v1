# app.py — Entry Point Utama Aplikasi (User-Facing)
# Versi gabungan fnb_project + fnb_project1:
#   - Semua tab baru dari fnb_project1 (RFM, Inventori, Operasional, PL Advanced)
#   - Storage toggle + badge + _get_user_db_preference dari fnb_project
#   - use_database per paket + load data dual-mode (DB vs in-memory)

import os
import pandas as pd
import streamlit as st

# ── require_auth HARUS dipanggil SEBELUM import lain yang pakai session ──
from auth import (
    require_auth,
    is_admin,
    attempt_login,
    is_logged_in,
    clear_session,
    get_current_package_key,
    get_current_role,
    get_current_full_name,
    refresh_user_license,
    get_current_user_id,
)

from config import PAGE_TITLE
from formatters import safe_html
from database import (
    init_db,
    load_dataframe_from_db,
    save_dataframe_smart_append,
    create_user,
    create_license,
    create_payment,
    get_package_tab_access,
    get_package_use_database,
    get_user_by_username,
)
from data_loaders import (
    load_data_gmv,
    load_data_gmv_moka,
    load_cogs_data,
    load_data_waiter,
    load_data_ulasan,
    load_data_purchase,
    load_pl_data,
    load_kalender_data,
)
from packages import (
    PACKAGE_DEFINITIONS,
    PACKAGE_ORDER,
    get_allowed_tabs,
    ADMIN_TAB,
    get_package_config,
)
from ui.sidebar import build_sidebar, build_global_filters
from ui.welcome import build_welcome_screen, build_footer
from ui.pricing import build_pricing_page
from ui.register import build_register_page
from ui.payment import build_payment_page, build_payment_success_page
from admin_panel import build_admin_panel

from ui.tabs.tab1_sales import build_tab1_sales
from ui.tabs.tab2_cogs import build_tab2_cogs
from ui.tabs.tab3_hr import build_tab3_hr
from ui.tabs.tab4_comparison import build_tab4_comparison
from ui.tabs.tab5_forecast import build_tab5_forecast
from ui.tabs.tab6_target import build_tab6_target
from ui.tabs.tab7_ulasan import build_tab7_ulasan
from ui.tabs.tab8_purchase import build_tab8_purchase
from ui.tabs.tab9_rekomendasi import build_tab9_rekomendasi
from ui.tabs.tab10_promo import build_tab10_promo
from ui.tabs.tab11_musiman import build_tab11_musiman
from ui.tabs.tab12_lab import build_tab12_lab
from ui.tabs.tab13_pl import build_tab13_pl
from ui.tabs.tab16_menu_engineering import build_tab16_menu_engineering
from ui.tabs.tab_enterprise_ai import build_tab_enterprise_ai

# ── Tab Baru (fnb_project1) ───────────────────────────────────────
from ui.tabs.tab14_rfm import build_tab14_rfm
from ui.tabs.tab15_inventory import build_tab15_inventory
from ui.tabs.tab17_operasional import build_tab17_operasional
from ui.tabs.tab13_pl_advanced import build_pl_advanced_section
from ui.tabs.tab_section_clarify import build_tab_section_clarify

from startup_check import run_startup_checks

# ──────────────────────────────────────────────────────────────────
# KONSTANTA
# ──────────────────────────────────────────────────────────────────

ALL_TABS_ORDERED = [
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

ENTERPRISE_AI_TAB = "🤖 Enterprise AI Assistant"

# ── Tab yang BELUM support Moka POS ──────────────────────────────
# Tab ini butuh data COGS / Waiter / Purchase yang belum ada mapping
# Mokanya. Saat Moka aktif, tab-tab ini tampil pesan "tidak tersedia".
# Hapus dari set ini setelah mapping Moka untuk data tersebut siap.
_MOKA_UNAVAILABLE_TABS = {
    "💰 COGS & Profit",
    "🧑‍🍳 SDM & Waktu Sibuk",
    "🛒 Pembelian",
    "⚖️ A/B Comparison",
    "💡 Rekomendasi",
    "💸 Analisis Promo",
    "🧪 Lab Strategi",
    "📉 Laporan Laba Rugi (P&L)",
    "📦 Inventori Lanjutan",
    "⚙️ Operasional Lanjutan",
    "🔧 Menu Engineering",
    "🍽️ Klarifikasi Section",
}


def _moka_unavailable(tab_name: str):
    """Tampilkan pesan standar untuk tab yang belum support Moka POS."""
    st.markdown(f"""
    <div style="
        background:#1a1a2e;
        border:1px solid #3b1f6e;
        border-radius:14px;
        padding:32px 36px;
        margin:24px 0;
        text-align:center;
    ">
        <div style="font-size:2.5rem;margin-bottom:12px">🚧</div>
        <div style="font-size:1.15rem;font-weight:700;color:#c4b5fd;margin-bottom:8px">
            Data tidak tersedia untuk Moka POS
        </div>
        <div style="font-size:0.88rem;color:#9ca3af;max-width:420px;margin:0 auto;line-height:1.6">
            Tab <strong style="color:#e9d5ff">{tab_name}</strong> membutuhkan data
            yang belum tersedia dari format export Moka saat ini.<br><br>
            Fitur ini akan tersedia setelah mapping data Moka untuk tab ini selesai dikembangkan.
        </div>
    </div>
    """, unsafe_allow_html=True)

_TAB_DATA_NEEDS = {
    "📊 Penjualan (GMV)"         : ["gmv"],
    "💰 COGS & Profit"           : ["cogs", "gmv"],
    "🧑‍🍳 SDM & Waktu Sibuk"    : ["waiter", "gmv"],
    "🛒 Pembelian"               : ["purchase", "gmv"],
    "⚖️ A/B Comparison"         : ["gmv", "cogs", "waiter"],
    "🎯 Target"                  : ["gmv"],
    "🔮 Forecast (AI)"           : ["gmv"],
    "❤️ Ulasan"                  : ["ulasan"],
    "💡 Rekomendasi"             : ["gmv", "cogs"],
    "💸 Analisis Promo"          : ["gmv", "cogs"],
    "✨ Analisis Musiman"        : ["gmv"],
    "🧪 Lab Strategi"            : ["gmv", "cogs"],
    "📉 Laporan Laba Rugi (P&L)" : ["pl", "gmv"],
    "👥 RFM & Loyalitas"         : ["gmv"],
    "📦 Inventori Lanjutan"      : ["purchase", "gmv"],
    "⚙️ Operasional Lanjutan"   : ["gmv", "waiter"],
    "🔧 Menu Engineering"        : ["gmv", "cogs"],
    "🍽️ Klarifikasi Section"    : ["gmv", "cogs"],
}

_GMV_FILTER_TABS = {
    "📊 Penjualan (GMV)",
    "💰 COGS & Profit",
    "🧑‍🍳 SDM & Waktu Sibuk",
    "⚖️ A/B Comparison",
    "🎯 Target",
    "🔮 Forecast (AI)",
    "💡 Rekomendasi",
    "💸 Analisis Promo",
    "✨ Analisis Musiman",
    "🧪 Lab Strategi",
    "👥 RFM & Loyalitas",
    "📦 Inventori Lanjutan",
    "⚙️ Operasional Lanjutan",
    "🔧 Menu Engineering",
    "🍽️ Klarifikasi Section",
}

_UPLOADER_CONFIG = {
    "gmv"     : ("GMV / Sales",  "up_gmv"),
    "cogs"    : ("COGS",         "up_cogs"),
    "waiter"  : ("SDM / Waiter", "up_waiter"),
    "ulasan"  : ("Ulasan",       "up_ulasan"),
    "purchase": ("Pembelian",    "up_purchase"),
    "pl"      : ("P&L",          "up_pl"),
}

# ──────────────────────────────────────────────────────────────────
# KONFIGURASI HALAMAN
# ──────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ──────────────────────────────────────────────────────────────────
# STARTUP CHECKS — validasi konfigurasi P0 sebelum app berjalan
run_startup_checks(show_in_ui=True)

# INIT DATABASE
# ──────────────────────────────────────────────────────────────────
init_db()

# ──────────────────────────────────────────────────────────────────
# AUTH GUARD
# ──────────────────────────────────────────────────────────────────
require_auth()


# ──────────────────────────────────────────────────────────────────
# REGISTRASI
# ──────────────────────────────────────────────────────────────────

def _finalize_free_registration(reg_data: dict):
    from datetime import date, timedelta

    username = reg_data["username"]
    ok, msg = create_user(
        username=username,
        email=reg_data["email"],
        password=reg_data["password"],
        role="user",
        full_name=reg_data["full_name"],
        phone=reg_data.get("phone", ""),
        company=reg_data.get("company", ""),
    )
    if not ok:
        st.error(f"Gagal membuat akun: {msg}")
        if st.button("← Coba Lagi"):
            st.session_state.pop("registration_data", None)
            st.rerun()
        return

    user = get_user_by_username(username)
    if user:
        start = date.today()
        create_license(
            user_id=user["id"],
            package_key="free",
            status="trial",
            billing_cycle="trial",
            start_date=start.isoformat(),
            end_date=(start + timedelta(days=30)).isoformat(),
        )

    st.success(f"✅ Akun trial gratis berhasil dibuat! Selamat datang, {reg_data['full_name']}!")
    st.info("Silakan login menggunakan username dan password yang sudah dibuat.")
    st.session_state.pop("registration_data", None)
    st.session_state.pop("selected_package", None)
    st.rerun()


def _finalize_paid_registration(
    reg_data: dict, pkg_key: str, billing: str, payment_result: dict
):
    """
    Dipanggil HANYA setelah user mengirim bukti pembayaran.
    Membuat akun + lisensi pending + payment record ke DB.
    """
    from datetime import date, timedelta

    username = reg_data["username"]
    try:
        from database import get_packages_merged
        cfg = get_packages_merged().get(pkg_key, PACKAGE_DEFINITIONS.get(pkg_key, {}))
    except Exception:
        cfg = PACKAGE_DEFINITIONS.get(pkg_key, {})
    amount = cfg.get("price_yearly" if billing == "yearly" else "price_monthly", 0)

    ok, msg = create_user(
        username=username,
        email=reg_data["email"],
        password=reg_data["password"],
        role="user",
        full_name=reg_data["full_name"],
        phone=reg_data.get("phone", ""),
        company=reg_data.get("company", ""),
        notes=f"Paket {pkg_key} — menunggu konfirmasi pembayaran",
    )
    if not ok:
        st.error(f"Gagal menyimpan akun: {msg}")
        return

    user = get_user_by_username(username)
    if user:
        start = date.today()
        end   = start + timedelta(days=(365 if billing == "yearly" else 30))
        create_license(
            user_id=user["id"],
            package_key=pkg_key,
            status="pending",
            billing_cycle=billing,
            start_date=start.isoformat(),
            end_date=end.isoformat(),
        )
        pay_ok, _, pay_id = create_payment(
            user_id=user["id"],
            amount=amount,
            notes=payment_result.get("notes", ""),
        )
        if pay_ok:
            st.session_state["pending_payment_id"] = pay_id


# ──────────────────────────────────────────────────────────────────
# MAIN APPLICATION
# ──────────────────────────────────────────────────────────────────

def _get_effective_tabs(package_key: str) -> list[str]:
    """
    Ambil daftar tab yang boleh diakses user berdasarkan paket + DB override.

    FIX 2 (lanjutan): Fungsi ini sudah benar — selalu pakai get_package_tab_access()
    dari DB. Pastikan semua pemanggil tab access menggunakan fungsi ini,
    bukan langsung baca PACKAGE_DEFINITIONS[key]["tabs"].
    """
    try:
        db_overrides = get_package_tab_access(package_key)
    except Exception:
        db_overrides = {}
    return get_allowed_tabs(package_key, db_overrides if db_overrides else None)


def _show_analysis_title(df_gmv, selected_tab: str = ""):
    """
    Tampilkan judul laporan di paling atas halaman.
    Membaca branch & periode yang SUDAH aktif dari session_state (di-set oleh _build_gmv_filter).
    Tidak ditampilkan pada tab: Profil, Admin, Enterprise AI.
    """
    _SKIP_TITLE_TABS = {ENTERPRISE_AI_TAB, ADMIN_TAB}
    if selected_tab in _SKIP_TITLE_TABS:
        return
    if st.session_state.get("show_profile"):
        return
    if df_gmv is None or df_gmv.empty:
        return
    try:
        col_date = "Sales Date In"
        if col_date not in df_gmv.columns:
            return

        company_name = st.session_state.get("gmv_company_name", "PT. San Thai Indonesia")

        # ── Branch label — ikuti filter aktif ─────────────────────
        active_branch = st.session_state.get("active_branch_filter", "Semua")
        if active_branch == "Semua" or not active_branch:
            branch_label = "Semua Cabang"
        else:
            branch_label = active_branch

        # ── Periode — utamakan range tersimpan dari filter aktif ──
        # _build_gmv_filter menyimpan "active_date_start" & "active_date_end"
        active_start = st.session_state.get("active_date_start")
        active_end   = st.session_state.get("active_date_end")
        active_period_type = st.session_state.get("active_period_filter", "Semua")

        if active_start and active_end:
            start_str = active_start
            end_str   = active_end
        else:
            # Fallback: gunakan min/max dari df yang dikirim (filtered_gmv)
            min_d = pd.to_datetime(df_gmv[col_date]).min()
            max_d = pd.to_datetime(df_gmv[col_date]).max()
            start_str = min_d.strftime("%d-%m-%Y")
            end_str   = max_d.strftime("%d-%m-%Y")

        # Label mode periode untuk badge
        period_badge_map = {
            "Semua": ("🗓️", "#6b7280"),
            "Harian": ("📅", "#f59e0b"),
            "Mingguan": ("📆", "#8b5cf6"),
            "Bulanan": ("🗃️", "#3b82f6"),
            "Custom": ("⚙️", "#ec4899"),
        }
        period_icon, period_color = period_badge_map.get(active_period_type, ("🗓️", "#6b7280"))

        period_display = f"{start_str} &nbsp;–&nbsp; {end_str}" if start_str != end_str else start_str

        st.markdown(
            f"""<div style="
                background:linear-gradient(135deg,#1e3a5f,#0f1a2e);
                border:1px solid #2563eb55;
                border-radius:14px;
                padding:20px 28px;
                margin-bottom:18px;
                text-align:center;
                box-shadow:0 4px 24px rgba(37,99,235,0.10);">
                <div style="font-size:11px;color:#60a5fa;text-transform:uppercase;
                            letter-spacing:.16em;font-weight:700;margin-bottom:8px">
                    📊 &nbsp;LAPORAN ANALITIK
                </div>
                <div style="font-size:1.85rem;font-weight:900;color:#f0f2f5;margin-bottom:14px;
                            letter-spacing:.01em;line-height:1.2">
                    {safe_html(company_name)}
                </div>
                <div style="display:flex;gap:40px;flex-wrap:wrap;justify-content:center;align-items:center">
                    <div style="text-align:center">
                        <span style="font-size:10px;color:#9ca3af;text-transform:uppercase;
                                     letter-spacing:.10em;display:block;margin-bottom:4px">🏪 &nbsp;CABANG</span>
                        <span style="font-size:1.05rem;font-weight:800;color:#34d399;
                                     background:#34d39918;border:1px solid #34d39940;
                                     border-radius:8px;padding:3px 14px;display:inline-block">
                            {branch_label}
                        </span>
                    </div>
                    <div style="width:1px;height:36px;background:#2d3a55;flex-shrink:0"></div>
                    <div style="text-align:center">
                        <span style="font-size:10px;color:#9ca3af;text-transform:uppercase;
                                     letter-spacing:.10em;display:block;margin-bottom:4px">📅 &nbsp;PERIODE</span>
                        <span style="font-size:1.05rem;font-weight:800;color:#60a5fa;
                                     background:#3b82f618;border:1px solid #3b82f640;
                                     border-radius:8px;padding:3px 14px;display:inline-block">
                            {period_display}
                        </span>
                    </div>
                    <div style="width:1px;height:36px;background:#2d3a55;flex-shrink:0"></div>
                    <div style="text-align:center">
                        <span style="font-size:10px;color:#9ca3af;text-transform:uppercase;
                                     letter-spacing:.10em;display:block;margin-bottom:4px">⚡ &nbsp;MODE</span>
                        <span style="font-size:0.9rem;font-weight:700;
                                     color:{period_color};background:{period_color}18;
                                     border:1px solid {period_color}40;
                                     border-radius:8px;padding:3px 12px;display:inline-block">
                            {period_icon} {active_period_type}
                        </span>
                    </div>
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
    except Exception:
        pass


def _build_main_app():
    # ──────────────────────────────────────────────────────────────
    # FIX 1: Refresh lisensi dari DB setiap kali app di-render.
    # Ini memastikan perubahan yang dibuat admin (ganti paket, perpanjang,
    # suspend, update tab access) langsung terlihat di session user
    # tanpa perlu user logout dan login ulang.
    # ──────────────────────────────────────────────────────────────
    refresh_user_license()

    # ── Halaman upgrade pricing (dari tombol Lihat Paket di sidebar) ──
    if st.session_state.get("show_pricing_upgrade"):
        from ui.pricing import build_pricing_page
        if st.button("← Kembali ke Dashboard", key="back_from_pricing"):
            st.session_state["show_pricing_upgrade"] = False
            st.rerun()
        chosen = build_pricing_page()
        if chosen:
            st.session_state["selected_package"] = chosen
            st.session_state["show_pricing_upgrade"] = False
            if chosen == "enterprise":
                # Enterprise → halaman kontak, tidak perlu logout
                st.session_state["auth_page"] = "enterprise_contact"
                from auth import clear_session
                clear_session()
            else:
                # Berbayar/free → register (logout dulu)
                st.session_state["auth_page"] = "register"
                from auth import clear_session
                clear_session()
            st.rerun()
        return

    pkg_key = get_current_package_key()
    role    = get_current_role()

    if role == "admin":
        allowed_tabs = list(ALL_TABS_ORDERED)
    else:
        # FIX 2: Gunakan _get_effective_tabs() yang sudah mempertimbangkan DB override
        allowed_tabs = _get_effective_tabs(pkg_key or "free")

    # Dashboard dulu, Admin Panel di paling bawah
    page_names = list(allowed_tabs)
    if role == "admin":
        page_names.append(ADMIN_TAB)

    with st.sidebar:
        _build_sidebar_content(pkg_key, role, get_current_full_name())

    if not page_names:
        st.warning("Tidak ada fitur yang dapat diakses. Hubungi admin.")
        return

    _route_to_tab(page_names, pkg_key, role)


def _build_sidebar_content(pkg_key, role, full_name):
    from auth import get_current_username, get_current_license_end_date, get_current_license_status
    from ui.sidebar_user_panel import build_user_profile_panel

    st.markdown("### 📊 FnB Analyst")
    st.divider()

    pkg_cfg      = get_package_config(pkg_key or "free") if pkg_key else {}
    pkg_name     = pkg_cfg.get("name", "Trial")
    pkg_color    = pkg_cfg.get("color", "#6B7280")
    supports_db  = (role == "admin") or get_package_use_database(pkg_key or "free")
    user_uses_db = st.session_state.get("user_db_preference", supports_db) and supports_db

    if role == "admin":
        st.markdown(f"👤 **{full_name.upper()}**")
        st.markdown(
            "<span style='background:#3b0764;color:#d8b4fe;border-radius:4px;"
            "padding:2px 8px;font-size:11px;font-weight:700'>ADMIN</span>",
            unsafe_allow_html=True,
        )
    else:
        build_user_profile_panel(
            username=get_current_username(),
            full_name=full_name,
            pkg_name=pkg_name,
            pkg_color=pkg_color,
            pkg_badge_color=pkg_cfg.get("badge_color", "#1a1f2e"),
            end_date=get_current_license_end_date(),
            license_status=get_current_license_status(),
            user_uses_db=user_uses_db,
        )

    st.divider()

    if pkg_key in ("free", None) and role != "admin":
        st.info("✨ Upgrade untuk akses lebih banyak fitur analitik")
        if st.button("🚀 Lihat Paket", use_container_width=True):
            st.session_state["show_pricing_upgrade"] = True
            st.rerun()

    if st.button("🚪 Logout", use_container_width=True, type="secondary"):
        clear_session()
        st.rerun()


# ──────────────────────────────────────────────────────────────────
# FILTER GMV
# ──────────────────────────────────────────────────────────────────

def _build_gmv_filter(df_gmv: pd.DataFrame) -> pd.DataFrame:
    """
    Filter Periode, Cabang, dan Menu — UI/UX yang ditingkatkan.
    Menggunakan pola "Terapkan Filter" (tombol simpan) agar filter tidak
    langsung reaktif — user bisa atur semua pilihan dulu baru klik tombol.
    Menyimpan branch, periode, dan rentang tanggal aktif ke session_state
    agar header (_show_analysis_title) selalu sinkron dengan filter.
    """
    if df_gmv is None or df_gmv.empty:
        return df_gmv

    min_date = df_gmv["Sales Date In"].min().date()
    max_date = df_gmv["Sales Date In"].max().date()

    # ── Inisialisasi session_state untuk filter yang disimpan ─────
    if "applied_filter" not in st.session_state:
        st.session_state["applied_filter"] = {}

    # ── Container filter utama ────────────────────────────────────
    st.markdown(
        """<div style="
            background:linear-gradient(135deg,#0d1b2e,#111827);
            border:1px solid #1e3a5f;
            border-radius:14px;
            padding:18px 22px 12px 22px;
            margin-bottom:8px;
            box-shadow:0 2px 16px rgba(0,0,0,0.35);">
        """,
        unsafe_allow_html=True,
    )

    col_period, col_sep, col_branch = st.columns([5, 0.1, 3])

    with col_period:
        st.markdown(
            "<p style='margin:0 0 6px 0;font-size:13px;font-weight:700;"
            "color:#93c5fd;letter-spacing:.06em;'>🗓️&nbsp; FILTER PERIODE</p>",
            unsafe_allow_html=True,
        )
        period_opt = st.radio(
            "Tampilkan:",
            ["Semua", "Harian", "Mingguan", "Bulanan", "Custom"],
            horizontal=True,
            key="period_filter",
            label_visibility="collapsed",
        )

    with col_branch:
        sel_branch = "Semua"
        if "Branch" in df_gmv.columns:
            branch_list = sorted(df_gmv["Branch"].dropna().unique().tolist())
            if len(branch_list) > 0:
                st.markdown(
                    "<p style='margin:0 0 6px 0;font-size:13px;font-weight:700;"
                    "color:#6ee7b7;letter-spacing:.06em;'>🏪&nbsp; FILTER CABANG</p>",
                    unsafe_allow_html=True,
                )
                options = ["Semua Cabang"] + branch_list
                sel_raw = st.selectbox(
                    "Pilih Cabang",
                    options=options,
                    key="filter_branch",
                    label_visibility="collapsed",
                )
                sel_branch = "Semua" if sel_raw == "Semua Cabang" else sel_raw

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Tampilkan sub-filter tanggal (jika bukan Semua) ──────────
    active_start = min_date
    active_end   = max_date
    d1 = d2 = None

    if period_opt == "Harian":
        with st.container():
            st.markdown(
                "<div style='background:#0f1a2e;border:1px solid #1e3a5f;"
                "border-radius:10px;padding:12px 18px;margin:4px 0 10px 0'>",
                unsafe_allow_html=True,
            )
            sel_date = st.date_input(
                "📅 Pilih Tanggal", max_date,
                min_value=min_date, max_value=max_date,
                key="filter_harian",
            )
            st.markdown("</div>", unsafe_allow_html=True)
        active_start = active_end = sel_date
        d1 = d2 = sel_date

    elif period_opt == "Mingguan":
        with st.container():
            st.markdown(
                "<div style='background:#0f1a2e;border:1px solid #1e3a5f;"
                "border-radius:10px;padding:12px 18px;margin:4px 0 10px 0'>",
                unsafe_allow_html=True,
            )
            col_w1, col_w2 = st.columns([2, 3])
            with col_w1:
                sel_date = st.date_input(
                    "📆 Tanggal dalam minggu", max_date,
                    min_value=min_date, max_value=max_date,
                    key="filter_mingguan",
                )
            week_start = sel_date - pd.Timedelta(days=sel_date.weekday())
            week_end   = week_start + pd.Timedelta(days=6)
            with col_w2:
                st.markdown(
                    f"<div style='padding:8px 0;color:#93c5fd;font-size:13px;font-weight:600'>"
                    f"📅 {week_start.strftime('%d %b %Y')} &nbsp;→&nbsp; {week_end.strftime('%d %b %Y')}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)
        active_start, active_end = week_start, week_end
        d1, d2 = week_start, week_end

    elif period_opt == "Bulanan":
        months_series = df_gmv["Sales Date In"].dt.to_period("M").dropna().unique()
        months_sorted = sorted(months_series, reverse=True)
        month_labels = [p.strftime("%B %Y") for p in months_sorted]
        month_map    = {p.strftime("%B %Y"): p for p in months_sorted}

        if month_labels:
            with st.container():
                st.markdown(
                    "<div style='background:#0f1a2e;border:1px solid #1e3a5f;"
                    "border-radius:10px;padding:12px 18px;margin:4px 0 10px 0'>",
                    unsafe_allow_html=True,
                )
                col_m1, col_m2 = st.columns([2, 3])
                with col_m1:
                    sel_month_label = st.selectbox(
                        "🗃️ Pilih Bulan", month_labels, key="filter_bulanan"
                    )
                period_obj = month_map[sel_month_label]
                m_start = period_obj.start_time.date()
                m_end   = period_obj.end_time.date()
                with col_m2:
                    st.markdown(
                        f"<div style='padding:8px 0;color:#93c5fd;font-size:13px;font-weight:600'>"
                        f"📅 {m_start.strftime('%d %b')} &nbsp;→&nbsp; {m_end.strftime('%d %b %Y')}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                st.markdown("</div>", unsafe_allow_html=True)
            active_start, active_end = m_start, m_end
            d1, d2 = m_start, m_end
        else:
            st.warning("Tidak ada data bulan tersedia.")

    elif period_opt == "Custom":
        with st.container():
            st.markdown(
                "<div style='background:#0f1a2e;border:1px solid #1e3a5f;"
                "border-radius:10px;padding:12px 18px;margin:4px 0 10px 0'>",
                unsafe_allow_html=True,
            )
            col_d1, col_d2, col_d3 = st.columns([2, 2, 3])
            with col_d1:
                d1 = st.date_input(
                    "⬅️ Dari", min_date,
                    min_value=min_date, max_value=max_date,
                    key="filter_custom_start",
                )
            with col_d2:
                d2 = st.date_input(
                    "➡️ Sampai", max_date,
                    min_value=min_date, max_value=max_date,
                    key="filter_custom_end",
                )
            with col_d3:
                if d1 <= d2:
                    delta = (d2 - d1).days + 1
                    st.markdown(
                        f"<div style='padding:8px 0;color:#6ee7b7;font-size:13px;font-weight:600'>"
                        f"✅ {delta} hari dipilih"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        "<div style='padding:8px 0;color:#f87171;font-size:13px;font-weight:600'>"
                        "⚠️ Tanggal tidak valid"
                        "</div>",
                        unsafe_allow_html=True,
                    )
            st.markdown("</div>", unsafe_allow_html=True)
        if d1 <= d2:
            active_start, active_end = d1, d2
        else:
            st.error("Tanggal awal harus sebelum atau sama dengan tanggal akhir.")
            d1 = d2 = None

    # ── Tombol Terapkan Filter (di bawah semua filter) ──────────
    st.markdown(
        "<div style='background:#0a1628;border:1px solid #1e3a5f;"
        "border-radius:10px;padding:10px 18px;margin:6px 0 4px 0;'>",
        unsafe_allow_html=True,
    )
    col_btn, col_status = st.columns([2, 5])
    with col_btn:
        apply_clicked = st.button(
            "💾 Terapkan Filter",
            key="btn_apply_filter",
            type="primary",
            use_container_width=True,
            help="Klik untuk menerapkan filter Cabang & Periode ke seluruh analisis",
        )
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Simpan snapshot saat tombol diklik ───────────────────────
    if apply_clicked:
        st.session_state["applied_filter"] = {
            "branch":     sel_branch,
            "period":     period_opt,
            "date_start": d1,
            "date_end":   d2,
        }
        st.toast("✅ Filter berhasil diterapkan!", icon="✅")

    # Ambil filter tersimpan, atau gunakan widget saat ini (pertama kali)
    af = st.session_state.get("applied_filter", {})
    if not af:
        applied_branch = sel_branch
        applied_period = period_opt
        applied_d1     = d1
        applied_d2     = d2
    else:
        applied_branch = af.get("branch",     sel_branch)
        applied_period = af.get("period",     period_opt)
        applied_d1     = af.get("date_start", d1)
        applied_d2     = af.get("date_end",   d2)

    with col_status:
        st.markdown(
            f"<div style='padding:8px 0;color:#94a3b8;font-size:12px;'>"
            f"🏪 Cabang: <b>{applied_branch}</b> &nbsp;|&nbsp; "
            f"🗓️ Periode: <b>{applied_period}</b>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # ── Terapkan filter ke DataFrame ─────────────────────────────
    filtered = df_gmv.copy()

    # 1. Filter cabang
    if applied_branch != "Semua" and "Branch" in filtered.columns:
        filtered = filtered[filtered["Branch"] == applied_branch]

    # 2. Filter tanggal
    if applied_period == "Harian" and applied_d1:
        filtered = filtered[filtered["Sales Date In"].dt.date == applied_d1]
        active_start = active_end = applied_d1
    elif applied_period == "Mingguan" and applied_d1 and applied_d2:
        filtered = filtered[
            (filtered["Sales Date In"].dt.date >= applied_d1)
            & (filtered["Sales Date In"].dt.date <= applied_d2)
        ]
        active_start, active_end = applied_d1, applied_d2
    elif applied_period == "Bulanan" and applied_d1 and applied_d2:
        filtered = filtered[
            (filtered["Sales Date In"].dt.date >= applied_d1)
            & (filtered["Sales Date In"].dt.date <= applied_d2)
        ]
        active_start, active_end = applied_d1, applied_d2
    elif applied_period == "Custom" and applied_d1 and applied_d2:
        if applied_d1 <= applied_d2:
            filtered = filtered[
                (filtered["Sales Date In"].dt.date >= applied_d1)
                & (filtered["Sales Date In"].dt.date <= applied_d2)
            ]
            active_start, active_end = applied_d1, applied_d2

    # ── Simpan ke session_state agar header selalu sinkron ────────
    st.session_state["active_branch_filter"] = applied_branch
    st.session_state["active_period_filter"]  = applied_period
    st.session_state["active_date_start"]     = active_start.strftime("%d-%m-%Y") if hasattr(active_start, "strftime") else str(active_start)
    st.session_state["active_date_end"]       = active_end.strftime("%d-%m-%Y")   if hasattr(active_end, "strftime") else str(active_end)

    # Info ringkas jika data kosong setelah filter
    if filtered.empty:
        st.warning("⚠️ Tidak ada data yang cocok dengan filter yang dipilih.")

    return filtered


def _get_user_db_preference(pkg_key: str, role: str) -> bool:
    """
    Ambil preferensi user apakah mau simpan ke database atau tidak.

    Prioritas:
    1. Admin → selalu True
    2. Paket tidak support DB → selalu False (tidak bisa override)
    3. User punya preferensi di session_state → pakai itu
    4. Default: ikut setting paket dari DB
    """
    if role == "admin":
        return True

    pkg_supports_db = get_package_use_database(pkg_key or "free")
    if not pkg_supports_db:
        return False  # paket tidak mendukung, tidak bisa di-override

    # Pakai preferensi user jika sudah pernah di-set
    if "user_db_preference" in st.session_state:
        return bool(st.session_state["user_db_preference"])

    # Default: ikut paket
    st.session_state["user_db_preference"] = True
    return True


def _route_to_tab(page_names: list, pkg_key: str, role: str):
    with st.sidebar:
        st.divider()
        if st.button("👤 Profil Saya", use_container_width=True, key="btn_profile"):
            st.session_state["show_profile"] = True
            st.rerun()
        else:
            st.session_state.setdefault("show_profile", False)

        # ── Toggle POS — sebelum navigasi ─────────────────────────
        st.divider()
        st.markdown(
            "<p style='margin:0 0 6px 0;font-size:12px;font-weight:700;"
            "color:#9ca3af;text-transform:uppercase;letter-spacing:.08em'>"
            "⚙️ &nbsp;Sumber Data POS</p>",
            unsafe_allow_html=True,
        )
        active_pos = st.radio(
            "POS aktif",
            options=["ESB", "Moka POS"],
            index=0 if st.session_state.get("active_pos", "ESB") == "ESB" else 1,
            horizontal=True,
            label_visibility="collapsed",
            key="pos_radio",
        )
        # Jika POS berubah → clear semua cache & uploads agar tidak
        # ada data silang antara ESB dan Moka
        if active_pos != st.session_state.get("active_pos"):
            st.session_state["active_pos"] = active_pos
            st.session_state.pop("_sidebar_uploads", None)
            load_data_gmv.clear()
            load_data_gmv_moka.clear()
            load_cogs_data.clear()
            load_data_waiter.clear()
            load_data_ulasan.clear()
            load_data_purchase.clear()
            st.rerun()
        st.session_state.setdefault("active_pos", "ESB")

        # Badge POS aktif
        _pos_color = "#3b82f6" if active_pos == "ESB" else "#7c3aed"
        st.markdown(
            f"<span style='background:{_pos_color}22;color:{_pos_color};"
            f"border:1px solid {_pos_color}55;border-radius:6px;"
            f"padding:2px 10px;font-size:11px;font-weight:700'>"
            f"{'🔵 ESB aktif' if active_pos == 'ESB' else '🟣 Moka POS aktif'}"
            f"</span>",
            unsafe_allow_html=True,
        )

        st.divider()
        selected = st.radio(
            "Navigasi",
            page_names,
            label_visibility="collapsed",
        )

        # ── Upload Data (di bawah navigasi) ──────────────────────
        st.divider()

        supports_db = (role == "admin") or get_package_use_database(pkg_key or "free")

        # Toggle DB
        # FIX: jangan pakai key= pada toggle agar session_state bisa diset
        # dari luar widget (misalnya setelah save). Gunakan value= saja.
        _db_on = st.session_state.get("use_db", False)
        if supports_db:
            new_db = st.toggle(
                "💾 Simpan ke Database",
                value=_db_on,
                # key dihapus — state dikelola via "use_db" bukan widget key
                help="ON → tombol simpan muncul di tiap file upload.",
            )
            if new_db != _db_on:
                st.session_state["use_db"] = new_db
                st.session_state["user_db_preference"] = new_db
            if st.session_state.get("use_db", False):
                st.caption("🗄️ Database aktif — klik 💾 di tiap file untuk simpan")
            else:
                st.caption("⚡ Mode sementara — aktifkan toggle untuk simpan permanen")
        else:
            st.caption("⚡ Mode sementara — upgrade paket untuk simpan ke database")

        st.markdown("#### 📂 Upload Data")

        def _on_file_change():
            load_data_gmv.clear()
            load_data_gmv_moka.clear()
            load_cogs_data.clear()
            load_data_waiter.clear()
            load_data_ulasan.clear()
            load_data_purchase.clear()

        def _uploader_block(label, widget_key, table_name, caption_text):
            f = st.file_uploader(label, type=["xlsx", "csv"],
                                 key=widget_key, on_change=_on_file_change)
            if caption_text:
                st.caption(caption_text)
            if f is not None:
                sig   = f"{f.name}_{f.size}"
                saved = st.session_state.get(f"saved_sig_{table_name}") == sig
                db_on = st.session_state.get("use_db", False)
                if saved:
                    st.markdown(
                        "<span style='color:#4ade80;font-size:11px'>✅ Tersimpan di database</span>",
                        unsafe_allow_html=True,
                    )
                elif db_on:
                    st.markdown(
                        f"<span style='color:#fbbf24;font-size:11px'>"
                        f"📄 {f.name[:28]}{'...' if len(f.name)>28 else ''} "
                        f"({f.size/1024:.0f} KB)</span>",
                        unsafe_allow_html=True,
                    )
                    if st.button("💾 Simpan ke Database", key=f"save_btn_{table_name}",
                                 use_container_width=True, type="primary"):
                        st.session_state[f"pending_save_{table_name}"] = True
                        st.rerun()
                else:
                    st.button("🔒 Simpan ke Database", key=f"save_btn_{table_name}",
                              use_container_width=True, disabled=True,
                              help="Aktifkan toggle Database untuk menyimpan")
            return f

        # ── Tampilkan uploader sesuai POS yang aktif ──────────────
        if active_pos == "ESB":
            # Uploader ESB — seperti semula
            _uploads_result = {
                "gmv":      _uploader_block("📊 GMV / Penjualan",   "uploader_gmv",      "gmv_data",      "Header baris ke-10"),
                "cogs":     _uploader_block("💰 COGS",              "uploader_cogs",     "cogs_data",     "Header baris ke-13"),
                "waiter":   _uploader_block("🧑‍🍳 SDM / Waiter",     "uploader_waiter",   "waiter_data",   "Header baris ke-12"),
                "ulasan":   _uploader_block("❤️ Ulasan Pelanggan",  "uploader_ulasan",   "ulasan_data",   "Kolom: Nama, Rating, Ulasan"),
                "purchase": _uploader_block("🛒 Pembelian",         "uploader_purchase", "purchase_data", "Header baris ke-12"),
                "pl":       _uploader_block("📉 Profit & Loss",     "uploader_pl",       "pl_data",       "Format wide kolom bulan"),
            }
        else:
            # Uploader Moka POS — 1 file + Ulasan tetap ada
            st.markdown(
                "<span style='font-size:11px;color:#a78bfa'>"
                "Upload export dari dashboard Moka POS</span>",
                unsafe_allow_html=True,
            )
            _moka_file = _uploader_block(
                "🟣 Moka — Sales / Transaction Report",
                "uploader_moka_gmv",
                "gmv_data",
                "Export dari menu Report → Sales Report atau Transaction Report",
            )
            _uploads_result = {
                "gmv"     : _moka_file,
                "cogs"    : None,   # belum tersedia dari Moka
                "waiter"  : None,   # belum tersedia dari Moka
                "purchase": None,   # belum tersedia dari Moka
                "pl"      : None,   # belum tersedia dari Moka
                "ulasan"  : _uploader_block(
                    "❤️ Ulasan Pelanggan",
                    "uploader_ulasan",
                    "ulasan_data",
                    "Kolom: Nama, Rating, Ulasan",
                ),
                "_is_moka": True,   # flag untuk loader — pakai load_data_gmv_moka
            }

        st.session_state["_sidebar_uploads"] = _uploads_result

    needed_keys = _TAB_DATA_NEEDS.get(selected, [])

    # uploads diisi dari _build_sidebar_content yang sudah render semua 6 uploader
    uploads: dict = st.session_state.get("_sidebar_uploads", {
        "gmv": None, "cogs": None, "waiter": None,
        "ulasan": None, "purchase": None, "pl": None,
    })

    pkg_supports_db = (role == "admin") or get_package_use_database(pkg_key or "free")
    use_db          = _get_user_db_preference(pkg_key, role)

    # Toggle dan upload sudah dihandle sepenuhnya oleh sidebar.py
    # use_db dibaca dari session_state yang di-set sidebar
    use_db = st.session_state.get("use_db", False)

    # ── Simpan upload ke DB — HANYA jika user klik "Simpan ke DB" ──
    # PERUBAHAN: save tidak lagi otomatis.
    # User klik tombol "💾 Simpan ke DB" di sidebar → set pending_save_{table}=True
    # Di sini kita proses pending tersebut, lalu clear flag-nya.
    _SAVE_MAP = {
        "gmv":      ("gmv_data",      "Sales Date In", load_data_gmv),
        "cogs":     ("cogs_data",     "Sales Date",    load_cogs_data),
        "waiter":   ("waiter_data",   "Order Time",    load_data_waiter),
        "ulasan":   ("ulasan_data",   "Nama",          load_data_ulasan),
        "purchase": ("purchase_data", "Purchase Date", load_data_purchase),
        "pl":       ("pl_data",       "Date",          load_pl_data),
    }
    for up_key, (table, date_col, loader) in _SAVE_MAP.items():
        pending_key = f"pending_save_{table}"
        if not st.session_state.get(pending_key):
            continue  # User belum klik simpan untuk file ini
        uploaded_file = uploads.get(up_key)
        if not uploaded_file:
            st.session_state.pop(pending_key, None)
            continue
        # Proses & simpan
        with st.spinner(f"Menyimpan {table} ke database..."):
            # FIX BUG: panggil loader dengan use_db=False secara EKSPLISIT
            # agar data yang disimpan = data PENUH dari file, bukan dari DB/cache.
            # Loader dipanggil fresh: cache key berbeda dari versi use_db=True.
            # JANGAN gunakan hasil load yang sudah di-filter oleh dashboard (excluded_menus dll).
            try:
                result = loader(uploaded_file, use_db=False)
            except TypeError:
                result = loader(uploaded_file)
            df = result[0] if isinstance(result, tuple) else result
            if df is not None:
                rows_before_save = len(df)
                save_dataframe_smart_append(df, table, date_col, user_id=get_current_user_id())
                # Tandai file ini sudah tersimpan (untuk badge ✅ di sidebar)
                sig = f"{uploaded_file.name}_{uploaded_file.size}"
                st.session_state[f"saved_sig_{table}"] = sig
                # FIX: hanya set use_db dan user_db_preference.
                # JANGAN set toggle_user_db — itu widget key yang tidak boleh
                # diubah manual setelah widget dirender (StreamlitAPIException).
                st.session_state["user_db_preference"] = True
                st.session_state["use_db"] = True
                # FIX BUG: reset applied_filter dan excluded_menus saat data baru disimpan
                # agar dashboard menampilkan data DB yang PENUH, bukan data file yang difilter.
                # User bisa set ulang filter setelah data tampil dari DB.
                st.session_state.pop("applied_filter", None)
                st.session_state.pop("excluded_menus", None)
                try:
                    loader.clear()
                except Exception:
                    pass
                st.cache_data.clear()
                st.toast(f"✅ {table.replace('_data','').upper()} tersimpan! Toggle Database otomatis diaktifkan.", icon="💾")
        st.session_state.pop(pending_key, None)  # clear flag

    # ── Load data ─────────────────────────────────────────────────
    # Strategi:
    #   1. use_db=True  → baca dari SQLite (data persisten)
    #   2. use_db=False → pakai file upload langsung (in-memory)
    #   3. FALLBACK:  jika use_db=True tapi DB kosong + ada file upload → pakai file
    #      (agar data langsung tampil SEBELUM user sempat klik simpan)
    df_gmv = df_cogs = df_waiter = df_ulasan = df_purchase = df_pl = None

    def _load_with_fallback(db_key, db_loader_fn, file_obj, file_loader_fn,
                            date_cols=None, numeric_cfg=None):
        """
        PRIORITAS DATA:
          1. File upload (jika ada) — selalu prioritas utama, angka paling fresh
          2. Database (jika use_db=True dan tidak ada file upload) — data persisten
          3. None — tidak ada data sama sekali

        Kenapa file diutamakan:
          - User baru upload = data terbaru, harus langsung tampil tanpa perlu simpan dulu
          - Mencegah selisih angka antara "sebelum simpan" vs "sesudah simpan ke DB"
          - DB hanya dipakai saat tidak ada file (mode persistensi murni)
        """
        # PRIORITAS 1: file upload selalu menang (angka paling fresh, cegah selisih)
        if file_obj is not None:
            result = file_loader_fn(file_obj)
            return result[0] if isinstance(result, tuple) else result

        # PRIORITAS 2: DB — hanya jika tidak ada file upload
        if use_db:
            kwargs = {"user_id": get_current_user_id()}
            if date_cols:
                kwargs["date_cols"] = date_cols
            if numeric_cfg:
                kwargs["numeric_cols_config"] = numeric_cfg
            df_db = db_loader_fn(db_key, **kwargs)
            if df_db is not None and not df_db.empty:
                return df_db

        # PRIORITAS 3: tidak ada data sama sekali
        return None

    if "gmv" in needed_keys:
        # Baca nama bisnis dari baris ke-2 file (sebelum header data) — ESB only
        _is_moka = uploads.get("_is_moka", False)
        if uploads.get("gmv") and not _is_moka:
            try:
                import openpyxl
                wb = openpyxl.load_workbook(uploads["gmv"], read_only=True, data_only=True)
                ws = wb.active
                row2_vals = [ws.cell(row=2, column=c).value for c in range(1, 5)]
                company_raw = next((v for v in row2_vals if v and str(v).strip()), None)
                if company_raw:
                    st.session_state["gmv_company_name"] = str(company_raw).strip()
                wb.close()
            except Exception:
                pass

        if _is_moka and uploads.get("gmv"):
            # Moka POS — pakai loader khusus Moka
            result = load_data_gmv_moka(uploads["gmv"])
            df_gmv, _company, _period, _branch = result if isinstance(result, tuple) else (result, None, None, None)
            if _company:
                st.session_state["gmv_company_name"] = _company
        else:
            df_gmv = _load_with_fallback(
                "gmv_data", load_dataframe_from_db, uploads.get("gmv"), load_data_gmv,
                date_cols=["Sales Date In", "Sales Date Out", "Order Time"],
                # FIX: pastikan semua kolom numerik di-cast saat baca dari DB
                numeric_cfg={
                    "Qty": "float", "Price (Net)": "float", "Service Charge": "float",
                    "Tax": "float", "Total Nett Sales": "float", "Bill Discount": "float",
                    "Total Gross Sales": "float", "Total After Bill Discount": "float",
                    "Difference Price": "float", "Discount": "float",
                    "Price": "float", "Subtotal": "float", "Nett Sales": "float",
                    "Total": "float", "VAT": "float",
                },
            )

    if "cogs" in needed_keys:
        df_cogs = _load_with_fallback(
            "cogs_data", load_dataframe_from_db, uploads.get("cogs"), load_cogs_data,
            date_cols=["Sales Date"],
        )

    if "waiter" in needed_keys:
        df_waiter = _load_with_fallback(
            "waiter_data", load_dataframe_from_db, uploads.get("waiter"), load_data_waiter,
            date_cols=["Order Time"],
        )

    if "ulasan" in needed_keys:
        df_ulasan = _load_with_fallback(
            "ulasan_data", load_dataframe_from_db, uploads.get("ulasan"), load_data_ulasan,
        )

    if "purchase" in needed_keys:
        df_purchase = _load_with_fallback(
            "purchase_data", load_dataframe_from_db, uploads.get("purchase"), load_data_purchase,
            date_cols=["Purchase Date", "Required Date"],
        )

    if "pl" in needed_keys:
        df_pl = _load_with_fallback(
            "pl_data", load_dataframe_from_db, uploads.get("pl"), load_pl_data,
            date_cols=["Date"],
        )

    # ── Panel Manajemen Database (di sidebar, setelah df di-load) ──
    with st.sidebar:
        try:
            from ui.db_management_panel import build_db_management_panel
            build_db_management_panel(
                df_gmv=df_gmv,
                df_cogs=df_cogs,
                df_waiter=df_waiter,
                df_ulasan=df_ulasan,
                df_purchase=df_purchase,
                df_pl=df_pl,
            )
        except Exception:
            pass

    # ── Strategi: placeholder judul di atas, filter di bawah ──────
    # 1. Reservasi slot kosong untuk judul (title_slot)
    # 2. Render filter GMV (mengisi session_state: branch, tanggal)
    # 3. Terapkan filter yang SAMA ke semua df lain (cogs, waiter, dll)
    # 4. Isi title_slot dengan judul sinkron
    NO_DATA_TABS = {ENTERPRISE_AI_TAB, ADMIN_TAB}

    # ── Banner Simpan ke Database (tampil di main area jika ada file belum tersimpan) ──
    if selected not in NO_DATA_TABS and not st.session_state.get("show_profile"):
        try:
            from ui.save_to_db_button import build_save_to_db_banner, build_upload_status_indicator
            build_save_to_db_banner(uploads, pkg_supports_db=pkg_supports_db)
        except Exception:
            pass

    title_slot = st.empty()

    filtered_gmv      = df_gmv
    filtered_cogs     = df_cogs
    filtered_waiter   = df_waiter
    filtered_purchase = df_purchase
    filtered_pl       = df_pl
    filtered_ulasan   = df_ulasan

    if selected in _GMV_FILTER_TABS and df_gmv is not None:
        filtered_gmv = _build_gmv_filter(df_gmv)

        sel_branch = st.session_state.get("active_branch_filter", "Semua")
        date_start = st.session_state.get("active_date_start")
        date_end   = st.session_state.get("active_date_end")

        def _apply_filters(df, date_col):
            if df is None or df.empty:
                return df
            res = df.copy()
            if sel_branch != "Semua" and "Branch" in res.columns:
                res = res[res["Branch"] == sel_branch]
            if date_start and date_end and date_col in res.columns:
                try:
                    d_start = pd.to_datetime(date_start, format="%d-%m-%Y").date()
                    d_end   = pd.to_datetime(date_end,   format="%d-%m-%Y").date()
                    col_dates = pd.to_datetime(res[date_col], errors="coerce").dt.date
                    res = res[(col_dates >= d_start) & (col_dates <= d_end)]
                except Exception:
                    pass
            return res

        filtered_cogs     = _apply_filters(df_cogs,     "Sales Date")
        filtered_waiter   = _apply_filters(df_waiter,   "Order Time")
        filtered_purchase = _apply_filters(df_purchase, "Purchase Date")
        # ulasan: tidak ada kolom tanggal standar, hanya filter cabang jika ada
        if df_ulasan is not None and sel_branch != "Semua" and "Branch" in (df_ulasan.columns if df_ulasan is not None else []):
            filtered_ulasan = df_ulasan[df_ulasan["Branch"] == sel_branch]
        # P&L: format wide per bulan, tidak bisa difilter per tanggal baris
        filtered_pl = df_pl

    with title_slot.container():
        _show_analysis_title(filtered_gmv, selected_tab=selected)

    # ── Tampilkan Welcome Screen jika belum ada data apapun ──────
    all_data_empty = all(
        df is None or (hasattr(df, "empty") and df.empty)
        for df in [df_gmv, df_cogs, df_waiter, df_ulasan, df_purchase, df_pl]
    )
    has_any_upload = any(v is not None for v in uploads.values())

    if all_data_empty and selected not in NO_DATA_TABS and not st.session_state.get("show_profile"):
        if has_any_upload or use_db:
            # Ada sumber data (file/DB) tapi belum ter-load — cek apakah ini
            # memang sedang loading (pertama kali) atau sudah stuck (loop).
            # FIX BUG: gunakan counter untuk membatasi agar spinner tidak
            # muncul terus-menerus ketika DB aktif tapi kosong / file gagal parse.
            _load_attempt = st.session_state.get("_load_attempt_count", 0)
            if _load_attempt < 2:
                st.session_state["_load_attempt_count"] = _load_attempt + 1
                st.info(
                    "⏳ Memuat data... Jika ini terus muncul, coba upload ulang file "
                    "atau nonaktifkan lalu aktifkan kembali toggle Database.",
                    icon="🔄",
                )
                return
            else:
                # Sudah > 2 kali masuk ke sini tapi data tetap kosong:
                # DB aktif tapi tidak ada data tersimpan, atau file gagal diparse.
                # Reset counter dan tampilkan welcome screen + pesan diagnostik.
                st.session_state.pop("_load_attempt_count", None)
                if use_db:
                    st.warning(
                        "🗄️ Toggle Database aktif, tetapi belum ada data tersimpan di database. "
                        "Upload file terlebih dahulu lalu klik **💾 Simpan ke Database**, "
                        "atau nonaktifkan toggle Database untuk mode upload langsung.",
                        icon="⚠️",
                    )
                elif has_any_upload:
                    st.warning(
                        "⚠️ File terdeteksi tetapi gagal dimuat. "
                        "Pastikan format file sesuai (GMV / COGS / Waiter Report) lalu upload ulang.",
                        icon="⚠️",
                    )
                build_welcome_screen()
                build_footer()
                return
        else:
            # Benar-benar tidak ada sumber data apapun → welcome screen
            st.session_state.pop("_load_attempt_count", None)
            build_welcome_screen()
            build_footer()
            return
    else:
        # Data berhasil dimuat — reset counter
        st.session_state.pop("_load_attempt_count", None)

    # ── Routing ───────────────────────────────────────────────────
    # ── Halaman profil ────────────────────────────────────────────
    if st.session_state.get("show_profile"):
        from ui.profile import build_profile_page
        if st.button("← Kembali ke Dashboard", key="back_from_profile"):
            st.session_state["show_profile"] = False
            st.rerun()
        build_profile_page()
        return

    # ── Guard: tab belum support Moka POS ─────────────────────────
    _active_pos = st.session_state.get("active_pos", "ESB")
    if _active_pos == "Moka POS" and selected in _MOKA_UNAVAILABLE_TABS:
        _moka_unavailable(selected)
        return

    if selected == ADMIN_TAB:
        # FIX #013: explicit admin check at routing level (defense in depth)
        if not is_admin():
            st.error("⛔ Akses ditolak.")
            return
        build_admin_panel()

    elif selected == "📊 Penjualan (GMV)":
        build_tab1_sales(filtered_gmv)

    elif selected == "💰 COGS & Profit":
        build_tab2_cogs(filtered_cogs, filtered_gmv)

    elif selected == "🧑‍🍳 SDM & Waktu Sibuk":
        build_tab3_hr(filtered_waiter, filtered_gmv)

    elif selected == "🛒 Pembelian":
        total_sales = (
            filtered_gmv["Total Nett Sales"].sum()
            if filtered_gmv is not None
            and not filtered_gmv.empty
            and "Total Nett Sales" in filtered_gmv.columns
            else 0
        )
        build_tab8_purchase(filtered_purchase, total_sales)

    elif selected == "⚖️ A/B Comparison":
        build_tab4_comparison(df_gmv, df_cogs, df_waiter)

    elif selected == "🎯 Target":
        build_tab6_target(filtered_gmv)

    elif selected == "🔮 Forecast (AI)":
        build_tab5_forecast(filtered_gmv)

    elif selected == "❤️ Ulasan":
        build_tab7_ulasan(filtered_ulasan)

    elif selected == "💡 Rekomendasi":
        build_tab9_rekomendasi(filtered_gmv, filtered_cogs)

    elif selected == "💸 Analisis Promo":
        build_tab10_promo(filtered_gmv, filtered_cogs)

    elif selected == "✨ Analisis Musiman":
        build_tab11_musiman(filtered_gmv, None)

    elif selected == "🧪 Lab Strategi":
        build_tab12_lab(filtered_gmv, filtered_cogs)

    elif selected == "📉 Laporan Laba Rugi (P&L)":
        build_tab13_pl(filtered_pl)
        build_pl_advanced_section(filtered_pl, df_gmv=filtered_gmv)

    elif selected == "👥 RFM & Loyalitas":
        build_tab14_rfm(filtered_gmv)

    elif selected == "📦 Inventori Lanjutan":
        build_tab15_inventory(filtered_purchase, filtered_gmv)

    elif selected == "⚙️ Operasional Lanjutan":
        build_tab17_operasional(filtered_gmv, filtered_waiter)

    elif selected == "🔧 Menu Engineering":
        build_tab16_menu_engineering(filtered_gmv, filtered_cogs)

    elif selected == "🍽️ Klarifikasi Section":
        build_tab_section_clarify(filtered_gmv, filtered_cogs)

    elif selected == "🤖 Enterprise AI Assistant":
        build_tab_enterprise_ai()

    else:
        st.info(f"Tab '{selected}' belum tersedia.")


# ──────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────

def main():
    _build_main_app()


if __name__ == "__main__":
    main()