import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from src.common.config import get_db_config, get_segmentation_config
from src.common.db import get_engine

CATEGORICAL_LIGHT = [
    "#2a78d6",
    "#1baf7a",
    "#eda100",
    "#008300",
    "#4a3aa7",
    "#e34948",
    "#e87ba4",
    "#eb6834",
]
CATEGORICAL_DARK = [
    "#3987e5",
    "#199e70",
    "#c98500",
    "#008300",
    "#9085e9",
    "#e66767",
    "#d55181",
    "#d95926",
]

AGE_ORDER = ["<25", "25-34", "35-44", "45-54", "55-64", "65+"]
CATEGORY_ORDER = ["Basic", "Standard", "Premium"]

FEATURE_LABELS = {
    "avg_account_balance": "Solde moyen",
    "total_loan_amount": "Encours de crédit",
    "avg_transaction_amount": "Montant moyen / transaction",
    "transaction_frequency": "Fréquence de transaction",
    "nb_products": "Nombre de produits",
    "account_age_days": "Ancienneté du compte (j)",
}

st.set_page_config(
    page_title="ClustIQ — Customer 360 & Segmentation",
    page_icon=":material/insights:",
    layout="wide",
)

st.markdown(
    "<style>[data-testid='stMainBlockContainer']{padding-top:56px;}</style>",
    unsafe_allow_html=True,
)


def get_palette() -> dict:
    dark = st.context.theme.type == "dark"
    return {
        "dark": dark,
        "categorical": CATEGORICAL_DARK if dark else CATEGORICAL_LIGHT,
        "brand": "#3987e5" if dark else "#2a78d6",
        "surface": "#1a1a19" if dark else "#fcfcfb",
        "ink": "#ffffff" if dark else "#0b0b0b",
        "muted": "#898781",
        "grid": "#2c2c2a" if dark else "#e1e0d9",
        "negative": "#3987e5" if dark else "#2a78d6",
        "positive": "#e66767" if dark else "#e34948",
        "diverging_mid": "#383835" if dark else "#f0efec",
        "warning": "#fab219",
    }


def load_customer_level_data() -> pd.DataFrame:
    db_config = get_db_config()
    engine = get_engine()

    attributes = pd.read_sql(
        f"""
        SELECT DISTINCT customer_id, age_range, gender, region, customer_category
        FROM {db_config["customer_360_view"]}
        """,
        engine,
    )
    segments = pd.read_sql(f"SELECT * FROM {db_config['segmentation_table']}", engine)

    df = segments.merge(attributes, on="customer_id", how="left")
    df["segment"] = df["segment"].astype("Int64").astype(str)
    return df


def segment_color_map(df: pd.DataFrame, palette: dict) -> dict:
    segments = sorted(df["segment"].dropna().unique(), key=lambda s: int(s))
    colors = palette["categorical"]
    return {seg: colors[i % len(colors)] for i, seg in enumerate(segments)}


def style_chart(
    fig: go.Figure, palette: dict, showlegend: bool = False, height: int = 360
) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="system-ui, -apple-system, 'Segoe UI', sans-serif",
            color=palette["ink"],
            size=13,
        ),
        margin=dict(l=8, r=8, t=8, b=8),
        showlegend=showlegend,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            bgcolor="rgba(0,0,0,0)",
        ),
        height=height,
        hoverlabel=dict(
            bgcolor=palette["surface"],
            font_color=palette["ink"],
            bordercolor=palette["grid"],
        ),
        hovermode="closest",
    )
    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        linecolor=palette["grid"],
        tickfont=dict(color=palette["muted"]),
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor=palette["grid"],
        zeroline=False,
        tickfont=dict(color=palette["muted"]),
    )
    return fig


def render_sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    with st.sidebar:
        st.markdown("### :material/filter_list: Filtres")
        segments = sorted(df["segment"].dropna().unique(), key=lambda s: int(s))
        selected_segments = st.pills(
            "Segment", segments, selection_mode="multi", key="filter_segments"
        )

        age_ranges = [a for a in AGE_ORDER if a in df["age_range"].dropna().unique()]
        selected_ages = st.pills(
            "Tranche d'âge", age_ranges, selection_mode="multi", key="filter_ages"
        )

        regions = st.multiselect(
            "Région", sorted(df["region"].dropna().unique()), key="filter_regions"
        )

    filtered = df.copy()
    if regions:
        filtered = filtered[filtered["region"].isin(regions)]
    if selected_ages:
        filtered = filtered[filtered["age_range"].isin(selected_ages)]
    if selected_segments:
        filtered = filtered[filtered["segment"].isin(selected_segments)]
    return filtered


def render_kpis(df: pd.DataFrame) -> None:
    median_frequency = df["transaction_frequency"].median()
    high_potential_share = (
        (df["transaction_frequency"] >= median_frequency) & (df["nb_products"] <= 1)
    ).mean()

    with st.container(horizontal=True):
        st.metric(
            ":material/group: Clients actifs",
            f"{df['customer_id'].nunique():,}",
            border=True,
        )
        st.metric(
            ":material/account_balance: Solde moyen",
            f"{df['avg_account_balance'].mean():,.0f}",
            border=True,
        )
        st.metric(
            ":material/inventory_2: Produits / client",
            f"{df['nb_products'].mean():.1f}",
            border=True,
        )
        st.metric(
            ":material/sync_alt: Fréquence transaction",
            f"{df['transaction_frequency'].mean():.1f}",
            border=True,
        )
        st.metric(
            ":material/target: Potentiel cross-sell",
            f"{high_potential_share:.0%}",
            help="Part des clients à fréquence de transaction élevée mais peu de produits souscrits.",
            border=True,
        )


def render_overview_tab(df: pd.DataFrame, color_map: dict, palette: dict) -> None:
    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            st.markdown("**Répartition des segments**")
            st.caption("Taille de chaque segment issu du clustering K-Means.")
            counts = (
                df["segment"].value_counts().reindex(sorted(color_map), fill_value=0)
            )
            total = counts.sum()
            fig = go.Figure(
                go.Bar(
                    x=counts.index,
                    y=counts.values,
                    marker_color=[color_map[s] for s in counts.index],
                    text=[
                        f"{c:,} ({c / total:.0%})" if total else "0"
                        for c in counts.values
                    ],
                    textposition="outside",
                )
            )
            fig.update_xaxes(title="Segment")
            fig.update_yaxes(title="Clients", rangemode="tozero")
            st.plotly_chart(style_chart(fig, palette), width="stretch")

    with col2:
        with st.container(border=True):
            st.markdown("**Répartition par région**")
            st.caption("Top 10 des régions par nombre de clients.")
            region_counts = df["region"].value_counts().head(10).sort_values()
            fig = go.Figure(
                go.Bar(
                    x=region_counts.values,
                    y=region_counts.index,
                    orientation="h",
                    marker_color=palette["brand"],
                )
            )
            fig.update_xaxes(title="Clients", rangemode="tozero")
            fig.update_yaxes(title=None)
            st.plotly_chart(style_chart(fig, palette, height=360), width="stretch")

    col3, col4 = st.columns(2)

    with col3:
        with st.container(border=True):
            st.markdown("**Répartition par tranche d'âge**")
            age_counts = df["age_range"].value_counts().reindex(AGE_ORDER, fill_value=0)
            fig = go.Figure(
                go.Bar(
                    x=age_counts.index,
                    y=age_counts.values,
                    marker_color=palette["categorical"][1],
                )
            )
            fig.update_xaxes(title="Tranche d'âge")
            fig.update_yaxes(title="Clients", rangemode="tozero")
            st.plotly_chart(style_chart(fig, palette, height=320), width="stretch")

    with col4:
        with st.container(border=True):
            st.markdown("**Répartition par catégorie client**")
            category_counts = (
                df["customer_category"]
                .value_counts()
                .reindex(CATEGORY_ORDER, fill_value=0)
            )
            fig = go.Figure(
                go.Bar(
                    x=category_counts.index,
                    y=category_counts.values,
                    marker_color=palette["categorical"][2],
                )
            )
            fig.update_xaxes(title="Catégorie")
            fig.update_yaxes(title="Clients", rangemode="tozero")
            st.plotly_chart(style_chart(fig, palette, height=320), width="stretch")


def render_segment_profile_tab(
    df: pd.DataFrame, feature_cols: list[str], color_map: dict, palette: dict
) -> None:
    available = [c for c in feature_cols if c in df.columns]

    with st.container(border=True):
        st.markdown("**Profil comportemental par segment**")
        st.caption(
            "Écart de chaque segment à la moyenne globale, en écarts-types. "
            "Le rouge indique un segment au-dessus de la moyenne, le bleu en-dessous — les valeurs affichées sont les moyennes réelles."
        )
        means = df.groupby("segment")[available].mean().reindex(sorted(color_map))
        std = df[available].std(ddof=0).replace(0, 1)
        z = (means - df[available].mean()) / std

        text = means.copy()
        for col in available:
            text[col] = means[col].map(lambda v: f"{v:,.1f}")

        zmax = max(float(z.abs().max().max()), 0.5)
        fig = go.Figure(
            go.Heatmap(
                z=z.values,
                x=[
                    FEATURE_LABELS.get(c, c.replace("_", " ").capitalize())
                    for c in available
                ],
                y=[f"Segment {s}" for s in means.index],
                text=text.values,
                texttemplate="%{text}",
                textfont=dict(color=palette["ink"], size=12),
                zmin=-zmax,
                zmax=zmax,
                colorscale=[
                    [0.0, palette["negative"]],
                    [0.5, palette["diverging_mid"]],
                    [1.0, palette["positive"]],
                ],
                colorbar=dict(
                    title="Écart-type",
                    outlinewidth=0,
                    tickfont=dict(color=palette["muted"]),
                ),
                xgap=2,
                ygap=2,
            )
        )
        fig.update_xaxes(side="top")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(
            style_chart(fig, palette, height=160 + 46 * len(means.index)),
            width="stretch",
        )

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("**Solde moyen par segment**")
            st.caption(
                "Distribution des soldes — repère les segments à forte valeur et leurs valeurs extrêmes."
            )
            fig = px.box(
                df,
                x="segment",
                y="avg_account_balance",
                color="segment",
                color_discrete_map=color_map,
            )
            fig.update_xaxes(
                title="Segment", categoryorder="array", categoryarray=sorted(color_map)
            )
            fig.update_yaxes(title="Solde")
            st.plotly_chart(style_chart(fig, palette), width="stretch")

    with col2:
        with st.container(border=True):
            st.markdown("**Encours de crédit par segment**")
            st.caption(
                "Distribution des encours — identifie les segments les plus engagés en crédit."
            )
            fig = px.box(
                df,
                x="segment",
                y="total_loan_amount",
                color="segment",
                color_discrete_map=color_map,
            )
            fig.update_xaxes(
                title="Segment", categoryorder="array", categoryarray=sorted(color_map)
            )
            fig.update_yaxes(title="Encours de crédit")
            st.plotly_chart(style_chart(fig, palette), width="stretch")


def render_opportunities_tab(df: pd.DataFrame, color_map: dict, palette: dict) -> None:
    median_frequency = df["transaction_frequency"].median()

    with st.container(border=True):
        st.markdown("**Zones d'opportunité cross-sell**")
        st.caption(
            "Chaque point est un client. La zone en surbrillance repère les clients très actifs "
            "(fréquence de transaction élevée) mais souscrivant à un seul produit ou moins — la cible prioritaire de cross-sell."
        )
        fig = px.scatter(
            df,
            x="transaction_frequency",
            y="nb_products",
            color="segment",
            color_discrete_map=color_map,
            category_orders={"segment": sorted(color_map)},
            opacity=0.75,
            custom_data=["customer_id"],
        )
        fig.update_traces(
            marker=dict(size=9, line=dict(width=1, color=palette["surface"])),
            hovertemplate="Client %{customdata[0]}<br>Fréquence: %{x}<br>Produits: %{y}<extra></extra>",
        )
        x_max = max(float(df["transaction_frequency"].max()), median_frequency + 1)
        fig.add_shape(
            type="rect",
            xref="x",
            yref="y domain",
            x0=median_frequency,
            x1=x_max,
            y0=0,
            y1=0.5,
            fillcolor=palette["warning"],
            opacity=0.12,
            line_width=0,
            layer="below",
        )
        fig.add_annotation(
            xref="x",
            yref="y domain",
            x=median_frequency,
            y=0.46,
            xanchor="left",
            yanchor="top",
            text="Fort potentiel cross-sell",
            showarrow=False,
            font=dict(color=palette["muted"], size=11),
        )
        fig.add_vline(x=median_frequency, line_dash="dash", line_color=palette["grid"])
        fig.add_hline(
            y=df["nb_products"].median(), line_dash="dash", line_color=palette["grid"]
        )
        fig.update_xaxes(title="Fréquence de transaction")
        fig.update_yaxes(title="Nombre de produits", rangemode="tozero")
        st.plotly_chart(
            style_chart(fig, palette, showlegend=True, height=440), width="stretch"
        )

    with st.container(border=True):
        st.markdown("**Profils à forte valeur**")
        st.caption(
            "Solde moyen et volume de crédit les plus élevés — clients prioritaires pour la rétention."
        )
        high_value = df.sort_values(
            ["avg_account_balance", "total_loan_amount"], ascending=False
        ).head(20)
        st.dataframe(
            high_value[
                [
                    "customer_id",
                    "segment",
                    "region",
                    "age_range",
                    "customer_category",
                    "avg_account_balance",
                    "total_loan_amount",
                ]
            ],
            column_config={
                "customer_id": st.column_config.TextColumn("Client", pinned=True),
                "segment": st.column_config.TextColumn("Segment"),
                "region": st.column_config.TextColumn("Région"),
                "age_range": st.column_config.TextColumn("Âge"),
                "customer_category": st.column_config.TextColumn("Catégorie"),
                "avg_account_balance": st.column_config.ProgressColumn(
                    "Solde moyen",
                    format="%.0f",
                    min_value=0,
                    max_value=float(df["avg_account_balance"].max() or 1),
                ),
                "total_loan_amount": st.column_config.ProgressColumn(
                    "Encours de crédit",
                    format="%.0f",
                    min_value=0,
                    max_value=float(df["total_loan_amount"].max() or 1),
                ),
            },
            hide_index=True,
        )

    with st.container(border=True):
        st.markdown("**Clients à fort potentiel**")
        st.caption(
            "Fréquence de transaction élevée mais peu de produits souscrits — potentiel de cross-sell."
        )
        high_potential = (
            df[
                (df["transaction_frequency"] >= median_frequency)
                & (df["nb_products"] <= 1)
            ]
            .sort_values("transaction_frequency", ascending=False)
            .head(20)
        )
        st.dataframe(
            high_potential[
                [
                    "customer_id",
                    "segment",
                    "region",
                    "age_range",
                    "transaction_frequency",
                    "nb_products",
                ]
            ],
            column_config={
                "customer_id": st.column_config.TextColumn("Client", pinned=True),
                "segment": st.column_config.TextColumn("Segment"),
                "region": st.column_config.TextColumn("Région"),
                "age_range": st.column_config.TextColumn("Âge"),
                "transaction_frequency": st.column_config.ProgressColumn(
                    "Fréquence de transaction",
                    format="%.0f",
                    min_value=0,
                    max_value=float(df["transaction_frequency"].max() or 1),
                ),
                "nb_products": st.column_config.NumberColumn("Produits souscrits"),
            },
            hide_index=True,
        )


def main() -> None:
    st.title(":material/insights: ClustIQ")
    st.caption(
        "Customer 360 & segmentation client — démonstrateur sur données publiques Berka, "
        "branchable sur les données réelles STB via config/mapping_stb.yaml sans changement de code."
    )

    try:
        df = load_customer_level_data()
    except Exception as exc:
        st.error(
            "Impossible de charger les données. Vérifiez que `make all` (ou au minimum "
            "`make database ingestion transformation segmentation`) a bien été exécuté et que MySQL est accessible."
        )
        st.exception(exc)
        return

    if df.empty:
        st.warning(
            "Aucune donnée disponible. Lancez `make all` pour générer le pipeline."
        )
        return

    filtered = render_sidebar_filters(df)
    if filtered.empty:
        st.warning("Aucun client ne correspond aux filtres sélectionnés.")
        return

    palette = get_palette()
    color_map = segment_color_map(df, palette)
    feature_cols = get_segmentation_config()["features"]["numeric"]

    render_kpis(filtered)

    tab_overview, tab_profiles, tab_opportunities = st.tabs(
        [
            ":material/bar_chart: Vue d'ensemble",
            ":material/query_stats: Profils de segments",
            ":material/target: Opportunités commerciales",
        ]
    )
    with tab_overview:
        render_overview_tab(filtered, color_map, palette)
    with tab_profiles:
        render_segment_profile_tab(filtered, feature_cols, color_map, palette)
    with tab_opportunities:
        render_opportunities_tab(filtered, color_map, palette)


if __name__ == "__main__":
    main()
