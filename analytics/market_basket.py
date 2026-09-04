# analytics/market_basket.py — Market Basket Analysis (Apriori)

import pandas as pd
import streamlit as st
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder

from config import FILTER_REGEX_PACKAGE

ADDON_KEYWORDS = [
    "UPGRADE", "ADDITIONAL", "ADD ON", "ADD-ON",
    "REFILL", "OCHA", "MINERAL WATER",
]


@st.cache_data
def get_market_basket_rules(df: pd.DataFrame, min_support_threshold: float) -> pd.DataFrame:
    """
    Menjalankan Market Basket Analysis (Apriori) pada data GMV.
    Returns DataFrame berisi association rules dengan expected_value.
    """
    try:
        df_filtered = df[
            ~df["Menu"].str.contains(FILTER_REGEX_PACKAGE, na=False, case=False, regex=True)
        ]

        menu_prices = df_filtered.groupby("Menu")["Price (Net)"].mean()

        # Filter menu yang muncul lebih dari sekali
        menu_counts = df_filtered["Menu"].value_counts()
        relevant_menus = menu_counts[menu_counts > 1].index
        df_filtered = df_filtered[df_filtered["Menu"].isin(relevant_menus)]

        transactions_list = (
            df_filtered.groupby("Bill Number")["Menu"].apply(list).values.tolist()
        )
        if not transactions_list:
            return pd.DataFrame()

        te = TransactionEncoder()
        te_ary = te.fit(transactions_list).transform(transactions_list)
        df_encoded = pd.DataFrame(te_ary, columns=te.columns_)

        frequent_itemsets = apriori(
            df_encoded, min_support=min_support_threshold, use_colnames=True
        )
        if frequent_itemsets.empty:
            return pd.DataFrame()

        rules = association_rules(frequent_itemsets, metric="lift", min_threshold=1.0)
        if rules.empty:
            return pd.DataFrame()

        # Filter add-on dari antecedents
        def _is_addon(item_set):
            for item in item_set:
                if any(kw in str(item).upper() for kw in ADDON_KEYWORDS):
                    return True
            return False

        rules = rules[~rules["antecedents"].apply(_is_addon)]

        # Hanya aturan 1 item antecedent dan 1 item consequent
        rules = rules[rules["antecedents"].apply(len) == 1]
        rules = rules[rules["consequents"].apply(len) == 1]

        if rules.empty:
            return pd.DataFrame()

        rules["consequents_str"] = rules["consequents"].apply(lambda x: next(iter(x)))
        rules = rules.merge(
            menu_prices.rename("consequent_price"),
            left_on="consequents_str", right_index=True, how="left",
        )
        rules["consequent_price"] = rules["consequent_price"].fillna(0)
        rules["expected_value"] = rules["confidence"] * rules["consequent_price"]

        rules["antecedents"] = rules["antecedents"].apply(lambda x: ", ".join(list(x)))
        rules["consequents"] = rules["consequents"].apply(lambda x: ", ".join(list(x)))

        return rules[
            ["antecedents", "consequents", "confidence", "lift",
             "consequent_price", "expected_value"]
        ].sort_values("expected_value", ascending=False)

    except Exception as e:
        st.error(f"Gagal menjalankan Market Basket Analysis: {e}")
        return pd.DataFrame()
