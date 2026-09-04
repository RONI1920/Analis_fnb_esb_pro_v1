# ui/pricing.py — Halaman Pricing (Full Native Streamlit)
# DIUPDATE: Baca harga & deskripsi dari DB agar sinkron dengan Admin Panel.

from __future__ import annotations
import streamlit as st
import pandas as pd
from packages import PRICING_DISPLAY_ORDER, ALL_TABS, format_price

_ENTERPRISE_CSS = """
<style>
/* ── Enterprise card banner ── */
.ent-pricing-card {
    background: linear-gradient(135deg, #1a0a2e 0%, #2d1060 50%, #1a0a2e 100%);
    border: 2px solid #7c3aed;
    border-radius: 16px;
    padding: 28px 32px;
    margin: 24px 0 8px;
    position: relative;
    overflow: hidden;
}
.ent-pricing-card::before {
    content: '';
    position: absolute;
    top: -60px; right: -60px;
    width: 220px; height: 220px;
    background: radial-gradient(circle, rgba(168,85,247,0.18) 0%, transparent 70%);
    border-radius: 50%;
}
.ent-pricing-card::after {
    content: '';
    position: absolute;
    bottom: -40px; left: -40px;
    width: 160px; height: 160px;
    background: radial-gradient(circle, rgba(109,40,217,0.12) 0%, transparent 70%);
    border-radius: 50%;
}
.ent-top-row {
    display: flex; align-items: center; justify-content: space-between;
    flex-wrap: wrap; gap: 12px;
    margin-bottom: 20px;
}
.ent-badge-row {
    display: flex; gap: 8px; flex-wrap: wrap;
}
.ent-badge {
    display: inline-flex; align-items: center; gap: 5px;
    font-size: 11px; font-weight: 700; letter-spacing: .1em;
    text-transform: uppercase; padding: 4px 12px; border-radius: 20px;
}
.ent-badge.exclusive {
    background: linear-gradient(90deg, #7c3aed, #a855f7);
    color: #fff;
}
.ent-badge.ai {
    background: rgba(168,85,247,0.15);
    border: 1px solid #7c3aed;
    color: #c4b5fd;
}
.ent-title {
    font-size: 28px; font-weight: 800; color: #f0f2f5;
    margin: 0 0 4px;
}
.ent-price-label {
    font-size: 13px; color: #9ca3af; margin-bottom: 20px;
}
.ent-desc {
    font-size: 14px; color: #d1d5db; line-height: 1.6;
    margin-bottom: 20px; max-width: 680px;
}
.ent-features {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 10px; margin-bottom: 24px;
}
.ent-feat-item {
    display: flex; align-items: flex-start; gap: 8px;
    font-size: 13px; color: #e2e8f0;
}
.ent-feat-icon {
    color: #a78bfa; font-size: 15px; flex-shrink: 0; margin-top: 1px;
}
.ent-ai-highlight {
    background: rgba(139,92,246,0.12);
    border: 1px solid rgba(139,92,246,0.35);
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 20px;
    display: flex; align-items: flex-start; gap: 12px;
}
.ent-ai-highlight .icon { font-size: 28px; }
.ent-ai-highlight .text { font-size: 13px; color: #c4b5fd; line-height: 1.6; }
.ent-ai-highlight .text strong { color: #e9d5ff; }
.ent-divider { border: none; border-top: 1px solid #3b1f6b; margin: 20px 0; }
</style>
"""


def _get_pricing_data() -> dict[str, dict]:
    try:
        from database import get_packages_merged
        return get_packages_merged()
    except Exception:
        from packages import PACKAGE_DEFINITIONS
        return PACKAGE_DEFINITIONS


def build_pricing_page() -> str | None:
    chosen_package = None
    st.markdown(_ENTERPRISE_CSS, unsafe_allow_html=True)

    pkg_data = _get_pricing_data()

    # Paket reguler (tanpa enterprise) untuk baris kolom
    regular_keys = [k for k in PRICING_DISPLAY_ORDER if k in pkg_data and k != "enterprise"]
    display_keys = regular_keys  # untuk grid kolom

    # ── Hero ──────────────────────────────────────────────────────
    st.markdown("## 🚀 Data Driven Analyst FnB")
    st.caption("Pilih paket yang sesuai dengan kebutuhan bisnis Anda. Mulai gratis, upgrade kapan saja.")
    st.divider()

    # ── Baris 1: Badge populer (sejajar) ─────────────────────────
    badge_cols = st.columns(len(display_keys), gap="medium")
    for i, key in enumerate(display_keys):
        cfg = pkg_data[key]
        with badge_cols[i]:
            if cfg.get("highlight"):
                st.success("⭐ PALING POPULER")
            else:
                st.empty()

    # ── Baris 2: Nama paket ───────────────────────────────────────
    name_cols = st.columns(len(display_keys), gap="medium")
    for i, key in enumerate(display_keys):
        cfg = pkg_data[key]
        with name_cols[i]:
            grade = cfg.get("grade")
            if grade:
                st.markdown(f"### Grade {grade}")
            else:
                st.markdown(f"### {cfg['name']}")

    # ── Baris 3: Harga ────────────────────────────────────────────
    price_cols = st.columns(len(display_keys), gap="medium")
    for i, key in enumerate(display_keys):
        cfg = pkg_data[key]
        price = cfg["price_monthly"]
        with price_cols[i]:
            if price == 0:
                st.markdown("## 🆓 Gratis")
                st.caption("Tidak perlu kartu kredit")
            else:
                st.markdown(f"## {format_price(price)}")
                st.caption(f"per bulan · atau {format_price(cfg['price_yearly'])}/tahun")

    # ── Baris 4: Deskripsi ────────────────────────────────────────
    desc_cols = st.columns(len(display_keys), gap="medium")
    for i, key in enumerate(display_keys):
        cfg = pkg_data[key]
        with desc_cols[i]:
            st.caption(cfg["description"])

    st.write("")

    # ── Baris 5: Fitur per paket ──────────────────────────────────
    max_tabs = max(len(pkg_data[k]["tabs"]) for k in display_keys)

    feat_cols = st.columns(len(display_keys), gap="medium")
    for i, key in enumerate(display_keys):
        cfg = pkg_data[key]
        try:
            from database import get_package_tab_access, get_package_use_database
            from packages import get_allowed_tabs
            db_overrides = get_package_tab_access(key)
            tabs = get_allowed_tabs(key, db_overrides if db_overrides else None)
            use_db = get_package_use_database(key)
        except Exception:
            tabs = cfg["tabs"]
            use_db = cfg.get("use_database", False)

        with feat_cols[i]:
            # ── Badge penyimpanan — nilai jual utama ─────────────
            if use_db:
                st.markdown(
                    "<div style=\'background:linear-gradient(90deg,#064e3b,#065f46);"
                    "border:1px solid #059669;border-radius:6px;padding:5px 10px;"
                    "font-size:11px;font-weight:700;color:#6ee7b7;margin-bottom:10px;"
                    "display:inline-flex;align-items:center;gap:6px;\'>"
                    "🗄️ Penyimpanan Database</div>",
                    unsafe_allow_html=True,
                )
                st.caption("Data tersimpan permanen, tidak hilang saat refresh")
            else:
                st.markdown(
                    "<div style=\'background:#1e2535;border:1px solid #374151;"
                    "border-radius:6px;padding:5px 10px;font-size:11px;font-weight:700;"
                    "color:#9ca3af;margin-bottom:10px;display:inline-flex;"
                    "align-items:center;gap:6px;\'>"
                    "⚡ Mode Sementara</div>",
                    unsafe_allow_html=True,
                )
                st.caption("Data in-memory, perlu upload ulang setiap sesi")
            st.write("")
            st.caption(f"**{len(tabs)} fitur analitik:**")
            for tab in tabs:
                st.markdown(f"✅ {tab}")
            for _ in range(max_tabs - len(tabs)):
                st.markdown("　")

    st.write("")

    # ── Baris 6: Tombol pilih ─────────────────────────────────────
    btn_cols = st.columns(len(display_keys), gap="medium")
    for i, key in enumerate(display_keys):
        cfg = pkg_data[key]
        with btn_cols[i]:
            if key == "free":
                label = "🎉 Mulai Gratis"
                btn_type = "primary"
            elif cfg.get("highlight"):
                label = "🌟 Pilih Paket Ini"
                btn_type = "primary"
            else:
                label = "Pilih Paket Ini"
                btn_type = "secondary"

            if st.button(label, key=f"pick_{key}",
                         use_container_width=True, type=btn_type):
                chosen_package = key

    # ══════════════════════════════════════════════════════════════
    # ENTERPRISE CARD — tampil penuh di bawah paket reguler
    # ══════════════════════════════════════════════════════════════
    if "enterprise" in pkg_data:
        ent = pkg_data["enterprise"]

        st.markdown("<hr style='border-top:1px solid #2d3348; margin: 32px 0 0;'>", unsafe_allow_html=True)

        st.markdown("""
        <div class="ent-pricing-card">
            <div class="ent-top-row">
                <div>
                    <div class="ent-badge-row">
                        <span class="ent-badge exclusive">✨ Enterprise</span>
                        <span class="ent-badge ai">🤖 AI Assistant Included</span>
                        <span class="ent-badge" style="background:linear-gradient(90deg,#064e3b,#065f46);border:1px solid #059669;color:#6ee7b7;">🗄️ Database Permanen</span>
                    </div>
                </div>
            </div>
            <div class="ent-title">🏢 Enterprise</div>
            <div class="ent-price-label">Harga custom · Negosiasi langsung dengan tim kami</div>
            <div class="ent-desc">
                Solusi lengkap untuk bisnis F&B multi-outlet yang membutuhkan analitik mendalam,
                AI interaktif berbasis data real-time, dan dukungan prioritas.
                Semua fitur tersedia tanpa batasan.
            </div>
            <div class="ent-ai-highlight">
                <div class="icon">🤖</div>
                <div class="text">
                    <strong>Enterprise AI Assistant — Eksklusif paket ini</strong><br>
                    Tanyakan apapun tentang bisnis Anda dalam bahasa natural.
                    Ketik <em>"Revenue hari ini di outlet A"</em> atau <em>"Menu paling untung bulan ini"</em>
                    — AI akan query database secara real-time dan tampilkan visualisasi otomatis.
                    Tidak perlu buka tab satu per satu.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Fitur Enterprise dalam 3 kolom
        try:
            from database import get_package_tab_access
            from packages import get_allowed_tabs
            db_overrides = get_package_tab_access("enterprise")
            ent_tabs = get_allowed_tabs("enterprise", db_overrides if db_overrides else None)
        except Exception:
            ent_tabs = ent.get("tabs", ALL_TABS)

        col_f1, col_f2, col_f3 = st.columns(3)
        third = len(ent_tabs) // 3 + 1
        with col_f1:
            st.caption(f"**{len(ent_tabs)} fitur analitik termasuk:**")
            for tab in ent_tabs[:third]:
                st.markdown(f"✅ {tab}")
        with col_f2:
            st.caption("&nbsp;", unsafe_allow_html=True)
            for tab in ent_tabs[third:third*2]:
                st.markdown(f"✅ {tab}")
        with col_f3:
            st.caption("&nbsp;", unsafe_allow_html=True)
            for tab in ent_tabs[third*2:]:
                st.markdown(f"✅ {tab}")

        st.write("")

        # Info enterprise khusus — bukan tombol beli langsung
        st.markdown(
            """<div style="background:linear-gradient(135deg,#431407,#3b0764);
                border:1px solid #c2410c44;border-radius:12px;padding:20px 24px;margin-top:8px">
                <div style="font-size:0.95rem;font-weight:700;color:#fed7aa;margin-bottom:6px">
                    🤝 Proses Bergabung Enterprise
                </div>
                <div style="font-size:0.82rem;color:#fdba74;line-height:1.7">
                    1. Daftar akun → tim kami hubungi dalam 1×24 jam<br>
                    2. Diskusi kebutuhan, fitur, dan jumlah outlet<br>
                    3. Penawaran harga custom sesuai skala bisnis<br>
                    4. Setup & onboarding bersama tim teknis kami
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)

        col_btn, col_info = st.columns([1, 2])
        with col_btn:
            if st.button("🤝 Hubungi Tim Enterprise", key="pick_enterprise",
                         use_container_width=True, type="primary"):
                # Arahkan ke halaman enterprise contact (bukan register biasa)
                chosen_package = "enterprise"
        with col_info:
            st.caption("Tidak ada pembayaran di muka. Tim kami yang akan menghubungi Anda untuk diskusi selanjutnya.")

    st.divider()

    # ── Tabel perbandingan ────────────────────────────────────────
    with st.expander("📊 Lihat Perbandingan Fitur Lengkap"):
        all_display = display_keys + (["enterprise"] if "enterprise" in pkg_data else [])
        header = ["Fitur / Tab"] + [
            f"Grade {pkg_data[k]['grade']}" if pkg_data[k].get("grade")
            else pkg_data[k]["name"]
            for k in all_display
        ]
        rows = []

        # Baris pertama: status penyimpanan database
        db_row = ["🗄️ Penyimpanan Database"]
        for k in all_display:
            try:
                from database import get_package_use_database
                use_db = get_package_use_database(k)
            except Exception:
                use_db = pkg_data[k].get("use_database", False)
            db_row.append("✅ Permanen" if use_db else "⚡ Sementara")
        rows.append(db_row)

        # Spacer
        rows.append(["── Fitur Analitik ──"] + ["" for _ in all_display])

        for tab in ALL_TABS:
            row = [tab]
            for k in all_display:
                try:
                    from database import get_package_tab_access
                    from packages import get_allowed_tabs
                    db_overrides = get_package_tab_access(k)
                    effective_tabs = get_allowed_tabs(k, db_overrides if db_overrides else None)
                except Exception:
                    effective_tabs = pkg_data[k]["tabs"]
                row.append("✅" if tab in effective_tabs else "—")
            rows.append(row)

        df = pd.DataFrame(rows, columns=header)
        st.dataframe(df, use_container_width=True, hide_index=True)

    # ── FAQ ───────────────────────────────────────────────────────
    st.markdown("### ❓ Pertanyaan Umum")

    with st.expander("Apakah paket Gratis benar-benar gratis?"):
        st.write("Ya! Tidak memerlukan kartu kredit. Anda mendapat akses 30 hari ke fitur dasar GMV.")

    with st.expander("Bagaimana cara upgrade ke paket berbayar?"):
        st.write(
            "Setelah memilih paket berbayar, Anda akan diarahkan ke halaman pembayaran via QRIS. "
            "Setelah admin mengkonfirmasi, akses langsung aktif."
        )

    with st.expander("Apa itu Enterprise AI Assistant?"):
        st.write(
            "Fitur eksklusif paket Enterprise — dashboard berbasis percakapan AI. "
            "Anda cukup ketik pertanyaan dalam bahasa Indonesia seperti "
            "'tampilkan revenue hari ini outlet Lippo Mall' dan AI akan mengambil data "
            "dari database secara real-time lalu menampilkan grafik otomatis."
        )

    with st.expander("Apa bedanya Penyimpanan Database vs Mode Sementara?"):
        st.write(
            "**🗄️ Penyimpanan Database (Starter ke atas):** "
            "Setiap file yang Anda upload tersimpan permanen di database lokal. "
            "Data tetap ada meski browser ditutup, dan langsung tersedia saat buka ulang — "
            "tidak perlu upload ulang setiap sesi. Cocok untuk monitoring harian yang konsisten.\n\n"
            "**⚡ Mode Sementara (Gratis):** "
            "Data hanya ada selama sesi berlangsung. Saat Anda refresh atau tutup browser, "
            "data hilang dan perlu diupload ulang. Cocok untuk analisis sekali pakai atau trial."
        )

    with st.expander("Apakah data saya aman?"):
        st.write("Data tersimpan secara lokal di server yang Anda jalankan. Kami tidak menyimpan data bisnis Anda.")

    with st.expander("Bisa batal kapan saja?"):
        st.write(
            "Langganan berjalan hingga tanggal berakhir dan tidak diperpanjang otomatis "
            "kecuali Anda melakukan pembayaran ulang."
        )

    st.divider()

    # ── Login hint — HANYA tampil jika user BELUM login ──────────
    # Jika user sudah login (mode upgrade dari dalam app → show_pricing_upgrade),
    # tombol login disembunyikan karena tidak relevan dan membingungkan.
    try:
        from auth import is_logged_in as _is_logged_in
        _already_logged_in = _is_logged_in()
    except Exception:
        _already_logged_in = st.session_state.get("show_pricing_upgrade", False)

    if not _already_logged_in:
        st.markdown(
            "<div style='text-align:center;padding:8px 0'>"
            "<span style='color:#6b7280;font-size:13px'>Sudah punya akun? &nbsp;</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        col_l1, col_l2, col_l3 = st.columns([2, 1, 2])
        with col_l2:
            if st.button("🔑 Login ke Akun Saya", use_container_width=True, type="secondary"):
                st.session_state["auth_page"] = "login"
                st.rerun()

    return chosen_package