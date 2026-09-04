# ui/enterprise_contact.py — Enterprise Contact Page
# Halaman kontak untuk paket Enterprise dengan UI/UX premium

from __future__ import annotations
import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

.ent-hero-wrapper {
    background: linear-gradient(135deg, #05071a 0%, #0d1230 40%, #130a2e 100%);
    border: 1px solid rgba(139, 92, 246, 0.3);
    border-radius: 24px;
    padding: 52px 48px 44px;
    position: relative;
    overflow: hidden;
    margin-bottom: 32px;
}
.ent-hero-wrapper::before {
    content: '';
    position: absolute;
    top: -80px; right: -80px;
    width: 320px; height: 320px;
    background: radial-gradient(circle, rgba(139,92,246,0.15) 0%, transparent 65%);
    border-radius: 50%;
    pointer-events: none;
}
.ent-hero-wrapper::after {
    content: '';
    position: absolute;
    bottom: -60px; left: -60px;
    width: 240px; height: 240px;
    background: radial-gradient(circle, rgba(99,102,241,0.10) 0%, transparent 65%);
    border-radius: 50%;
    pointer-events: none;
}
.ent-tag-row {
    display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px;
}
.ent-tag {
    display: inline-flex; align-items: center; gap: 5px;
    font-size: 10px; font-weight: 700; letter-spacing: .12em;
    text-transform: uppercase; padding: 4px 12px; border-radius: 20px;
}
.ent-tag.purple {
    background: linear-gradient(90deg, #6d28d9, #7c3aed);
    color: #fff;
}
.ent-tag.green {
    background: rgba(16,185,129,0.15);
    border: 1px solid rgba(16,185,129,0.4);
    color: #6ee7b7;
}
.ent-tag.blue {
    background: rgba(59,130,246,0.12);
    border: 1px solid rgba(59,130,246,0.3);
    color: #93c5fd;
}
.ent-hero-title {
    font-size: 2.6rem; font-weight: 900; color: #f0f4ff;
    margin: 0 0 8px; line-height: 1.15;
    letter-spacing: -.02em;
}
.ent-hero-subtitle {
    font-size: 1.05rem; color: #94a3b8; line-height: 1.65;
    max-width: 600px; margin-bottom: 0;
}
.ent-hero-subtitle strong { color: #c4b5fd; }

/* ── Contact cards ── */
.ent-contact-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 16px;
    margin: 24px 0;
}
.ent-contact-card {
    background: rgba(30, 27, 75, 0.6);
    border: 1px solid rgba(109, 40, 217, 0.3);
    border-radius: 14px;
    padding: 20px 20px 18px;
    transition: border-color .2s;
}
.ent-contact-card:hover { border-color: rgba(139, 92, 246, 0.6); }
.ent-contact-icon { font-size: 28px; margin-bottom: 10px; display: block; }
.ent-contact-label {
    font-size: 10px; font-weight: 700; letter-spacing: .12em;
    text-transform: uppercase; color: #7c3aed; margin-bottom: 4px;
}
.ent-contact-value {
    font-size: 14px; color: #e2e8f0; font-weight: 500;
    word-break: break-all;
}
.ent-contact-caption { font-size: 11px; color: #64748b; margin-top: 4px; }

/* ── Process steps ── */
.ent-steps { margin: 8px 0 24px; }
.ent-step {
    display: flex; align-items: flex-start; gap: 16px;
    padding: 14px 0;
    border-bottom: 1px solid rgba(51,65,85,0.5);
}
.ent-step:last-child { border-bottom: none; }
.ent-step-num {
    width: 32px; height: 32px; border-radius: 50%; flex-shrink: 0;
    background: linear-gradient(135deg, #6d28d9, #4f46e5);
    display: flex; align-items: center; justify-content: center;
    font-size: 13px; font-weight: 800; color: #fff;
}
.ent-step-title { font-size: 14px; font-weight: 700; color: #e2e8f0; margin-bottom: 2px; }
.ent-step-desc { font-size: 12px; color: #94a3b8; line-height: 1.5; }

/* ── Feature pills ── */
.ent-feat-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 10px;
    margin: 16px 0 0;
}
.ent-feat-pill {
    display: flex; align-items: center; gap: 8px;
    background: rgba(30, 27, 75, 0.5);
    border: 1px solid rgba(109,40,217,0.25);
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 12px; color: #cbd5e1; font-weight: 500;
}
.ent-feat-pill .ico { font-size: 16px; flex-shrink: 0; }

/* ── SLA badge ── */
.ent-sla {
    background: linear-gradient(90deg, rgba(6,78,59,0.6), rgba(6,95,70,0.4));
    border: 1px solid rgba(16,185,129,0.35);
    border-radius: 12px;
    padding: 16px 20px;
    display: flex; align-items: center; gap: 14px;
    margin-top: 20px;
}
.ent-sla-icon { font-size: 28px; }
.ent-sla-title { font-size: 13px; font-weight: 700; color: #6ee7b7; margin-bottom: 2px; }
.ent-sla-desc { font-size: 12px; color: #a7f3d0; }
</style>
"""

_FEATURES = [
    ("🤖", "Enterprise AI Assistant"),
    ("🗄️", "Database Permanen"),
    ("📊", "Semua 17+ Tab Analitik"),
    ("🏪", "Multi-Outlet Support"),
    ("📈", "Forecasting AI"),
    ("👥", "RFM & Loyalitas"),
    ("🔧", "Menu Engineering"),
    ("📉", "Laporan P&L Lanjutan"),
    ("⚖️", "A/B Comparison"),
    ("🛡️", "Priority Support"),
    ("🔄", "Onboarding Terdedikasi"),
    ("⚙️", "Kustomisasi Fitur"),
]


def build_enterprise_contact_page() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)

    # ── Back button ───────────────────────────────────────────────
    if st.button("← Kembali ke Halaman Paket", key="ent_back_top"):
        st.session_state["auth_page"] = "pricing"
        st.rerun()

    # ── Hero ──────────────────────────────────────────────────────
    st.markdown("""
    <div class="ent-hero-wrapper">
        <div class="ent-tag-row">
            <span class="ent-tag purple">✨ Enterprise</span>
            <span class="ent-tag green">🤖 AI Included</span>
            <span class="ent-tag blue">🗄️ Database Permanen</span>
        </div>
        <div class="ent-hero-title">Solusi Analitik Skala Penuh<br>untuk Bisnis F&B Anda</div>
        <div class="ent-hero-subtitle">
            Semua fitur tanpa batas, AI assistant berbasis data real-time,
            dan <strong>dukungan teknis terdedikasi</strong> untuk membantu bisnis Anda
            tumbuh berbasis data.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Layout 2 kolom ────────────────────────────────────────────
    col_left, col_right = st.columns([3, 2], gap="large")

    with col_left:
        # ── Kontak ────────────────────────────────────────────────
        st.markdown("#### 📬 Hubungi Kami Langsung")
        st.markdown("""
        <div class="ent-contact-grid">
            <div class="ent-contact-card">
                <span class="ent-contact-icon">📧</span>
                <div class="ent-contact-label">Email</div>
                <div class="ent-contact-value">enterprise@datadrivenanalyst.com</div>
                <div class="ent-contact-caption">Respons dalam 1×24 jam</div>
            </div>
            <div class="ent-contact-card">
                <span class="ent-contact-icon">💬</span>
                <div class="ent-contact-label">WhatsApp Business</div>
                <div class="ent-contact-value">+62 812-xxxx-xxxx</div>
                <div class="ent-contact-caption">Senin–Jumat, 08.00–17.00 WIB</div>
            </div>
            <div class="ent-contact-card">
                <span class="ent-contact-icon">📅</span>
                <div class="ent-contact-label">Demo Langsung</div>
                <div class="ent-contact-value">Jadwalkan via email</div>
                <div class="ent-contact-caption">Gratis, tanpa komitmen</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Form kontak sederhana ─────────────────────────────────
        st.markdown("#### 📝 Atau Isi Form Ini — Tim Kami yang Hubungi")

        # FIX BUG: sembunyikan form jika sudah berhasil disubmit di sesi ini
        # agar mencegah data ganda akibat rerun Streamlit setelah st.balloons()
        if st.session_state.get("enterprise_form_submitted"):
            _submitted_name  = st.session_state.get("_ent_submitted_name", "")
            _submitted_email = st.session_state.get("_ent_submitted_email", "")
            st.success(
                f"✅ Terima kasih, **{_submitted_name}**! Kami akan menghubungi Anda "
                f"di **{_submitted_email}** dalam 1×24 jam kerja."
            )
            st.info("📬 Formulir sudah terkirim. Jika perlu mengubah detail, hubungi kami langsung via email atau WhatsApp.", icon="ℹ️")
            if st.button("✏️ Isi Ulang Form", key="ent_reset_form"):
                st.session_state["enterprise_form_submitted"] = False
                st.session_state.pop("_ent_submitted_name", None)
                st.session_state.pop("_ent_submitted_email", None)
                st.rerun()
        else:
            with st.form("enterprise_inquiry_form", border=False):
                c1, c2 = st.columns(2)
                with c1:
                    nama = st.text_input("Nama Lengkap *", placeholder="Budi Santoso")
                with c2:
                    perusahaan = st.text_input("Nama Bisnis / Restoran *", placeholder="PT. Makan Enak")

                c3, c4 = st.columns(2)
                with c3:
                    email = st.text_input("Email *", placeholder="budi@restoran.com")
                with c4:
                    wa = st.text_input("No. WhatsApp", placeholder="08xx-xxxx-xxxx")

                jumlah_outlet = st.selectbox(
                    "Jumlah Outlet",
                    ["1 outlet", "2–5 outlet", "6–10 outlet", "10+ outlet"],
                )
                kebutuhan = st.text_area(
                    "Ceritakan kebutuhan Anda (opsional)",
                    placeholder="Misalnya: kami punya 3 outlet di Jakarta, ingin monitoring revenue harian dan forecast...",
                    height=100,
                )

                submitted = st.form_submit_button(
                    "🚀 Kirim & Minta Tim Kami Menghubungi",
                    use_container_width=True,
                    type="primary",
                )

                if submitted:
                    if not nama or not perusahaan or not email:
                        st.error("⚠️ Nama, Nama Bisnis, dan Email wajib diisi.")
                    elif "@" not in email:
                        st.error("⚠️ Format email tidak valid.")
                    else:
                        # Simpan inquiry ke DB jika tersedia
                        try:
                            import sqlite3
                            from config import DB_FILE
                            conn = sqlite3.connect(DB_FILE)
                            conn.execute("""
                                CREATE TABLE IF NOT EXISTS enterprise_inquiries (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    nama TEXT, perusahaan TEXT, email TEXT,
                                    whatsapp TEXT, jumlah_outlet TEXT,
                                    kebutuhan TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                )
                            """)
                            conn.execute(
                                "INSERT INTO enterprise_inquiries "
                                "(nama, perusahaan, email, whatsapp, jumlah_outlet, kebutuhan) "
                                "VALUES (?, ?, ?, ?, ?, ?)",
                                (nama, perusahaan, email, wa, jumlah_outlet, kebutuhan),
                            )
                            conn.commit()
                            conn.close()
                        except Exception:
                            pass  # DB optional — form tetap tampil sukses

                        # Kirim notifikasi ke admin
                        try:
                            from database import push_admin_notification
                            push_admin_notification(
                                type="enterprise_inquiry",
                                title=f"🏢 Enterprise Inquiry Baru — {perusahaan}",
                                body=f"Dari: {nama} ({email}) | {jumlah_outlet} | {kebutuhan[:120] if kebutuhan else '-'}",
                                ref_table="enterprise_inquiries",
                            )
                        except Exception:
                            pass

                        # FIX BUG: set flag SEBELUM rerun agar form langsung
                        # disembunyikan dan tidak bisa disubmit ulang (data ganda)
                        st.session_state["enterprise_form_submitted"] = True
                        st.session_state["_ent_submitted_name"]  = nama
                        st.session_state["_ent_submitted_email"] = email
                        st.balloons()
                        st.rerun()

        st.markdown("""
        <div class="ent-sla">
            <span class="ent-sla-icon">⚡</span>
            <div>
                <div class="ent-sla-title">Garansi Respons 1×24 Jam Kerja</div>
                <div class="ent-sla-desc">
                    Tidak ada pembayaran di muka. Diskusi kebutuhan dulu,
                    penawaran harga menyusul setelah kami memahami skala bisnis Anda.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_right:
        # ── Proses bergabung ──────────────────────────────────────
        st.markdown("#### 🗺️ Proses Bergabung")
        st.markdown("""
        <div class="ent-steps">
            <div class="ent-step">
                <div class="ent-step-num">1</div>
                <div>
                    <div class="ent-step-title">Hubungi / Isi Form</div>
                    <div class="ent-step-desc">Via email, WA, atau form di kiri. Tidak ada komitmen apa pun.</div>
                </div>
            </div>
            <div class="ent-step">
                <div class="ent-step-num">2</div>
                <div>
                    <div class="ent-step-title">Diskusi Kebutuhan</div>
                    <div class="ent-step-desc">Tim kami menghubungi Anda dalam 1×24 jam untuk memahami skala dan kebutuhan bisnis.</div>
                </div>
            </div>
            <div class="ent-step">
                <div class="ent-step-num">3</div>
                <div>
                    <div class="ent-step-title">Penawaran Custom</div>
                    <div class="ent-step-desc">Harga disesuaikan jumlah outlet, fitur, dan durasi kontrak.</div>
                </div>
            </div>
            <div class="ent-step">
                <div class="ent-step-num">4</div>
                <div>
                    <div class="ent-step-title">Setup & Onboarding</div>
                    <div class="ent-step-desc">Tim teknis kami membantu instalasi, migrasi data, dan pelatihan tim Anda.</div>
                </div>
            </div>
            <div class="ent-step">
                <div class="ent-step-num">5</div>
                <div>
                    <div class="ent-step-title">Priority Support Aktif</div>
                    <div class="ent-step-desc">Dedicated support channel, update prioritas, dan review bulanan bersama tim Anda.</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Semua fitur ───────────────────────────────────────────
        st.markdown("#### 🎯 Semua Fitur Termasuk")
        pills_html = '<div class="ent-feat-grid">'
        for ico, label in _FEATURES:
            pills_html += f'<div class="ent-feat-pill"><span class="ico">{ico}</span>{label}</div>'
        pills_html += '</div>'
        st.markdown(pills_html, unsafe_allow_html=True)

    st.divider()

    # ── Back button bawah ─────────────────────────────────────────
    col_b1, col_b2, col_b3 = st.columns([1, 1, 1])
    with col_b1:
        if st.button("← Kembali ke Halaman Paket", key="ent_back_bottom",
                     use_container_width=True):
            st.session_state["auth_page"] = "pricing"
            st.rerun()
    with col_b2:
        if st.button("🔑 Login ke Akun Saya", key="ent_to_login",
                     use_container_width=True, type="secondary"):
            st.session_state["auth_page"] = "login"
            st.rerun()
