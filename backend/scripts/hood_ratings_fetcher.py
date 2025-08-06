
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from data.scrapers.yad2_scraper import Yad2Scraper
import json
import time

scraper = Yad2Scraper()
neighborhoods_to_fetch = []
results = {}

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
        result = scraper.scrape_hood_data(hood_id)
        results[hood_id] = result
        print(f"Finished fetching ratings for hood {hood_id}")
        time.sleep(2)
    except Exception as e:
        print(f"Error fetching ratings for hood {hood_id}: {e}")
        time.sleep(2)
    
with open(f'backend/data/sources/hood_ratings.json', 'w', encoding='utf-8') as file:
    json.dump(results, file, indent=4, ensure_ascii=False)
    print(f"Finished fetching ratings for {len(results)} hoods")

