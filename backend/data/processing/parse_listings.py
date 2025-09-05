import json
import os
import sys

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)

from backend.data.scrapers.yad2_scraper import Yad2Scraper
from backend.src.utils.attributes_mapping import ATTRIBUTE_EN_TO_HE_MAPPING, map_hebrew_to_english_attributes

# --- Configuration & Helper Data ---

# Define property types considered relevant for standard apartment hunting
VALID_PROPERTY_TYPES = {'דירה', 'דופלקס', 'גג/ פנטהאוז'}
MINIMUM_PRICE_THRESHOLD = 500

# Mapping for property condition IDs found in the sample data
# You might need to expand this based on all possible values in your full dataset
PROPERTY_CONDITION_MAP = {
    2: {'name_he': 'משופץ', 'name_en': 'Renovated'},
    3: {'name_he': 'מצב טוב', 'name_en': 'Good Condition'},
    6: {'name_he': 'חדש מקבלן', 'name_en': 'New from Contractor'}
}

# --- Main Parsing Function ---

def parse_listings(raw_data):
    """
    Loads listing data from a JSON file, filters for relevant apartment listings,
    and structures the data for database insertion.

    Args:
        filepath (str): The path to the JSON file containing the listing data.

    Returns:
        dict: A dictionary containing lists of structured data for each table:
              {'listings': [], 'images': [],
               'property_conditions': []}
              Returns None if the file cannot be read or parsed.
    """

    listings_data = []
    images_data = []
    property_conditions_data = []

    processed_condition_ids = set()

    print(f"Processing {len(raw_data)} raw listings...")
    filtered_count = 0

    for listing in raw_data:
        # --- Filtering ---
        # Basic structure checks
        if not all(k in listing for k in ['orderId', 'token', 'price', 'address', 'additionalDetails', 'metaData']):
            filtered_count += 1
            continue

        # Essential nested structure checks
        address_info = listing.get('address', {})
        details_info = listing.get('additionalDetails', {})
        meta_info = listing.get('metaData', {})
        prop_info = details_info.get('property', {})
        condition_info = details_info.get('propertyCondition', {})
        coords_info = address_info.get('coords', {})
        house_info = address_info.get('house', {})

        if not all([address_info, details_info, meta_info, prop_info]):
             filtered_count += 1
             continue

        # Extract essential fields for filtering
        price = listing.get('price')
        prop_type = prop_info.get('text')
        rooms = details_info.get('roomsCount')
        sqm = details_info.get('squareMeter')
        city = address_info.get('city', {}).get('text')
        street = address_info.get('street', {}).get('text')

        # Apply filters
        try:
            # Check price validity
            if price is None or not isinstance(price, (int, float)) or price <= MINIMUM_PRICE_THRESHOLD:
                filtered_count += 1
                continue
            # Check property type relevance
            if prop_type not in VALID_PROPERTY_TYPES:
                filtered_count += 1
                continue
            # Check essential details exist
            if rooms is None or sqm is None or city is None or street is None:
                filtered_count += 1
                continue
            # Convert rooms to float, handle potential errors
            rooms_float = float(rooms)
            sqm_int = int(sqm)

        except (ValueError, TypeError):
             # Handle cases where rooms/sqm are not valid numbers
             filtered_count += 1
             continue


        # --- Data Extraction (If Filters Passed) ---
        order_id = listing['orderId']
        token = listing['token']
        #link_yad2 = f'https://www.yad2.co.il/realestate/item/{token}'

        # Prepare listing dictionary matching the DB schema
        listing_entry = {
            'listing_id': order_id,
            'yad2_url_token': token,
            'subcategory_id': listing.get('subcategoryId'),
            'category_id': listing.get('categoryId'),
            'ad_type': listing.get('adType'),
            'price': price,
            'property_type': prop_type,
            'rooms_count': rooms_float,
            'square_meter': sqm_int,
            'property_condition_id': condition_info.get('id'),
            'cover_image_url': meta_info.get('coverImage'),
            'video_url': meta_info.get('video'),
            'priority': listing.get('priority'),
            'city': city,
            'area': address_info.get('area', {}).get('text'),
            'neighborhood_text': address_info.get('neighborhood', {}).get('text'),
            'street': street,
            'house_number': house_info.get('number'),
            'floor': house_info.get('floor'),
            'longitude': coords_info.get('lon'),
            'latitude': coords_info.get('lat'),
            'attributes': [],  # Initialize empty attributes list for enrich_listings function
        }
        listings_data.append(listing_entry)

        # Extract Images
        image_urls = meta_info.get('images', [])
        if isinstance(image_urls, list):
            for img_url in image_urls:
                if img_url: # Ensure URL is not empty
                    images_data.append({
                        'listing_id': order_id,
                        'image_url': img_url
                    })


        # Extract Property Condition
        condition_id = condition_info.get('id')
        if condition_id is not None and condition_id not in processed_condition_ids:
             condition_details = PROPERTY_CONDITION_MAP.get(condition_id)
             if condition_details:
                 property_conditions_data.append({
                     'condition_id': condition_id,
                     'condition_name_he': condition_details['name_he'],
                     'condition_name_en': condition_details['name_en']
                 })
                 processed_condition_ids.add(condition_id)
             else:
                 # Handle unknown condition IDs if necessary (e.g., add with NULL names)
                 print(f"Warning: Unknown property condition ID {condition_id} for order_id {order_id}")


    print(f"Filtering complete. Kept {len(listings_data)} listings, filtered out {filtered_count}.")

    return {
        'listings': listings_data,
        'images': images_data,
        'property_conditions': property_conditions_data
    }


def enrich_listings(listings_data, scraper_instance=None):
    """
    Enrich the listings data with the attributes from the yad2 api
    """
    try:
        # Use provided scraper instance or create new one
        if scraper_instance is None:
            scraper = Yad2Scraper()
        else:
            scraper = scraper_instance
            
        for listing in listings_data:
            try:
                result = scraper.get_attributes(listing['yad2_url_token'])
                
                # Safely extract description (provide default if missing)
                listing['description'] = result.get('description', '')
                
                # Safely extract active features (provide default if missing)
                active_features = result.get('active_features', [])
                
                # Map Hebrew features to English attributes
                english_attributes = map_hebrew_to_english_attributes(active_features)
                
                # Ensure attributes list exists before extending
                if 'attributes' not in listing:
                    listing['attributes'] = []
                listing['attributes'].extend(english_attributes)
                
            except Exception as e:
                print(f"Warning: Failed to enrich listing {listing.get('yad2_url_token', 'unknown')}: {e}")
                # Set default values if enrichment fails
                if 'description' not in listing:
                    listing['description'] = ''
                if 'attributes' not in listing:
                    listing['attributes'] = []
                # Continue with other listings even if one fails
                continue
                
    except Exception as e:
        print(f"Warning: Enrichment failed, continuing without enrichment: {e}")
        # Return listings without enrichment rather than failing completely
        
    return listings_data



