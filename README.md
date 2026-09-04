# 📊 FnB Analyst Dashboard

Dashboard analisis data bisnis F&B berbasis Streamlit.

---

## 🗂️ Struktur Project

```
📁 project/
├── app.py                    # ✅ Entry point — jalankan ini
├── config.py                 # Konstanta & konfigurasi global
├── database.py               # Koneksi & operasi SQLite
├── data_loaders.py           # Fungsi load_data_* (GMV, COGS, dll)
├── formatters.py             # format_rupiah, format_persen, dll
├── requirements.txt
│
├── auth.py                   # (sudah ada) Autentikasi user
├── admin_panel.py            # (sudah ada) Panel admin
│
├── analytics/                # 🔬 Logika kalkulasi & analisis
│   ├── gmv.py                # KPI penjualan, menu, operasional
│   ├── cogs.py               # Analisis profit & margin
│   ├── hr.py                 # Waiter, fraud detection, musiman
│   ├── purchase.py           # Analisis biaya pembelian
│   ├── forecast.py           # Prophet forecasting
│   └── market_basket.py      # Apriori / MBA
│
├── insights/
│   └── generators.py         # Semua generate_*_insights()
│
└── ui/                       # 🖥️ Semua kode tampilan
    ├── charts.py             # create_horizontal/vertical_bar_chart
    ├── sidebar.py            # build_sidebar, build_global_filters
    ├── welcome.py            # build_welcome_screen, build_footer
    └── tabs/
        ├── tab1_sales.py     # 📊 Penjualan GMV
        ├── tab2_cogs.py      # 💰 COGS & Profit
        ├── tab3_hr.py        # 🧑‍🍳 SDM & Waktu + Fraud
        ├── tab4_comparison.py# ⚖️ A/B Comparison
        ├── tab5_forecast.py  # 🔮 Forecast AI
        ├── tab6_target.py    # 🎯 Pencapaian Target
        ├── tab7_ulasan.py    # ❤️ Ulasan Pelanggan
        ├── tab8_purchase.py  # 🛒 Laporan Pembelian
        ├── tab9_rekomendasi.py # 💡 Market Basket
        ├── tab10_promo.py    # 💸 Simulator Promo
        ├── tab11_musiman.py  # ✨ Weekend vs Libur
        ├── tab12_lab.py      # 🧪 Lab Strategi
        └── tab13_pl.py       # 📉 P&L Dashboard
```

---

## 🚀 Cara Menjalankan

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## 🔧 Cara Maintenance

| Mau ubah apa? | Edit file ini |
|---|---|
| Tambah/ubah analisis GMV | `analytics/gmv.py` |
| Ubah tampilan Tab Penjualan | `ui/tabs/tab1_sales.py` |
| Ubah teks insight otomatis | `insights/generators.py` |
| Ubah skema database | `database.py` → `init_db()` |
| Tambah tab baru | Buat `ui/tabs/tab_baru.py`, import di `app.py` |
| Ubah warna/style grafik | `ui/charts.py` |
| Ubah filter global | `ui/sidebar.py` → `build_global_filters()` |

---

## 📁 File Pendukung Lainnya

- `style.css` — CSS kustom (opsional)
- `pic1.json`, `pic2.json`, `pic3.json` — Animasi Lottie untuk welcome screen
- `kalender/kalender_event1.csv` — Data kalender libur nasional
