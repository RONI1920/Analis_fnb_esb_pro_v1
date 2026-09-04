# ui/charts.py — Fungsi Pembuatan Grafik Plotly

import plotly.express as px
import pandas as pd


def create_horizontal_bar_chart(
    data: pd.DataFrame,
    x_col: str,
    y_col: str,
    x_title: str,
    y_title: str,
    sort_order: str = "-x",
):
    """Membuat grafik batang horizontal Plotly yang profesional."""
    sort_ascending = sort_order != "-x"
    data_sorted = data.sort_values(by=x_col, ascending=sort_ascending)

    fig = px.bar(
        data_sorted,
        x=x_col, y=y_col,
        orientation="h",
        labels={x_col: x_title, y_col: ""},
        title=y_title,
        color=x_col,
        color_continuous_scale=px.colors.sequential.Blues,
        template="plotly_white",
        text=x_col,
    )
    fig.update_layout(
        xaxis_title=x_title,
        yaxis_title="",
        xaxis_side="top",
        coloraxis_showscale=False,
        title_x=0.01,
        title_font_size=18,
        margin=dict(l=0, r=20, t=60, b=20),
        yaxis=(
            {"categoryorder": "total ascending"}
            if sort_ascending
            else {"categoryorder": "total descending"}
        ),
    )
    fig.update_traces(
        texttemplate="%{x:.2s}",
        textposition="outside",
        hovertemplate=f"<b>%{{y}}</b><br>{x_title}: %{{x:,.0f}}<extra></extra>",
    )
    fig.update_yaxes(showgrid=False)
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="#E5E5E5")
    return fig


def create_vertical_bar_chart(
    data: pd.DataFrame,
    x_col: str,
    y_col: str,
    x_title: str,
    y_title: str,
    x_type: str = "N",
    sort_order=None,
):
    """Membuat grafik batang vertikal Plotly yang profesional."""
    category_orders = {x_col: sort_order} if sort_order else {}

    fig = px.bar(
        data,
        x=x_col, y=y_col,
        title=f"{y_title} vs {x_title}",
        labels={x_col: x_title, y_col: y_title},
        color=x_col,
        template="plotly_white",
        category_orders=category_orders,
        text=y_col,
    )
    fig.update_layout(
        xaxis_title=x_title,
        yaxis_title=y_title,
        showlegend=False,
        title_x=0.01,
        title_font_size=18,
        margin=dict(l=0, r=0, t=60, b=0),
        yaxis_tickformat=".2s",
    )
    fig.update_traces(
        texttemplate="%{y:.2s}",
        textposition="outside",
        hovertemplate=f"<b>%{{x}}</b><br>{y_title}: %{{y:,.0f}}<extra></extra>",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="#E5E5E5")
    return fig
