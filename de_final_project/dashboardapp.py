import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(
    page_title="Somerville Crime Analytics",
    page_icon="🚓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .main {
        padding-top: 2rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    h1 {
        color: #1e3a8a;
        padding-bottom: 10px;
    }
    .stat-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    div[data-testid="stExpander"] {
        background-color: #f8f9fa;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

# === Load Data ===
@st.cache_data
def load_data():
    df = pd.read_csv("incidents_with_latlon.csv")
    df = df.dropna(subset=["latitude", "longitude"])
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df['Year Reported'] = pd.to_numeric(df['Year Reported'], errors='coerce')
    df['Hour'] = pd.to_datetime(df['Time'], format='%I:%M %p', errors='coerce').dt.hour
    df['date_numeric'] = (df['Date'] - df['Date'].min()).dt.days
    return df

df = load_data()

# === Header ===
col1, col2 = st.columns([3, 1])
with col1:
    st.title("🚓 Somerville Police Crime Analytics Dashboard")
    st.markdown("**Real-time insights into crime patterns and trends**")
with col2:
    st.image("https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTW6zdhYtmF1foNwY5uIs2DjbWZ8f_oK4EuWQ&s", width=100)

st.markdown("---")

# === Integrated Filters ===
st.subheader("Filter Data")

# Date Range Slider
col1, col2 = st.columns([3, 1])
with col1:
    min_date = df['Date'].min().date()
    max_date = df['Date'].max().date()
    
    # Create slider with date values
    date_range = st.slider(
        "Select Date Range",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="MMM DD, YYYY"
    )
    
    start_date = pd.to_datetime(date_range[0])
    end_date = pd.to_datetime(date_range[1])

with col2:
    st.metric("Date Range", f"{(end_date - start_date).days} days")

# Other filters in expandable sections
col1, col2, col3, col4 = st.columns(4)

with col1:
    with st.expander("Crime Categories", expanded=False):
        categories = sorted(df["Offense Category"].dropna().unique())
        selected_categories = st.multiselect(
            "Select categories",
            categories,
            default=categories,
            key="categories"
        )

with col2:
    with st.expander("🔎 Specific Crime Types", expanded=False):
        crime_types = sorted(df["Offense Sub-Category"].dropna().unique())
        selected_crime_types = st.multiselect(
            "Select specific crimes",
            crime_types,
            default=crime_types,
            key="crime_types"
        )

with col3:
    with st.expander("Police Shift", expanded=False):
        shifts = sorted(df["Police Shift"].dropna().unique())
        selected_shifts = st.multiselect(
            "Select shifts",
            shifts,
            default=shifts,
            key="shifts"
        )

with col4:
    with st.expander("Wards", expanded=False):
        wards = sorted(df["Ward"].dropna().unique())
        selected_wards = st.multiselect(
            "Select wards",
            wards,
            default=wards,
            key="wards"
        )

# === Apply Filters ===
filtered_df = df[
    (df["Date"] >= start_date) &
    (df["Date"] <= end_date) &
    (df["Offense Category"].isin(selected_categories)) &
    (df["Offense Sub-Category"].isin(selected_crime_types)) &
    (df["Police Shift"].isin(selected_shifts)) &
    (df["Ward"].isin(selected_wards))
]

st.markdown("---")

# === Key Metrics ===
st.subheader("📊 Key Metrics")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Incidents", f"{len(filtered_df):,}")
with col2:
    most_common_crime = filtered_df["Offense Sub-Category"].mode()[0] if len(filtered_df) > 0 else "N/A"
    st.metric("Most Common Crime", most_common_crime)
with col3:
    most_dangerous_ward = filtered_df["Ward"].mode()[0] if len(filtered_df) > 0 else "N/A"
    st.metric("Highest Crime Ward", f"Ward {most_dangerous_ward}")
with col4:
    peak_shift = filtered_df["Police Shift"].mode()[0] if len(filtered_df) > 0 else "N/A"
    st.metric("Peak Activity Shift", peak_shift.split('(')[0].strip() if peak_shift != "N/A" else "N/A")

st.markdown("---")

# === Map Visualization with Folium ===
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Crime Incident Map")
    
    # Create Folium map centered on Somerville
    if len(filtered_df) > 0:
        center_lat = filtered_df['latitude'].mean()
        center_lon = filtered_df['longitude'].mean()
    else:
        center_lat, center_lon = 42.3876, -71.0995
    
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=13,
        tiles='OpenStreetMap'
    )
    
    # Color mapping for different offense types
    color_map = {
        "Burglary/Breaking And Entering": "#FF8C00",  # Dark Orange
        "Larceny/Theft Offenses": "#FF4400B0",           # Red-Orange
        "Assault Offenses": "#DC1414",                 # Crimson
        "Theft From Motor Vehicle": "#887249",         # Orange
        "Motor Vehicle Theft": "#FFD700",              # Gold
        "Robbery": "#33B222",                          # Firebrick
        "Weapon Law Violations": "#00FFEE",            # Dark Red
        "Drug/Narcotic Offenses": "#9400D3",           # Dark Violet
        "Vandalism": "#A8A3CE",                        # Deep Pink
    }
    
    # Add markers for each incident
    for idx, row in filtered_df.iterrows():
        color = color_map.get(row['Offense Sub-Category'], '#6495ED')
        
        popup_html = f"""
        <div style="font-family: Arial; width: 250px;">
            <h4 style="color: #1e3a8a; margin-bottom: 8px;">{row['Type']}</h4>
            <p style="margin: 4px 0;"><b>Crime:</b> {row['Offense Sub-Category']}</p>
            <p style="margin: 4px 0;"><b>Date:</b> {row['Date'].strftime('%m/%d/%Y') if pd.notna(row['Date']) else 'N/A'}</p>
            <p style="margin: 4px 0;"><b>Time:</b> {row['Time']}</p>
            <p style="margin: 4px 0;"><b>Ward:</b> {row['Ward']}</p>
            <p style="margin: 4px 0;"><b>Details:</b> {row['Description'][:100]}...</p>
        </div>
        """
        
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=6,
            popup=folium.Popup(popup_html, max_width=300),
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.7,
            weight=2
        ).add_to(m)
    
    # Display map
    st_folium(m, width=None, height=500, returned_objects=[])

with col2:
    st.subheader("Map Legend")
    st.markdown("""
    **Crime Types:**
    - **Burglary/Breaking & Entering**
    - **Larceny/Theft Offenses**
    - **Assault Offenses**
    - **Theft From Motor Vehicle**
    - **Motor Vehicle Theft**
    - **Robbery**
    - **Weapon Law Violations**
    - **Drug/Narcotic Offenses**
    - **Vandalism**
    - **Other Offenses**
    """)
    
    st.subheader("Quick Stats")
    if len(filtered_df) > 0:
        st.dataframe(
            filtered_df['Offense Sub-Category'].value_counts().head(10).reset_index()
            .rename(columns={'Offense Sub-Category': 'Crime Type', 'count': 'Count'}),
            hide_index=True,
            height=250
        )
    else:
        st.info("No data to display")

st.markdown("---")

# === Analytics Section ===
st.subheader("Crime Analytics & Trends")

tab1, tab2, tab3, tab4 = st.tabs(["📅 Temporal Trends", "🏘️ Geographic Analysis", "🔢 Crime Types", "⏰ Time Analysis"])

with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        # Crimes over time
        if len(filtered_df) > 0:
            crimes_over_time = filtered_df.groupby(filtered_df['Date'].dt.to_period('M')).size().reset_index()
            crimes_over_time['Date'] = crimes_over_time['Date'].dt.to_timestamp()
            crimes_over_time.columns = ['Date', 'Count']
            
            fig_timeline = px.line(
                crimes_over_time,
                x='Date',
                y='Count',
                title='Crime Incidents Over Time',
                markers=True
            )
            fig_timeline.update_traces(line_color='#667eea', line_width=3)
            fig_timeline.update_layout(hovermode='x unified')
            st.plotly_chart(fig_timeline, use_container_width=True)
        else:
            st.info("No data to display")
    
    with col2:
        # Year comparison
        if len(filtered_df) > 0:
            yearly_counts = filtered_df['Year Reported'].value_counts().sort_index()
            fig_yearly = px.bar(
                x=yearly_counts.index,
                y=yearly_counts.values,
                title='Incidents by Year',
                labels={'x': 'Year', 'y': 'Count'},
                color=yearly_counts.values,
                color_continuous_scale='Reds'
            )
            st.plotly_chart(fig_yearly, use_container_width=True)
        else:
            st.info("No data to display")

with tab2:
    col1, col2 = st.columns(2)
    
    with col1:
        # Crimes by Ward
        if len(filtered_df) > 0:
            ward_counts = filtered_df['Ward'].value_counts().reset_index()
            ward_counts.columns = ['Ward', 'Count']
            
            fig_ward = px.bar(
                ward_counts,
                x='Ward',
                y='Count',
                title='Crime Distribution by Ward',
                color='Count',
                color_continuous_scale='Viridis'
            )
            st.plotly_chart(fig_ward, use_container_width=True)
        else:
            st.info("No data to display")
    
    with col2:
        # Heatmap by category and ward
        if len(filtered_df) > 0:
            heatmap_data = pd.crosstab(filtered_df['Ward'], filtered_df['Offense Category'])
            
            fig_heatmap = px.imshow(
                heatmap_data,
                title='Crime Categories by Ward',
                labels=dict(x="Crime Category", y="Ward", color="Incidents"),
                color_continuous_scale='RdYlBu_r',
                aspect='auto'
            )
            st.plotly_chart(fig_heatmap, use_container_width=True)
        else:
            st.info("No data to display")

with tab3:
    col1, col2 = st.columns(2)
    
    with col1:
        # Top 10 offense types
        if len(filtered_df) > 0:
            top_offenses = filtered_df['Offense Sub-Category'].value_counts().head(10)
            
            fig_offenses = px.bar(
                x=top_offenses.values,
                y=top_offenses.index,
                orientation='h',
                title='Top 10 Offense Types',
                labels={'x': 'Count', 'y': 'Offense Type'},
                color=top_offenses.values,
                color_continuous_scale='Oranges'
            )
            st.plotly_chart(fig_offenses, use_container_width=True)
        else:
            st.info("No data to display")
    
    with col2:
        # Crime category pie chart
        if len(filtered_df) > 0:
            category_counts = filtered_df['Offense Category'].value_counts()
            
            fig_pie = px.pie(
                values=category_counts.values,
                names=category_counts.index,
                title='Crime Categories Distribution',
                hole=0.4
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No data to display")

with tab4:
    col1, col2 = st.columns(2)
    
    with col1:
        # Crimes by shift
        if len(filtered_df) > 0:
            shift_counts = filtered_df['Police Shift'].value_counts()
            
            fig_shift = px.bar(
                x=shift_counts.index,
                y=shift_counts.values,
                title='Incidents by Police Shift',
                labels={'x': 'Shift', 'y': 'Count'},
                color=shift_counts.values,
                color_continuous_scale='Blues'
            )
            fig_shift.update_xaxes(tickangle=45)
            st.plotly_chart(fig_shift, use_container_width=True)
        else:
            st.info("No data to display")
    
    with col2:
        # Hourly distribution
        if len(filtered_df) > 0 and 'Hour' in filtered_df.columns:
            hourly_counts = filtered_df['Hour'].value_counts().sort_index()
            
            fig_hourly = px.line(
                x=hourly_counts.index,
                y=hourly_counts.values,
                title='Crimes by Hour of Day',
                labels={'x': 'Hour (24h)', 'y': 'Count'},
                markers=True
            )
            fig_hourly.update_traces(line_color='#764ba2', line_width=3)
            st.plotly_chart(fig_hourly, use_container_width=True)
        else:
            st.info("No data to display")

st.markdown("---")

with st.expander("View Detailed Data Table", expanded=False):
    if len(filtered_df) > 0:
        st.dataframe(
            filtered_df[[
                "incident_number", "Date", "Time", "Offense Type", 
                "Offense Sub-Category", "Ward", "Police Shift", "Type", 
                "Description", "latitude", "longitude"
            ]].sort_values('Date', ascending=False),
            use_container_width=True,
            height=400
        )
        
        # Download button
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="Download Filtered Data as CSV",
            data=csv,
            file_name=f"somerville_crime_data_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No data to display")

st.markdown("---")
st.caption("Data Source: Somerville Police Department and Somerville Data Portal")