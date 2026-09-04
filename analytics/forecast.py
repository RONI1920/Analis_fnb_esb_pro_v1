# analytics/forecast.py — Forecasting dengan Prophet

import pandas as pd
import streamlit as st
from prophet import Prophet


@st.cache_data
def get_prophet_projection(prophet_data: pd.DataFrame, sisa_hari: int):
    """
    Melatih model Prophet dan mengembalikan total ramalan untuk sisa hari.
    prophet_data harus memiliki kolom 'ds' dan 'y'.
    """
    try:
        if len(prophet_data) < 7:
            st.warning("Data bulan ini < 7 hari, ramalan Prophet tidak akurat.")
            return None

        with st.spinner("Menjalankan model ramalan Prophet..."):
            model = Prophet(
                weekly_seasonality=True,
                daily_seasonality=False,
                changepoint_prior_scale=0.1,
            )
            model.fit(prophet_data)
            future_df = model.make_future_dataframe(periods=sisa_hari)
            forecast_df = model.predict(future_df)

        if sisa_hari > 0:
            return forecast_df.iloc[-sisa_hari:]["yhat"].sum()
        return 0

    except Exception as e:
        st.error(f"Gagal menjalankan ramalan Prophet: {e}", icon="🤖")
        return None
