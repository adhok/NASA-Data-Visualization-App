import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from PIL import Image
from io import BytesIO

# Page config
st.set_page_config(
    page_title="NASA Data Explorer",
    page_icon="🚀",
    layout="wide"
)

st.sidebar.image("https://www.nasa.gov/wp-content/uploads/2023/03/nasa-logo-web-rgb.png", 
                width=500)



# Main navigation
st.sidebar.title("NASA Data Explorer")
page = st.sidebar.radio(
    "Select Dataset",
    ["Mars Rover Photos", "Near Earth Objects", "Mars Weather", "Earth Imagery (EPIC)"]
)

# API key input (in a real app, use secrets management)
api_key = st.sidebar.text_input("NASA API Key (or use DEMO_KEY)", "DEMO_KEY")

# Function to fetch data with error handling
def fetch_nasa_data(url, params=None):
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data: {e}")
        return None

# MARS ROVER PHOTOS PAGE
if page == "Mars Rover Photos":
    st.title("Mars Rover Photo Explorer")
    st.markdown("Browse the latest photos from NASA's Mars rovers: Curiosity, Opportunity, and Perseverance")
    
    # Rover selection
    rover = st.sidebar.selectbox(
        "Select Rover",
        ["Curiosity", "Opportunity", "Perseverance"]
    )
    
    # Date selection
    today = datetime.now()
    max_date = today
    default_date = today - timedelta(days=7)
    
    earth_date = st.sidebar.date_input(
        "Select Earth Date",
        default_date,
        max_value=max_date
    )
    
    # Fetch rover photos
    @st.cache_data(ttl=3600)
    def get_rover_photos(rover, date, api_key):
        url = f"https://api.nasa.gov/mars-photos/api/v1/rovers/{rover}/photos"
        params = {
            "earth_date": date.strftime("%Y-%m-%d"),
            "api_key": api_key
        }
        return fetch_nasa_data(url, params)
    
    with st.spinner("Fetching Mars rover photos..."):
        data = get_rover_photos(rover.lower(), earth_date, api_key)
        if data:
            photos = data.get("photos", [])
        else:
            photos = []
    
    # Display results
    if not photos:
        st.info(f"No photos found for {rover} on {earth_date.strftime('%Y-%m-%d')}. Try another date or rover.")
    else:
        # Display count
        st.subheader(f"Found {len(photos)} photos")
        
        # Optional camera filter
        cameras = list(set(photo["camera"]["name"] for photo in photos))
        selected_camera = st.selectbox("Filter by camera", ["All"] + cameras)
        
        if selected_camera != "All":
            photos = [photo for photo in photos if photo["camera"]["name"] == selected_camera]
        
        # Display photos in a grid
        cols = 3
        for i in range(0, len(photos), cols):
            row_photos = photos[i:i+cols]
            columns = st.columns(cols)
            
            for j, photo in enumerate(row_photos):
                if j < len(columns):  # Ensure we don't exceed column count
                    with columns[j]:
                        # Display the image
                        img_url = photo["img_src"]
                        st.image(img_url, use_container_width=True)
                        
                        # Display metadata in an expander
                        with st.expander("Photo Details"):
                            st.write(f"**ID:** {photo['id']}")
                            st.write(f"**Sol:** {photo['sol']}")
                            st.write(f"**Camera:** {photo['camera']['full_name']} ({photo['camera']['name']})")
                            st.write(f"**Earth Date:** {photo['earth_date']}")
                            st.write(f"**Rover Status:** {photo['rover']['status']}")
                            st.markdown(f"[Open full-size image]({img_url})")

# NEAR EARTH OBJECTS PAGE
elif page == "Near Earth Objects":
    st.title("Near Earth Objects Explorer")
    st.markdown("Discover asteroids and comets that pass close to Earth")
    
    # Date range selection (NEO API works with a date range)
    st.sidebar.subheader("Select Date Range")
    start_date = st.sidebar.date_input(
        "Start Date",
        datetime.now() - timedelta(days=7)
    )
    
    end_date = st.sidebar.date_input(
        "End Date",
        datetime.now()
    )
    
    # Check if date range is valid (max 7 days)
    date_difference = (end_date - start_date).days
    if date_difference > 7:
        st.sidebar.warning("Maximum date range is 7 days. Adjusting to first 7 days.")
        end_date = start_date + timedelta(days=7)
    
    # Fetch NEO data
    @st.cache_data(ttl=3600)
    def get_neo_data(start_date, end_date, api_key):
        url = "https://api.nasa.gov/neo/rest/v1/feed"
        params = {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "api_key": api_key
        }
        return fetch_nasa_data(url, params)
    
    with st.spinner("Fetching Near Earth Objects data..."):
        data = get_neo_data(start_date, end_date, api_key)
        
    if data:
        # Process the data
        neo_data = []
        for date, neos in data["near_earth_objects"].items():
            for neo in neos:
                neo_info = {
                    "id": neo["id"],
                    "name": neo["name"],
                    "date": date,
                    "diameter_min_km": neo["estimated_diameter"]["kilometers"]["estimated_diameter_min"],
                    "diameter_max_km": neo["estimated_diameter"]["kilometers"]["estimated_diameter_max"],
                    "is_hazardous": neo["is_potentially_hazardous_asteroid"],
                    "close_approach_date": neo["close_approach_data"][0]["close_approach_date"],
                    "miss_distance_km": float(neo["close_approach_data"][0]["miss_distance"]["kilometers"]),
                    "relative_velocity_kph": float(neo["close_approach_data"][0]["relative_velocity"]["kilometers_per_hour"])
                }
                neo_data.append(neo_info)
        
        df = pd.DataFrame(neo_data)
        
        # Display total count
        st.subheader(f"Found {len(df)} Near Earth Objects between {start_date} and {end_date}")
        
        # Filters
        st.sidebar.subheader("Filters")
        show_hazardous_only = st.sidebar.checkbox("Show potentially hazardous only")
        
        if show_hazardous_only:
            df = df[df["is_hazardous"] == True]
            st.subheader(f"Showing {len(df)} potentially hazardous objects")
        
        # Size filter
        min_size, max_size = st.sidebar.slider(
            "Size Range (km diameter)",
            min_value=0.0,
            max_value=float(df["diameter_max_km"].max()) + 0.5,
            value=(0.0, float(df["diameter_max_km"].max()) + 0.5),
            step=0.1
        )
        
        df = df[(df["diameter_max_km"] >= min_size) & (df["diameter_min_km"] <= max_size)]
        
        # Visualizations
        st.subheader("NEO Size vs. Miss Distance")
        
        # Calculate average diameter for plotting
        df["avg_diameter_km"] = (df["diameter_min_km"] + df["diameter_max_km"]) / 2
        
        fig = px.scatter(
            df,
            x="miss_distance_km",
            y="avg_diameter_km",
            color="is_hazardous",
            size="avg_diameter_km",
            hover_name="name",
            color_discrete_map={True: "red", False: "blue"},
            labels={
                "miss_distance_km": "Miss Distance (km)",
                "avg_diameter_km": "Average Diameter (km)",
                "is_hazardous": "Is Potentially Hazardous"
            },
            title="NEO Size vs. Miss Distance"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Table of NEOs
        st.subheader("Near Earth Objects Data")
        
        # Format the DataFrame for display
        display_df = df.copy()
        display_df["avg_diameter_km"] = display_df["avg_diameter_km"].round(4)
        display_df["miss_distance_km"] = (display_df["miss_distance_km"] / 1000).round(0)  # Convert to thousands of km
        display_df["relative_velocity_kph"] = display_df["relative_velocity_kph"].round(0)
        
        # Rename columns for better display
        display_df = display_df.rename(columns={
            "id": "ID",
            "name": "Name",
            "date": "Date",
            "avg_diameter_km": "Diameter (km)",
            "is_hazardous": "Potentially Hazardous",
            "close_approach_date": "Close Approach Date",
            "miss_distance_km": "Miss Distance (thousand km)",
            "relative_velocity_kph": "Velocity (km/h)"
        })
        
        # Select columns to show
        display_cols = ["Name", "Close Approach Date", "Diameter (km)", "Miss Distance (thousand km)", 
                        "Velocity (km/h)", "Potentially Hazardous"]
        
        st.dataframe(display_df[display_cols], use_container_width=True)

# MARS WEATHER PAGE
elif page == "Mars Weather":
    st.title("Mars Weather Service")
    st.markdown("Explore weather data from the Mars Curiosity rover")
    
    # Note about Mars Weather API
    st.info("The Mars InSight weather service was discontinued in 2021, but we can access archived data.")
    
    # Fetch the latest available Mars weather data
    @st.cache_data(ttl=86400)  # Cache for a day since this is archived data
    def get_mars_weather(api_key):
        url = "https://api.nasa.gov/insight_weather/"
        params = {
            "api_key": api_key,
            "feedtype": "json",
            "ver": "1.0"
        }
        # Due to the discontinuation, we'll use static demo data if the API fails
        try:
            data = fetch_nasa_data(url, params)
            return data
        except:
            # Provide example data from when the service was active
            st.warning("Using archived sample data as the real-time service is no longer available.")
            
            # Sample data structure based on historical InSight data
            return {
                "sol_keys": ["259", "260", "261", "262", "263", "264", "265"],
                "259": {
                    "AT": {"av": -77.064, "ct": 152488, "mn": -99.429, "mx": -13.668},
                    "HWS": {"av": 4.563, "ct": 74455, "mn": 0.156, "mx": 17.617},
                    "PRE": {"av": 761.006, "ct": 144432, "mn": 742.1498, "mx": 780.3891},
                    "WD": {
                        "most_common": {"compass_degrees": 202.5, "compass_point": "SSW", "compass_right": -0.382684, "compass_up": -0.923879, "ct": 11582},
                        "1": {"compass_degrees": 202.5, "compass_point": "SSW", "compass_right": -0.382684, "compass_up": -0.923879, "ct": 11582},
                        "2": {"compass_degrees": 180.0, "compass_point": "S", "compass_right": 0.0, "compass_up": -1.0, "ct": 10306},
                        "3": {"compass_degrees": 225.0, "compass_point": "SW", "compass_right": -0.707107, "compass_up": -0.707107, "ct": 9936},
                    },
                    "First_UTC": "2019-08-19T08:03:59Z",
                    "Last_UTC": "2019-08-20T08:43:34Z",
                    "Season": "winter"
                },
                # Add similar data for other sols...
                "validity_checks": {
                    "259": {"AT": "Pass", "HWS": "Pass", "PRE": "Pass", "WD": "Pass"},
                    # Add similar data for other sols...
                }
            }
    
    weather_data = get_mars_weather(api_key)
    
    if weather_data and "sol_keys" in weather_data:
        # Extracting and organizing the data
        sols = weather_data["sol_keys"]
        
        weather_df = pd.DataFrame()
        
        for sol in sols:
            if sol in weather_data:
                sol_data = weather_data[sol]
                
                # Check if the required weather measurements exist
                temp_data = sol_data.get("AT", {})
                pressure_data = sol_data.get("PRE", {})
                wind_data = sol_data.get("HWS", {})
                
                # Create a row for this sol
                row = {
                    "Sol": int(sol),
                    "Earth Date": sol_data.get("First_UTC", "Unknown"),
                    "Season": sol_data.get("Season", "Unknown"),
                    "Avg Temp (°C)": temp_data.get("av"),
                    "Min Temp (°C)": temp_data.get("mn"),
                    "Max Temp (°C)": temp_data.get("mx"),
                    "Avg Pressure (Pa)": pressure_data.get("av"),
                    "Avg Wind Speed (m/s)": wind_data.get("av"),
                    "Max Wind Speed (m/s)": wind_data.get("mx")
                }
                
                # Append to DataFrame
                weather_df = pd.concat([weather_df, pd.DataFrame([row])], ignore_index=True)
        
        # Format dates
        weather_df["Earth Date"] = pd.to_datetime(weather_df["Earth Date"]).dt.strftime('%Y-%m-%d')
        
        # Display Mars weather data
        st.subheader("Mars Weather Data by Sol")
        st.dataframe(weather_df, use_container_width=True)
        
        # Visualizations
        st.subheader("Temperature Trends on Mars")
        
        # Temperature chart
        temp_fig = px.line(
            weather_df,
            x="Sol",
            y=["Min Temp (°C)", "Avg Temp (°C)", "Max Temp (°C)"],
            title="Temperature Range by Sol",
            labels={"value": "Temperature (°C)", "variable": "Measurement"}
        )
        st.plotly_chart(temp_fig, use_container_width=True)
        
        # Pressure chart
        st.subheader("Atmospheric Pressure on Mars")
        pressure_fig = px.line(
            weather_df,
            x="Sol",
            y="Avg Pressure (Pa)",
            title="Average Atmospheric Pressure by Sol",
            labels={"Avg Pressure (Pa)": "Pressure (Pa)"}
        )
        st.plotly_chart(pressure_fig, use_container_width=True)
        
        # Wind speed chart
        st.subheader("Wind Speed on Mars")
        wind_fig = px.line(
            weather_df,
            x="Sol",
            y=["Avg Wind Speed (m/s)", "Max Wind Speed (m/s)"],
            title="Wind Speed by Sol",
            labels={"value": "Wind Speed (m/s)", "variable": "Measurement"}
        )
        st.plotly_chart(wind_fig, use_container_width=True)
        
        # Mars vs Earth comparison
        st.subheader("Mars vs Earth: Key Environmental Factors")
        
        comparison_data = {
            "Factor": ["Average Temperature", "Atmospheric Pressure", "Gravity", "Day Length"],
            "Mars": ["-63°C", "600 Pa", "3.72 m/s²", "24h 37m"],
            "Earth": ["15°C", "101,325 Pa", "9.81 m/s²", "24h"]
        }
        
        comparison_df = pd.DataFrame(comparison_data)
        st.table(comparison_df)
        
    else:
        st.error("Unable to retrieve Mars weather data. The InSight weather service was discontinued in 2021.")
        st.info("The Mars InSight lander's mission ended in December 2022 after four years of collecting unique science data.")



# Then add this new section for the EPIC API
elif page == "Earth Imagery (EPIC)":
    st.title("Earth Polychromatic Imaging Camera (EPIC)")
    st.markdown("Explore stunning full-disk images of Earth from the Deep Space Climate Observatory satellite")
    
    # Date selection for EPIC images
    st.sidebar.subheader("Select Date")
    epic_date = st.sidebar.date_input(
        "Image Date",
        datetime.now() - timedelta(days=2)  # Usually 2 days delay in processing
    )
    
    # Image type selection
    image_type = st.sidebar.selectbox(
        "Image Type",
        ["Natural Color", "Enhanced Color"],
        index=0
    )
    
    # Map selection to API parameter
    image_type_param = "natural" if image_type == "Natural Color" else "enhanced"
    
    # Fetch EPIC images
    @st.cache_data(ttl=3600)
    def get_epic_images(date, image_type, api_key):
        formatted_date = date.strftime("%Y-%m-%d")
        url = f"https://api.nasa.gov/EPIC/api/{image_type}"
        params = {
            "date": formatted_date,
            "api_key": api_key
        }
        return fetch_nasa_data(url, params)
    
    with st.spinner(f"Fetching EPIC images for {epic_date.strftime('%Y-%m-%d')}..."):
        epic_data = get_epic_images(epic_date, image_type_param, api_key)
    
    if epic_data and len(epic_data) > 0:
        st.success(f"Found {len(epic_data)} Earth images for {epic_date.strftime('%Y-%m-%d')}")
        
        # Create slider for time selection
        if len(epic_data) > 1:
            image_index = st.slider("Select image by time", 0, len(epic_data)-1, 0)
            selected_image = epic_data[image_index]
        else:
            selected_image = epic_data[0]
        
        # Extract image details
        image_date = selected_image["date"].split(" ")[0].replace("-", "/")
        image_time = selected_image["date"].split(" ")[1].split(".")[0]
        image_id = selected_image["identifier"]
        
        # Construct image URL
        image_url = f"https://api.nasa.gov/EPIC/archive/{image_type_param}/{image_date}/png/{image_id}.png?api_key={api_key}"
        
        # Display the image
        st.subheader(f"Earth on {epic_date.strftime('%Y-%m-%d')} at {image_time} UTC")
        st.image(image_url, use_container_width=True)
        
        # Display metadata
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Image Details")
            st.write(f"**Date & Time:** {selected_image['date']} UTC")
            st.write(f"**Image ID:** {image_id}")
            st.write(f"**Centroid Coordinates:** Lat {selected_image['centroid_coordinates']['lat']:.2f}°, Lon {selected_image['centroid_coordinates']['lon']:.2f}°")
            
            if "dscovr_j2000_position" in selected_image:
                st.write("**Satellite Position (km):**")
                st.write(f"X: {selected_image['dscovr_j2000_position']['x']:.0f}")
                st.write(f"Y: {selected_image['dscovr_j2000_position']['y']:.0f}")
                st.write(f"Z: {selected_image['dscovr_j2000_position']['z']:.0f}")
        
        with col2:
            st.subheader("About This View")
            st.write("This image was captured by NASA's Earth Polychromatic Imaging Camera (EPIC) aboard NOAA's Deep Space Climate Observatory spacecraft (DSCOVR).")
            st.write("DSCOVR orbits at Lagrange point 1, approximately 1.5 million km from Earth, providing a unique view of the entire sunlit side of our planet.")
            if image_type == "Natural Color":
                st.write("This natural color image shows Earth as the human eye would see it from space.")
            else:
                st.write("This enhanced color image uses specialized filtering to highlight details in Earth's atmosphere and surface features.")
        
        # Add a feature to compare multiple images if available
        if len(epic_data) > 1:
            st.subheader("Daily Timelapse")
            st.write("View how Earth rotated throughout this day")
            
            show_timelapse = st.checkbox("Show all images from this day")
            
            if show_timelapse:
                # Create a grid of images
                cols = 3  # Number of columns in the grid
                rows = (len(epic_data) + cols - 1) // cols  # Calculate necessary rows
                
                for i in range(0, len(epic_data), cols):
                    row_images = epic_data[i:i+cols]
                    columns = st.columns(cols)
                    
                    for j, img_data in enumerate(row_images):
                        with columns[j]:
                            # Format date for URL
                            img_date = img_data["date"].split(" ")[0].replace("-", "/")
                            img_time = img_data["date"].split(" ")[1].split(".")[0]
                            img_id = img_data["identifier"]
                            
                            # Construct image URL
                            img_url = f"https://api.nasa.gov/EPIC/archive/{image_type_param}/{img_date}/png/{img_id}.png?api_key={api_key}"
                            
                            # Display the image with time caption
                            st.image(img_url, use_container_width=True)
                            st.caption(f"{img_time} UTC")
    
    else:
        st.warning(f"No EPIC images available for {epic_date.strftime('%Y-%m-%d')}. Try selecting a different date.")
        st.info("EPIC images typically have a 1-2 day delay in processing and availability. Try selecting a date from 2-3 days ago.")
        
        # Show sample image if no data available
        st.subheader("Sample EPIC Image")
        st.markdown("Here's an example of what EPIC images look like:")
        st.image("https://epic.gsfc.nasa.gov/epic-galleries/2023/natural/thumbs/epic_1b_20230714001751_01.jpg", use_container_width=True)









# Add footer with API usage info
st.sidebar.markdown("---")
st.sidebar.caption(
    "Note: The DEMO_KEY has a limit of 30 requests/hour and 50/day. "
    "For more usage, get a free API key from NASA."
)
st.sidebar.markdown("[Get a NASA API key](https://api.nasa.gov)")