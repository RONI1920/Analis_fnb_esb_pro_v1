# ui/tabs/tab5_forecast.py — Tab 5: Forecast dengan Prophet (Enhanced)

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from prophet import Prophet
from prophet.plot import plot_plotly, plot_components_plotly

from insights.generators import generate_forecast_insights
from formatters import format_rupiah

# Kategori yang layak di-forecast (min data points)
MIN_DAYS_FORECAST = 30
EXCLUDE_CATS = {"Coin Claw Machine", "New Add-ons", "Additional"}


# ── Helper ─────────────────────────────────────────────────────────────────────

def _prepare_daily(df: pd.DataFrame, col_filter: str = None, val_filter: str = None) -> pd.DataFrame:
    """Aggregate daily revenue, optionally filtered by category or menu."""
    d = df.copy()
    if col_filter and val_filter:
        d = d[d[col_filter] == val_filter]
    daily = (
        d.groupby(d["Sales Date In"].dt.date)["Total After Bill Discount"]
        .sum().reset_index()
        .rename(columns={"Sales Date In": "ds", "Total After Bill Discount": "y"})
    )
    daily["ds"] = pd.to_datetime(daily["ds"])
    return daily.sort_values("ds")


def _run_prophet(daily: pd.DataFrame, periods: int, changepoint_scale: float = 0.05):
    """Train Prophet and return (model, forecast_df)."""
    model = Prophet(
        weekly_seasonality=True,
        daily_seasonality=False,
        yearly_seasonality=False,
        changepoint_prior_scale=changepoint_scale,
        interval_width=0.95,
    )
    model.fit(daily)
    future = model.make_future_dataframe(periods=periods)
    forecast = model.predict(future)
    return model, forecast


def _confidence_chart(daily: pd.DataFrame, forecast: pd.DataFrame, title: str) -> go.Figure:
    """Build an enhanced forecast chart with confidence interval shading."""
    last_date = daily["ds"].max()
    hist = forecast[forecast["ds"] <= last_date]
    fut  = forecast[forecast["ds"] >  last_date]

    fig = go.Figure()

    # Confidence band — full
    fig.add_trace(go.Scatter(
        x=pd.concat([forecast["ds"], forecast["ds"][::-1]]),
        y=pd.concat([forecast["yhat_upper"], forecast["yhat_lower"][::-1]]),
        fill="toself", fillcolor="rgba(52,152,219,0.15)",
        line=dict(color="rgba(255,255,255,0)"),
        name="Confidence 95%", hoverinfo="skip",
    ))
    # Historical actual
    fig.add_trace(go.Scatter(
        x=daily["ds"], y=daily["y"],
        mode="lines", name="Aktual",
        line=dict(color="#2c3e50", width=1.5),
        hovertemplate="<b>%{x|%d %b %Y}</b><br>Aktual: Rp %{y:,.0f}<extra></extra>",
    ))
    # Historical fitted
    fig.add_trace(go.Scatter(
        x=hist["ds"], y=hist["yhat"],
        mode="lines", name="Fitted",
        line=dict(color="#3498db", width=1.5, dash="dot"),
        hovertemplate="Fitted: Rp %{y:,.0f}<extra></extra>",
    ))
    # Future forecast
    fig.add_trace(go.Scatter(
        x=fut["ds"], y=fut["yhat"],
        mode="lines+markers", name="Forecast",
        line=dict(color="#e74c3c", width=2.5),
        marker=dict(size=4),
        hovertemplate="<b>%{x|%d %b %Y}</b><br>Forecast: Rp %{y:,.0f}<br>Min: Rp %{customdata[0]:,.0f}<br>Max: Rp %{customdata[1]:,.0f}<extra></extra>",
        customdata=list(zip(fut["yhat_lower"], fut["yhat_upper"])),
    ))
    # Vertical line: today boundary
    last_date_ms = int(pd.Timestamp(last_date).timestamp() * 1000)
    fig.add_vline(x=last_date_ms, line_dash="dash", line_color="gray",
                  annotation_text="Data terakhir", annotation_position="top left")

    fig.update_layout(
        title=title, height=430,
        yaxis_title="Revenue (Rp)",
        xaxis_title="Tanggal",
        legend=dict(orientation="h", y=1.08),
        hovermode="x unified",
    )
    return fig


# ── Main Tab ───────────────────────────────────────────────────────────────────

def build_tab5_forecast(data_gmv):
    st.header("🔮 Peramalan Tren Penjualan")
    st.info("Menggunakan **Prophet** untuk forecast dengan confidence interval 95%.")

    if data_gmv is None or data_gmv.empty:
        st.warning("Silakan upload file Laporan GMV (File 1) di sidebar.")
        return

    # ── Pengaturan ─────────────────────────────────────────
    st.subheader("⚙️ Pengaturan Forecast")
    c1, c2, c3 = st.columns(3)
    forecast_days      = c1.slider("Hari ke depan:", 7, 90, 30)
    changepoint_scale  = c2.select_slider(
        "Sensitivitas Tren:",
        options=[0.01, 0.05, 0.1, 0.3, 0.5],
        value=0.05,
        help="Nilai kecil = tren lebih smooth. Nilai besar = lebih reaktif terhadap perubahan.",
    )
    forecast_mode      = c3.radio(
        "Mode Forecast:",
        ["Total Revenue", "Per Kategori", "Per Menu"],
        help="Pilih level detail forecast.",
    )

    # ════════════════════════════════════════════════════════
    # MODE 1: TOTAL REVENUE
    # ════════════════════════════════════════════════════════
    if forecast_mode == "Total Revenue":
        daily = _prepare_daily(data_gmv)

        if len(daily) < MIN_DAYS_FORECAST:
            st.warning(f"Data kurang ({len(daily)} hari). Minimal {MIN_DAYS_FORECAST} hari.")
            return

        last_date = daily["ds"].max()
        st.info(f"Data s.d. **{last_date.strftime('%d %b %Y')}** — forecast **{forecast_days} hari** ke depan.")

        with st.spinner("Melatih model Prophet..."):
            try:
                model, forecast = _run_prophet(daily, forecast_days, changepoint_scale)
            except Exception as e:
                st.error(f"Gagal melatih model: {e}")
                return

        # KPI forecast
        future_only = forecast[forecast["ds"] > last_date]
        st.subheader("📊 Ringkasan Forecast")
        f1, f2, f3, f4 = st.columns(4)
        f1.metric("Total Forecast",      format_rupiah(future_only["yhat"].sum()))
        f2.metric("Rata-rata Harian",     format_rupiah(future_only["yhat"].mean()))
        f3.metric("Batas Bawah (95%)",    format_rupiah(future_only["yhat_lower"].sum()))
        f4.metric("Batas Atas (95%)",     format_rupiah(future_only["yhat_upper"].sum()))

        st.markdown("---")
        st.subheader(f"📈 Forecast {forecast_days} Hari ke Depan")
        st.plotly_chart(
            _confidence_chart(daily, forecast, "Forecast Total Revenue Harian"),
            use_container_width=True,
        )

        # Komponen
        st.subheader("📊 Komponen Tren & Pola Mingguan")
        st.plotly_chart(plot_components_plotly(model, forecast), use_container_width=True)

        # Tabel
        with st.expander("📋 Tabel Data Forecast"):
            tbl = future_only[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
            # Revenue tidak bisa negatif — clip ke 0
            tbl["yhat"]       = tbl["yhat"].clip(lower=0)
            tbl["yhat_lower"] = tbl["yhat_lower"].clip(lower=0)
            tbl["yhat_upper"] = tbl["yhat_upper"].clip(lower=0)
            tbl.columns = ["Tanggal", "Estimasi", "Batas Bawah", "Batas Atas"]
            tbl["Estimasi"]    = tbl["Estimasi"].apply(format_rupiah)
            tbl["Batas Bawah"] = tbl["Batas Bawah"].apply(format_rupiah)
            tbl["Batas Atas"]  = tbl["Batas Atas"].apply(format_rupiah)
            st.dataframe(tbl, use_container_width=True, hide_index=True)

        # Insight
        st.markdown("---")
        st.header("💡 Insight Forecast")
        insights = generate_forecast_insights(forecast, last_date)
        with st.expander("Temuan Kunci", expanded=True):
            for ins in insights:
                st.markdown(f"&bull; {ins}")

    # ════════════════════════════════════════════════════════
    # MODE 2: PER KATEGORI
    # ════════════════════════════════════════════════════════
    elif forecast_mode == "Per Kategori":
        if "Menu Category" not in data_gmv.columns:
            st.warning("Kolom 'Menu Category' tidak ditemukan.")
            return

        # Pilih kategori
        all_cats = [
            c for c in data_gmv["Menu Category"].dropna().unique()
            if c not in EXCLUDE_CATS
        ]
        sel_cats = st.multiselect(
            "Pilih Kategori (maks 5):",
            sorted(all_cats),
            default=sorted(all_cats)[:3],
            max_selections=5,
        )
        if not sel_cats:
            st.info("Pilih minimal 1 kategori.")
            return

        st.markdown("---")

        # Summary forecast semua kategori terpilih
        summary_rows = []
        charts = {}

        with st.spinner("Melatih model per kategori..."):
            for cat in sel_cats:
                daily_cat = _prepare_daily(data_gmv, "Menu Category", cat)
                if len(daily_cat) < MIN_DAYS_FORECAST:
                    continue
                try:
                    _, fc = _run_prophet(daily_cat, forecast_days, changepoint_scale)
                    future_fc = fc[fc["ds"] > daily_cat["ds"].max()]
                    summary_rows.append({
                        "Kategori":        cat,
                        "Forecast_Total":  future_fc["yhat"].sum(),
                        "Forecast_Daily":  future_fc["yhat"].mean(),
                        "Lower":           future_fc["yhat_lower"].sum(),
                        "Upper":           future_fc["yhat_upper"].sum(),
                    })
                    charts[cat] = (daily_cat, fc)
                except Exception:
                    continue

        if not summary_rows:
            st.warning("Tidak ada kategori dengan data cukup.")
            return

        df_summary = pd.DataFrame(summary_rows).sort_values("Forecast_Total", ascending=False)

        # Summary bar chart
        st.subheader(f"📊 Perbandingan Forecast {forecast_days} Hari — per Kategori")
        fig_sum = go.Figure()
        fig_sum.add_trace(go.Bar(
            x=df_summary["Kategori"], y=df_summary["Forecast_Total"],
            name="Forecast",
            marker_color="#3498db",
            error_y=dict(
                type="data",
                symmetric=False,
                array=df_summary["Upper"] - df_summary["Forecast_Total"],
                arrayminus=df_summary["Forecast_Total"] - df_summary["Lower"],
                color="gray",
            ),
            text=df_summary["Forecast_Total"].apply(
                lambda v: "Rp " + f"{int(v/1e6):.0f}M"
            ),
            textposition="outside",
        ))
        fig_sum.update_layout(height=380, yaxis_title="Total Forecast (Rp)", showlegend=False)
        st.plotly_chart(fig_sum, use_container_width=True)

        # Summary table
        tbl_sum = df_summary.copy()
        for col in ["Forecast_Total", "Forecast_Daily", "Lower", "Upper"]:
            tbl_sum[col] = tbl_sum[col].apply(format_rupiah)
        tbl_sum.columns = ["Kategori", "Total Forecast", "Avg Harian", "Batas Bawah", "Batas Atas"]
        st.dataframe(tbl_sum, use_container_width=True, hide_index=True)

        st.markdown("---")

        # Detail chart per kategori
        st.subheader("📈 Detail Forecast per Kategori")
        for cat in sel_cats:
            if cat not in charts:
                continue
            daily_cat, fc_cat = charts[cat]
            with st.expander(f"📂 {cat}", expanded=(cat == sel_cats[0])):
                st.plotly_chart(
                    _confidence_chart(daily_cat, fc_cat, f"Forecast — {cat}"),
                    use_container_width=True,
                )

    # ════════════════════════════════════════════════════════
    # MODE 3: PER MENU
    # ════════════════════════════════════════════════════════
    elif forecast_mode == "Per Menu":
        # Pilih dari top 30 menu by revenue
        top_menus = (
            data_gmv[data_gmv["Price (Net)"] > 0]
            .groupby("Menu")["Total After Bill Discount"]
            .sum().nlargest(30).index.tolist()
        )
        sel_menus = st.multiselect(
            "Pilih Menu (maks 3):",
            top_menus,
            default=top_menus[:2],
            max_selections=3,
        )
        if not sel_menus:
            st.info("Pilih minimal 1 menu.")
            return

        st.markdown("---")

        with st.spinner("Melatih model per menu..."):
            for menu in sel_menus:
                daily_menu = _prepare_daily(data_gmv, "Menu", menu)
                if len(daily_menu) < MIN_DAYS_FORECAST:
                    st.warning(f"Data {menu} kurang ({len(daily_menu)} hari). Skip.")
                    continue
                try:
                    _, fc_menu = _run_prophet(daily_menu, forecast_days, changepoint_scale)
                    future_fc  = fc_menu[fc_menu["ds"] > daily_menu["ds"].max()]

                    st.subheader(f"🍽️ {menu}")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Total Forecast",   format_rupiah(future_fc["yhat"].sum()))
                    m2.metric("Rata-rata Harian",  format_rupiah(future_fc["yhat"].mean()))
                    m3.metric("Range 95%",
                               f"{format_rupiah(future_fc['yhat_lower'].sum())} – {format_rupiah(future_fc['yhat_upper'].sum())}")

                    st.plotly_chart(
                        _confidence_chart(daily_menu, fc_menu, f"Forecast Revenue — {menu}"),
                        use_container_width=True,
                    )
                    st.markdown("---")
                except Exception as e:
                    st.error(f"Gagal forecast {menu}: {e}")