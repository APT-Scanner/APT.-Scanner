import json
import os

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
              {'listings': [], 'images': [], 'tags': [], 'listing_tags': [],
               'property_conditions': []}
              Returns None if the file cannot be read or parsed.
    """

    listings_data = []
    images_data = []
    tags_data = []
    listing_tags_data = []
    property_conditions_data = []

    processed_tag_ids = set()
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
            'order_id': order_id,
            'token': token,
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
        }
        listings_data.append(listing_entry)

        # Extract Images
        image_urls = meta_info.get('images', [])
        if isinstance(image_urls, list):
            for img_url in image_urls:
                if img_url: # Ensure URL is not empty
                    images_data.append({
                        'listing_order_id': order_id,
                        'image_url': img_url
                    })

        # Extract Tags
        listing_tags = listing.get('tags', [])
        if isinstance(listing_tags, list):
            for tag in listing_tags:
                tag_id = tag.get('id')
                tag_name = tag.get('name')
                tag_priority = tag.get('priority')
                if tag_id is not None and tag_name is not None:
                    # Add unique tag definition
                    if tag_id not in processed_tag_ids:
                        tags_data.append({'tag_id': tag_id, 'tag_name': tag_name})
                        processed_tag_ids.add(tag_id)
                    # Add listing-tag relationship
                    listing_tags_data.append({
                        'listing_order_id': order_id,
                        'tag_id': tag_id,
                        'priority': tag_priority
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
        'tags': tags_data,
        'listing_tags': listing_tags_data,
        'property_conditions': property_conditions_data
    }

# --- Execution ---
if __name__ == "__main__":
    structured_data = parse_listings()

    if structured_data:
        with open('structured_apt_list.json', 'w', encoding='utf-8') as outfile:
            json.dump(structured_data, outfile, ensure_ascii=False, indent=4)
