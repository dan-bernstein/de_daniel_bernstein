import streamlit as st
import pandas as pd
import pydeck as pdk

# === Load Data ===
@st.cache_data
def load_data():
    df = pd.read_csv("/Users/danielbernstein/de_daniel_bernstein/de_final_project/incidents_with_latlon.csv")
    df = df.dropna(subset=["latitude", "longitude"])
    return df

df = load_data()

st.title("🚓 Somerville Police Crime Map")
st.caption("Interactive map of crime incidents with filters by category and time")

# === Sidebar Filters ===
st.sidebar.header("🔍 Filters")

# Year filter
years = sorted(df["Year Reported"].dropna().unique())
selected_years = st.sidebar.multiselect(
    "Select Year(s)", years, default=years
)

# Offense Category filter
categories = sorted(df["Offense Category"].dropna().unique())
selected_categories = st.sidebar.multiselect(
    "Select Offense Category", categories, default=categories
)

# Police Shift filter
shifts = sorted(df["Police Shift"].dropna().unique())
selected_shifts = st.sidebar.multiselect(
    "Select Police Shift", shifts, default=shifts
)

# Filter the dataframe
filtered_df = df[
    df["Year Reported"].isin(selected_years)
    & df["Offense Category"].isin(selected_categories)
    & df["Police Shift"].isin(selected_shifts)
]

st.subheader(f"Showing {len(filtered_df)} incidents")
st.map(filtered_df[["latitude", "longitude"]])

# === Optional Detailed Map ===
st.subheader("🗺️ Detailed Map View")
view_state = pdk.ViewState(
    latitude=42.3876,
    longitude=-71.0995,
    zoom=13,
    pitch=45,
)

layer = pdk.Layer(
    "ScatterplotLayer",
    data=filtered_df,
    get_position=["longitude", "latitude"],
    get_color="[255, 0, 0, 160]",
    get_radius=50,
    pickable=True,
)

tooltip = {
    "html": "<b>Type:</b> {Type}<br/>"
            "<b>Description:</b> {Description}<br/>"
            "<b>Date:</b> {Date}<br/>"
            "<b>Offense:</b> {Offense Type}",
    "style": {"backgroundColor": "steelblue", "color": "white"}
}

st.pydeck_chart(pdk.Deck(map_style="mapbox://styles/mapbox/light-v9",
                         initial_view_state=view_state,
                         layers=[layer],
                         tooltip=tooltip))

# === Show Data Table ===
st.subheader("📋 Data Table")
st.dataframe(filtered_df[
    ["incident_number", "Date", "Time", "Offense Type", "Offense Category", "Type", "Description", "latitude", "longitude"]
])


