from populate_database import populate_listings
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from data.scrapers.yad2_scraper import Yad2Scraper
from data.processing.parse_listings import parse_listings
import json
import time

scraper = Yad2Scraper()
neighborhoods_to_fetch = []

with open('backend/data/sources/yad2_hood_mapping.json', 'r', encoding='utf-8') as file:
    hood_mapping = json.load(file)
    for hood in hood_mapping:
        neighborhoods_to_fetch.append(hood['hoodId'])

for hood_id in neighborhoods_to_fetch:
    direct_params = {
        'top_area': 2,           
        'area': 1,               
        'city': 5000,
        'neighborhood': hood_id,
        'image_only': True,      
        'price_only': True,     
    }
    try:
        results = scraper.scrape_apt_listing(num_requested_pages=1, **direct_params)
        parsed_results = parse_listings(results)
        populate_listings(parsed_results)
        print(f"Finished fetching listings for hood {hood_id}")
        time.sleep(3)
    except Exception as e:
        print(f"Error fetching listings for hood {hood_id}: {e}")
        time.sleep(3)

