# ui/admin_notifications_tab.py
# Tab Notifikasi Admin — Streamlit native components (no custom HTML cards)

from __future__ import annotations
import streamlit as st
from database import (
    get_admin_notifications,
    count_unread_notifications,
    mark_notification_read,
    mark_all_notifications_read,
    delete_notification,
)

_TYPE_META = {
    "enterprise_inquiry": {"icon": "🏢", "label": "Enterprise",  "color": "violet"},
    "new_user":           {"icon": "👤", "label": "User Baru",   "color": "blue"},
    "new_payment":        {"icon": "💳", "label": "Pembayaran",  "color": "orange"},
    "license_expiring":   {"icon": "⏰", "label": "Lisensi",     "color": "red"},
    "system":             {"icon": "⚙️", "label": "Sistem",      "color": "gray"},
}
_DEFAULT_META = {"icon": "🔔", "label": "Info", "color": "gray"}


def _relative_time(dt_str: str) -> str:
    from datetime import datetime, timezone
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        diff = int((datetime.now(timezone.utc) - dt).total_seconds())
        if diff < 60:    return "baru saja"
        if diff < 3600:  return f"{diff // 60} menit lalu"
        if diff < 86400: return f"{diff // 3600} jam lalu"
        return f"{diff // 86400} hari lalu"
    except Exception:
        return dt_str[:16] if dt_str else ""


@st.fragment(run_every=30)
def build_notifications_tab() -> None:
    """Tab Notifikasi Admin — auto-refresh tiap 30 detik."""

    # ── Auto-migrate: pastikan tabel ada di DB yang sudah lama ──
    _ensure_table()

    # ── Cek lisensi hampir habis ─────────────────────────────────
    _check_expiring_licenses()

    # ── Header ──────────────────────────────────────────────────
    unread = count_unread_notifications()

    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        if unread > 0:
            st.markdown(f"### 🔔 Notifikasi &nbsp; <span style='background:#ef4444;color:#fff;"
                        f"border-radius:12px;padding:2px 10px;font-size:13px'>{unread}</span>",
                        unsafe_allow_html=True)
        else:
            st.markdown("### 🔔 Notifikasi")
        st.caption("🟢 Live · auto-refresh tiap 30 detik")
    with col_h2:
        if unread > 0:
            if st.button("✅ Tandai Semua Dibaca", use_container_width=True,
                         key="mark_all_read_btn", type="secondary"):
                mark_all_notifications_read()
                st.rerun(scope="fragment")

    st.divider()

    # ── Filter ──────────────────────────────────────────────────
    filter_opts = ["Semua", "Belum Dibaca", "🏢 Enterprise",
                   "👤 User Baru", "💳 Pembayaran", "⏰ Lisensi"]
    chosen_filter = st.radio(
        "Filter:", filter_opts, horizontal=True,
        key="notif_filter_radio", label_visibility="collapsed",
    )

    # ── Ambil & filter data ──────────────────────────────────────
    unread_only = (chosen_filter == "Belum Dibaca")
    all_notifs  = get_admin_notifications(unread_only=unread_only, limit=100)

    type_map = {
        "🏢 Enterprise": "enterprise_inquiry",
        "👤 User Baru":  "new_user",
        "💳 Pembayaran": "new_payment",
        "⏰ Lisensi":    "license_expiring",
    }
    if chosen_filter in type_map:
        all_notifs = [n for n in all_notifs if n["type"] == type_map[chosen_filter]]

    if not all_notifs:
        st.info("Tidak ada notifikasi" if chosen_filter == "Semua"
                else f"Tidak ada notifikasi untuk filter '{chosen_filter}'")
        return

    # ── Render setiap notifikasi ─────────────────────────────────
    for notif in all_notifs:
        meta    = _TYPE_META.get(notif["type"], _DEFAULT_META)
        is_read = bool(notif["is_read"])
        title   = str(notif.get("title") or "")
        body    = str(notif.get("body")  or "")
        waktu   = _relative_time(str(notif.get("created_at") or ""))

        # Container per notifikasi — warna berbeda jika belum dibaca
        with st.container(border=True):
            col_ico, col_txt, col_act = st.columns([0.5, 7, 2])

            with col_ico:
                st.markdown(f"## {meta['icon']}")

            with col_txt:
                # Badge label tipe
                badge_colors = {
                    "violet": ("#7c3aed", "rgba(109,40,217,0.15)"),
                    "blue":   ("#0ea5e9", "rgba(14,165,233,0.15)"),
                    "orange": ("#f59e0b", "rgba(245,158,11,0.15)"),
                    "red":    ("#ef4444", "rgba(239,68,68,0.15)"),
                    "gray":   ("#6b7280", "rgba(107,114,128,0.15)"),
                }
                fg, bg = badge_colors.get(meta["color"], badge_colors["gray"])
                st.markdown(
                    f"<span style='background:{bg};color:{fg};"
                    f"border-radius:8px;padding:2px 10px;"
                    f"font-size:11px;font-weight:700'>"
                    f"{meta['label']}</span>",
                    unsafe_allow_html=True,
                )
                # Judul — bold jika belum dibaca
                weight = "700" if not is_read else "400"
                opacity = "1.0" if not is_read else "0.55"
                st.markdown(
                    f"<p style='margin:4px 0 2px;font-size:15px;"
                    f"font-weight:{weight};opacity:{opacity}'>{title}</p>",
                    unsafe_allow_html=True,
                )
                if body:
                    st.caption(body)
                st.caption(f"🕐 {waktu}" + ("" if is_read else " · **Belum dibaca**"))

            with col_act:
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                if not is_read:
                    if st.button("✓ Baca", key=f"read_btn_{notif['id']}",
                                 use_container_width=True, type="primary"):
                        mark_notification_read(notif["id"])
                        st.rerun(scope="fragment")
                if st.button("🗑 Hapus", key=f"del_btn_{notif['id']}",
                             use_container_width=True):
                    delete_notification(notif["id"])
                    st.rerun(scope="fragment")

    st.caption(f"Menampilkan {len(all_notifs)} notifikasi")


def _ensure_table() -> None:
    """Buat tabel admin_notifications jika belum ada (DB lama)."""
    try:
        from database import get_db_connection
        conn = get_db_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS admin_notifications (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                type       TEXT NOT NULL,
                title      TEXT NOT NULL,
                body       TEXT,
                ref_id     INTEGER,
                ref_table  TEXT,
                is_read    INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    except Exception:
        pass


def _check_expiring_licenses() -> None:
    """Inject notif otomatis untuk lisensi yang habis dalam 7 hari."""
    try:
        from database import get_db_connection
        from datetime import date
        conn = get_db_connection()
        conn.row_factory = __import__('sqlite3').Row
        rows = conn.execute("""
            SELECT l.id, l.end_date, u.username, u.full_name, l.package_key
            FROM licenses l
            JOIN users u ON u.id = l.user_id
            WHERE l.status IN ('active', 'trial')
              AND l.end_date BETWEEN date('now') AND date('now', '+7 days')
        """).fetchall()
        for row in rows:
            existing = conn.execute("""
                SELECT id FROM admin_notifications
                WHERE type='license_expiring' AND ref_id=?
                  AND date(created_at)=date('now')
            """, (row["id"],)).fetchone()
            if not existing:
                days_left = (date.fromisoformat(row["end_date"]) - date.today()).days
                conn.execute("""
                    INSERT INTO admin_notifications
                        (type, title, body, ref_id, ref_table)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    "license_expiring",
                    f"⏰ Lisensi Hampir Habis — {row['username']}",
                    f"Paket: {row['package_key']} | Berakhir: {row['end_date']} "
                    f"({days_left} hari lagi)",
                    row["id"], "licenses",
                ))
        conn.commit()
        conn.close()
    except Exception:
        pass
