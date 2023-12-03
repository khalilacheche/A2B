import streamlit as st
import pydeck as pdk
import geopy.distance
import pickle
import pandas as pd
import requests
import ast

# from helpers import get_coordinates, find_recommended_paths


MODE_TO_EMOJI = {
    "FOOT": "🚶",
    "BIKE": "🚲",
    "CAR": "🚗",
    "BUS": "🚌",
    "TRAM": "🚋",
    "TRAIN": "🚅",
    "METRO": "🚇",
    "FUNICULAR": "🚠",
    "CABLE_CAR": "🚡",
    "GONDOLA": "🚡",
    "TRAMWAY": "🚋",
}

CACHE_FILE = "cache.pkl"


def calculate_score(row, co2_weight, time_weight, transfers_weight):
    return (
        co2_weight * row["CO2 emissions"]
        + time_weight * row["time"]
        + transfers_weight * row["transfers"]
    )


def clicked(
    start, end, date, h_m, time_slider, no_of_transfers, comfort_slider, co2_emissions
):
    df = pd.read_csv("path.csv")
    df["score"] = df.apply(
        lambda x: calculate_score(x, co2_emissions, time_slider, no_of_transfers),
        axis=1,
    )
    df = df.sort_values(by="score", ascending=True)
    df = df.head(5)
    for i, row in df.iterrows():
        with st.expander(f"Path {i} ({row['score'] * 100:.2f})"):
            path = row["path"]
            path = ast.literal_eval(path)

            for j, p in enumerate(path):
                # st.write(f"Step {j}: {p}")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"Mode: {MODE_TO_EMOJI[p['mode']]}")
                with col2:
                    st.write(f"Departure: {p['departure_time']} -> {p['arrival_time']}")
                    if p["mode"] in ["FOOT", "BIKE", "CAR"]:
                        # st.write(f"Distance: {p['distance']} m")
                        pass
                    else:
                        st.write(
                            f"           {p['departurePlace']} -> {p['arrivalPlace']}"
                        )


def display_map(start, end):
    start_lat, start_lon = start
    end_lat, end_lon = end
    start = pdk.Layer(
        "ScatterplotLayer",
        data=[
            {
                "position": [start_lon, start_lat],
                "radius": 50,
                "color": [255, 0, 0],
            }
        ],
        get_position="position",
        get_radius="radius",
        get_fill_color="color",
        pickable=True,
    )
    end = pdk.Layer(
        "ScatterplotLayer",
        data=[{"position": [end_lon, end_lat], "radius": 50, "color": [0, 255, 0]}],
        get_position="position",
        get_radius="radius",
        get_fill_color="color",
        pickable=True,
    )

    dist = geopy.distance.geodesic((start_lat, start_lon), (end_lat, end_lon)).km

    center_lat = (start_lat + end_lat) / 2
    center_lon = (start_lon + end_lon) / 2

    # zoom = 4 + (400 / dist) * (15 - 4) * 0.1
    # zoom = max(4, min(15, zoom))
    MIN_ZOOM = 8
    MAX_ZOOM = 15
    DIST_TO_ZOOM = 15
    zoom = MAX_ZOOM - (dist / DIST_TO_ZOOM) * (MAX_ZOOM - MIN_ZOOM)
    zoom = max(MIN_ZOOM, min(MAX_ZOOM, zoom))

    deck = pdk.Deck(
        layers=[start, end],
        initial_view_state=pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=zoom,
        ),
    )
    st.pydeck_chart(deck)


def get_coordinates(query):
    base_url = "https://nominatim.openstreetmap.org/search"
    params = {"q": query, "format": "json"}

    response = requests.get(base_url, params=params)

    if response.status_code == 200:
        data = response.json()
        if data:
            # Assuming the first result is the desired location
            latitude = float(data[0]["lat"])
            longitude = float(data[0]["lon"])
            return latitude, longitude
        else:
            return None
    else:
        print("Error:", response.status_code)
        return None


def main():
    st.title("Route Planner")
    col1, col2 = st.columns(2)
    with col1:
        start_q = st.text_input("Start Point", value="Chemin des triaudes 9")
    with col2:
        end_q = st.text_input("End Point", value="Quai Jean-Pascal-Delamuraz 1")
    start_lat_lon = get_coordinates(start_q)
    end_lat_lon = get_coordinates(end_q)
    if start_lat_lon and end_lat_lon:
        display_map(start_lat_lon, end_lat_lon)
        col1, col2, col3 = st.columns(3)
        with st.expander("Route Preferences"):
            time_slider = st.slider("How long the trip takes=", 0.0, 1.0, 0.5)
            no_of_transfers = st.slider("How many transfers?", 0.0, 1.0, 0.5)
            comfort_slider = st.slider(
                "How comfortable you want the trip?", 0.0, 1.0, 0.5
            )
            co2_emissions = st.slider("Environmental impact?", 0.0, 1.0, 0.5)

        col1, col2 = st.columns(2)
        with col1:
            d = st.date_input("Departure date", value=None)
            d = d.strftime("%Y-%m-%d")
        with col2:
            h_m = st.time_input("Departure time", value=None)
            h_m = h_m.strftime("%H:%M")

        _, _, col2, _, _ = st.columns(5)

        if st.button(
            "Get Route!",
        ):
            clicked(
                start_lat_lon,
                end_lat_lon,
                d,
                h_m,
                time_slider,
                no_of_transfers,
                comfort_slider,
                co2_emissions,
            )


if __name__ == "__main__":
    main()
