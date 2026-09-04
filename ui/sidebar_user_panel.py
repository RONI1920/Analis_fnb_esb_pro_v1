# ui/sidebar_user_panel.py — Panel profil user di sidebar (lihat lisensi)

import streamlit as st


def build_user_profile_panel(username: str, full_name: str, pkg_name: str,
                               pkg_color: str, pkg_badge_color: str,
                               end_date: str | None, license_status: str | None,
                               user_uses_db: bool):
    """
    Panel profil user di sidebar:
    - Badge paket + storage mode
    - Sisa hari lisensi
    """

    # ── Header nama + badge ──────────────────────────────────────
    st.markdown(f"👤 **{full_name.upper()}**")

    storage_badge  = "🗄️ DB"   if user_uses_db else "⚡ Temp"
    storage_color  = "#6ee7b7" if user_uses_db else "#9ca3af"
    storage_bg     = "#064e3b" if user_uses_db else "#1e2535"

    st.markdown(
        f"<div style='display:flex;align-items:center;gap:6px;margin-top:2px'>"
        f"<span style='background:{pkg_badge_color};color:{pkg_color};"
        f"border:1px solid {pkg_color}44;border-radius:4px;"
        f"padding:2px 7px;font-size:11px;font-weight:700'>{pkg_name}</span>"
        f"<span style='background:{storage_bg};color:{storage_color};"
        f"border-radius:4px;padding:2px 7px;font-size:11px;font-weight:600'>"
        f"{storage_badge}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── Sisa hari lisensi ────────────────────────────────────────
    if end_date and license_status in ("active", "trial"):
        from datetime import date
        try:
            sisa = (date.fromisoformat(end_date) - date.today()).days
            if sisa <= 7:
                st.warning(f"⚠️ Lisensi berakhir **{sisa} hari lagi** ({end_date})")
            elif sisa <= 30:
                st.caption(f"⏳ Aktif hingga {end_date} ({sisa} hari lagi)")
            else:
                st.caption(f"✅ Aktif hingga {end_date}")
        except Exception:
            pass


