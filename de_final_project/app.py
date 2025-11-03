import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

df = pd.read_csv("test.csv")

m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=13)
for _, row in df.iterrows():
    if pd.notnull(row['lat']) and pd.notnull(row['lon']):
        folium.Marker([row['lat'], row['lon']], popup=row['Type']).add_to(m)

st.title("Somerville Crime Map")
st_folium(m, width=700, height=500)

