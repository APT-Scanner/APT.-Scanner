import urllib.parse
import requests
import json
from typing import Dict, Any
from bs4 import BeautifulSoup
import re
import os

class MadlanScraper:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def extract_metrics_from_html(self, html_content: str) -> Dict[str, str]:
        soup = BeautifulSoup(html_content, 'html.parser')
        metrics = {}
        metric_divs = soup.find_all("div", attrs={"data-auto": re.compile(r"^metric-")})
        for div in metric_divs:
            value_div = div.find("div", class_="css-i8008d")
            label_div = div.find("div", class_="css-efxhiv")
            if value_div and label_div:
                label = label_div.get_text(strip=True)
                value = value_div.get_text(strip=True)
                metrics[label] = value
        
        overview_block = soup.find("div", attrs={"data-auto": "AreaOverview-block"})
        if overview_block:
            overview_text = overview_block.find("div", class_="css-ixartp")
            if overview_text:
                metrics["סקירה כללית"] = overview_text.get_text(strip=True)

        return metrics

    def build_neighborhood_string(self, neighborhood: str, city: str, country: str = "ישראל") -> str:
        return f"שכונה-{neighborhood}-{city}-{country}"

    def encode_to_url(self, text: str) -> str:
        return urllib.parse.quote(text)

    def build_url(self, neighborhood: str, city: str, country: str = "ישראל") -> str:
        base_url = "https://www.madlan.co.il/area-info/"

        full_path = f"שכונה-{neighborhood}-{city}-{country}".replace(" ", "-")

        query_params = {
            "term": full_path,
            "marketplace": "residential"
        }

        query_string = "&".join([f"{k}={v}" for k, v in query_params.items()])
        full_url = f"{base_url}{full_path}?{query_string}"

        return full_url

    def scrape(self, neighborhood: str, city: str, country: str = "ישראל", **kwargs) -> Dict[str, Any]:
        url = self.build_url(neighborhood=neighborhood, city=city, country=country, **kwargs)
        payload = {
            "api_key": self.api_key,
            "url": url,
            "json_response": True
        }
        headers = {
            "Content-Type": "application/json"
        }
        response = requests.post("https://api.scrapeowl.com/v1/scrape", data=json.dumps(payload), headers=headers)
        try:
            html_content = response.json().get('html', '')
            if not html_content:
                raise ValueError("No HTML content found in the response.")
            return self.extract_metrics_from_html(html_content)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"שגיאה בניתוח התגובה: {e}")
            return {"error": str(e), "raw_response": response.text}

    def save_to_json(self, data: Dict[str, Any], file_path: str = 'response.json'):
        with open(file_path, 'w', encoding='utf-8') as f:
            pretty_json = json.dumps(data, indent=4, ensure_ascii=False)
            f.write(pretty_json)
        print(f"הנתונים נשמרו בהצלחה ל-{file_path}")

if __name__ == "__main__":
    scraper = MadlanScraper(api_key=os.getenv("SCRAPEOWL_API_KEY"))
    
    with open("data/sources/yad2_hood_mapping.json", "r", encoding='utf-8') as f:
        neighborhoods = json.load(f)
    
    results = {}
    
    for neighborhood in neighborhoods:
        # Use madlan_name if available, otherwise use regular neighborhood_name
        neighborhood_name = neighborhood.get("madlan_name", neighborhood["neigborhood_name"])
        city_name = neighborhood["city_name"]
        country = "ישראל"
        
        print(f"Scraping data for {neighborhood_name}, {city_name}...")
        
        try:
            data = scraper.scrape(
                neighborhood=neighborhood_name, 
                city=city_name, 
                country=country
            )
            
            # Add metadata to the scraped data
            results[neighborhood["hoodId"]] = {
                "neighborhood_id": neighborhood["hoodId"],
                "neighborhood_name": neighborhood["neigborhood_name"],
                "madlan_name": neighborhood.get("madlan_name"),
                "city_name": city_name,
                "scraped_data": data,
                "scraped_with_madlan_name": "madlan_name" in neighborhood
            }
            
            print(f"Successfully scraped data for {neighborhood_name}")
            
        except Exception as e:
            print(f"Failed to scrape {neighborhood_name}: {e}")
            results[neighborhood["hoodId"]] = {
                "neighborhood_id": neighborhood["hoodId"],
                "neighborhood_name": neighborhood["neigborhood_name"],
                "madlan_name": neighborhood.get("madlan_name"),
                "city_name": city_name,
                "error": str(e),
                "scraped_with_madlan_name": "madlan_name" in neighborhood
            }
    
    # Save all results to a JSON file
    output_file = "data/sources/madlan_scraped_data.json"
    scraper.save_to_json(results, output_file)
    print(f"All results saved to {output_file}")
    print(f"Successfully scraped {len([r for r in results.values() if 'error' not in r])} neighborhoods")
    print(f"Failed to scrape {len([r for r in results.values() if 'error' in r])} neighborhoods")