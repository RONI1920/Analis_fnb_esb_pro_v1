# analytics/ulasan_analysis.py — Analisis Ulasan Mendalam

import re
from collections import Counter

import pandas as pd
import streamlit as st


# ── Keyword Dictionary Lengkap ─────────────────────────────────────────────────
KEYWORD_DICT = {
    "Makanan": [
        "enak", "lezat", "porsi", "hambar", "asin", "dingin", "basi", "mantap",
        "nikmat", "segar", "rasanya", "rasa", "makanan", "makanannya", "menu",
        "kakigori", "dessert", "dessertnya", "toast", "minuman", "manis",
        "gurih", "sedap", "yummy", "delicious", "fresh",
    ],
    "Pelayanan": [
        "ramah", "cepat", "lama", "jutek", "sopan", "membantu", "lambat",
        "pelayanan", "pelayanannya", "staff", "waiter", "waitress", "service",
        "sigap", "profesional", "responsif", "tanggap", "baik", "helpful",
        "friendly", "slow", "fast",
    ],
    "Suasana": [
        "nyaman", "bersih", "kotor", "berisik", "adem", "panas", "cozy",
        "tempat", "suasana", "tempatnya", "unik", "lucu", "keren", "bagus",
        "instagramable", "foto", "interior", "dekorasi", "cantik", "aesthetic",
        "recommended", "recommend",
    ],
    "Harga": [
        "murah", "mahal", "worth", "promo", "diskon", "terjangkau", "harga",
        "harganya", "worth it", "overpriced", "pricey", "affordable", "budget",
        "sesuai", "sepadan",
    ],
    "Antrian & Waktu": [
        "antri", "antrian", "tunggu", "nunggu", "lama", "cepat", "pesanan",
        "order", "waiting", "queue", "menit", "jam",
    ],
    "Kebersihan": [
        "bersih", "kotor", "jorok", "hygienis", "higienis", "rapih", "rapi",
        "clean", "dirty", "kumuh",
    ],
}

SENTIMEN_POS = {
    "enak", "lezat", "mantap", "nikmat", "segar", "ramah", "cepat", "sopan",
    "membantu", "nyaman", "bersih", "unik", "lucu", "keren", "bagus",
    "worth", "terjangkau", "murah", "recommended", "recommend", "baik",
    "helpful", "friendly", "fast", "yummy", "delicious", "fresh", "cozy",
    "sigap", "profesional", "cantik", "aesthetic", "instagramable", "rapi", "rapih",
}
SENTIMEN_NEG = {
    "hambar", "asin", "basi", "lama", "jutek", "lambat", "kotor", "berisik",
    "panas", "mahal", "overpriced", "pricey", "jorok", "kotor", "kumuh",
    "dirty", "slow", "antri", "tunggu", "nunggu", "kecewa", "buruk", "jelek",
    "mengecewakan", "tidak", "kurang",
}


@st.cache_data
def prepare_ulasan(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Bersihkan dan enriched DataFrame ulasan."""
    df = df_raw.copy()
    df["Rating_Clean"] = (
        df["Rating"].astype(str).str.extract(r"(\d+)").fillna(0).astype(int)
    )
    df = df[df["Rating_Clean"] > 0].copy()
    df["Ulasan_Clean"] = df["Ulasan"].astype(str).str.replace(r"Lainnya$", "", regex=True).str.strip()

    df["NPS_Category"] = df["Rating_Clean"].apply(
        lambda r: "Promoter" if r >= 5 else ("Passive" if r == 4 else "Detractor")
    )
    df["Sentimen"] = df["Rating_Clean"].apply(
        lambda r: "Positif" if r >= 4 else ("Netral" if r == 3 else "Negatif")
    )
    df["Topik"] = df["Ulasan_Clean"].apply(_find_topics)
    df["Kata_Positif"] = df["Ulasan_Clean"].apply(_count_pos_words)
    df["Kata_Negatif"] = df["Ulasan_Clean"].apply(_count_neg_words)
    df["Panjang_Ulasan"] = df["Ulasan_Clean"].str.len()
    return df


def _find_topics(text: str) -> str:
    text_lower = str(text).lower()
    found = []
    for topic, keys in KEYWORD_DICT.items():
        for k in keys:
            if re.search(r"\b" + re.escape(k) + r"\b", text_lower):
                found.append(topic)
                break
    return ", ".join(found) if found else "Lainnya"


def _count_pos_words(text: str) -> int:
    words = set(re.findall(r"\b\w+\b", str(text).lower()))
    return len(words & SENTIMEN_POS)


def _count_neg_words(text: str) -> int:
    words = set(re.findall(r"\b\w+\b", str(text).lower()))
    return len(words & SENTIMEN_NEG)


@st.cache_data
def get_word_frequency(df: pd.DataFrame, sentimen: str = "semua", top_n: int = 20) -> pd.DataFrame:
    """Frekuensi kata per sentimen."""
    STOPWORDS = {
        "yang", "dan", "di", "ke", "dari", "ini", "itu", "dengan", "untuk",
        "ada", "bisa", "juga", "tapi", "karena", "saya", "kami", "kita",
        "mereka", "lebih", "sangat", "banget", "sudah", "sudah", "belum",
        "tidak", "buat", "sama", "semua", "lagi", "saat", "banyak", "sini",
        "sana", "nya", "pun", "aja", "nih", "loh", "deh", "yah", "gak",
        "ngga", "nggak", "ga", "udah", "udh", "yg", "dgn", "utk", "krn",
        "lainnya", "atau", "kalau", "kalo", "kayak", "kaya", "emang",
        "memang", "meski", "meskipun", "seperti", "spt", "jadi", "sdh",
    }
    if sentimen == "Positif":
        texts = df[df["Sentimen"] == "Positif"]["Ulasan_Clean"]
    elif sentimen == "Negatif":
        texts = df[df["Sentimen"] == "Negatif"]["Ulasan_Clean"]
    else:
        texts = df["Ulasan_Clean"]

    all_words = []
    for text in texts.astype(str):
        words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
        all_words.extend([w for w in words if w not in STOPWORDS])

    freq = Counter(all_words).most_common(top_n)
    return pd.DataFrame(freq, columns=["Kata", "Frekuensi"])


@st.cache_data
def get_topic_sentiment_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Breakdown topik vs sentimen."""
    rows = []
    for _, row in df.iterrows():
        topics = [t.strip() for t in str(row["Topik"]).split(",") if t.strip()]
        for topic in topics:
            rows.append({"Topik": topic, "Sentimen": row["Sentimen"], "Rating": row["Rating_Clean"]})
    df_long = pd.DataFrame(rows)
    return (
        df_long.groupby(["Topik", "Sentimen"])
        .size()
        .reset_index(name="Jumlah")
        .sort_values("Jumlah", ascending=False)
    )


@st.cache_data
def get_rating_distribution(df: pd.DataFrame) -> pd.DataFrame:
    dist = df["Rating_Clean"].value_counts().reset_index()
    dist.columns = ["Rating", "Jumlah"]
    dist = dist.sort_values("Rating")
    dist["Persen"] = (dist["Jumlah"] / dist["Jumlah"].sum() * 100).round(1)
    return dist


@st.cache_data
def get_nps_breakdown(df: pd.DataFrame) -> dict:
    total = len(df)
    promoters   = (df["NPS_Category"] == "Promoter").sum()
    passives    = (df["NPS_Category"] == "Passive").sum()
    detractors  = (df["NPS_Category"] == "Detractor").sum()
    nps = (promoters - detractors) / total * 100 if total > 0 else 0
    return {
        "total": total,
        "promoters": promoters, "promoters_pct": promoters / total * 100,
        "passives":  passives,  "passives_pct":  passives  / total * 100,
        "detractors": detractors, "detractors_pct": detractors / total * 100,
        "nps": nps,
        "avg_rating": df["Rating_Clean"].mean(),
    }


@st.cache_data
def get_notable_reviews(df: pd.DataFrame, n: int = 5) -> dict:
    """Ambil ulasan paling informatif per sentimen."""
    pos = df[df["Sentimen"] == "Positif"].nlargest(n, "Panjang_Ulasan")[["Nama", "Rating_Clean", "Ulasan_Clean"]]
    neg = df[df["Sentimen"] == "Negatif"].nlargest(n, "Panjang_Ulasan")[["Nama", "Rating_Clean", "Ulasan_Clean"]]
    return {"positif": pos, "negatif": neg}