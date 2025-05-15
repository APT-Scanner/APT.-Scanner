import requests
import json
from typing import Dict, Any
from dotenv import load_dotenv
import os

load_dotenv()

class Yad2Scraper:
    """A scalable and dynamic scraper for Yad2 real estate listings."""
    
    BASE_URL = "https://www.yad2.co.il/realestate/_next/data"
    
    AREAS = {
        "תל אביב והמרכז": 2
    }
    
    SUB_AREAS = {
        "תל אביב": 1
    }
    
    PROPERTY_GROUPS = {
        "apartments": "apartments",
        "houses": "houses",
        "misc": "misc",
        "commercial": "commercial",
    }
    
    PROPERTY_TYPES = {
        "דירה": 1,
        "דירת גן": 3,
        "בית פרטי/קוטג'": 5,
        "גג/פנטהאוז": 6,
        "מגרשים": 33,
        "דופלקס": 7,
        "תיירות ונופש": 25,
        "דו משפחתי": 39,
        "מרתף/פרטר": 49,
        "טריפלקס": 51,
        "יחידת דיור": 11,
        "משק חקלאי/נחלה": 32,
        "משק עזר": 55,
        "החלפת דירות": 31,
        "דיור מגון": 61,
        "סאבלט": 43,
        "בניין מגורים": 44,
        "סטודיו/לופט": 4,
        "מחסן": 45,
        "חניה": 30,
        "קב' רכישה/זכות לנכס": 50,
        "כללי": 41,
    }
    
    PROPERTY_CONDITION = {
        "חדש מקבלן": 1,
        "משופץ": 6,
        "שמור": 2,
        "חדש": 3,
        "דרוש שיפוץ": 5,
    }
    
    PROPERTY_CHARACTERISTICS = {
        "parking": "חניה",
        "elevator": "מעלית",
        "airConditioner": "מיזוג",
        "balcony": "מרפסת",
        "shelter": "ממ״ד",
        "bars": "סורגים",
        "warhouse": "מחסן",
        "accessibility": "גישה לנכים",
        "renovated": "משופץ",
        "furniture": "מרוהט", 
        "pets": "חיות מחמד",
        "forPartners": "לשותפים",
    }
    
    def __init__(self, api_username: str, api_password: str):
        """Initialize the scraper with API credentials."""
        self.api_username = api_username
        self.api_password = api_password
        self.hash_id = None  # Will be set later
        
    def set_hash_id(self, hash_id: str):
        """Set the hash ID for the API requests."""
        self.hash_id = hash_id

    def from_json_config(self, config: Dict[str, Any]) -> Dict:
        """
        Create scraper parameters from a JSON configuration that matches Yad2's API structure.
        
        Parameters:
        - config: Dictionary containing Yad2 search parameters as provided in the example
        
        Returns:
        - Dictionary of parameters to use with the scrape method
        """
        params = {}
        
        # Process price range
        if "priceRange" in config:
            min_price, max_price = config["priceRange"]
            if min_price is not None and max_price is not None:
                params["price"] = f"{min_price}-{max_price}"
        
        # Process room range
        if "roomRange" in config:
            min_rooms, max_rooms = config["roomRange"]
            if min_rooms is not None and max_rooms is not None:
                params["rooms"] = f"{min_rooms}-{max_rooms}"
        
        # Process floor range
        if "floorRange" in config:
            min_floor, max_floor = config["floorRange"]
            if min_floor is not None and max_floor is not None:
                params["floor"] = f"{min_floor}-{max_floor}"
        
        # Process square meter range
        if "squareMeterRange" in config:
            min_sqm, max_sqm = config["squareMeterRange"]
            if min_sqm is not None and max_sqm is not None:
                params["squaremeter"] = f"{min_sqm}-{max_sqm}"
        
        # Process built square meter range
        if "squareMeterBuildRange" in config:
            min_sqm_build, max_sqm_build = config["squareMeterBuildRange"]
            if min_sqm_build is not None and max_sqm_build is not None:
                params["squaremeter_build"] = f"{min_sqm_build}-{max_sqm_build}"
        
        # Process ad attributes
        if "adAttributes" in config:
            ad_attributes = config["adAttributes"]
            params["image_only"] = ad_attributes.get("isImageOnly", False)
            params["price_only"] = ad_attributes.get("isPriceOnly", False)
            params["settlements_only"] = ad_attributes.get("isSettlementsOnly", False)
            params["price_dropped"] = ad_attributes.get("isPriceDropped", False)
        
        # Process advertiser attributes
        if "advertiser" in config:
            advertiser = config["advertiser"]
            params["from_brokerage"] = advertiser.get("isFromBrokerage", False)
            params["new_from_contractor"] = advertiser.get("isNewFromContractor", False)
        
        # Process property types
        if "propertyTypes" in config:
            selected_property_types = []
            for prop_type in config["propertyTypes"]:
                if prop_type.get("checked", False):
                    selected_property_types.append(prop_type["value"])
            
            if selected_property_types:
                params["property_type"] = selected_property_types
        
        # Process property characteristics
        if "propertyCharacteristics" in config:
            for characteristic in config["propertyCharacteristics"]:
                char_key = characteristic.get("key")
                if char_key in self.PROPERTY_CHARACTERISTICS.keys():
                    params[char_key] = True
        
        # Process property condition
        if "propertyCondition" in config:
            selected_conditions = []
            for condition in config["propertyCondition"]:
                if condition.get("checked", False):
                    selected_conditions.append(condition["value"])
            
            if selected_conditions:
                params["property_condition"] = selected_conditions
        
        # Process locations
        if "locations" in config:
            for location in config["locations"]:
                if "topAreaId" in location:
                    params["top_area"] = location["topAreaId"]
                if "areaId" in location:
                    params["area"] = location["areaId"]
                if "cityId" in location:
                    params["city"] = location["cityId"]
                if "hoodId" in location and location["hoodId"]:
                    params["neighborhood"] = location["hoodId"]
                if "streetId" in location and location["streetId"]:
                    params["street"] = location["streetId"]
                break
        
        # Process page number
        if "page" in config:
            params["page"] = config["page"]
        
        # Process free text
        if "freeText" in config and config["freeText"]:
            params["free_text"] = config["freeText"]
        
        # Process sorting
        if "sort" in config and config["sort"]:
            params["sort"] = config["sort"]
            
        # Process entrance date
        if "entranceDate" in config and config["entranceDate"]:
            params["entrance_date"] = config["entranceDate"]
        
        return params
        
    def build_query_params(self, **kwargs) -> Dict[str, str]:
        """
        Build query parameters dynamically based on user input.
        
        Parameters:
        - top_area: int or str - Top-level area ID or name
        - area: int or str - Sub-area ID or name
        - city: int or str - City ID or name
        - neighborhood: str - Neighborhood ID
        - street: str - Street ID
        - property_group: List[str] - Property groups (apartments, houses, misc, commercial)
        - property_type: List[int or str] - Property types (can be IDs or names)
        - rooms: str - Room range (e.g., "2.5-3", "1-4")
        - price: str - Price range (e.g., "2000-17000")
        - squaremeter: str - Square meter range (e.g., "40-480")
        - squaremeter_build: str - Built square meter range (e.g., "20-480")
        - property_condition: List[int or str] - Property condition (can be IDs or names)
        - floor: str - Floor range (e.g., "2-19")
        - image_only: bool - Only listings with images
        - price_only: bool - Only listings with prices
        - settlements_only: bool - Only settlement listings
        - price_dropped: bool - Only listings with dropped prices
        - from_brokerage: bool - Only from brokerage
        - new_from_contractor: bool - Only new from contractors
        - parking: bool - Has parking
        - elevator: bool - Has elevator
        - air_conditioner: bool - Has air conditioner
        - balcony: bool - Has balcony
        - shelter: bool - Has shelter
        - bars: bool - Has bars
        - warhouse: bool - Has warehouse
        - accessibility: bool - Is accessible
        - renovated: bool - Is renovated
        - furniture: bool - Has furniture
        - pets: bool - Allows pets
        - for_partners: bool - For partners
        - free_text: str - Free text search
        - sort: str - Sort criteria
        - entrance_date: str - Entrance date
        
        Returns:
        - Dictionary of query parameters
        """
        params = {}
        
        # Process top area
        if "top_area" in kwargs:
            top_area = kwargs["top_area"]
            if isinstance(top_area, str) and top_area in self.AREAS:
                params["topArea"] = str(self.AREAS[top_area])
            else:
                params["topArea"] = str(top_area)
        
        # Process area
        if "area" in kwargs:
            area = kwargs["area"]
            if isinstance(area, str) and area in self.SUB_AREAS:
                params["area"] = str(self.SUB_AREAS[area])
            else:
                params["area"] = str(area)
        
        # Process city
        if "city" in kwargs:
            params["city"] = str(kwargs["city"])
        
        # Process neighborhood
        if "neighborhood" in kwargs:
            params["neighborhood"] = str(kwargs["neighborhood"])
            
        # Process street
        if "street" in kwargs:
            params["street"] = str(kwargs["street"])
        
        # Process property group
        if "property_group" in kwargs:
            property_groups = kwargs["property_group"]
            if isinstance(property_groups, list):
                params["propertyGroup"] = ",".join(property_groups)
            else:
                params["propertyGroup"] = property_groups
        
        # Process property type
        if "property_type" in kwargs:
            property_types = kwargs["property_type"]
            if isinstance(property_types, list):
                # Convert names to IDs if necessary
                property_ids = []
                for prop in property_types:
                    if isinstance(prop, str) and prop in self.PROPERTY_TYPES:
                        property_ids.append(str(self.PROPERTY_TYPES[prop]))
                    else:
                        property_ids.append(str(prop))
                params["property"] = ",".join(property_ids)
            else:
                params["property"] = property_types
        
        # Process rooms
        if "rooms" in kwargs:
            params["rooms"] = kwargs["rooms"]
        
        # Process price
        if "price" in kwargs:
            params["price"] = kwargs["price"]
        
        # Process square meter
        if "squaremeter" in kwargs:
            params["squaremeter"] = kwargs["squaremeter"]
        
        # Process built square meter
        if "squaremeter_build" in kwargs:
            params["squareMeterBuild"] = kwargs["squaremeter_build"]
        
        # Process property condition
        if "property_condition" in kwargs:
            property_conditions = kwargs["property_condition"]
            if isinstance(property_conditions, list):
                # Convert names to IDs if necessary
                condition_ids = []
                for cond in property_conditions:
                    if isinstance(cond, str) and cond in self.PROPERTY_CONDITION:
                        condition_ids.append(str(self.PROPERTY_CONDITION[cond]))
                    else:
                        condition_ids.append(str(cond))
                params["propertyCondition"] = ",".join(condition_ids)
            else:
                params["propertyCondition"] = property_conditions
        
        # Process floor
        if "floor" in kwargs:
            params["floor"] = kwargs["floor"]
        
        # Process free text
        if "free_text" in kwargs:
            params["freeText"] = kwargs["free_text"]
            
        # Process sort
        if "sort" in kwargs:
            params["sort"] = kwargs["sort"]
            
        # Process entrance date
        if "entrance_date" in kwargs:
            params["entranceDate"] = kwargs["entrance_date"]
        
        # Process boolean parameters
        boolean_param_mapping = {
            "image_only": "imageOnly",
            "price_only": "priceOnly",
            "settlements_only": "settlementsOnly",
            "price_dropped": "priceDropped",
            "from_brokerage": "fromBrokerage",
            "new_from_contractor": "newFromContractor",
            "parking": "parking",
            "elevator": "elevator",
            "air_conditioner": "airConditioner",
            "balcony": "balcony",
            "shelter": "shelter",
            "bars": "bars",
            "warhouse": "warhouse",
            "accessibility": "accessibility",
            "renovated": "renovated",
            "furniture": "furniture",
            "pets": "pets",
            "for_partners": "forPartners",
        }
        
        for param_name, url_param in boolean_param_mapping.items():
            if param_name in kwargs and kwargs[param_name]:
                params[url_param] = "1"
        
        return params
    
    def build_url(self, page: int = 1, **kwargs) -> str:
        """Build the full URL for the API request."""
        if not self.hash_id:
            raise ValueError("Hash ID is not set. Call set_hash_id() first.")
        
        params = self.build_query_params(**kwargs)
        if "page" in kwargs:
            params["page"] = str(kwargs["page"])
        else:
            params["page"] = str(page)
        
        # Construct the base URL
        url = f"{self.BASE_URL}/{self.hash_id}/rent.json"
        
        # Add query parameters
        if params:
            query_string = "&".join([f"{key}={value}" for key, value in params.items()])
            url = f"{url}?{query_string}"
        
        return url
    
    def scrape_apt_listing(self, page: int = 1, **kwargs) -> Dict[str, Any]:
        """
        Scrape listings based on provided parameters.
        
        Parameters:
        - page: int - Page number
        - **kwargs: Additional parameters for filtering (see build_query_params)
        
        Returns:
        - Parsed JSON data
        """

        url = self.build_url(page=page, **kwargs)
        payload = {
            "api_key": os.getenv("SCRAPEOWL_API_KEY"),
            "url": url,
            "json_response": True
        }
        headers = {
            "Content-Type": "application/json"
        }
        response = requests.post("https://api.scrapeowl.com/v1/scrape", data=json.dumps(payload), headers=headers)
        
        try:
            json_data = json.loads(response.content)
            if 'html' in json_data:
                content = json.loads(json_data['html'])
                private_listings = content['pageProps']['feed']['private']
                platinum_listings = content['pageProps']['feed']['platinum']
                combined_listings = private_listings + platinum_listings
                return combined_listings
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error parsing response: {e}")
            return {"error": str(e), "raw_response": response.text}
        
    def save_to_json(self, data: Dict[str, Any], file_path: str = 'response.json'):
        """Save the scraped data to a JSON file."""
        with open(file_path, 'w', encoding='utf-8') as f:
            pretty_json = json.dumps(data, indent=4, ensure_ascii=False)
            f.write(pretty_json)
        print(f"Data successfully saved to {file_path}")

    def scrape_hood_data(self, hood_id) -> Dict[str, Any]:
        url = f'https://gw.yad2.co.il/neighborhood-survey/{hood_id}/'

        payload = {
            "api_key": os.getenv("SCRAPEOWL_API_KEY"),
            "url": url,
            "json_response": True
        }
        headers = {
            "Content-Type": "application/json"
        }
        response = requests.post("https://api.scrapeowl.com/v1/scrape", data=json.dumps(payload), headers=headers)
        
        try:
            json_data = json.loads(response.content)
            if 'html' in json_data:
                content = json.loads(json_data['html'])
                hood_data = content['data']['segmantList']
                return hood_data
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error parsing response: {e}")
            return {"error": str(e), "raw_response": response.text}
        
    def scrape_hood_nearby_education(self, city_id, hood_id) -> Dict[str, Any]:
        
        url = f'https://gw.yad2.co.il/nearby-education/?cityId={city_id}&neighborhoodId={hood_id}'

        payload = {
            "api_key": os.getenv("SCRAPEOWL_API_KEY"),
            "url": url,
            "json_response": True
        }
        headers = {
            "Content-Type": "application/json"
        }
        response = requests.post("https://api.scrapeowl.com/v1/scrape", data=json.dumps(payload), headers=headers)
        
        try:
            json_data = json.loads(response.content)
            if 'html' in json_data:
                content = json.loads(json_data['html'])
                education_data = content['data']
                return education_data
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error parsing response: {e}")
            return {"error": str(e), "raw_response": response.text}
        
def is_listing_still_alive(token: str):
    url = f"https://www.yad2.co.il/realestate/item/{token}"
    try:
        payload = {
            "api_key": os.getenv("SCRAPEOWL_API_KEY"),
            "url": url,
            "json_response": True
        }
        headers = {
            "Content-Type": "application/json"
        }
        #response = requests.post("https://api.scrapeowl.com/v1/scrape", data=json.dumps(payload), headers=headers)
        
        return True
    except:
        return False


# Example usage
if __name__ == "__main__":
    # Initialize the scraper
    api_username = os.getenv('SCRAPER_API_USERNAME')
    api_password = os.getenv('SCRAPER_API_PASSWORD')
    scraper = Yad2Scraper(api_username, api_password)
    
    # Set the hash ID (this changes periodically on the Yad2 website)
    scraper.set_hash_id('K8ZXlI0K9KoJKzwo7O4rZ')
    
    direct_params = {
        'top_area': 2,           
        'area': 1,               
        'city': 5000,            # Tel Aviv city area       
        'image_only': True,      
        'price_only': True,      
    }

    results = scraper.scrape_apt_listing(**direct_params)
    #results = scraper.scrape_hood_data(1461)
    
    scraper.save_to_json(results)