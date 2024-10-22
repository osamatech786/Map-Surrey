import folium
import requests
import streamlit as st
from streamlit.components.v1 import html
from pyairtable import Table
from dotenv import load_dotenv
import os
import pandas as pd

st.set_page_config(
    page_title="Prevista - Surrey",
    page_icon="https://lirp.cdn-website.com/d8120025/dms3rep/multi/opt/social-image-88w.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def get_secret(key):
    try:
        # Attempt to get the secret from environment variables
        secret = os.getenv(key)
        if secret is None:
            raise ValueError("Secret not found in environment variables")
        return secret
    except (ValueError, TypeError) as e:
        # If an error occurs, fall back to Streamlit secrets
        if hasattr(st, 'secrets'):
            return st.secrets.get(key)
        # If still not found, return None or handle as needed
        return None
    
# Airtable credentials
load_dotenv()
AIRTABLE_API_KEY = get_secret("PAT")
AIRTABLE_BASE_ID = get_secret("BASE_ID")
AIRTABLE_TABLE_NAME = get_secret("MAP")

table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)

# @st.cache_data(show_spinner=False, ttl=300)
def load_places_from_airtable():
    records = table.all()
    places = []

    if not records:
        st.error("No records found in Airtable.")
        return places

    for rec in records:
        fields = rec.get('fields', {})  # Use get to avoid KeyError
        place = fields.get('Place', '')
        latitude = fields.get('Latitude')  # No default; check later
        longitude = fields.get('Longitude')  # No default; check later
        info = fields.get('Info', '')  # Default to empty string

        # Debug: Log the fields fetched for each record
        # st.write(f"Fetched record: {fields}")

        # Ensure latitude and longitude are valid floats
        try:
            latitude = float(latitude) if latitude is not None else None
            longitude = float(longitude) if longitude is not None else None
        except (TypeError, ValueError):
            st.warning(f"Invalid latitude or longitude for {place}. Skipping record.")
            continue

        # Debug: Log the final values before adding to places
        # st.write(f"Checking record: Place='{place}', Latitude='{latitude}', Longitude='{longitude}', Info='{info}'")

        # Only add to places if the required fields are available
        if place and latitude is not None and longitude is not None:
            places.append({
                'Place': place,
                'Location': (latitude, longitude),
                'Info': info,  # Even if info is empty, it will still be added
                'ID': rec['id']
            })
        else:
            st.warning(f"Missing information for {place}: Place='{place}', Latitude='{latitude}', Longitude='{longitude}', Info='{info}'. Skipping record.")

    # Debug: Show the final list of places
    # st.write(f"Final places list: {places}")

    return places

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

    # Load places from Airtable
    places = load_places_from_airtable()  # This will return a list of places

    # Add markers for specific places
    for details in places:  # Iterate directly over the list of places
        place = details['Place']
        info = details['Info']  # Get the info field

        # Determine the pin color based on Info
        if info == "Already Engaging":
            pin_color = 'green'
        elif info == "In Progress":
            pin_color = 'orange'
        else:
            pin_color = 'gray'
        
        # Debug print statements
        print(f"Place: {place}, Info: {info}, Pin Color: {pin_color}")

        folium.Marker(
            location=details["Location"],
            popup=folium.Popup(info, max_width=300),
            tooltip=place,
            icon=folium.Icon(color=pin_color, icon='info-sign')
        ).add_to(m)

    return m


def main():
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Map View", "Update Data"])

    if page == "Map View":
        map_view()
    elif page == "Update Data":
        update_data_page()

def map_view():
    st.title('Surrey Map - UK')
    st.write("### Delivery Centres & JCP ")

    # Load and filter data
    surrey_geojson = load_surrey_data()

    # Create and display map
    m = create_map(surrey_geojson)

    # Increase the height to ensure the map is visible and sufficiently large
    html_string = m._repr_html_()
    html(html_string, height=600)  # Adjust height here as needed


def update_data_page():
    st.title("Update Data - Password Protected")
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        password = st.text_input("Enter Password:", type="password")
        if st.button("Submit Password"):
            if password == get_secret("PASS"):
                st.session_state.authenticated = True
                st.success("Access Granted")
            else:
                st.error("Incorrect Password")
                return

    if st.session_state.authenticated:
        st.write("### Editable Airtable Data")
        
        # Fetch records from Airtable
        records = load_places_from_airtable()

        # Convert the list of records into a DataFrame
        records_df = pd.DataFrame(records)

        # Check if records_df is empty
        if records_df.empty:
            st.write("No records available.")
            return

        # Flatten the Location column to separate Latitude and Longitude
        records_df[['Latitude', 'Longitude']] = pd.DataFrame(records_df['Location'].tolist(), index=records_df.index)
        records_df = records_df.drop(columns=["Location"], errors='ignore')

        # Rearrange the columns to have "Info" last
        records_df = records_df[['Place', 'Latitude', 'Longitude', 'Info', 'ID']]

        # Sort the DataFrame to match Airtable order
        records_df.sort_values(by='Place', inplace=True)  # Change 'Place' to the column you want to sort by

        # Make the DataFrame editable
        edited_df = st.data_editor(
            records_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Place": st.column_config.TextColumn(label="Place", required=True),
                "Latitude": st.column_config.NumberColumn(label="Latitude", required=True),
                "Longitude": st.column_config.NumberColumn(label="Longitude", required=True),
                "Info": st.column_config.TextColumn(label="Info", required=False),
                "ID": st.column_config.TextColumn(label="ID", required=False, disabled=True),  # Optional: hide ID
            }
        )

        # Button to update the table
        if st.button("Update Table"):
            for idx, row in edited_df.iterrows():
                updated_fields = {
                    "Place": row['Place'],
                    "Info": row['Info'],
                    "Latitude": row['Latitude'],  # Update using correct field names
                    "Longitude": row['Longitude']  # Update using correct field names
                }
                # Update the Airtable record
                table.update(row['ID'], updated_fields)  # Use original record ID for updates
            st.success("All changes saved successfully!")

        # Add new record section
        st.write("### Add a New Record")
        new_place = st.text_input("Place")
        new_latitude = st.number_input("Latitude", format="%.6f")
        new_longitude = st.number_input("Longitude", format="%.6f")
        new_info = st.text_input("Info")

        if st.button("Add Record"):
            if new_place and new_latitude is not None and new_longitude is not None:
                new_record = {
                    "Place": new_place,
                    "Latitude": new_latitude,
                    "Longitude": new_longitude,
                    "Info": new_info
                }
                table.create(new_record)  # Add to Airtable
                st.success(f"Record '{new_place}' added successfully.")
                st.rerun()  # Refresh to show new record

        # Delete selected records
        st.write("### Delete Selected Records")
        delete_ids = st.multiselect("Select records to delete:", records_df['Place'])  # Use multiselect for multiple options

        if st.button("Delete Selected"):
            for place in delete_ids:
                record_to_delete = records_df[records_df['Place'] == place]
                if not record_to_delete.empty:
                    table.delete(record_to_delete['ID'].values[0])  # Delete from Airtable
                    st.success(f"Record '{place}' deleted successfully.")
                else:
                    st.warning(f"Record '{place}' not found.")
            st.rerun()  # Refresh to update the display



if __name__ == '__main__':
    main()

# python -m streamlit run app.py
# Dev : https://linkedin.com/in/osamatech786