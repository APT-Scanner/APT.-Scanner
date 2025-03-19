import requests
import time
import pandas as pd
import math
import logging
import json
import os
from datetime import datetime

# Set up logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f'neighborhood_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

logger.info("Script started")

API_KEY = 'AIzaSyBLnQfEYu5AZBgngdkTDpMd7oRWsK7imFM'
endpoint = 'https://places.googleapis.com/v1/places:searchNearby'
headers = {
    'Content-Type': 'application/json',
    'X-Goog-FieldMask': 'places.displayName,places.id,places.location,places.rating,places.userRatingCount,places.types'
}

logger.info(f"Using Places API endpoint: {endpoint}")
    
keywords = ["mall", "center", "centre", "קניון", "מרכז"]
def contains_shopping_keyword(name):
    name_lower = name.lower()
    return any(kw in name_lower for kw in keywords)

allowed_languages = ["en", "iw"]
def valid_mall(place):
    name = place["displayName"]
    lang_code = name.get("languageCode")
    if lang_code not in allowed_languages:
        return False
    if not contains_shopping_keyword(name.get("text", "")):
        return False
    if place.get("rating", 0) < 2.5 or place.get("userRatingCount", 0) < 20:
        return False
    return True

# Function to calculate the Haversine distance between two geographical points
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371  
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# This function searches for places of a specific type within a specified radius from two centers
def get_nearby_places_two_circles(lat, lng, place_type, radius=1000):
    logger.info(f"Getting {place_type} places near ({lat}, {lng}) with radius {radius}m")
    
    lat_offset = 0.0045
    centers = [(lat, lng), (lat + lat_offset, lng)]
    places_collected = []

    for center_lat, center_lng in centers:
        logger.info(f"Searching from center ({center_lat}, {center_lng})")
        payload = {
            "includedTypes": [place_type],
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": center_lat, "longitude": center_lng},
                    "radius": radius
                }
            },
            "maxResultCount": 20
        }
        
        try:
            logger.debug(f"API request payload: {json.dumps(payload)}")
            resp = requests.post(endpoint, headers=headers, json=payload, params={"key": API_KEY})
            
            logger.info(f"API response status code: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                places = data.get("places", [])
                logger.info(f"Found {len(places)} {place_type} places at center ({center_lat}, {center_lng})")
                places_collected.extend(places)
            else:
                error_msg = resp.text
                logger.error(f"API request failed: {resp.status_code} - {error_msg}")
                logger.error(f"Request details: {place_type} at ({center_lat}, {center_lng})")
        except Exception as e:
            logger.exception(f"Exception during API request: {str(e)}")
        
        # API rate limiting
        logger.debug("Sleeping for 1 second for rate limiting")
        time.sleep(1)

    unique_places = {p['id']: p for p in places_collected}
    logger.info(f"Total unique {place_type} places after de-duplication: {len(unique_places)}")
    return list(unique_places.values())

# This function geocodes a neighborhood name to get its latitude and longitude using Google Maps API
def get_neighborhood_coordinates(neighborhood_name):
    logger.info(f"Geocoding neighborhood: {neighborhood_name}")
    geo_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": f"{neighborhood_name}, Tel Aviv, Israel", "key": API_KEY}
    
    try:
        logger.debug(f"Geocoding API request for: {neighborhood_name}")
        resp = requests.get(geo_url, params=params)
        
        logger.info(f"Geocoding API response code: {resp.status_code}")
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            if results:
                loc = results[0]["geometry"]["location"]
                logger.info(f"Found coordinates for {neighborhood_name}: ({loc['lat']}, {loc['lng']})")
                return loc["lat"], loc["lng"]
            else:
                logger.warning(f"No geocoding results found for {neighborhood_name}")
        else:
            logger.error(f"Geocoding error: {resp.status_code} - {resp.text}")
    except Exception as e:
        logger.exception(f"Exception during geocoding request: {str(e)}")
    
    return None, None

neighborhoods = ["Florentin", "Neve Tzedek", "Lev HaIr", "Jaffa",
                  "Ramat Aviv", "Sarona", "Basel", "Yad Eliyahu"]

logger.info(f"Processing {len(neighborhoods)} neighborhoods: {', '.join(neighborhoods)}")

all_data = []
for i, nbh in enumerate(neighborhoods):
    logger.info(f"===== Processing neighborhood {i+1}/{len(neighborhoods)}: {nbh} =====")
    
    try:
        lat, lng = get_neighborhood_coordinates(nbh)
        if not lat:
            logger.warning(f"Skipping {nbh} due to failed geocoding")
            continue

        logger.info(f"Collecting data for {nbh}...")
        
        bars = get_nearby_places_two_circles(lat, lng, "bar")
        logger.info(f"{nbh}: Found {len(bars)} bars")
        
        restaurants = get_nearby_places_two_circles(lat, lng, "restaurant")
        logger.info(f"{nbh}: Found {len(restaurants)} restaurants")
        
        clubs = get_nearby_places_two_circles(lat, lng, "night_club")
        logger.info(f"{nbh}: Found {len(clubs)} night clubs")
        
        primary_schools = get_nearby_places_two_circles(lat, lng, "primary_school")
        logger.info(f"{nbh}: Found {len(primary_schools)} primary schools")
        
        elementary_schools = get_nearby_places_two_circles(lat, lng, "elementary_school")
        logger.info(f"{nbh}: Found {len(elementary_schools)} elementary schools")
        
        secondary_schools = get_nearby_places_two_circles(lat, lng, "secondary_school")
        logger.info(f"{nbh}: Found {len(secondary_schools)} secondary schools")
        
        high_schools = get_nearby_places_two_circles(lat, lng, "high_school")
        logger.info(f"{nbh}: Found {len(high_schools)} high schools")
        
        malls = get_nearby_places_two_circles(lat, lng, "shopping_mall")
        logger.info(f"{nbh}: Found {len(malls)} shopping malls")
        
        beaches = get_nearby_places_two_circles(lat, lng, "beach", radius=3000) 
        logger.info(f"{nbh}: Found {len(beaches)} beaches (with extended radius)")

        if beaches:
            min_beach_dist = min(
                haversine_distance(lat, lng, b['location']['latitude'], b['location']['longitude'])
                for b in beaches
            )
            logger.info(f"{nbh}: Closest beach is {round(min_beach_dist, 2)}km away")
        else:
            min_beach_dist = None
            logger.warning(f"{nbh}: No beaches found within search radius")

        filtered_malls = [m for m in malls if valid_mall(m)]
        logger.info(f"{nbh}: {len(filtered_malls)} malls meet quality criteria (from total {len(malls)})")
        
        entertainment_places = bars + restaurants + clubs
        unique_entertainment_places = {p['id']: p for p in entertainment_places}
        logger.info(f"{nbh}: {len(unique_entertainment_places)} unique entertainment places")

        data = {
            "Neighborhood": nbh,
            "Latitude": lat,
            "Longitude": lng,
            "Bars_Count": len(bars),
            "Restaurants_Count": len(restaurants),
            "Clubs_Count": len(clubs),
            "Shopping_Malls_Count": len(filtered_malls),
            "Unique_Entertainment_Count": len(unique_entertainment_places),
            "Primary_Schools_Count": len(primary_schools),
            "Elementary_Schools_Count": len(elementary_schools),
            "Secondary_Schools_Count": len(secondary_schools),
            "High_Schools_Count": len(high_schools),
            "Closest_Beach_Distance_km": round(min_beach_dist, 2) if min_beach_dist else None
        }
        all_data.append(data)
        logger.info(f"Successfully processed {nbh}")
    except Exception as e:
        logger.exception(f"Error processing neighborhood {nbh}: {str(e)}")

try:
    df = pd.DataFrame(all_data)
    output_file = "tel_aviv_neighborhoods_extended.csv"
    df.to_csv(output_file, index=False)
    logger.info(f"Data successfully saved to {output_file}")
    logger.info(f"Final data summary:\n{df}")
except Exception as e:
    logger.exception(f"Error saving data to CSV: {str(e)}")

logger.info("Script completed")
print(f"Log file created: {log_file}")
