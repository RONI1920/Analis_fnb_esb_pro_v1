# ui/tabs/tab10_promo.py — Tab 10: Analisis & Simulator Profitabilitas Promo

import pandas as pd
import streamlit as st

from formatters import format_rupiah


def build_tab10_promo(filtered_gmv, filtered_cogs):
    st.header("💸 Analisis & Simulator Profitabilitas Promo")
    st.info("Simulasikan profit dari skenario diskon atau promo paket.")

    if filtered_gmv is None or filtered_cogs is None:
        st.error("Simulator Promo memerlukan File 1 (GMV) dan File 2 (COGS) sekaligus.")
        return

    # ── Siapkan Data Harga & COGS ──────────────────────────
    @st.cache_data
    def _get_prices(df_gmv):
        col = "Price (Pricelist)" if "Price (Pricelist)" in df_gmv.columns else "Price (Net)"
        valid = df_gmv[df_gmv[col] > 0]
        prices = valid.groupby("Menu")[col].mean().reset_index()
        prices.rename(columns={col: "Harga Jual"}, inplace=True)
        return prices

    @st.cache_data
    def _get_cogs(df_cogs):
        valid = df_cogs[df_cogs["COGS"] > 0]
        return valid.groupby("Menu")["COGS"].mean().reset_index()

    with st.spinner("Menggabungkan data Harga dan COGS..."):
        prices_df = _get_prices(filtered_gmv)
        cogs_df = _get_cogs(filtered_cogs)
        profit_df = pd.merge(prices_df, cogs_df, on="Menu", how="inner")

    if profit_df.empty:
        st.error("Tidak ada menu yang nama-nya cocok antara GMV dan COGS.")
        return

    profit_df["Margin (Rp)"] = profit_df["Harga Jual"] - profit_df["COGS"]
    menu_list = profit_df[profit_df["Harga Jual"] > 0]["Menu"].unique()

    if len(menu_list) == 0:
        st.warning("Tidak ada menu valid untuk dianalisis.")
        return

    st.markdown("---")

    # ── Skenario 1: Diskon Menu Tunggal ────────────────────
    st.subheader("Scenario 1: Diskon Menu Tunggal")

    s1c1, s1c2 = st.columns([2, 1])
    with s1c1:
        sel_menu = st.selectbox("Pilih Menu:", menu_list, key="promo_s1_menu")
    with s1c2:
        disc_pct = st.slider("Diskon (%):", 0, 100, 15, key="promo_s1_disc")
    qty_s1 = st.number_input("Target Kuantitas:", min_value=1, value=50, step=10, key="promo_s1_qty")

    if sel_menu:
        try:
            row = profit_df[profit_df["Menu"] == sel_menu].iloc[0]
            orig_price = row["Harga Jual"]
            cogs = row["COGS"]
            orig_margin = row["Margin (Rp)"]
            new_price = orig_price * (1 - disc_pct / 100)
            new_margin = new_price - cogs
            total_promo = new_margin * qty_s1
            total_normal = orig_margin * qty_s1
            selisih = total_promo - total_normal

            st.markdown("##### 📈 Hasil Simulasi")
            with st.container(border=True):
                k1, k2, k3 = st.columns(3)
                k1.metric("Harga Promo", format_rupiah(new_price), f"Normal: {format_rupiah(orig_price)}", delta_color="inverse")
                k2.metric("COGS", format_rupiah(cogs), "Biaya Tetap", delta_color="off")
                k3.metric("Profit per Item", format_rupiah(new_margin), f"Normal: {format_rupiah(orig_margin)}")

            st.metric(f"🎉 TOTAL PROFIT ({qty_s1} terjual)", format_rupiah(total_promo),
                      f"Selisih: {format_rupiah(selisih)} vs Normal",
                      delta_color="normal" if selisih >= 0 else "inverse")
        except Exception as e:
            st.error(f"Gagal menghitung simulasi: {e}")

    st.markdown("---")

    # ── Skenario 2: Promo Paket BOGO ──────────────────────
    st.subheader("Scenario 2: Promo Paket (Buy A, Get B Free)")
    st.write("Untuk BOGO (Buy 1 Get 1 Free), pilih menu **yang sama** di kedua kotak.")

    s2c1, s2c2 = st.columns(2)
    with s2c1:
        menu_A = st.selectbox("Jika Beli (Menu A):", menu_list, key="promo_s2_a")
    with s2c2:
        menu_B = st.selectbox("Gratis (Menu B):", menu_list, key="promo_s2_b")
    qty_s2 = st.number_input("Target Paket Terjual:", min_value=1, value=30, step=5, key="promo_s2_qty")

    if menu_A and menu_B:
        try:
            rowA = profit_df[profit_df["Menu"] == menu_A].iloc[0]
            rowB = profit_df[profit_df["Menu"] == menu_B].iloc[0]
            revenue = rowA["Harga Jual"]
            total_cogs = rowA["COGS"] + rowB["COGS"]
            profit_per_deal = revenue - total_cogs
            total_promo = profit_per_deal * qty_s2
            total_normal = rowA["Margin (Rp)"] * qty_s2
            selisih = total_promo - total_normal

            st.markdown("##### 📦 Hasil Simulasi Paket")
            with st.container(border=True):
                k1, k2, k3 = st.columns(3)
                k1.metric("Revenue Paket", format_rupiah(revenue))
                k2.metric("Total COGS Paket", format_rupiah(total_cogs), "COGS A + COGS B", delta_color="inverse")
                k3.metric("Profit per Paket", format_rupiah(profit_per_deal))

            st.metric(f"🎉 TOTAL PROFIT ({qty_s2} paket)", format_rupiah(total_promo),
                      f"Selisih: {format_rupiah(selisih)} vs Jual Normal",
                      delta_color="inverse")

            if menu_A == menu_B:
                st.warning(f"**BOGO:** {qty_s2} paket = {qty_s2 * 2} item terjual dengan profit {format_rupiah(total_promo)}.")
        except Exception as e:
            st.error(f"Gagal menghitung simulasi paket: {e}")
