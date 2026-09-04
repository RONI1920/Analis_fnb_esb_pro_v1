# data_loaders.py — Fungsi Pemuatan Data dari File Upload atau Database
#
# PERUBAHAN UTAMA:
#   - _detect_header_row(): auto-detect baris header berdasarkan kolom kunci
#   - _read_file_raw(): baca file ke DataFrame tanpa asumsi header
#   - Semua loader (GMV, COGS, Waiter, Purchase, P&L) pakai auto-detect
#   - Tidak ada lagi hardcode header=9, header=12, dst.

import re
import pandas as pd
import streamlit as st

from database import load_dataframe_from_db
from config import KALENDER_PATH


# ── FIX #007: File magic-byte validation ──────────────────────────
_XLSX_MAGIC = b"PK"  # ZIP / xlsx
_MAX_FILE_MB = 50

def _validate_file_magic(uploaded_file) -> tuple[bool, str]:
    """Reject files where magic bytes do not match claimed extension."""
    try:
        if uploaded_file.size > _MAX_FILE_MB * 1024 * 1024:
            return False, f"Ukuran file melebihi batas {_MAX_FILE_MB}MB"
        uploaded_file.seek(0)
        header = uploaded_file.read(8)
        uploaded_file.seek(0)
        name = uploaded_file.name.lower()
        if name.endswith((".xlsx", ".xlsm")):
            if header[:4] != _XLSX_MAGIC:
                return False, "File bukan format Excel yang valid (magic bytes salah)"
        elif name.endswith(".csv"):
            # CSV should be plain text — no null bytes
            uploaded_file.seek(0)
            sample = uploaded_file.read(512)
            uploaded_file.seek(0)
            if b"\x00" in sample:
                return False, "File CSV mengandung byte tidak valid"
        else:
            return False, "Format file tidak didukung. Gunakan .xlsx atau .csv"
        return True, ""
    except Exception:
        return False, "Gagal memvalidasi file"


# ──────────────────────────────────────────────────────────────────
# HELPERS: AUTO-DETECT HEADER
# ──────────────────────────────────────────────────────────────────

def _read_file_raw(uploaded_file, nrows=None) -> pd.DataFrame | None:
    """
    Baca file xlsx/csv tanpa header (header=None).
    Kembalikan DataFrame mentah atau None jika gagal.
    """
    try:
        name = uploaded_file.name.lower()
        if name.endswith(".xlsx") or name.endswith(".xlsm"):
            return pd.read_excel(
                uploaded_file, header=None, nrows=nrows, engine="openpyxl"
            )
        elif name.endswith(".csv"):
            return pd.read_csv(
                uploaded_file, header=None, nrows=nrows, encoding="latin1"
            )
        else:
            return None
    except Exception:
        return None


def _detect_header_row(uploaded_file, key_columns: list[str], max_scan: int = 30) -> int | None:
    """
    Scan baris pertama `max_scan` baris untuk menemukan baris header.

    Mencari baris yang mengandung SEMUA kata kunci dari `key_columns`
    (case-insensitive, partial match).

    Returns:
        int  → index baris header (0-based), siap dipakai sebagai `header=N` di pandas
        None → tidak ditemukan, fallback ke header=0
    """
    uploaded_file.seek(0)
    raw = _read_file_raw(uploaded_file, nrows=max_scan)
    uploaded_file.seek(0)

    if raw is None:
        return None

    key_lower = [k.lower() for k in key_columns]

    for idx, row in raw.iterrows():
        row_values = [str(v).lower() for v in row if pd.notna(v)]
        row_text   = " ".join(row_values)
        if all(any(key in cell for cell in row_values) or key in row_text for key in key_lower):
            return int(idx)

    return None


def _read_file_with_detected_header(
    uploaded_file,
    key_columns: list[str],
    fallback_header: int = 0,
    max_scan: int = 30,
) -> pd.DataFrame | None:
    """
    Baca file dengan header yang di-detect otomatis.
    Jika tidak ditemukan, pakai fallback_header.
    """
    header_row = _detect_header_row(uploaded_file, key_columns, max_scan)
    row = header_row if header_row is not None else fallback_header

    try:
        name = uploaded_file.name.lower()
        if name.endswith(".xlsx") or name.endswith(".xlsm"):
            return pd.read_excel(uploaded_file, header=row, engine="openpyxl")
        elif name.endswith(".csv"):
            return pd.read_csv(uploaded_file, header=row, encoding="latin1")
        else:
            return None
    except Exception:
        return None


def _extract_meta_from_raw(raw: pd.DataFrame, label: str, col: int = 1) -> str:
    """
    Cari nilai metadata (Company, Period, Branch) di kolom tertentu
    dengan cara mencari baris yang mengandung label (case-insensitive).
    Lebih robust daripada hardcode iloc[N, col].
    """
    label_lower = label.lower()
    for _, row in raw.iterrows():
        cell0 = str(row.iloc[0]).lower() if pd.notna(row.iloc[0]) else ""
        if label_lower in cell0:
            try:
                val = row.iloc[col]
                if pd.notna(val) and str(val).strip():
                    return str(val).strip()
            except IndexError:
                pass
    return "N/A"


# ──────────────────────────────────────────────────────────────────
# GMV
# ──────────────────────────────────────────────────────────────────

# Kolom kunci yang pasti ada di baris header GMV
_GMV_KEY_COLS = ["Sales Number", "Sales Date In", "Bill Number", "Menu Category"]


@st.cache_data
def load_data_gmv(uploaded_file, use_db=False):
    """Muat dan bersihkan data GMV — header row di-detect otomatis."""

    if use_db:
        with st.spinner("Memuat GMV dari database..."):
            numeric_config = {
                "Qty": "float",
                "Price (Net)": "float",
                "Service Charge": "float",
                "Tax": "float",
                "Total Nett Sales": "float",
                "Bill Discount": "float",
                "Total Gross Sales": "float",
                "Total After Bill Discount": "float",
                "Difference Price": "float",
                "Discount": "float",
            }
            df = load_dataframe_from_db(
                "gmv_data",
                date_cols=["Sales Date In", "Sales Date Out", "Order Time"],
                numeric_cols_config=numeric_config,
            )
            if df is None:
                return None, None, None, None
            return df, None, None, None

    if uploaded_file is None:
        return None, None, None, None

    company_name = period_str = branch_name_header = "N/A"

    # ── Baca metadata dari baris atas ────────────────────────────
    try:
        uploaded_file.seek(0)
        raw_meta = _read_file_raw(uploaded_file, nrows=30)
        if raw_meta is not None:
            company_name      = _extract_meta_from_raw(raw_meta, "PT.", col=0) \
                                or _extract_meta_from_raw(raw_meta, "company", col=1)
            # Fallback: ambil baris ke-2 col 0 (nama perusahaan biasanya di sini)
            if company_name == "N/A":
                try:
                    company_name = str(raw_meta.iloc[1, 0])
                except Exception:
                    pass
            period_str        = _extract_meta_from_raw(raw_meta, "period", col=1)
            branch_name_header = _extract_meta_from_raw(raw_meta, "branch", col=1)
    except Exception:
        pass

    # ── Baca data utama dengan header auto-detect ─────────────────
    uploaded_file.seek(0)
    df_data = _read_file_with_detected_header(
        uploaded_file,
        key_columns=_GMV_KEY_COLS,
        fallback_header=9,  # fallback ke nilai lama jika tidak terdeteksi
    )

    if df_data is None or df_data.empty:
        st.error("Gagal membaca data GMV. Pastikan format file benar.")
        return None, None, None, None

    df_data.columns = [str(col).strip().title() for col in df_data.columns]

    # Drop baris yang sepenuhnya kosong (sering ada di akhir file)
    df_data.dropna(how="all", inplace=True)

    numeric_cols = [
        "Qty", "Price (Net)", "Service Charge", "Tax",
        "Total Nett Sales", "Bill Discount", "Total Gross Sales",
        "Total After Bill Discount", "Difference Price", "Discount",
    ]
    for col in numeric_cols:
        if col in df_data.columns:
            df_data[col] = pd.to_numeric(df_data[col], errors="coerce").fillna(0)

    for col in ["Sales Date In", "Sales Date Out", "Order Time"]:
        if col in df_data.columns:
            df_data[col] = pd.to_datetime(df_data[col], errors="coerce")

    df_data["Company"] = company_name
    df_data["Period"]  = period_str

    # Deteksi kolom Branch
    found_branch_col = next(
        (c for c in df_data.columns if "Branch" in c or "Outlet" in c), None
    )
    if found_branch_col:
        if found_branch_col != "Branch":
            df_data.rename(columns={found_branch_col: "Branch"}, inplace=True)
        df_data["Branch"] = df_data["Branch"].fillna(branch_name_header)
    else:
        df_data["Branch"] = branch_name_header

    # FIX BUG: dropna di sini hanya untuk TAMPILAN dashboard.
    # Baris tanpa Bill Number atau Sales Date In dihapus dari tampilan
    # karena tidak bisa dianalisis dengan benar.
    # NAMUN: saat SAVE ke DB, app.py memanggil loader ini SEBELUM filter diterapkan.
    # Selisih jumlah baris antara file dan DB bisa disebabkan oleh baris yang null di sini.
    # Ini WAJAR dan BENAR — data tidak valid tidak seharusnya masuk DB.
    #
    # CATATAN: jika Anda melihat perbedaan jumlah baris antara file dan DB,
    # cek berapa baris yang tidak punya Bill Number atau Sales Date In di file asli.
    if "Bill Number" in df_data.columns and "Sales Date In" in df_data.columns:
        rows_before_dropna = len(df_data)
        df_data.dropna(subset=["Bill Number", "Sales Date In"], inplace=True)
        rows_dropped = rows_before_dropna - len(df_data)
        if rows_dropped > 0:
            import warnings
            warnings.warn(
                f"load_data_gmv: {rows_dropped} baris dihapus karena "
                f"Bill Number atau Sales Date In kosong (null). "
                f"Ini NORMAL jika ada baris summary/total di akhir file.",
                stacklevel=2
            )

    return df_data, company_name, period_str, branch_name_header


# ──────────────────────────────────────────────────────────────────
# COGS
# ──────────────────────────────────────────────────────────────────

_COGS_KEY_COLS = ["Menu", "Sales Date", "COGS", "Harga Jual"]


@st.cache_data
def load_cogs_data(uploaded_file, use_db=False):
    """Muat dan bersihkan data COGS — header row di-detect otomatis."""

    if use_db:
        with st.spinner("Memuat COGS dari database..."):
            df = load_dataframe_from_db(
                "cogs_data",
                date_cols=["Sales Date"],
                numeric_cols_config={
                    "Harga Jual": "float",
                    "COGS": "float",
                    "Qty": "float",
                    "Total": "float",
                },
            )
            return df

    if uploaded_file is None:
        return None

    uploaded_file.seek(0)
    df = _read_file_with_detected_header(
        uploaded_file,
        key_columns=_COGS_KEY_COLS,
        fallback_header=12,
    )

    if df is None:
        st.error("Format file COGS tidak didukung.")
        return None

    df.rename(columns={"Price": "Harga Jual", "COGS Total": "COGS"}, inplace=True)

    required = ["Menu", "Harga Jual", "COGS", "Qty", "Total", "Sales Date"]
    missing  = [c for c in required if c not in df.columns]
    if missing:
        st.error(f"File COGS kekurangan kolom: {missing}")
        return None

    df["Menu"] = df["Menu"].astype(str)
    for col in ["Harga Jual", "COGS", "Qty", "Total"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["Sales Date"] = pd.to_datetime(df["Sales Date"], errors="coerce")
    df.dropna(how="all", inplace=True)

    if "Branch" in df.columns:
        df["Branch"] = df["Branch"].astype(str).str.strip().str.title()

    return df


# ──────────────────────────────────────────────────────────────────
# WAITER
# ──────────────────────────────────────────────────────────────────

_WAITER_KEY_COLS = ["Bill Number", "Waiter", "Order Time", "Total After Bill Discount"]


@st.cache_data
def load_data_waiter(uploaded_file, use_db=False):
    """Muat dan bersihkan data Waiter — header row di-detect otomatis."""

    if use_db:
        with st.spinner("Memuat Waiter dari database..."):
            df = load_dataframe_from_db(
                "waiter_data",
                date_cols=["Order Time"],
                numeric_cols_config={"Total After Bill Discount": "float"},
            )
            return df

    if uploaded_file is None:
        return None

    uploaded_file.seek(0)
    df = _read_file_with_detected_header(
        uploaded_file,
        key_columns=_WAITER_KEY_COLS,
        fallback_header=11,
    )

    if df is None:
        st.error("Format file Waiter tidak didukung.")
        return None

    required = ["Bill Number", "Waiter", "Order Time", "Total After Bill Discount"]
    if not all(c in df.columns for c in required):
        st.error(f"File Waiter harus memiliki kolom: {required}")
        return None

    df["Order Time"] = pd.to_datetime(df["Order Time"], errors="coerce")
    df["Total After Bill Discount"] = pd.to_numeric(
        df["Total After Bill Discount"], errors="coerce"
    ).fillna(0)
    df.dropna(subset=["Bill Number", "Order Time"], inplace=True)
    df.dropna(how="all", inplace=True)

    if "Branch" in df.columns:
        df["Branch"] = df["Branch"].astype(str).str.strip().str.title()

    return df


# ──────────────────────────────────────────────────────────────────
# ULASAN
# ──────────────────────────────────────────────────────────────────

@st.cache_data
def load_data_ulasan(uploaded_file, use_db=False):
    """Muat dan bersihkan data Ulasan Pelanggan."""

    if use_db:
        with st.spinner("Memuat Ulasan dari database..."):
            df = load_dataframe_from_db(
                "ulasan_data",
                numeric_cols_config={"Rating_Clean": "int"},
            )
            return df

    if uploaded_file is None:
        return None

    # Auto-detect header — konsisten dengan loader lain
    uploaded_file.seek(0)
    df = _read_file_with_detected_header(
        uploaded_file,
        key_columns=["Rating", "Ulasan"],
        fallback_header=0,
    )

    if df is None or "Rating" not in df.columns or "Ulasan" not in df.columns:
        st.error("File Ulasan harus memiliki kolom 'Rating' dan 'Ulasan'.")
        return None

    df["Rating_Clean"] = (
        df["Rating"].astype(str).str.extract(r"(\d+)").fillna(0).astype(int)
    )
    df.dropna(subset=["Ulasan"], inplace=True)
    df = df[df["Rating_Clean"] > 0]
    df["Ulasan"] = df["Ulasan"].astype(str)
    return df


# ──────────────────────────────────────────────────────────────────
# PURCHASE
# ──────────────────────────────────────────────────────────────────

_PURCHASE_KEY_COLS = ["Purchase Number", "Purchase Date", "Supplier Name", "Product Name"]


@st.cache_data
def load_data_purchase(uploaded_file, use_db=False):
    """Muat dan bersihkan data Laporan Pembelian — header row di-detect otomatis."""

    if use_db:
        with st.spinner("Memuat data Pembelian dari database..."):
            df = load_dataframe_from_db(
                "purchase_data",
                date_cols=["Purchase Date", "Required Date"],
                numeric_cols_config={
                    "PO Qty": "float",
                    "Receipt Qty": "float",
                    "Pricelist Price": "float",
                    "Price": "float",
                    "Discount": "float",
                    "VAT": "float",
                    "Total": "float",
                },
            )
            return df

    if uploaded_file is None:
        return None

    uploaded_file.seek(0)
    df = _read_file_with_detected_header(
        uploaded_file,
        key_columns=_PURCHASE_KEY_COLS,
        fallback_header=11,
    )

    if df is None:
        st.error("Format file Pembelian tidak didukung.")
        return None

    numeric_cols = [
        "PO Qty", "Receipt Qty", "Pricelist Price",
        "Price", "Discount", "VAT", "Total",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        elif col == "Total":
            st.error("Kolom 'Total' wajib ada di file Pembelian.")
            return None

    for col in ["Purchase Date", "Required Date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    required_text = ["Category", "Product Name", "Supplier Name"]
    if not all(c in df.columns for c in required_text):
        st.error(f"File Pembelian kekurangan kolom: {required_text}")
        return None

    df.dropna(subset=["Purchase Number", "Purchase Date"], inplace=True)
    df.dropna(how="all", inplace=True)

    if "Branch" in df.columns:
        df["Branch"] = df["Branch"].astype(str).str.strip().str.title()

    return df


# ──────────────────────────────────────────────────────────────────
# P&L
# ──────────────────────────────────────────────────────────────────

_PL_KEY_COLS = ["Account", "Description", "January"]


@st.cache_data
def load_pl_data(uploaded_file, use_db=False):
    """Muat dan bersihkan data Profit & Loss — header row di-detect otomatis."""

    if use_db:
        with st.spinner("Memuat P&L dari database..."):
            return load_dataframe_from_db(
                "pl_data",
                date_cols=["Date"],
                numeric_cols_config={"Value": "float"},
            )

    if uploaded_file is None:
        return None

    VALID_MONTHS = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]

    try:
        # ── Cari tahun dari metadata di atas header ───────────────
        period_year = pd.Timestamp.now().year
        uploaded_file.seek(0)
        raw_meta = _read_file_raw(uploaded_file, nrows=20)
        if raw_meta is not None:
            for _, row in raw_meta.iterrows():
                row_str = row.astype(str).str.cat(sep=" ")
                if "Period" in row_str or "period" in row_str:
                    found = re.findall(r"\b20\d{2}\b", row_str)
                    if found:
                        period_year = int(found[0])
                        break

        # ── Baca data dengan header auto-detect ───────────────────
        uploaded_file.seek(0)
        df = _read_file_with_detected_header(
            uploaded_file,
            key_columns=_PL_KEY_COLS,
            fallback_header=13,
        )

        if df is None or df.empty:
            st.error("Gagal membaca data P&L.")
            return None

        df.dropna(how="all", inplace=True)

        id_vars    = [c for c in df.columns if "Account" in str(c) or "Description" in str(c)]
        value_vars = [
            c for c in df.columns
            if c not in id_vars and any(m in str(c) for m in VALID_MONTHS)
        ]

        if not value_vars:
            st.error("Tidak ditemukan kolom bulan di file P&L.")
            return None

        df_melted = df.melt(
            id_vars=id_vars,
            value_vars=value_vars,
            var_name="Raw_Column",
            value_name="Value",
        )

        def parse_column(row):
            raw          = str(row["Raw_Column"])
            is_last_year = "Last Year" in raw
            month_num, month_name = 1, "Unknown"
            for i, m in enumerate(VALID_MONTHS):
                if m in raw:
                    month_num, month_name = i + 1, m
                    break
            year = period_year - 1 if is_last_year else period_year
            try:
                date_val = pd.Timestamp(year=year, month=month_num, day=1)
            except Exception:
                date_val = pd.Timestamp.now()
            branch = raw.split("(")[0].strip() if "(" in raw else "All Branch"
            return pd.Series([date_val, month_name, "Last Year" if is_last_year else "Current Year", branch])

        df_melted[["Date", "Month_Name", "Year_Type", "Branch"]] = df_melted.apply(
            parse_column, axis=1
        )
        df_melted["Value"] = pd.to_numeric(df_melted["Value"], errors="coerce").fillna(0)

        def categorize_account(code):
            code_clean = str(code).replace(" ", "").replace(".", "").replace("-", "").strip()
            if code_clean.startswith("4"):
                return "Revenue"
            elif code_clean.startswith("5"):
                return "COGS"
            elif any(code_clean.startswith(d) for d in ["6", "7", "8"]):
                return "Expense"
            return "Other"

        df_melted["Category"] = df_melted["Account"].apply(categorize_account)
        return df_melted[df_melted["Value"] != 0]

    except Exception as e:
        st.error(f"Gagal memproses file P&L: {e}")
        return None


# ──────────────────────────────────────────────────────────────────
# MOKA POS
# ──────────────────────────────────────────────────────────────────
#
# CATATAN DEVELOPER:
#   Loader ini adalah SKELETON — mapping kolom belum final karena
#   format export Moka belum tersedia saat ini.
#
#   CARA MENGEMBANGKAN NANTI:
#   1. Export file dari dashboard Moka (Sales Report / Transaction Report)
#   2. Lihat nama kolom aslinya
#   3. Update _MOKA_COLUMN_MAP di bawah sesuai kolom aktual
#   4. Update _MOKA_KEY_COLS sesuai 3-4 kolom yang pasti ada di header
#   5. Sisanya (cleaning, cast tipe, save ke DB) sudah siap
#
#   OUTPUT WAJIB: DataFrame dengan schema ESB (kolom sama persis dengan
#   load_data_gmv) agar semua tab downstream tidak perlu diubah.
# ──────────────────────────────────────────────────────────────────

# Kolom kunci untuk auto-detect header baris di file Moka
# UPDATE ini setelah dapat contoh file Moka asli
_MOKA_KEY_COLS = ["Transaction Date", "Invoice No", "Item Name", "Net Sales"]

# Mapping: nama kolom Moka → nama kolom ESB (target schema)
# UPDATE nilai sebelah kiri (key) setelah dapat contoh file Moka asli
_MOKA_COLUMN_MAP = {
    # ── Kolom Moka          : Kolom ESB (jangan ubah nilai kanan) ──
    "Transaction Date"      : "Sales Date In",
    "Invoice No"            : "Bill Number",
    "Payment No"            : "Sales Number",
    "Item Name"             : "Menu",
    "Category Name"         : "Menu Category",
    "Quantity"              : "Qty",
    "Net Sales"             : "Total Nett Sales",
    "Gross Sales"           : "Total Gross Sales",
    "Discount Amount"       : "Discount",
    "Payment Type Label"    : "Payment Method",
    "Tax Amount"            : "Tax",
    "Outlet Name"           : "Branch",
    # Tambahkan mapping baru di sini jika ada kolom Moka lain yang perlu
}

# Kolom numerik yang harus di-cast ke float setelah rename
_MOKA_NUMERIC_COLS = [
    "Qty", "Total Nett Sales", "Total Gross Sales",
    "Discount", "Tax", "Service Charge",
]


@st.cache_data
def load_data_gmv_moka(uploaded_file):
    """
    Muat dan bersihkan data dari export Moka POS.

    Output: DataFrame dengan schema ESB (kolom sama seperti load_data_gmv)
    sehingga semua tab analitik downstream tidak perlu diubah.

    File yang didukung: .xlsx dan .csv dari dashboard Moka.
    """
    if uploaded_file is None:
        return None, None, None, None

    # ── Validasi magic bytes ──────────────────────────────────────
    ok, err = _validate_file_magic(uploaded_file)
    if not ok:
        st.error(f"❌ File Moka tidak valid: {err}")
        return None, None, None, None

    # ── Baca dengan auto-detect header ───────────────────────────
    uploaded_file.seek(0)
    df = _read_file_with_detected_header(
        uploaded_file,
        key_columns=_MOKA_KEY_COLS,
        fallback_header=0,
    )

    if df is None or df.empty:
        st.error(
            "❌ Gagal membaca file Moka. "
            "Pastikan file adalah export Sales Report / Transaction Report dari dashboard Moka."
        )
        return None, None, None, None

    # ── Bersihkan nama kolom ──────────────────────────────────────
    df.columns = [str(c).strip() for c in df.columns]
    df.dropna(how="all", inplace=True)

    # ── Rename kolom Moka → schema ESB ───────────────────────────
    df.rename(columns=_MOKA_COLUMN_MAP, inplace=True)

    # ── Cast kolom numerik ────────────────────────────────────────
    for col in _MOKA_NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # ── Cast kolom tanggal ────────────────────────────────────────
    if "Sales Date In" in df.columns:
        df["Sales Date In"] = pd.to_datetime(df["Sales Date In"], errors="coerce")

    # ── Pastikan kolom wajib ada (fallback kosong jika tidak ada) ─
    _REQUIRED_COLS = {
        "Sales Date In"    : pd.NaT,
        "Bill Number"      : "",
        "Menu"             : "",
        "Menu Category"    : "",
        "Qty"              : 0.0,
        "Total Nett Sales" : 0.0,
        "Total Gross Sales": 0.0,
        "Discount"         : 0.0,
        "Tax"              : 0.0,
        "Payment Method"   : "",
        "Branch"           : "Moka",
    }
    for col, default in _REQUIRED_COLS.items():
        if col not in df.columns:
            df[col] = default

    # ── Drop baris tanpa tanggal atau bill number ─────────────────
    df.dropna(subset=["Sales Date In", "Bill Number"], inplace=True)
    df = df[df["Bill Number"].astype(str).str.strip() != ""]

    if df.empty:
        st.error(
            "❌ Data Moka kosong setelah cleaning. "
            "Periksa apakah kolom 'Transaction Date' dan 'Invoice No' terisi di file Anda."
        )
        return None, None, None, None

    # ── Ekstrak metadata ──────────────────────────────────────────
    company_name   = "Moka POS"
    period_str     = (
        f"{df['Sales Date In'].min().strftime('%d/%m/%Y')} – "
        f"{df['Sales Date In'].max().strftime('%d/%m/%Y')}"
        if not df["Sales Date In"].isna().all() else "N/A"
    )
    branch_name    = df["Branch"].iloc[0] if "Branch" in df.columns else "N/A"

    # Return tuple sama persis dengan load_data_gmv agar app.py tidak perlu ubah
    return df, company_name, period_str, branch_name


# ──────────────────────────────────────────────────────────────────
# KALENDER
# ──────────────────────────────────────────────────────────────────

@st.cache_data
def load_kalender_data(file_path: str = KALENDER_PATH):
    """Muat data kalender event dari CSV."""
    try:
        df = pd.read_csv(file_path)
        df["Tanggal"] = pd.to_datetime(df["Tanggal"]).dt.date
        return df
    except FileNotFoundError:
        st.error(f"File kalender tidak ditemukan: '{file_path}'")
        return None
    except Exception as e:
        st.error(f"Error membaca kalender: {e}")
        return None
