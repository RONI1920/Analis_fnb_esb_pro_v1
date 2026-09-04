# ui/tabs/tab12_lab.py — Tab 12: Lab Strategi (Menu Engineering + Profit Simulator)

import pandas as pd
import plotly.express as px
import streamlit as st

from formatters import format_rupiah


def build_tab12_lab(df_gmv, df_cogs):
    st.header("🧪 Lab Strategi & Eksperimen")
    st.caption("Analisis ini menggunakan **SEMUA DATA** (tidak terpengaruh filter tanggal).")

    if df_gmv is None or df_cogs is None:
        st.warning("⚠️ Harap upload **File 1 (GMV)** dan **File 2 (COGS)** di sidebar.")
        return

    try:
        # ── Siapkan Data ───────────────────────────────────
        col_harga = "Price (Pricelist)" if "Price (Pricelist)" in df_gmv.columns else "Price (Net)"

        df_gmv_p = df_gmv.copy()
        df_gmv_p["Menu_Match"] = df_gmv_p["Menu"].astype(str).str.strip().str.upper()
        sales_sum = (
            df_gmv_p.groupby("Menu_Match")
            .agg(Menu_Asli=("Menu", "first"),
                 Total_Qty=("Qty", "sum"),
                 Total_Revenue=("Total After Bill Discount", "sum"),
                 Harga_Jual=(col_harga, "mean"))
            .reset_index()
        )

        df_cogs_p = df_cogs.copy()
        df_cogs_p["Menu_Match"] = df_cogs_p["Menu"].astype(str).str.strip().str.upper()
        cogs_sum = df_cogs_p.groupby("Menu_Match").agg(COGS_Satuan=("COGS", "mean")).reset_index()

        df_master = pd.merge(sales_sum, cogs_sum, on="Menu_Match", how="inner")
        if df_master.empty:
            st.error("❌ Tidak ada nama menu yang cocok antara GMV dan COGS.")
            return

        df_master["Menu"] = df_master["Menu_Asli"]
        df_master["Total_COGS"] = df_master["Total_Qty"] * df_master["COGS_Satuan"]
        df_master["Gross_Profit"] = df_master["Total_Revenue"] - df_master["Total_COGS"]
        df_master = df_master[df_master["Total_Qty"] > 0]

        # ── Matrix Menu Engineering ────────────────────────
        st.subheader("1. Matrix Menu Engineering")

        avg_qty = df_master["Total_Qty"].mean()
        avg_profit = df_master["Gross_Profit"].mean()

        def _quadrant(row):
            hq = row["Total_Qty"] >= avg_qty
            hp = row["Gross_Profit"] >= avg_profit
            if hq and hp:   return "⭐ STARS (Laris & Untung)"
            if hq and not hp: return "🐴 PLOWHORSE (Laris, Margin Tipis)"
            if not hq and hp: return "❓ PUZZLE (Jarang Laku, Untung Besar)"
            return "🐕 DOGS (Kurang Laku, Rugi)"

        df_master["Kuadran"] = df_master.apply(_quadrant, axis=1)
        df_master["Hover_Profit"] = df_master["Gross_Profit"].apply(format_rupiah)
        df_master["Hover_Revenue"] = df_master["Total_Revenue"].apply(format_rupiah)
        df_master["Hover_Qty"] = df_master["Total_Qty"].apply(lambda x: f"{x:,.0f}")

        fig = px.scatter(
            df_master, x="Total_Qty", y="Gross_Profit",
            color="Kuadran", hover_name="Menu",
            hover_data={"Kuadran": False, "Total_Qty": False, "Gross_Profit": False,
                        "Hover_Qty": True, "Hover_Profit": True, "Hover_Revenue": True},
            size="Total_Revenue", size_max=40,
            title="Peta Kekuatan Menu (Stars vs Dogs)",
            color_discrete_map={
                "⭐ STARS (Laris & Untung)": "#2ecc71",
                "🐴 PLOWHORSE (Laris, Margin Tipis)": "#f1c40f",
                "❓ PUZZLE (Jarang Laku, Untung Besar)": "#3498db",
                "🐕 DOGS (Kurang Laku, Rugi)": "#e74c3c",
            },
        )
        fig.add_hline(y=avg_profit, line_dash="dot", annotation_text="Rata-rata Profit")
        fig.add_vline(x=avg_qty, line_dash="dot", annotation_text="Rata-rata Qty")
        fig.update_layout(yaxis=dict(tickprefix="Rp "),
                          xaxis_title="Qty Terjual", yaxis_title="Total Profit",
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True)

        # ── Filter Tabel per Kuadran ───────────────────────
        st.markdown("---")
        st.subheader("📋 Detail Menu per Kuadran")
        pilihan = st.selectbox("Tampilkan Data:", [
            "Semua Menu", "⭐ STARS (Laris & Untung)", "🐴 PLOWHORSE (Laris, Margin Tipis)",
            "❓ PUZZLE (Jarang Laku, Untung Besar)", "🐕 DOGS (Kurang Laku, Rugi)",
        ])

        df_tampil = df_master if pilihan == "Semua Menu" else df_master[df_master["Kuadran"] == pilihan]
        tbl = df_tampil[["Menu", "Kuadran", "Total_Qty", "Harga_Jual", "COGS_Satuan", "Gross_Profit"]].copy()
        tbl = tbl.sort_values("Gross_Profit", ascending=False)
        tbl["Total_Qty"] = tbl["Total_Qty"].apply(lambda x: f"{x:,.0f}")
        tbl["Harga_Jual"] = tbl["Harga_Jual"].apply(format_rupiah)
        tbl["COGS_Satuan"] = tbl["COGS_Satuan"].apply(format_rupiah)
        tbl["Gross_Profit"] = tbl["Gross_Profit"].apply(format_rupiah)
        st.dataframe(tbl, use_container_width=True, hide_index=True)

        tips = {
            "STARS": ("success", "Menu ini sempurna. Pastikan stok tidak kosong dan kualitas konsisten."),
            "DOGS": ("error", "Membebani operasional. Coba ganti resep, ubah nama, atau hapus dari menu."),
            "PLOWHORSE": ("warning", "Populer tapi untung tipis. Coba naikkan harga atau kurangi bahan mahal."),
            "PUZZLE": ("info", "Untung besar tapi jarang dibeli. Perbaiki foto atau minta waiter aktif menawarkan."),
        }
        for key, (fn_name, msg) in tips.items():
            if key in pilihan:
                getattr(st, fn_name)(f"💡 {msg}")

        # ── Simulator Profit ───────────────────────────────
        st.markdown("---")
        st.subheader("2. 🔮 Simulator Profit")
        menu_list = sorted(df_master["Menu"].unique())
        sel_sim = st.selectbox("Pilih Menu:", options=menu_list, key="lab_sim_menu")

        if sel_sim:
            row = df_master[df_master["Menu"] == sel_sim].iloc[0]
            curr_price = row["Harga_Jual"]
            curr_cogs = row["COGS_Satuan"]
            curr_qty = row["Total_Qty"]
            curr_profit = row["Gross_Profit"]

            st.markdown(f"**Saat Ini:** Harga `{format_rupiah(curr_price)}` | HPP `{format_rupiah(curr_cogs)}` | Profit Total `{format_rupiah(curr_profit)}`")

            sc1, sc2, sc3 = st.columns(3)
            with sc1:
                pct_price = st.slider("Ubah Harga (%)", -100, 100, 0, key="sim_price")
                new_price = curr_price * (1 + pct_price / 100)
                st.metric("Harga Baru", format_rupiah(new_price))
            with sc2:
                pct_cogs = st.slider("Ubah HPP (%)", -100, 100, 0, key="sim_cogs")
                new_cogs = curr_cogs * (1 + pct_cogs / 100)
                st.metric("HPP Baru", format_rupiah(new_cogs))
            with sc3:
                pct_qty = st.slider("Dampak Qty (%)", -100, 100, 0, key="sim_qty")
                new_qty = curr_qty * (1 + pct_qty / 100)
                st.metric("Qty Baru", f"{new_qty:,.0f}")

            new_profit = (new_price - new_cogs) * new_qty
            delta = new_profit - curr_profit
            st.metric("Estimasi Profit Total Baru", format_rupiah(new_profit), delta=format_rupiah(delta))

            if delta > 0:
                st.success("✅ **PROFIT NAIK!** Skenario ini menguntungkan.")
            elif delta < 0:
                st.error("⚠️ **PROFIT TURUN!** Hati-hati dengan skenario ini.")
            else:
                st.info("Profit tetap sama.")

    except Exception as e:
        st.error(f"Terjadi error di Lab Strategi: {e}")
        st.exception(e)
