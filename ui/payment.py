# ui/payment.py — Halaman Pembayaran Bank Transfer
# QRIS dinonaktifkan (di-comment) — uncomment bagian QRIS jika ingin diaktifkan kembali

from __future__ import annotations

import random
import urllib.parse

import streamlit as st
from config import PAYMENT_CONFIG
from packages import PACKAGE_DEFINITIONS, format_price


def _get_package_cfg(package_key: str) -> dict:
    """Ambil config paket dari DB (merged). Fallback ke hardcoded jika DB error."""
    try:
        from database import get_packages_merged

        merged = get_packages_merged()
        return merged.get(
            package_key,
            PACKAGE_DEFINITIONS.get(package_key, PACKAGE_DEFINITIONS["starter"]),
        )
    except Exception:
        return PACKAGE_DEFINITIONS.get(package_key, PACKAGE_DEFINITIONS["starter"])


# Alias untuk backward-compat internal
QRIS_CONFIG = PAYMENT_CONFIG

_PAY_CSS = """
<style>
.pay-wrap {
    max-width: 560px;
    margin: 0 auto;
}
.pay-header {
    text-align: center;
    padding: 32px 0 20px;
}
.pay-header h2 {
    font-size: 1.8rem;
    font-weight: 800;
    color: #f0f2f5;
    margin: 0 0 8px;
}
.pay-summary {
    background: #131929;
    border: 1px solid #2d3348;
    border-radius: 14px;
    padding: 20px 24px;
    margin-bottom: 24px;
}
.pay-summary-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid #1e2436;
    font-size: 0.9rem;
    color: #d1d5db;
}
.pay-summary-row:last-child { border-bottom: none; font-weight: 700; color: #f0f2f5; }
.pay-summary-row .label { color: #9ca3af; }

.status-pending {
    background: #3d2900;
    border: 1px solid #92400e;
    border-radius: 10px;
    padding: 14px 18px;
    color: #fcd34d;
    font-size: 0.88rem;
    margin-top: 16px;
}
.status-confirmed {
    background: #064e3b;
    border: 1px solid #065f46;
    border-radius: 10px;
    padding: 14px 18px;
    color: #6ee7b7;
    font-size: 0.88rem;
    margin-top: 16px;
}
</style>
"""


def _step_html(n: int, text: str) -> str:
    """Render satu langkah pembayaran sebagai HTML. Gunakan double-quote di atribut."""
    return (
        '<div style="display:flex;gap:12px;align-items:flex-start">'
        '<div style="min-width:26px;height:26px;border-radius:50%;background:#185FA5;'
        'color:#fff;font-size:0.78rem;font-weight:700;display:flex;'
        'align-items:center;justify-content:center;flex-shrink:0">'
        f"{n}"
        "</div>"
        '<div style="font-size:0.87rem;color:#d1d5db;line-height:1.5;padding-top:3px">'
        f"{text}"
        "</div>"
        "</div>"
    )


def build_payment_page(
    user_data: dict,
    package_key: str,
    billing_cycle: str = "monthly",
    payment_id: int | None = None,
) -> dict | None:
    """
    Halaman pembayaran Bank Transfer.
    Return: dict {"confirmed": False, "pending": True, ...} jika user submit bukti,
            atau None jika belum.

    user_data     : dict dari register.py
    package_key   : paket yang dipilih
    billing_cycle : "monthly" | "yearly"
    payment_id    : ID payment di DB jika sudah dibuat
    """
    cfg = _get_package_cfg(package_key)
    price = cfg["price_yearly"] if billing_cycle == "yearly" else cfg["price_monthly"]

    # ── Periksa konfigurasi pembayaran sebelum render ─────────────
    qconf = QRIS_CONFIG
    if not qconf.get("rekening") or not qconf.get("confirm_wa"):
        st.error(
            "⚠️ **Konfigurasi pembayaran belum lengkap.** "
            "Atur `PAYMENT_REKENING` dan `PAYMENT_CONFIRM_WA` di environment variable "
            "atau `.streamlit/secrets.toml` sebelum menerima pembayaran."
        )

    st.markdown(_PAY_CSS, unsafe_allow_html=True)
    st.markdown('<div class="pay-wrap">', unsafe_allow_html=True)

    # ── Header ────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="pay-header">
            <h2>&#x1F4B3; Pembayaran</h2>
            <p style="color:#9ca3af">Selesaikan pembayaran untuk mengaktifkan akun Anda</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Ringkasan order ───────────────────────────────────────────
    cycle_label = "Tahunan" if billing_cycle == "yearly" else "Bulanan"
    pkg_color = cfg["color"]
    pkg_name = cfg["name"]
    full_name = user_data.get("full_name", "-")
    username = user_data.get("username", "-")
    price_fmt = format_price(price)

    st.markdown(
        f"""
        <div class="pay-summary">
            <div class="pay-summary-row">
                <span class="label">Nama</span>
                <span>{full_name}</span>
            </div>
            <div class="pay-summary-row">
                <span class="label">Username</span>
                <span>{username}</span>
            </div>
            <div class="pay-summary-row">
                <span class="label">Paket</span>
                <span style="color:{pkg_color};font-weight:600">{pkg_name}</span>
            </div>
            <div class="pay-summary-row">
                <span class="label">Siklus</span>
                <span>{cycle_label}</span>
            </div>
            <div class="pay-summary-row">
                <span class="label">Total Bayar</span>
                <span style="color:#34d399;font-size:1.1rem">{price_fmt}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Pilihan siklus ────────────────────────────────────────────
    col_cycle1, col_cycle2 = st.columns(2)
    with col_cycle1:
        if st.button(
            f"📅 Bulanan — {format_price(cfg['price_monthly'])}",
            use_container_width=True,
            type="primary" if billing_cycle == "monthly" else "secondary",
            key="pay_monthly",
        ):
            st.session_state["billing_cycle"] = "monthly"
            st.rerun()
    with col_cycle2:
        if st.button(
            f"📆 Tahunan — {format_price(cfg['price_yearly'])} (hemat 2 bln)",
            use_container_width=True,
            type="primary" if billing_cycle == "yearly" else "secondary",
            key="pay_yearly",
        ):
            st.session_state["billing_cycle"] = "yearly"
            st.rerun()

    st.markdown("---")

    # ── BANK TRANSFER ─────────────────────────────────────────────
    # Kode unik 3 digit per session agar admin bisa identifikasi transfer
    if "transfer_unique_code" not in st.session_state:
        st.session_state["transfer_unique_code"] = random.randint(100, 999)
    unique_code = st.session_state["transfer_unique_code"]
    total_transfer = price + unique_code

    # Ambil nilai config sekali agar tidak ada f-string berlapis
    bank_name = qconf.get("bank_name", "-")
    rekening = qconf.get("rekening", "-")
    atas_nama = qconf.get("atas_nama", "-")
    total_fmt = f"Rp {total_transfer:,.0f}"
    total_fmt_strong = f"Rp {total_transfer:,.0f}"

    # Bangun langkah-langkah sebagai variabel terpisah
    steps = "".join(
        [
            _step_html(
                1,
                "Buka aplikasi <strong style=\"color:#f0f2f5\">m-BCA / BCA mobile</strong>"
                " atau mobile banking bank lain",
            ),
            _step_html(
                2,
                "Pilih menu <strong style=\"color:#f0f2f5\">Transfer</strong>"
                " \u2192 sesama BCA atau antar bank",
            ),
            _step_html(
                3,
                f"Masukkan nomor rekening"
                f" <strong style=\"color:#34d399\">{rekening}</strong>"
                f" atas nama <strong style=\"color:#f0f2f5\">{atas_nama}</strong>",
            ),
            _step_html(
                4,
                f"Masukkan nominal tepat"
                f" <strong style=\"color:#fbbf24\">{total_fmt_strong}</strong>"
                f" (sudah termasuk kode unik"
                f" <strong style=\"color:#fbbf24\">+{unique_code}</strong>)",
            ),
            _step_html(
                5,
                "Selesaikan transfer lalu"
                " <strong style=\"color:#f0f2f5\">screenshot bukti pembayaran</strong>",
            ),
            _step_html(
                6,
                "Upload bukti di bawah ini, lalu klik"
                " <strong style=\"color:#f0f2f5\">Kirim Bukti Pembayaran</strong>",
            ),
        ]
    )

    # ── Render Bank Transfer — dipecah jadi beberapa st.markdown() ──
    # Streamlit strip HTML jika ada newline/indentasi di dalam tag,
    # jadi setiap blok ditulis flat (satu baris) dan dipisah per bagian.

    st.markdown(f'<div style="background:#0f1a2e;border:1px solid #1e3a5f;border-radius:14px;padding:24px 28px;margin:16px 0 8px 0"><p style="font-size:13px;font-weight:700;color:#93c5fd;letter-spacing:.08em;text-transform:uppercase;margin:0 0 16px 0">&#x1F3E6;&nbsp;Instruksi Bank Transfer</p>', unsafe_allow_html=True)

    st.markdown(f'<div style="background:#131929;border-radius:10px;padding:16px 20px;margin-bottom:16px"><div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;font-size:0.9rem;border-bottom:1px solid #1e2436"><span style="color:#9ca3af">Bank</span><span style="color:#f0f2f5;font-weight:700">{bank_name}</span></div><div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;font-size:0.9rem;border-bottom:1px solid #1e2436"><span style="color:#9ca3af">No. Rekening</span><span style="color:#34d399;font-weight:800;font-size:1.1rem;letter-spacing:.04em">{rekening}</span></div><div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;font-size:0.9rem"><span style="color:#9ca3af">Atas Nama</span><span style="color:#f0f2f5;font-weight:600">{atas_nama}</span></div></div>', unsafe_allow_html=True)

    st.markdown(f'<div style="background:#1a2a1a;border:1px solid #166534;border-radius:10px;padding:14px 20px;margin-bottom:20px"><div style="font-size:11px;color:#86efac;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px">&#x1F4A1; Nominal yang harus ditransfer</div><div style="display:flex;align-items:baseline;gap:12px;flex-wrap:wrap"><span style="font-size:1.5rem;font-weight:900;color:#4ade80">{total_fmt}</span><span style="font-size:0.8rem;color:#6ee7b7">(harga {price_fmt} + kode unik <strong style="color:#fbbf24">+{unique_code}</strong>)</span></div><div style="font-size:0.78rem;color:#86efac;margin-top:8px">&#x26A0;&#xFE0F; Pastikan nominal transfer <strong>tepat</strong> termasuk kode unik agar admin dapat memverifikasi pembayaran Anda dengan cepat.</div></div>', unsafe_allow_html=True)

    st.markdown('<p style="font-size:13px;font-weight:700;color:#93c5fd;letter-spacing:.08em;text-transform:uppercase;margin:0 0 12px 0">&#x1F4CB;&nbsp;Langkah Pembayaran</p>', unsafe_allow_html=True)

    for step_html in [
        _step_html(1, 'Buka aplikasi <strong style="color:#f0f2f5">m-BCA / BCA mobile</strong> atau mobile banking bank lain'),
        _step_html(2, 'Pilih menu <strong style="color:#f0f2f5">Transfer</strong> \u2192 sesama BCA atau antar bank'),
        _step_html(3, f'Masukkan nomor rekening <strong style="color:#34d399">{rekening}</strong> atas nama <strong style="color:#f0f2f5">{atas_nama}</strong>'),
        _step_html(4, f'Masukkan nominal tepat <strong style="color:#fbbf24">{total_fmt}</strong> (sudah termasuk kode unik <strong style="color:#fbbf24">+{unique_code}</strong>)'),
        _step_html(5, 'Selesaikan transfer lalu <strong style="color:#f0f2f5">screenshot bukti pembayaran</strong>'),
        _step_html(6, 'Upload bukti di bawah ini, lalu klik <strong style="color:#f0f2f5">Kirim Bukti Pembayaran</strong>'),
    ]:
        st.markdown(step_html, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Upload bukti bayar ────────────────────────────────────────
    st.subheader("📤 Upload Bukti Pembayaran")

    uploaded_proof = st.file_uploader(
        "Upload screenshot bukti Transfer Anda",
        type=["jpg", "jpeg", "png", "webp"],
        help="Ukuran maksimal 5MB",
    )

    notes = st.text_area(
        "Catatan tambahan (opsional)",
        placeholder=f"contoh: Transfer via BCA jam 14:30, nominal {price_fmt}",
        height=80,
    )

    if uploaded_proof:
        st.image(uploaded_proof, caption="Preview bukti pembayaran", width=300)

    col_submit, col_wa = st.columns(2)
    result = None

    with col_submit:
        if st.button(
            "✅ Kirim Bukti Pembayaran",
            type="primary",
            use_container_width=True,
            disabled=uploaded_proof is None,
        ):
            proof_bytes = uploaded_proof.read()
            proof_mime = uploaded_proof.type or "image/jpeg"
            proof_name = uploaded_proof.name

            if payment_id:
                try:
                    from database import save_payment_proof

                    save_payment_proof(payment_id, proof_bytes, proof_mime, proof_name)
                except Exception:
                    pass  # Jangan blokir flow jika DB error

            result = {
                "confirmed": False,
                "pending": True,
                "payment_id": payment_id,
                "proof_filename": proof_name,
                "notes": notes,
                "proof_bytes": proof_bytes,
            }

    with col_wa:
        wa_number = qconf["confirm_wa"].replace("-", "").replace(" ", "")
        wa_msg = (
            f"Halo, saya sudah transfer untuk paket *{pkg_name}* "
            f"atas nama *{full_name}* (username: {username}). "
            f"Nominal transfer: *{total_fmt}* (kode unik: +{unique_code}). "
            "Mohon konfirmasinya. Terima kasih."
        )
        wa_url = f"https://wa.me/{wa_number}?text={urllib.parse.quote(wa_msg)}"
        st.link_button("💬 Konfirmasi via WhatsApp", wa_url, use_container_width=True)

    # ── Status menunggu ───────────────────────────────────────────
    if payment_id and not result:
        st.markdown(
            """
            <div class="status-pending">
                &#x23F3; <strong>Menunggu konfirmasi admin.</strong><br>
                Bukti pembayaran Anda sudah diterima. Admin akan memverifikasi dan
                mengaktifkan akun Anda dalam waktu singkat. Silakan cek kembali nanti.
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Back ──────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("← Kembali", use_container_width=False):
        st.session_state.pop("registration_data", None)
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
    return result


def _render_qris_placeholder():
    """Tampilkan placeholder QRIS (aktifkan kembali jika QRIS digunakan)."""
    left, center, right = st.columns([3, 2, 3])
    with center:
        st.image("asset/QRIS_CONTOH.webp")


def build_payment_success_page(package_key: str, username: str):
    """Halaman sukses setelah bukti pembayaran dikirim."""
    cfg = _get_package_cfg(package_key)
    pkg_name = cfg.get("name", package_key)

    st.success("✅ Bukti pembayaran berhasil dikirim!")
    st.markdown(
        f"""
        ### 🎉 Terima kasih, {username}!

        Bukti pembayaran untuk paket **{pkg_name}** sudah diterima.

        **Selanjutnya:**
        1. Tim admin kami akan memverifikasi pembayaran Anda
        2. Akun Anda akan diaktifkan dalam **&lt; 15 menit** (jam kerja)
        3. Anda akan bisa login dengan username dan password yang sudah dibuat

        ---
        **Butuh bantuan?**
        Hubungi admin via WhatsApp yang tertera di halaman pembayaran.
        """
    )

    if st.button("🔑 Login Sekarang", type="primary"):
        for key in [
            "selected_package",
            "registration_data",
            "billing_cycle",
            "payment_submitted",
            "reg_success",
        ]:
            st.session_state.pop(key, None)
        st.session_state["show_login"] = True
        st.rerun()