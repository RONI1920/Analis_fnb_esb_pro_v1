# ui/tabs/tab_enterprise_ai.py — Enterprise AI Assistant Dashboard
# Fitur eksklusif paket Enterprise: AI interaktif berbasis percakapan
# User bisa bertanya dalam bahasa natural → AI query DB → tampilkan visualisasi

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import DB_FILE
from formatters import format_rupiah

from services.ai_provider import ask_ai

# ──────────────────────────────────────────────────────────────────────────────
# CSS STYLING
# ──────────────────────────────────────────────────────────────────────────────

_AI_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Global reset untuk tab ini ── */
section[data-testid="stVerticalBlock"] {
    max-width: 100% !important;
}

/* ── Hero Banner ── */
.ent-hero {
    background: linear-gradient(135deg, #080c14 0%, #0f1625 45%, #0a0d1a 100%);
    border: 1px solid rgba(99, 102, 241, 0.25);
    border-radius: 20px;
    padding: 32px 40px 28px;
    margin-bottom: 28px;
    position: relative;
    overflow: hidden;
    font-family: 'DM Sans', sans-serif;
}
.ent-hero::before {
    content: '';
    position: absolute;
    top: -60px; right: -60px;
    width: 280px; height: 280px;
    background: radial-gradient(circle, rgba(99,102,241,0.12) 0%, transparent 65%);
    border-radius: 50%;
    pointer-events: none;
}
.ent-hero::after {
    content: '';
    position: absolute;
    bottom: -40px; left: 200px;
    width: 180px; height: 180px;
    background: radial-gradient(circle, rgba(139,92,246,0.08) 0%, transparent 70%);
    border-radius: 50%;
    pointer-events: none;
}
.ent-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: linear-gradient(90deg, rgba(99,102,241,0.2), rgba(139,92,246,0.2));
    border: 1px solid rgba(99,102,241,0.4);
    color: #a5b4fc;
    font-size: 10px; font-weight: 700;
    letter-spacing: .14em; text-transform: uppercase;
    padding: 4px 14px; border-radius: 20px;
    margin-bottom: 14px;
    font-family: 'DM Sans', sans-serif;
}
.ent-title {
    font-size: 28px; font-weight: 700;
    color: #f1f5f9; margin: 0 0 8px;
    line-height: 1.2;
    font-family: 'DM Sans', sans-serif;
    letter-spacing: -0.5px;
}
.ent-subtitle {
    font-size: 14px; color: #64748b; margin: 0;
    line-height: 1.6;
    font-family: 'DM Sans', sans-serif;
}

/* ── Empty state ── */
.empty-state {
    text-align: center;
    padding: 80px 20px;
    color: #334155;
    font-family: 'DM Sans', sans-serif;
}
.empty-state .icon { font-size: 48px; margin-bottom: 18px; opacity: 0.6; }
.empty-state .title {
    font-size: 18px; font-weight: 600;
    color: #6366f1; margin-bottom: 10px;
}
.empty-state .desc {
    font-size: 13px; color: #475569; line-height: 1.8;
}
.empty-state em { color: #818cf8; font-style: normal; font-weight: 500; }

/* ── Chat messages ── */
.msg-row-user {
    display: flex;
    justify-content: flex-end;
    align-items: flex-end;
    gap: 10px;
    margin-bottom: 4px;
}
.msg-row-ai {
    display: flex;
    justify-content: flex-start;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 4px;
}

/* Avatar AI */
.avatar-ai {
    width: 36px; height: 36px;
    border-radius: 10px;
    background: linear-gradient(135deg, #4f46e5, #7c3aed);
    display: flex; align-items: center; justify-content: center;
    font-size: 16px;
    flex-shrink: 0;
    margin-top: 2px;
    box-shadow: 0 4px 12px rgba(99,102,241,0.3);
}

/* User bubble */
.bubble-user {
    background: linear-gradient(135deg, #4338ca, #5b21b6);
    color: #ede9fe;
    padding: 13px 18px;
    border-radius: 18px 4px 18px 18px;
    max-width: 72%;
    font-size: 14px;
    line-height: 1.6;
    box-shadow: 0 4px 16px rgba(67,56,202,0.3);
    font-family: 'DM Sans', sans-serif;
    letter-spacing: 0.01em;
}

/* AI bubble */
.bubble-ai {
    background: #0f1625;
    border: 1px solid rgba(99,102,241,0.2);
    color: #cbd5e1;
    padding: 16px 20px;
    border-radius: 4px 18px 18px 18px;
    max-width: 82%;
    font-size: 14px;
    line-height: 1.7;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    font-family: 'DM Sans', sans-serif;
}
.bubble-ai strong { color: #818cf8; font-weight: 600; }
.bubble-ai .ts {
    font-size: 10px;
    color: #334155;
    margin-top: 8px;
    display: block;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.05em;
}

/* ── Streamlit overrides untuk input & button ── */
div[data-testid="stTextInput"] input {
    background: #0c1220 !important;
    border: 1px solid rgba(99,102,241,0.25) !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 14px !important;
    padding: 12px 16px !important;
}
div[data-testid="stTextInput"] input:focus {
    border-color: rgba(99,102,241,0.6) !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.08) !important;
}
div[data-testid="stTextInput"] input::placeholder {
    color: #334155 !important;
}

/* Send button */
div[data-testid="stFormSubmitButton"] button {
    background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
    border: none !important;
    color: white !important;
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    padding: 10px 18px !important;
    transition: opacity 0.2s, transform 0.1s !important;
    box-shadow: 0 4px 14px rgba(99,102,241,0.35) !important;
    letter-spacing: 0.02em !important;
    height: 46px !important;
}
div[data-testid="stFormSubmitButton"] button:hover {
    opacity: 0.88 !important;
    transform: translateY(-1px) !important;
}

/* ── Section separator ── */
.ai-divider {
    border: none;
    border-top: 1px solid rgba(99,102,241,0.1);
    margin: 14px 0;
}

/* ── Sidebar labels ── */
.sidebar-label {
    font-size: 10px;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-weight: 700;
    margin-bottom: 10px;
    font-family: 'DM Sans', sans-serif;
}

/* ── Stats badge di sidebar ── */
.stat-chip {
    background: #0c1220;
    border: 1px solid rgba(99,102,241,0.15);
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 8px;
    font-family: 'DM Sans', sans-serif;
}
.stat-chip .s-label {
    font-size: 10px; color: #475569;
    text-transform: uppercase; letter-spacing: 0.1em;
    font-weight: 600;
}
.stat-chip .s-value {
    font-size: 22px; font-weight: 700;
    color: #818cf8; margin-top: 2px;
    font-family: 'JetBrains Mono', monospace;
}

/* ── Schema card ── */
.schema-card {
    background: #0a0e1a;
    border: 1px solid rgba(99,102,241,0.12);
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 11px; color: #475569;
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 6px;
    line-height: 1.6;
}
.schema-card .tname {
    color: #818cf8; font-weight: 700; font-size: 11px;
    display: block; margin-bottom: 4px;
    letter-spacing: 0.04em;
}

/* ── Typing indicator ── */
.typing { display: flex; gap: 5px; padding: 4px 0; align-items: center; }
.typing span {
    width: 7px; height: 7px; border-radius: 50%;
    background: #4f46e5;
    animation: bounce 1.3s ease-in-out infinite;
    display: inline-block;
}
.typing span:nth-child(2) { animation-delay: .18s; background: #6366f1; }
.typing span:nth-child(3) { animation-delay: .36s; background: #818cf8; }
@keyframes bounce {
    0%,60%,100% { transform: translateY(0); opacity:.5; }
    30% { transform: translateY(-7px); opacity:1; }
}
</style>
"""


# ──────────────────────────────────────────────────────────────────────────────
# DATABASE SCHEMA HELPER
# ──────────────────────────────────────────────────────────────────────────────

DB_SCHEMA_DESCRIPTION = """
Database SQLite dengan tabel berikut:

1. gmv_data — Data penjualan harian
   Kolom penting: "Sales Date In" (DATETIME), "Branch" (TEXT), "Menu" (TEXT),
   "Menu Category" (TEXT), "Total Nett Sales" (REAL), "Total Gross Sales" (REAL),
   "Total After Bill Discount" (REAL), "Qty" (REAL), "Payment Method" (TEXT),
   "Waiter" (TEXT), "Bill Number" (TEXT), "Sales Type" (TEXT)

2. cogs_data — Data COGS & profit per menu
   Kolom: "Sales Date" (DATETIME), "Branch" (TEXT), "Menu" (TEXT),
   "Menu Category" (TEXT), "Harga Jual" (REAL), "COGS" (REAL),
   "Qty" (REAL), "Total" (REAL)

3. purchase_data — Data pembelian / pengadaan
   Kolom: "Purchase Date" (DATETIME), "Branch" (TEXT), "Supplier Name" (TEXT),
   "Category" (TEXT), "Sub Category" (TEXT), "Product Name" (TEXT),
   "PO Qty" (REAL), "Receipt Qty" (REAL), "Price" (REAL), "Total" (REAL)

4. waiter_data — Performa waiter / pelayan
   Kolom: "Bill Number" (TEXT), "Waiter" (TEXT), "Order Time" (DATETIME),
   "Total After Bill Discount" (REAL), "Branch" (TEXT), "Sales Type" (TEXT)

5. ulasan_data — Ulasan & rating pelanggan
   Kolom: "Nama" (TEXT), "Rating" (TEXT), "Ulasan" (TEXT), "Rating_Clean" (INTEGER)

6. pl_data — Laporan Laba Rugi (P&L)
   Kolom: "Account" (TEXT), "Description" (TEXT), "Date" (DATETIME),
   "Month_Name" (TEXT), "Value" (REAL), "Branch" (TEXT), "Category" (TEXT)

Branch yang tersedia: 'Milky Way By The Sea', 'Milky Way Land's End',
'Milky Way Lippo Mall Puri', 'Milky Way Pondok Indah Mall 2', 'Milky Way SuperHiro'

Data tersedia: Januari 2025 – Oktober 2025
"""

SYSTEM_PROMPT = f"""Kamu adalah AI Analyst khusus untuk aplikasi F&B Analytics bernama "Enterprise AI Assistant".
Tugasmu adalah membantu pemilik bisnis restoran/kafe memahami data bisnis mereka melalui percakapan natural.

{DB_SCHEMA_DESCRIPTION}

CARA KERJAMU:
1. Pahami pertanyaan user dalam bahasa Indonesia atau Inggris
2. Buat query SQL yang tepat untuk menjawab pertanyaan
3. Kembalikan respons HANYA dalam format JSON berikut (tanpa teks lain, tanpa markdown):

{{
  "answer": "Penjelasan singkat hasil analisis dalam bahasa Indonesia (2-3 kalimat, gunakan emoji yang relevan)",
  "sql": "SELECT ... FROM ... WHERE ...",
  "chart_type": "bar" | "line" | "pie" | "table" | "metric" | "none",
  "chart_config": {{
    "x": "nama_kolom_x",
    "y": "nama_kolom_y",
    "title": "Judul Grafik",
    "color": "nama_kolom_warna (opsional)"
  }},
  "insights": ["insight 1", "insight 2", "insight 3"],
  "followup": ["pertanyaan lanjutan 1", "pertanyaan lanjutan 2"]
}}

ATURAN SQL:
- Nama kolom yang mengandung spasi atau karakter khusus HARUS dikurung dengan tanda kutip ganda: "Sales Date In"
- Untuk filter tanggal gunakan: DATE("Sales Date In") = '2025-01-15' atau LIKE '2025-01%'
- Untuk revenue/omset gunakan kolom "Total Nett Sales" dari gmv_data
- Untuk profit gunakan: (Harga Jual - COGS) * Qty dari cogs_data
- Selalu tambahkan LIMIT 50 kecuali query aggregasi
- Format angka biarkan angka mentah (tanpa format Rp), formatting dilakukan di frontend

PEDOMAN JAWABAN:
- Jawab dalam bahasa Indonesia yang ramah dan profesional
- Sertakan angka/statistik spesifik dari data
- Berikan insight bisnis yang actionable
- Jika pertanyaan tidak bisa dijawab dari data, jelaskan dengan sopan
- chart_type "metric" untuk satu angka KPI, "table" untuk data tabular, "none" jika tidak ada data visual
"""


# ──────────────────────────────────────────────────────────────────────────────
# QUICK PROMPT TEMPLATES
# ──────────────────────────────────────────────────────────────────────────────

QUICK_PROMPTS = [
    "📊 Revenue hari ini semua outlet",
    "🏆 Top 10 menu terlaris bulan ini",
    "📍 Perbandingan omset per outlet",
    "📈 Tren revenue minggu ini vs minggu lalu",
    "💰 Profit margin per kategori menu",
    "⭐ Analisis rating dan ulasan pelanggan",
    "🛒 Pembelian terbesar bulan ini",
    "👨‍🍳 Performa waiter terbaik",
    "🔮 Prediksi revenue bulan depan",
    "📉 Menu dengan margin rendah",
]


# ──────────────────────────────────────────────────────────────────────────────
# DATABASE QUERY EXECUTOR
# ──────────────────────────────────────────────────────────────────────────────

def run_sql_query(sql: str) -> tuple[pd.DataFrame | None, str | None]:
    """Eksekusi SQL query dan kembalikan DataFrame atau error message."""
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query(sql, conn)
        conn.close()
        return df, None
    except Exception as e:
        return None, str(e)


# ──────────────────────────────────────────────────────────────────────────────
# AI API CALL 
# ──────────────────────────────────────────────────────────────────────────────

def call_ai_analyst(user_message, conversation_history):

    try:
        return ask_ai(
            SYSTEM_PROMPT,
            user_message,
            conversation_history,
        )

    except Exception as e:
        return {
            "answer": f"❌ Error AI: {str(e)[:200]}",
            "sql": None,
            "chart_type": "none",
            "chart_config": {},
            "insights": [],
            "followup": [],
        }

# ──────────────────────────────────────────────────────────────────────────────
# CHART RENDERER
# ──────────────────────────────────────────────────────────────────────────────

def render_chart(df: pd.DataFrame, chart_type: str, config: dict):
    """Render Plotly chart berdasarkan tipe dan konfigurasi."""
    if df is None or df.empty:
        st.info("📭 Tidak ada data untuk ditampilkan.")
        return

    x_col = config.get("x")
    y_col = config.get("y")
    title = config.get("title", "")
    color_col = config.get("color")

    # Pastikan kolom ada
    if x_col and x_col not in df.columns:
        x_col = df.columns[0]
    if y_col and y_col not in df.columns:
        y_col = df.columns[-1] if len(df.columns) > 1 else df.columns[0]

    PLOT_THEME = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0", size=12),
        title=dict(font=dict(color="#f0f2f5", size=14), x=0.01),
        margin=dict(l=0, r=0, t=40, b=0),
    )

    try:
        if chart_type == "metric":
            val = df.iloc[0, 0]
            col_name = df.columns[0]
            if isinstance(val, (int, float)):
                formatted = format_rupiah(val) if val > 100_000 else f"{val:,.0f}"
            else:
                formatted = str(val)
            st.metric(label=title or col_name, value=formatted)

        elif chart_type == "table":
            display_df = df.copy()
            for col in display_df.select_dtypes(include="number").columns:
                if display_df[col].max() > 100_000:
                    display_df[col] = display_df[col].apply(
                        lambda v: format_rupiah(v) if pd.notna(v) else "-"
                    )
            st.dataframe(display_df, use_container_width=True, hide_index=True)

        elif chart_type == "bar":
            if color_col and color_col in df.columns:
                fig = px.bar(df, x=x_col, y=y_col, color=color_col,
                             title=title, barmode="group")
            else:
                fig = px.bar(df, x=x_col, y=y_col, title=title,
                             color_discrete_sequence=["#6366f1"])
            fig.update_layout(**PLOT_THEME)
            fig.update_traces(marker_line_width=0)
            st.plotly_chart(fig, use_container_width=True)

        elif chart_type == "line":
            if color_col and color_col in df.columns:
                fig = px.line(df, x=x_col, y=y_col, color=color_col,
                              title=title, markers=True)
            else:
                fig = px.line(df, x=x_col, y=y_col, title=title,
                              markers=True, color_discrete_sequence=["#818cf8"])
            fig.update_layout(**PLOT_THEME)
            st.plotly_chart(fig, use_container_width=True)

        elif chart_type == "pie":
            fig = px.pie(df, names=x_col, values=y_col, title=title,
                         color_discrete_sequence=px.colors.sequential.Purples_r)
            fig.update_layout(**PLOT_THEME)
            fig.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig, use_container_width=True)

        else:
            st.dataframe(df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.warning(f"⚠️ Tidak dapat merender grafik: {e}")
        st.dataframe(df, use_container_width=True, hide_index=True)


# ──────────────────────────────────────────────────────────────────────────────
# MAIN TAB BUILDER
# ──────────────────────────────────────────────────────────────────────────────

def build_tab_enterprise_ai():
    """Tab utama Enterprise AI Assistant."""
    st.markdown(_AI_CSS, unsafe_allow_html=True)

    # ── Hero Banner ──────────────────────────────────────────────
    st.markdown("""
    <div class="ent-hero">
        <div class="ent-badge">✦ Enterprise Exclusive</div>
        <h1 class="ent-title">Enterprise AI Assistant</h1>
        <p class="ent-subtitle">
            Tanyakan apa saja tentang bisnis Anda dalam bahasa natural —
            AI akan menganalisis database real-time dan menyajikan visualisasi otomatis.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Inisialisasi session state ───────────────────────────────
    if "ai_chat_history" not in st.session_state:
        st.session_state.ai_chat_history = []
    if "ai_conv_history" not in st.session_state:
        st.session_state.ai_conv_history = []

    # ── Layout: Chat lebar (4) + Sidebar tools (1) ──────────────
    col_chat, col_tools = st.columns([4, 1], gap="large")

    # ────────────────────────── SIDEBAR TOOLS ───────────────────
    with col_tools:
        st.markdown('<div class="sidebar-label">⚙ Pengaturan</div>', unsafe_allow_html=True)
        show_sql = st.toggle("Tampilkan SQL", value=False)

        st.markdown("<hr class='ai-divider'>", unsafe_allow_html=True)
        st.markdown('<div class="sidebar-label">🔥 Quick Prompts</div>', unsafe_allow_html=True)

        for qp in QUICK_PROMPTS:
            if st.button(qp, key=f"qp_{qp}", use_container_width=True):
                st.session_state.ai_pending_prompt = qp
                st.rerun()

        st.markdown("<hr class='ai-divider'>", unsafe_allow_html=True)
        st.markdown('<div class="sidebar-label">📊 Session Stats</div>', unsafe_allow_html=True)

        n_turns = len([m for m in st.session_state.ai_chat_history if m["role"] == "user"])
        st.markdown(f"""
        <div class="stat-chip">
            <div class="s-label">Pertanyaan</div>
            <div class="s-value">{n_turns}</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🗑 Hapus Riwayat", use_container_width=True):
            st.session_state.ai_chat_history = []
            st.session_state.ai_conv_history = []
            st.rerun()

        st.markdown("<hr class='ai-divider'>", unsafe_allow_html=True)
        st.markdown('<div class="sidebar-label">🗄 Schema DB</div>', unsafe_allow_html=True)

        tables = [
            ("gmv_data", "Sales Date In, Branch, Menu, Total Nett Sales, Qty, Payment Method"),
            ("cogs_data", "Sales Date, Branch, Menu, Harga Jual, COGS, Qty"),
            ("purchase_data", "Purchase Date, Branch, Supplier, Category, Total"),
            ("waiter_data", "Bill Number, Waiter, Order Time, Total, Branch"),
            ("ulasan_data", "Nama, Rating, Ulasan, Rating_Clean"),
            ("pl_data", "Account, Description, Date, Value, Branch, Category"),
        ]
        for tname, cols in tables:
            st.markdown(f"""
            <div class="schema-card">
                <span class="tname">📋 {tname}</span>
                {cols}
            </div>
            """, unsafe_allow_html=True)

    # ────────────────────────── CHAT AREA ───────────────────────
    with col_chat:

        # ── Chat history container (native Streamlit) ────────────
        chat_box = st.container(height=520, border=False)

        with chat_box:
            if not st.session_state.ai_chat_history:
                st.markdown("""
                <div class="empty-state">
                    <div class="icon">✦</div>
                    <div class="title">Enterprise AI Assistant</div>
                    <div class="desc">
                        Tanyakan apa saja tentang data bisnis Anda.<br>
                        Contoh: <em>"Revenue hari ini di outlet Lippo Mall"</em><br>
                        atau <em>"Top 10 menu terlaris bulan Oktober"</em>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                for item in st.session_state.ai_chat_history:
                    if item["role"] == "user":
                        st.markdown(f"""
                        <div class="msg-row-user">
                            <div class="bubble-user">{item["content"]}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="msg-row-ai">
                            <div class="avatar-ai">✦</div>
                            <div class="bubble-ai">
                                {item["content"]}
                                <span class="ts">⏱ {item.get("ts", "")}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                        # Render chart jika ada
                        if item.get("chart_data") is not None:
                            try:
                                df_chart = pd.DataFrame(item["chart_data"])
                                render_chart(
                                    df_chart,
                                    item.get("chart_type", "table"),
                                    item.get("chart_config", {}),
                                )
                            except Exception:
                                pass

                        # SQL expander
                        if show_sql and item.get("sql"):
                            with st.expander("🔍 Lihat SQL Query"):
                                st.code(item["sql"], language="sql")

                        # Insights expander
                        if item.get("insights"):
                            with st.expander("💡 Business Insights"):
                                for ins in item["insights"]:
                                    st.markdown(f"→ {ins}")

        # ── Input Area (di luar chat_box, selalu di bawah) ───────
        st.markdown("<hr class='ai-divider'>", unsafe_allow_html=True)

        # Cek pending prompt dari quick buttons
        default_val = ""
        if "ai_pending_prompt" in st.session_state:
            default_val = st.session_state.pop("ai_pending_prompt")

        with st.form("ai_chat_form", clear_on_submit=True):
            col_inp, col_btn = st.columns([6, 1])
            with col_inp:
                user_input = st.text_input(
                    "Tanya AI Analyst",
                    value=default_val,
                    placeholder="Contoh: Revenue outlet Pondok Indah bulan Oktober...",
                    label_visibility="collapsed",
                )
            with col_btn:
                submitted = st.form_submit_button("Kirim →", use_container_width=True)

        if submitted and user_input.strip():
            _process_ai_message(user_input.strip(), show_sql)


# ──────────────────────────────────────────────────────────────────────────────
# MESSAGE PROCESSOR
# ──────────────────────────────────────────────────────────────────────────────

def _process_ai_message(user_input: str, show_sql: bool):
    """Proses pesan user: panggil AI, eksekusi SQL, update history."""

    # Tambahkan pesan user ke history
    st.session_state.ai_chat_history.append({
        "role": "user",
        "content": user_input,
    })

    # Panggil AI
    with st.spinner("🤖 AI sedang menganalisis data..."): 
        result = ask_ai( 
            SYSTEM_PROMPT, 
            user_input, 
            st.session_state.ai_conv_history 
        )

    answer = result.get("answer", "Maaf, tidak dapat memproses pertanyaan ini.")
    sql = result.get("sql")
    chart_type = result.get("chart_type", "none")
    chart_config = result.get("chart_config", {})
    insights = result.get("insights", [])
    followup = result.get("followup", [])

    # Eksekusi SQL jika ada
    df_result = None
    sql_error = None
    if sql and sql.strip().upper().startswith("SELECT"):
        df_result, sql_error = run_sql_query(sql)
        if sql_error:
            answer += f"\n\n⚠️ *Catatan: Terjadi error saat mengambil data: {sql_error[:100]}*"
            chart_type = "none"

    # Simpan ke history display
    ts = datetime.now().strftime("%H:%M")
    ai_entry = {
        "role": "assistant",
        "content": answer,
        "sql": sql,
        "chart_type": chart_type,
        "chart_config": chart_config,
        "chart_data": df_result.to_dict("records") if df_result is not None and not df_result.empty else None,
        "insights": insights,
        "followup": followup,
        "ts": ts,
    }
    st.session_state.ai_chat_history.append(ai_entry)

    # Update conversation history untuk konteks AI
    st.session_state.ai_conv_history.append({"role": "user", "content": user_input})
    st.session_state.ai_conv_history.append({"role": "assistant", "content": answer})

    # Simpan followup suggestions
    if followup:
        st.session_state.ai_followup = followup

    st.rerun()