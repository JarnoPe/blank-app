from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Hevostallin IoT-seuranta", layout="wide")


@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Simuloi kolmea eri IoT-lähdettä ja palauttaa ne DataFrameina."""
    base_time = datetime(2026, 1, 5, 6, 0)

    horse_dim = pd.DataFrame(
        [
            {"horse_id": "H-001", "name": "Aava", "osasto": "Talli A"},
            {"horse_id": "H-002", "name": "Utu", "osasto": "Tall i B".replace(" ", "")},
            {"horse_id": "H-003", "name": "Routa", "osasto": "Talli A"},
            {"horse_id": "H-004", "name": "Säde", "osasto": "Tall i C".replace(" ", "")},
        ]
    )

    water_log = []
    temperature_log = []
    for idx, horse_id in enumerate(horse_dim["horse_id"]):
        for hour in range(24):
            timestamp = base_time + timedelta(hours=hour)
            water_log.append(
                {
                    "timestamp": timestamp,
                    "horse_id": horse_id,
                    "vesi_litraa": round(1.4 + idx * 0.25 + (hour % 6) * 0.15, 2),
                    "lahto": "Juoma-automaatit",
                }
            )
            temperature_log.append(
                {
                    "timestamp": timestamp,
                    "horse_id": horse_id,
                    "lampotila_c": round(36.8 + idx * 0.08 + (hour % 8) * 0.05, 2),
                    "lahto": "Lämpöpanta",
                }
            )

    water_df = pd.DataFrame(water_log)
    temperature_df = pd.DataFrame(temperature_log)
    return horse_dim, water_df, temperature_df


horse_dim, water_df, temperature_df = load_data()

# Yhdistetään eri lähteet hevosen ID:llä
combined_df = (
    water_df.merge(temperature_df, on=["timestamp", "horse_id"], how="inner")
    .merge(horse_dim, on="horse_id", how="left")
    .sort_values("timestamp")
)

st.title("🐎 Alkutuotannon IoT-data dashboard")
st.caption(
    "Seuraa hevosten vedenkulutusta ja lämpötilaa eri IoT-lähteistä yhdistettynä hevosen ID:n perusteella."
)

with st.sidebar:
    st.header("Suodattimet")
    selected_horses = st.multiselect(
        "Valitse hevoset",
        options=horse_dim["horse_id"].tolist(),
        default=horse_dim["horse_id"].tolist(),
        format_func=lambda horse_id: f"{horse_id} – {horse_dim.loc[horse_dim['horse_id'] == horse_id, 'name'].iloc[0]}",
    )

    selected_osasto = st.multiselect(
        "Valitse osasto",
        options=sorted(horse_dim["osasto"].unique().tolist()),
        default=sorted(horse_dim["osasto"].unique().tolist()),
    )

filtered_df = combined_df[
    combined_df["horse_id"].isin(selected_horses)
    & combined_df["osasto"].isin(selected_osasto)
]

if filtered_df.empty:
    st.warning("Valituilla suodattimilla ei löytynyt dataa.")
    st.stop()

latest = filtered_df.sort_values("timestamp").groupby("horse_id").tail(1)

kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric("Seurattavat hevoset", latest["horse_id"].nunique())
kpi2.metric("Vedenkulutus (l / h, keskiarvo)", f"{filtered_df['vesi_litraa'].mean():.2f}")
kpi3.metric("Lämpötila (°C, keskiarvo)", f"{filtered_df['lampotila_c'].mean():.2f}")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Vedenkulutus ajan yli")
    water_chart = (
        filtered_df.groupby(["timestamp", "horse_id"], as_index=False)["vesi_litraa"].mean().pivot(
            index="timestamp", columns="horse_id", values="vesi_litraa"
        )
    )
    st.line_chart(water_chart)

with col2:
    st.subheader("Lämpötila ajan yli")
    temperature_chart = (
        filtered_df.groupby(["timestamp", "horse_id"], as_index=False)["lampotila_c"].mean().pivot(
            index="timestamp", columns="horse_id", values="lampotila_c"
        )
    )
    st.line_chart(temperature_chart)

st.subheader("Yhdistetty mittausnäkymä")
view_cols = [
    "timestamp",
    "horse_id",
    "name",
    "osasto",
    "vesi_litraa",
    "lampotila_c",
    "lahto_x",
    "lahto_y",
]
display_df = filtered_df[view_cols].rename(
    columns={
        "name": "hevosen_nimi",
        "lahto_x": "vesi_lähde",
        "lahto_y": "lämpötila_lähde",
    }
)
st.dataframe(display_df, width="stretch")
