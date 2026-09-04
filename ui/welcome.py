# ui/welcome.py — Halaman Selamat Datang & Footer

import json
import os
import streamlit as st

try:
    from streamlit_lottie import st_lottie
    _LOTTIE_AVAILABLE = True
except ImportError:
    _LOTTIE_AVAILABLE = False

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_lottiefile(filename: str):
    filepath = os.path.join(_BASE_DIR, "asset", filename)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _render_lottie_or_fallback(col, filename: str, key: str, fallback_icon: str, fallback_label: str):
    with col:
        lottie = _load_lottiefile(filename)
        if lottie and _LOTTIE_AVAILABLE:
            st_lottie(lottie, speed=1, loop=True, height=220, key=key)
        else:
            st.markdown(
                f"""<div style="display:flex;flex-direction:column;align-items:center;
                            justify-content:center;height:220px;border:1px solid #1e3a5f;
                            border-radius:12px;background:#0d1b2e;">
                    <div style="font-size:4rem;">{fallback_icon}</div>
                    <p style="color:#6ee7b7;font-size:0.85rem;margin-top:10px;">{fallback_label}</p>
                </div>""",
                unsafe_allow_html=True,
            )


# ── Definisi modul analitik lengkap ──────────────────────────────
_ANALYTICS_MODULES = [
    {
        "icon": "📊",
        "title": "Penjualan (GMV)",
        "color": "#3b82f6",
        "bg": "#1e3a5f18",
        "border": "#3b82f640",
        "items": [
            "Tren GMV harian, mingguan, dan bulanan",
            "Top 10 menu terlaris & pendapatan per kategori",
            "Analisis jam sibuk & hari peak transaksi",
            "Perbandingan kinerja antar cabang",
            "Rata-rata nilai transaksi (ATV) per periode",
        ],
        "kpi": ["Total GMV", "Jumlah Transaksi", "ATV", "Pertumbuhan MoM"],
    },
    {
        "icon": "💰",
        "title": "COGS & Profitabilitas",
        "color": "#10b981",
        "bg": "#10b98118",
        "border": "#10b98140",
        "items": [
            "Cost of Goods Sold per menu dan kategori",
            "Gross Profit Margin per item (bukan sekadar omzet)",
            "Identifikasi menu 'hidden gem' & menu drag-profit",
            "Rasio COGS terhadap penjualan per periode",
            "Simulasi dampak kenaikan biaya bahan baku",
        ],
        "kpi": ["Gross Margin %", "COGS Total", "Profit per Menu", "Menu Terprofitabel"],
    },
    {
        "icon": "🧑‍🍳",
        "title": "SDM & Waktu Sibuk",
        "color": "#f59e0b",
        "bg": "#f59e0b18",
        "border": "#f59e0b40",
        "items": [
            "Performa penjualan per waiter / kasir",
            "Deteksi anomali transaksi (void, diskon berlebih)",
            "Distribusi transaksi per shift & jam operasional",
            "Efisiensi layanan: waktu order ke pembayaran",
            "Ranking staf berdasarkan kontribusi GMV",
        ],
        "kpi": ["Top Waiter", "Anomali Transaksi", "Jam Tersibuk", "Rata-rata Order/Shift"],
    },
    {
        "icon": "🛒",
        "title": "Pembelian & Supplier",
        "color": "#8b5cf6",
        "bg": "#8b5cf618",
        "border": "#8b5cf640",
        "items": [
            "Total pembelian per supplier & kategori bahan",
            "Tren pengeluaran bahan baku bulanan",
            "Analisis harga satuan & deteksi kenaikan harga",
            "Perbandingan spending antar cabang",
            "Rasio pembelian vs penjualan (purchase-to-sales ratio)",
        ],
        "kpi": ["Total Pembelian", "Supplier Terbesar", "Kategori Terkostly", "Efisiensi Belanja"],
    },
    {
        "icon": "⚖️",
        "title": "A/B Comparison",
        "color": "#ec4899",
        "bg": "#ec489918",
        "border": "#ec489940",
        "items": [
            "Bandingkan dua periode secara berdampingan (misal: Ramadan vs normal)",
            "Delta GMV, transaksi, dan margin antar periode",
            "Visualisasi tren side-by-side untuk keputusan strategis",
            "Komparasi kinerja per cabang pada dua rentang waktu",
            "Export laporan perbandingan dalam format tabel",
        ],
        "kpi": ["Δ GMV", "Δ Margin", "Δ Transaksi", "Periode Terbaik"],
    },
    {
        "icon": "🎯",
        "title": "Target & Pencapaian",
        "color": "#f97316",
        "bg": "#f9731618",
        "border": "#f9731640",
        "items": [
            "Input & tracking target GMV bulanan per cabang",
            "Proyeksi pencapaian target secara real-time",
            "Gap analysis: seberapa jauh dari target bulan ini",
            "Visualisasi progress bar target harian vs aktual",
            "Alert otomatis jika proyeksi di bawah target",
        ],
        "kpi": ["% Pencapaian", "Sisa Target", "Proyeksi Akhir Bulan", "Run-rate Harian"],
    },
    {
        "icon": "🔮",
        "title": "Forecast AI (30 Hari)",
        "color": "#06b6d4",
        "bg": "#06b6d418",
        "border": "#06b6d440",
        "items": [
            "Ramalan tren GMV 30 hari ke depan berbasis historis",
            "Model machine learning: trend + seasonality + holiday effect",
            "Interval kepercayaan prediksi (confidence band)",
            "Identifikasi potensi peak & slow day ke depan",
            "Rekomendasi stocking & staffing berdasarkan forecast",
        ],
        "kpi": ["Prediksi GMV 30 Hari", "Tren Naik/Turun", "Hari Puncak", "Akurasi Model"],
    },
    {
        "icon": "❤️",
        "title": "Analisis Ulasan Pelanggan",
        "color": "#f43f5e",
        "bg": "#f43f5e18",
        "border": "#f43f5e40",
        "items": [
            "Analisis sentimen ulasan (positif / netral / negatif)",
            "Word cloud keluhan & pujian paling sering disebut",
            "Distribusi rating bintang & tren kepuasan pelanggan",
            "Identifikasi menu / layanan yang paling banyak dikeluhkan",
            "Perbandingan sentimen antar cabang",
        ],
        "kpi": ["Rating Rata-rata", "% Ulasan Positif", "Keluhan Utama", "NPS Estimasi"],
    },
    {
        "icon": "💡",
        "title": "Rekomendasi Cross-sell",
        "color": "#a78bfa",
        "bg": "#a78bfa18",
        "border": "#a78bfa40",
        "items": [
            "Algoritma Market Basket Analysis (jika beli A → tawarkan B)",
            "Identifikasi pasangan menu yang paling sering dipesan bersama",
            "Rekomendasi bundling untuk meningkatkan ATV",
            "Visualisasi association rules dengan confidence & lift score",
            "Segmentasi rekomendasi berdasarkan waktu / cabang",
        ],
        "kpi": ["Top 10 Pasangan Menu", "Lift Score", "Peluang Upsell", "Potensi ATV Tambahan"],
    },
    {
        "icon": "💸",
        "title": "Simulator Promo",
        "color": "#34d399",
        "bg": "#34d39918",
        "border": "#34d39940",
        "items": [
            "Simulasi skenario diskon (10%, 20%, 30%) dan dampak profit",
            "Analisis break-even point promo BOGO (buy one get one)",
            "Perbandingan profit dengan dan tanpa promo per menu",
            "Estimasi volume penjualan yang diperlukan agar promo menguntungkan",
            "Rekomendasi menu yang paling layak dipromosikan",
        ],
        "kpi": ["Profit After Promo", "Break-even Volume", "Diskon Optimal", "ROI Promo"],
    },
    {
        "icon": "✨",
        "title": "Analisis Musiman",
        "color": "#fbbf24",
        "bg": "#fbbf2418",
        "border": "#fbbf2440",
        "items": [
            "Perbandingan penjualan Hari Libur vs Hari Biasa",
            "Deteksi pola musiman: Lebaran, Nataru, long weekend",
            "Analisis dampak event lokal terhadap kinerja cabang",
            "Heat-map penjualan per hari dalam minggu × jam",
            "Kalender event terintegrasi untuk perencanaan stok & SDM",
        ],
        "kpi": ["Uplift Hari Libur %", "Hari Puncak", "Musim Terbaik", "Event Impact"],
    },
    {
        "icon": "🧪",
        "title": "Lab Strategi & Menu Engineering",
        "color": "#64748b",
        "bg": "#64748b18",
        "border": "#64748b40",
        "items": [
            "BCG Matrix menu: Stars / Cash Cows / Question Marks / Dogs",
            "Simulator perubahan harga jual dan dampak terhadap margin",
            "Analisis elastisitas harga berbasis data historis",
            "Menu Engineering: popularity vs profitability 2×2 matrix",
            "Rekomendasi aksi: pertahankan, promosikan, reformulasi, atau hapus",
        ],
        "kpi": ["Menu Stars", "Menu Dogs", "Harga Optimal", "Portfolio Score"],
    },
    {
        "icon": "📉",
        "title": "Profit & Loss (P&L)",
        "color": "#0ea5e9",
        "bg": "#0ea5e918",
        "border": "#0ea5e940",
        "items": [
            "Dashboard Laba Rugi eksekutif multi-cabang & multi-bulan",
            "Waterfall chart: dari revenue ke net profit step by step",
            "Breakdown biaya: COGS, opex, tenaga kerja, overhead",
            "Trend margin gross & net per bulan",
            "Drill-down P&L per cabang untuk analisis komparatif",
        ],
        "kpi": ["Net Profit", "EBITDA Estimasi", "Gross Margin", "Operating Ratio"],
    },
    {
        "icon": "📦",
        "title": "Manajemen Inventori",
        "color": "#6366f1",
        "bg": "#6366f118",
        "border": "#6366f140",
        "items": [
            "Tracking stok bahan baku vs penggunaan aktual",
            "Deteksi variance: bahan terpakai vs yang seharusnya (standar resep)",
            "Alert stok menipis otomatis per item & cabang",
            "Analisis food cost variance dan potensi kebocoran",
            "Laporan penggunaan bahan per menu engineering",
        ],
        "kpi": ["Stok Aktual", "Food Cost Variance", "Item Kritis", "Efisiensi Penggunaan"],
    },
    {
        "icon": "👥",
        "title": "RFM & Segmentasi Pelanggan",
        "color": "#14b8a6",
        "bg": "#14b8a618",
        "border": "#14b8a640",
        "items": [
            "Segmentasi pelanggan: Recency, Frequency, Monetary (RFM)",
            "Identifikasi Champions, Loyal Customers, At-Risk, dan Lost",
            "Analisis Lifetime Value (LTV) per segmen pelanggan",
            "Retensi & churn rate estimasi berdasarkan pola kunjungan",
            "Rekomendasi campaign & reward per segmen",
        ],
        "kpi": ["Segmen Champions", "Churn Risk %", "LTV Rata-rata", "Frekuensi Kunjungan"],
    },
    {
        "icon": "🤖",
        "title": "Enterprise AI Analyst",
        "color": "#818cf8",
        "bg": "#818cf818",
        "border": "#818cf840",
        "items": [
            "Tanya jawab natural language langsung ke data bisnis Anda",
            "Auto-insight: AI mendeteksi anomali & peluang secara proaktif",
            "Narasi otomatis laporan eksekutif dalam Bahasa Indonesia",
            "Rekomendasi strategis berbasis konteks bisnis F&B Anda",
            "Integrasi Claude AI / GPT-4 untuk analisis mendalam",
        ],
        "kpi": ["AI Insights", "Auto-Narasi", "Anomali Terdeteksi", "Rekomendasi Aksi"],
    },
]


def _render_analytics_card(mod: dict):
    """Render satu kartu modul analitik."""
    items_html = "".join(
        f"<li style='margin:4px 0;color:#d1d5db;font-size:13px;line-height:1.5'>{it}</li>"
        for it in mod["items"]
    )
    kpis_html = "".join(
        f"<span style='background:{mod['color']}20;border:1px solid {mod['color']}50;"
        f"color:{mod['color']};border-radius:6px;padding:2px 10px;"
        f"font-size:11px;font-weight:700;white-space:nowrap'>{kpi}</span>"
        for kpi in mod["kpi"]
    )
    st.markdown(
        f"""<div style="
            background:{mod['bg']};
            border:1px solid {mod['border']};
            border-left:4px solid {mod['color']};
            border-radius:12px;
            padding:16px 20px;
            margin-bottom:12px;
            height:100%;">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
                <span style="font-size:1.6rem">{mod['icon']}</span>
                <span style="font-size:1.05rem;font-weight:800;color:{mod['color']}">{mod['title']}</span>
            </div>
            <ul style="margin:0 0 12px 0;padding-left:18px">
                {items_html}
            </ul>
            <div style="display:flex;flex-wrap:wrap;gap:6px">
                {kpis_html}
            </div>
        </div>""",
        unsafe_allow_html=True,
    )


def build_welcome_screen():
    # ── Hero Section ─────────────────────────────────────────────
    st.markdown(
        """<div style="
            background:linear-gradient(135deg,#0d1b2e,#1e3a5f,#0d1b2e);
            border:1px solid #1e3a5f;
            border-radius:16px;
            padding:36px 28px;
            text-align:center;
            margin-bottom:24px;
            box-shadow:0 4px 32px rgba(37,99,235,0.15);">
            <div style="font-size:12px;color:#60a5fa;text-transform:uppercase;
                        letter-spacing:.2em;font-weight:700;margin-bottom:10px">
                🚀 DATA DRIVEN F&B ANALYTICS PLATFORM
            </div>
            <h1 style="color:#f0f2f5;font-size:2.2rem;font-weight:900;margin:0 0 12px 0;
                       line-height:1.2">
                Ubah Data Restoran Anda<br>
                <span style="color:#34d399">Menjadi Keputusan Bisnis</span>
            </h1>
            <p style="color:#9ca3af;font-size:1.05rem;margin:0 auto;max-width:560px;line-height:1.6">
                Platform analitik end-to-end khusus industri F&B — dari penjualan hingga
                P&amp;L, dari forecast AI hingga segmentasi pelanggan, semuanya dalam
                satu dashboard terintegrasi.
            </p>
        </div>""",
        unsafe_allow_html=True,
    )

    # ── Lottie / Visual ───────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    _render_lottie_or_fallback(col1, "pic2.json", "lottie_1", "📊", "Analisis Penjualan")
    _render_lottie_or_fallback(col2, "pic1.json", "lottie_2", "💡", "Insight Bisnis")
    _render_lottie_or_fallback(col3, "pic3.json", "lottie_3", "🚀", "Optimasi Profit")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Langkah Mulai ─────────────────────────────────────────────
    st.markdown(
        "<h2 style='color:#f0f2f5;margin-bottom:16px'>⚡ Mulai dalam 3 Langkah</h2>",
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    steps = [
        ("1", "Buka Sidebar", "⬅️",
         "Klik tombol <b>&gt;</b> di pojok kiri atas untuk membuka panel upload & navigasi.",
         "#3b82f6"),
        ("2", "Upload File GMV", "📂",
         "Klik <b>'Upload Laporan GMV'</b> dan pilih file Excel. Opsional: tambah COGS, Waiter, Ulasan, Purchase, P&L.",
         "#10b981"),
        ("3", "Lihat Insight", "💡",
         "Dashboard memproses data secara otomatis dan menampilkan 16 modul analitik siap pakai.",
         "#f59e0b"),
    ]
    for col, (num, title, icon, desc, color) in zip([c1, c2, c3], steps):
        with col:
            st.markdown(
                f"""<div style="padding:20px;border:1px solid {color}40;border-top:4px solid {color};
                border-radius:12px;text-align:center;background:{color}08;height:100%">
                <div style="font-size:2.8rem;margin-bottom:8px">{icon}</div>
                <div style="font-size:0.75rem;color:{color};font-weight:700;text-transform:uppercase;
                            letter-spacing:.1em;margin-bottom:6px">Langkah {num}</div>
                <h3 style="color:#f0f2f5;margin:0 0 10px 0;font-size:1rem">{title}</h3>
                <p style="color:#9ca3af;font-size:0.88rem;line-height:1.5;margin:0">{desc}</p>
                </div>""",
                unsafe_allow_html=True,
            )

    st.info("**Tips:** Centang 'Gunakan data terakhir dari database' jika sudah pernah simpan data — tidak perlu upload ulang setiap sesi.", icon="ℹ️")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Ringkasan statistik modul ─────────────────────────────────
    st.markdown(
        """<div style="
            background:linear-gradient(90deg,#0d1b2e,#1e3a5f,#0d1b2e);
            border:1px solid #1e3a5f;border-radius:12px;
            padding:20px 28px;margin-bottom:24px;text-align:center">
            <div style="display:flex;flex-wrap:wrap;justify-content:center;gap:32px">
                <div>
                    <div style="font-size:2rem;font-weight:900;color:#34d399">16</div>
                    <div style="font-size:12px;color:#9ca3af">Modul Analitik</div>
                </div>
                <div>
                    <div style="font-size:2rem;font-weight:900;color:#60a5fa">80+</div>
                    <div style="font-size:12px;color:#9ca3af">Metrik & KPI</div>
                </div>
                <div>
                    <div style="font-size:2rem;font-weight:900;color:#f59e0b">5</div>
                    <div style="font-size:12px;color:#9ca3af">Jenis Data Input</div>
                </div>
                <div>
                    <div style="font-size:2rem;font-weight:900;color:#f43f5e">AI</div>
                    <div style="font-size:12px;color:#9ca3af">Powered Forecast & Chat</div>
                </div>
                <div>
                    <div style="font-size:2rem;font-weight:900;color:#a78bfa">∞</div>
                    <div style="font-size:12px;color:#9ca3af">Multi-Cabang</div>
                </div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    # ── Detail Modul Analitik ─────────────────────────────────────
    st.markdown(
        "<h2 style='color:#f0f2f5;margin-bottom:4px'>🔍 Detail Modul Analitik</h2>"
        "<p style='color:#6b7280;font-size:14px;margin-bottom:20px'>"
        "Setiap modul dirancang khusus untuk kebutuhan operasional dan strategis bisnis F&B.</p>",
        unsafe_allow_html=True,
    )

    # Render dalam 2 kolom
    left_mods  = _ANALYTICS_MODULES[::2]   # index genap
    right_mods = _ANALYTICS_MODULES[1::2]  # index ganjil

    col_l, col_r = st.columns(2)
    with col_l:
        for mod in left_mods:
            _render_analytics_card(mod)
    with col_r:
        for mod in right_mods:
            _render_analytics_card(mod)

    st.markdown("<br>", unsafe_allow_html=True)


def build_footer():
    st.markdown(
        """
        <div id="custom-footer" style="text-align:center;padding:20px;color:#6b7280;
             border-top:1px solid #1e3a5f;margin-top:16px;font-size:13px;">
            Data Driven F&B Analyst Dashboard © 2025 &nbsp;|&nbsp;
            Developer © ronihidayat &nbsp;|&nbsp;
            <a href="https://api.whatsapp.com/message/542JTLNDT3HCO1" target="_blank"
               style="color:#34d399;text-decoration:none">📞 Contact</a> &nbsp;|&nbsp;
            <a href="https://www.linkedin.com/in/roni-hidayat0692/" target="_blank"
               style="color:#60a5fa;text-decoration:none">LinkedIn</a> &nbsp;|&nbsp;
            <a href="https://github.com/RONI1920" target="_blank"
               style="color:#9ca3af;text-decoration:none">GitHub</a>
        </div>
        """,
        unsafe_allow_html=True,
    )
