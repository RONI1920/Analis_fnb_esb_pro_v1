# services/notifier.py — Notifikasi Email (SMTP/Gmail gratis) + WhatsApp (wa.me gratis)
#
# CARA PAKAI GMAIL (gratis):
#   1. Aktifkan "2-Step Verification" di akun Google
#   2. Buat "App Password" di https://myaccount.google.com/apppasswords
#   3. Isi NOTIFY_EMAIL_SENDER dan NOTIFY_EMAIL_APP_PASSWORD di .env
#
# CARA PAKAI WHATSAPP (gratis via wa.me link):
#   - Tidak perlu API berbayar
#   - Sistem akan membuka link wa.me di browser user sehingga pesan terkirim
#   - Isi NOTIFY_WA_NUMBER di .env dengan nomor penerima (admin/owner)

import os
import smtplib
import streamlit as st
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ── Baca config dari .env / st.secrets ───────────────────────────────────────
def _get_cfg(key: str, default: str = "") -> str:
    try:
        # Coba streamlit secrets dulu (untuk cloud deployment)
        parts = key.split(".")
        obj = st.secrets
        for p in parts:
            obj = obj[p]
        return str(obj)
    except Exception:
        return os.getenv(key, default)


def _email_enabled() -> bool:
    return bool(_get_cfg("NOTIFY_EMAIL_SENDER") and _get_cfg("NOTIFY_EMAIL_APP_PASSWORD"))


def _wa_number() -> str:
    return _get_cfg("NOTIFY_WA_NUMBER", "").strip().replace("+", "").replace("-", "").replace(" ", "")


# ── Kirim Email via Gmail SMTP (gratis) ──────────────────────────────────────
def send_email_notification(to_email: str, subject: str, body_html: str) -> tuple[bool, str]:
    """
    Kirim email notifikasi via Gmail SMTP.
    Gratis — hanya butuh Gmail + App Password.
    Kembalikan (True, "") jika berhasil, (False, pesan_error) jika gagal.
    """
    if not _email_enabled():
        return False, "Konfigurasi email belum diatur (NOTIFY_EMAIL_SENDER / NOTIFY_EMAIL_APP_PASSWORD)"

    sender    = _get_cfg("NOTIFY_EMAIL_SENDER")
    app_pw    = _get_cfg("NOTIFY_EMAIL_APP_PASSWORD")
    smtp_host = _get_cfg("NOTIFY_SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(_get_cfg("NOTIFY_SMTP_PORT", "587"))

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"FnB Analyst <{sender}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(sender, app_pw)
            server.sendmail(sender, to_email, msg.as_string())

        return True, ""
    except smtplib.SMTPAuthenticationError:
        return False, "Autentikasi Gmail gagal. Pastikan App Password sudah benar."
    except smtplib.SMTPException as e:
        return False, f"SMTP error: {e}"
    except Exception as e:
        return False, f"Gagal kirim email: {e}"


# ── WhatsApp via wa.me (gratis, tanpa API berbayar) ──────────────────────────
def get_wa_link(message: str) -> str | None:
    """
    Buat link wa.me untuk kirim pesan WhatsApp.
    Klik link ini akan membuka WhatsApp dengan pesan sudah terisi.
    Gratis — tidak perlu API apapun.
    """
    wa_num = _wa_number()
    if not wa_num:
        return None
    from urllib.parse import quote
    return f"https://wa.me/{wa_num}?text={quote(message)}"


def show_wa_button(message: str, label: str = "📱 Kirim via WhatsApp"):
    """Tampilkan tombol WhatsApp di Streamlit (membuka wa.me di tab baru)."""
    link = get_wa_link(message)
    if link:
        st.markdown(
            f"""<a href="{link}" target="_blank" style="
                display:inline-flex;align-items:center;gap:8px;
                background:#25D366;color:white;border-radius:8px;
                padding:8px 16px;font-weight:600;font-size:0.9rem;
                text-decoration:none;margin-top:8px">
                💬 {label}
            </a>""",
            unsafe_allow_html=True,
        )


# ── Template pesan ─────────────────────────────────────────────────────────

def _email_template(title: str, body: str, color: str = "#6ee7b7") -> str:
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;
                background:#0f1420;color:#e5e7eb;border-radius:12px;
                overflow:hidden;border:1px solid #2d3348">
        <div style="background:linear-gradient(135deg,#1d4ed8,#7c3aed);
                    padding:20px 24px">
            <h2 style="margin:0;color:white;font-size:1.2rem">📊 FnB Analyst</h2>
        </div>
        <div style="padding:24px">
            <h3 style="color:{color};margin-top:0">{title}</h3>
            {body}
        </div>
        <div style="padding:12px 24px;background:#0a0e18;
                    color:#6b7280;font-size:11px;text-align:center">
            FnB Analyst Dashboard · Pesan otomatis, jangan dibalas
        </div>
    </div>
    """


def notify_upload_success(
    to_email: str | None,
    username: str,
    table: str,
    rows: int,
    min_date: str,
    max_date: str,
    dupes: int = 0,
):
    """Notifikasi berhasil upload data."""
    subject = f"✅ Upload Data Berhasil — {table}"
    body = f"""
    <p>Halo <b>{username}</b>,</p>
    <p>Data <b>{table}</b> berhasil diupload ke dashboard FnB Analyst.</p>
    <table style="border-collapse:collapse;width:100%;margin:12px 0">
        <tr><td style="padding:6px 0;color:#9ca3af">Total baris</td>
            <td style="font-weight:700;color:#6ee7b7">{rows:,} baris</td></tr>
        <tr><td style="padding:6px 0;color:#9ca3af">Periode</td>
            <td style="font-weight:700;color:#f0f2f5">{min_date} → {max_date}</td></tr>
        {"<tr><td style='padding:6px 0;color:#9ca3af'>Duplikat dihapus</td><td style='color:#fbbf24'>" + str(dupes) + " baris</td></tr>" if dupes else ""}
    </table>
    <p style="color:#9ca3af;font-size:0.85rem">Silakan cek dashboard untuk melihat analisis terbaru.</p>
    """
    if to_email:
        send_email_notification(to_email, subject, _email_template("Upload Data Berhasil ✅", body))

    # Teks WA
    wa_msg = (
        f"✅ *FnB Analyst - Upload Berhasil*\n\n"
        f"User: {username}\n"
        f"Data: {table}\n"
        f"Baris: {rows:,}\n"
        f"Periode: {min_date} → {max_date}"
        + (f"\nDuplikat dihapus: {dupes}" if dupes else "")
    )
    return wa_msg


def notify_password_changed(to_email: str | None, username: str, full_name: str):
    """Notifikasi ganti password."""
    from datetime import datetime
    waktu = datetime.now().strftime("%d/%m/%Y %H:%M")

    subject = "🔒 Password Berhasil Diubah — FnB Analyst"
    body = f"""
    <p>Halo <b>{full_name}</b>,</p>
    <p>Password akun FnB Analyst Anda berhasil diubah pada <b>{waktu}</b>.</p>
    <p style="background:#1a1f2e;border-left:3px solid #ef4444;
              padding:12px 16px;border-radius:0 8px 8px 0;margin:16px 0;
              color:#fca5a5">
        ⚠️ Jika Anda tidak melakukan perubahan ini, segera hubungi admin.
    </p>
    <p style="color:#9ca3af;font-size:0.85rem">Username: <b style="color:#e5e7eb">{username}</b></p>
    """
    if to_email:
        send_email_notification(
            to_email, subject,
            _email_template("Password Diubah 🔒", body, color="#fca5a5")
        )

    wa_msg = (
        f"🔒 *FnB Analyst - Password Diubah*\n\n"
        f"Akun: {username} ({full_name})\n"
        f"Waktu: {waktu}\n\n"
        f"Jika Anda tidak melakukan ini, segera hubungi admin."
    )
    return wa_msg
