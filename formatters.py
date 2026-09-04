
import html as _html

def safe_html(text) -> str:
    """FIX #009: Escape user-supplied text before embedding in HTML.
    Use this for every variable injected into unsafe_allow_html=True blocks.
    """
    if text is None:
        return ""
    return _html.escape(str(text), quote=True)

# formatters.py — Fungsi Format Angka & Teks

import pandas as pd


def format_rupiah(amount) -> str:
    """Format angka menjadi string Rupiah dengan titik pemisah ribuan."""
    if pd.isna(amount):
        amount = 0
    return f"Rp {amount:,.0f}".replace(",", ".")


def format_angka_bulat(number) -> str:
    """Format angka kuantitas menjadi bulat tanpa desimal."""
    if pd.isna(number):
        number = 0
    return f"{number:.0f}"


def format_persen(number) -> str:
    """Format angka menjadi string persentase."""
    if pd.isna(number):
        number = 0
    return f"{number:,.1f}%"


def calculate_delta(value_A, value_B, formatter_func, higher_is_better=True):
    """
    Menghitung delta antara A dan B.
    Returns: (delta_abs_formatted, delta_pct_str, delta_color)
    """
    delta_abs = value_A - value_B

    if formatter_func == format_rupiah:
        delta_abs_formatted = formatter_func(delta_abs)
    elif formatter_func == format_angka_bulat:
        delta_abs_formatted = formatter_func(delta_abs)
    else:
        delta_abs_formatted = f"{delta_abs:,.2f}"

    delta_pct_str = ""
    delta_color = "off"

    if value_B != 0:
        delta_pct = (delta_abs / value_B) * 100
        arrow = "🔼" if delta_pct > 0 else "🔽"
        delta_pct_str = f"{arrow} {delta_pct:.1f}%"
        if delta_abs > 0:
            delta_color = "normal" if higher_is_better else "inverse"
        elif delta_abs < 0:
            delta_color = "inverse" if higher_is_better else "normal"
    elif value_A != 0:
        delta_pct_str = "🔼 100% +"
        delta_color = "normal" if higher_is_better else "inverse"
    else:
        delta_pct_str = "-"

    return delta_abs_formatted, delta_pct_str, delta_color

def tab_error_guard(tab_name: str):
    """
    Context manager: wrap isi tab dengan try/except agar satu tab crash
    tidak merusak seluruh dashboard.

    Pemakaian:
        with tab_error_guard("GMV"):
            ... kode tab ...
    """
    import contextlib
    import streamlit as _st
    from logger import capture_exception as _cap_exc

    @contextlib.contextmanager
    def _guard():
        try:
            yield
        except Exception as _e:
            _cap_exc(_e, f"tab:{tab_name}")
            _st.error(
                f"⚠️ Terjadi kesalahan saat memuat tab **{tab_name}**.\n\n"
                f"Detail error telah dicatat. Coba refresh halaman atau hubungi admin."
            )
            with _st.expander("Detail teknis (untuk developer)"):
                import traceback
                _st.code(traceback.format_exc())

    return _guard()

