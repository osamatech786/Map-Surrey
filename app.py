import folium
import requests
import streamlit as st
from streamlit.components.v1 import html
import csv

st.set_page_config(
    page_title="Prevista - Surrey",
    page_icon="https://lirp.cdn-website.com/d8120025/dms3rep/multi/opt/social-image-88w.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Define specific places to highlight (example coordinates)
places = {}
csv_file_path = 'resources/places.csv'
with open(csv_file_path, mode='r') as file:
    reader = csv.DictReader(file)
    
    # Iterate over each row in the CSV file
    for row in reader:
        # Extract data from the row
        place = row['Place'].strip()
        latitude = float(row['Latitude'])
        longitude = float(row['Longitude'])
        info = row['Info'].strip()
        
        # Check if any value is missing in the row
        is_complete = all(row[field] for field in ['Place', 'Latitude', 'Longitude', 'Info'])
        
        # Update the dictionary with a flag for completeness
        places[place] = {
            'location': (latitude, longitude),
            'info': info,
            'is_complete': is_complete
        }

# Load the Surrey GeoJSON data
@st.cache_data
def load_surrey_data():
    url = 'https://raw.githubusercontent.com/glynnbird/ukcountiesgeojson/master/surrey.geojson'
    response = requests.get(url)
    geojson_data = response.json()
    return geojson_data

def create_map(surrey_geojson):
    # Extract coordinates from the GeoJSON
    coords = surrey_geojson['geometry']['coordinates'][0]
    surrey_center = [
        (sum(lat for lon, lat in coords) / len(coords),
         sum(lon for lon, lat in coords) / len(coords))
    ]
    # Adjust the zoom level here
    m = folium.Map(location=surrey_center[0], zoom_start=10)  # Increased zoom level for a closer view

    # Add Surrey boundary
    folium.GeoJson(
        surrey_geojson,
        style_function=lambda x: {'fillColor': 'lightblue', 'color': 'black', 'weight': 2}
    ).add_to(m)

    # Add markers for specific places
    for place, details in places.items():
        # Determine the pin color based on Info
        if details['info'] == "Already Engaging":
            pin_color = 'green'
        elif details['info'] == "In Progress":
            pin_color = 'orange'
        else:
            pin_color = 'gray'
        
        # Debug print statements
        print(f"Place: {place}, Info: {details['info']}, Pin Color: {pin_color}")

        folium.Marker(
            location=details["location"],
            popup=folium.Popup(details["info"], max_width=300),
            tooltip=place,
            icon=folium.Icon(color=pin_color, icon='info-sign')
        ).add_to(m)

    return m


def main():
    st.title('Surrey Map - UK')
    st.write("### Delivery Centres & JCP ")

    # Load and filter data
    surrey_geojson = load_surrey_data()

    # Create and display map
    m = create_map(surrey_geojson)

    # Increase the height to ensure the map is visible and sufficiently large
    html_string = m._repr_html_()
    html(html_string, height=600)  # Adjust height here as needed

if __name__ == "__main__":
    main()

# pip install folium requests streamlit
# python -m streamlit run app.py
# Dev : https://linkedin.com/in/osamatech786
