import json
import csv
import os
import psycopg2
from psycopg2.extras import execute_values, RealDictCursor # RealDictCursor to return rows as dictionaries
import logging
        
# --- Database Connection Details ---
DB_NAME = os.getenv("DB_NAME", "default_db")
DB_USER = os.getenv("DB_USER", "default_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "default_password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

# --- File Names ---
NEIGHBORHOOD_DETAILS_CSV = 'data/sources/neighborhood_details.csv'
YAD2_HOOD_MAPPING_JSON = 'data/sources/yad2_hood_mapping.json'
LISTINGS_DATA_FILE = 'data/sources/listings_data.json'
NEIGHBORHOOD_VARIANTS_MAP_JSON = 'data/sources/neighborhood_variants_map.json'


# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)


def get_db_connection():
    """Creates and returns a database connection."""
    logger.info("Attempting to connect to the database...")
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        logger.info("Database connection successful.")
        return conn
    except psycopg2.Error as e:
        logger.exception(f"Error connecting to the database: {e}") # Use exception to log traceback
        return None

def safe_float(value, default=None):
    """Convert value to float safely."""
    if value is None or value == '':
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int(value, default=None):
    """Convert value to int safely."""
    if value is None or value == '':
        return default
    try:
        # Handle potential float strings like '2.0'
        return int(float(value))
    except (ValueError, TypeError):
        return default

def populate_lookups(conn):
    """Populates the lookup tables (conditions, tags)."""
    if not conn:
        logger.error("Cannot populate lookups: No database connection.")
        return
    cursor = conn.cursor()
    try:
        logger.info("Populating/Updating lookup tables (conditions, tags)...")

        # --- Property Conditions ---
        conditions = [
            (2, 'משופץ', 'Renovated'),
            (3, 'מצב טוב', 'Good Condition'),
            (6, 'חדש מקבלן', 'New from Contractor'),
            # ... Add more as needed
        ]
        execute_values(cursor,
                       "INSERT INTO property_conditions (condition_id, condition_name_he, condition_name_en) VALUES %s ON CONFLICT (condition_id) DO NOTHING",
                       conditions)
        logger.debug(f"Processed {len(conditions)} property conditions.")

        # --- Tags ---
        tags = [
            (1007, '3 כיווני אוויר'), (1023, 'קרוב לפארק'), (1091, 'בהזדמנות'),
            (1006, 'נוף פתוח לעיר'), (1002, 'נכס עורפי'), (1019, 'משופצת אדריכלית'),
            (1018, 'בניין משופץ'), (1020, 'מטבח גדול'), (1092, 'חבל לפספס'),
            (1009, 'ממ"ד'), (1004, 'נוף פתוח לים'), (1005, 'נוף פתוח לפארק'),
            (1017, 'קרוב לים'), (1003, 'חניה'), (1012, '2 מרפסות'),
            (1021, 'גמיש במחיר'), (1010, '3 חדרי מקלחת'),
            # ... Add more as needed
        ]
        execute_values(cursor,
                       "INSERT INTO tags (tag_id, tag_name) VALUES %s ON CONFLICT (tag_id) DO NOTHING",
                       tags)
        logger.debug(f"Processed {len(tags)} tags.")

        conn.commit()
        logger.info("Lookup tables updated successfully.")
    except psycopg2.Error as e:
        conn.rollback()
        logger.exception(f"Error updating lookup tables: {e}")
    finally:
        if cursor:
            cursor.close()


def populate_neighborhoods(conn):
    """Loads data from CSV and JSON mapping, populates the neighborhoods table."""
    if not conn:
        logger.error("Cannot populate neighborhoods: No database connection.")
        return False

    if not os.path.exists(NEIGHBORHOOD_DETAILS_CSV) or not os.path.exists(YAD2_HOOD_MAPPING_JSON):
        logger.error(f"Error: Neighborhood data files not found ({NEIGHBORHOOD_DETAILS_CSV}, {YAD2_HOOD_MAPPING_JSON}).")
        return False

    cursor = conn.cursor()
    try:
        logger.info(f"Loading Yad2 neighborhood ID mapping from {YAD2_HOOD_MAPPING_JSON}...")
        with open(YAD2_HOOD_MAPPING_JSON, 'r', encoding='utf-8') as f:
            yad2_mapping_list = json.load(f)

        # Create a dictionary for quick lookup of ID by Hebrew name
        yad2_hood_lookup = {item['neigborhood_name']: item for item in yad2_mapping_list if 'neigborhood_name' in item}
        logger.info(f"Found mapping for {len(yad2_hood_lookup)} neighborhoods.")

        logger.info(f"Loading neighborhood details from {NEIGHBORHOOD_DETAILS_CSV}...")
        neighborhood_data_to_insert = []
        processed_count = 0
        skipped_count = 0

        with open(NEIGHBORHOOD_DETAILS_CSV, 'r', encoding='utf-8') as f:
            # Use DictReader for easy access by column name
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                hebrew_name = row.get('Hebrew Neighborhood Name')
                if not hebrew_name:
                    logger.warning(f"Skipping row {i+1} in CSV: Missing 'Hebrew Neighborhood Name'.")
                    skipped_count += 1
                    continue

                # Find the corresponding Yad2 ID from the mapping
                yad2_info = yad2_hood_lookup.get(hebrew_name)
                if not yad2_info or not yad2_info.get('hoodId'):
                    logger.warning(f"Yad2 ID not found for neighborhood '{hebrew_name}' in mapping file. Skipping.")
                    skipped_count += 1
                    continue

                yad2_hood_id = safe_int(yad2_info.get('hoodId'))
                if yad2_hood_id is None:
                    logger.warning(f"Invalid hoodId found for '{hebrew_name}'. Skipping.")
                    skipped_count += 1
                    continue

                # Prepare the record for insertion/update, converting types safely
                data = (
                    yad2_hood_id,
                    hebrew_name,
                    row.get('English Neighborhood Name'), # Assumes header is 'English Neighborhood Name'
                    safe_float(row.get('Average Purchase Price')),
                    safe_float(row.get('Average Rent Price')),
                    safe_float(row.get('Socioeconomic Index')),
                    safe_float(row.get('School Rating')),
                    row.get('General Overview'),
                    safe_int(row.get('Bars_Count'), 0),
                    safe_int(row.get('Restaurants_Count'), 0),
                    safe_int(row.get('Clubs_Count'), 0),
                    safe_int(row.get('Shopping_Malls_Count'), 0),
                    safe_int(row.get('Unique_Entertainment_Count'), 0),
                    safe_int(row.get('Primary_Schools_Count'), 0),
                    safe_int(row.get('Elementary_Schools_Count'), 0),
                    safe_int(row.get('Secondary_Schools_Count'), 0),
                    safe_int(row.get('High_Schools_Count'), 0),
                    safe_int(row.get('Universities_Count'), 0),
                    safe_float(row.get('Closest_Beach_Distance_km')),
                    safe_float(row.get('Latitude')),
                    safe_float(row.get('Longitude')),
                    safe_int(yad2_info.get('cityId')),
                    safe_int(yad2_info.get('areaId')),
                    safe_int(yad2_info.get('topAreaId')),
                    safe_int(yad2_info.get('docCount'))
                )
                neighborhood_data_to_insert.append(data)
                processed_count += 1

        logger.info(f"Updating {processed_count} neighborhoods in the database (skipped {skipped_count})...")
        if neighborhood_data_to_insert:
            cols = [
                'yad2_hood_id', 'hebrew_name', 'english_name', 'avg_purchase_price',
                'avg_rent_price', 'socioeconomic_index', 'avg_school_rating',
                'general_overview', 'bars_count', 'restaurants_count', 'clubs_count',
                'shopping_malls_count', 'unique_entertainment_count',
                'primary_schools_count', 'elementary_schools_count',
                'secondary_schools_count', 'high_schools_count', 'universities_count',
                'closest_beach_distance_km', 'latitude', 'longitude', 'yad2_city_id',
                'yad2_area_id', 'yad2_top_area_id', 'yad2_doc_count'
            ]
            cols_sql = ", ".join(cols)
            # Upsert logic: Update if yad2_hood_id exists, otherwise insert.
            sql = f"""
                INSERT INTO neighborhoods ({cols_sql}) VALUES %s
                ON CONFLICT (yad2_hood_id) DO UPDATE SET
                    hebrew_name = EXCLUDED.hebrew_name,
                    english_name = EXCLUDED.english_name,
                    avg_purchase_price = EXCLUDED.avg_purchase_price,
                    avg_rent_price = EXCLUDED.avg_rent_price,
                    socioeconomic_index = EXCLUDED.socioeconomic_index,
                    avg_school_rating = EXCLUDED.avg_school_rating,
                    general_overview = EXCLUDED.general_overview,
                    bars_count = EXCLUDED.bars_count,
                    restaurants_count = EXCLUDED.restaurants_count,
                    clubs_count = EXCLUDED.clubs_count,
                    shopping_malls_count = EXCLUDED.shopping_malls_count,
                    unique_entertainment_count = EXCLUDED.unique_entertainment_count,
                    primary_schools_count = EXCLUDED.primary_schools_count,
                    elementary_schools_count = EXCLUDED.elementary_schools_count,
                    secondary_schools_count = EXCLUDED.secondary_schools_count,
                    high_schools_count = EXCLUDED.high_schools_count,
                    universities_count = EXCLUDED.universities_count,
                    closest_beach_distance_km = EXCLUDED.closest_beach_distance_km,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    yad2_city_id = EXCLUDED.yad2_city_id,
                    yad2_area_id = EXCLUDED.yad2_area_id,
                    yad2_top_area_id = EXCLUDED.yad2_top_area_id,
                    yad2_doc_count = EXCLUDED.yad2_doc_count,
                    updated_at = NOW() -- Ensure updated_at is set on update
            """
            execute_values(cursor, sql, neighborhood_data_to_insert, page_size=500) # Use page_size for large datasets
            conn.commit()
            logger.info("Neighborhoods table updated successfully.")
            return True
        else:
            logger.info("No valid neighborhood data found to update.")
            return False

    except (psycopg2.Error, FileNotFoundError, json.JSONDecodeError, csv.Error, KeyError) as e:
        conn.rollback()
        logger.exception(f"Error updating neighborhoods table: {e}")
        return False
    finally:
        if cursor:
            cursor.close()


def populate_listings(conn):
    """Loads listing data and populates listings, images, and listing_tags tables, using pre-mapping for variants."""
    if not conn:
        logger.error("Cannot populate listings: No database connection.")
        return

    # 1. Load processed listing data (no changes here)
    logger.info(f"Loading processed listing data...")
    structured_data = None
    try:
         if not os.path.exists(LISTINGS_DATA_FILE):
             logger.error(f"Error: Listing data file {LISTINGS_DATA_FILE} not found.")
             return
         with open(LISTINGS_DATA_FILE, 'r', encoding='utf-8') as f:
            structured_data = json.load(f)
         logger.info(f"Loaded data for {len(structured_data.get('listings',[]))} listings from {LISTINGS_DATA_FILE}")
    except (FileNotFoundError, json.JSONDecodeError) as e:
         logger.exception(f"Error loading listing data: {e}")
         return
    if not structured_data:
        logger.error("Failed to load or process listing data.")
        return

    listings_list = structured_data.get('listings', [])
    images_list = structured_data.get('images', [])
    listing_tags_list = structured_data.get('listing_tags', [])

    if not listings_list:
        logger.info("No valid listing data found to process.")
        return

    logger.info(f"Loading neighborhood variant mapping from {NEIGHBORHOOD_VARIANTS_MAP_JSON}...")
    variant_to_canonical_map = {}
    try:
        if not os.path.exists(NEIGHBORHOOD_VARIANTS_MAP_JSON):
             logger.warning(f"Neighborhood variant mapping file not found at {NEIGHBORHOOD_VARIANTS_MAP_JSON}. Proceeding without variant mapping.")
        else:
            with open(NEIGHBORHOOD_VARIANTS_MAP_JSON, 'r', encoding='utf-8') as f:
                variant_list = json.load(f)
                for item in variant_list:
                    if 'listing_variant' in item and 'canonical_name' in item:
                        variant_to_canonical_map[item['listing_variant']] = item['canonical_name']
                logger.info(f"Loaded {len(variant_to_canonical_map)} variant mappings.")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.exception(f"Error loading neighborhood variant mapping file: {e}. Proceeding without it.")

    # 2. Create lookup dictionary for neighborhood ID by CANONICAL Hebrew name from DB (no changes here)
    logger.info("Creating neighborhood lookup dictionary (canonical names) from DB...")
    neighborhood_name_to_id = {}
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("SELECT yad2_hood_id, hebrew_name FROM neighborhoods WHERE hebrew_name IS NOT NULL")
        rows = cursor.fetchall()
        for row in rows:
            neighborhood_name_to_id[row['hebrew_name']] = row['yad2_hood_id']
        logger.info(f"Created lookup for {len(neighborhood_name_to_id)} canonical neighborhoods.")
    except psycopg2.Error as e:
        logger.exception(f"Error fetching neighborhoods from DB: {e}")
    finally:
        if cursor:
            cursor.close()


    # 3. Update/Insert listings, images, and listing_tags
    cursor = conn.cursor()
    try:
        logger.info(f"Processing {len(listings_list)} listings for DB update/insert...")
        listings_to_insert_update = []
        processed_listings_count = 0
        unmapped_listings_count = 0 

        for listing_dict in listings_list:
            raw_hood_name = listing_dict.get('neighborhood_text')
            canonical_name = None
            neighborhood_id = None

            if raw_hood_name:

                neighborhood_id = neighborhood_name_to_id.get(raw_hood_name)
                if neighborhood_id:
                    canonical_name = raw_hood_name 
                else:
                    canonical_name_from_map = variant_to_canonical_map.get(raw_hood_name)
                    if canonical_name_from_map:
                        neighborhood_id = neighborhood_name_to_id.get(canonical_name_from_map)
                        if neighborhood_id:
                           canonical_name = canonical_name_from_map 
                        else:

                           logger.warning(f"Mapped canonical name '{canonical_name_from_map}' for variant '{raw_hood_name}' not found in DB lookup (listing {listing_dict.get('order_id')}). Setting neighborhood_id to NULL.")

            if neighborhood_id is None:
                if raw_hood_name: 
                    logger.warning(f"Neighborhood ID not found for raw name '{raw_hood_name}' (listing {listing_dict.get('order_id')}) after checking direct match and variant map. Setting neighborhood_id to NULL.")
                else:
                     logger.warning(f"Raw neighborhood name was missing for listing {listing_dict.get('order_id')}. Setting neighborhood_id to NULL.")
                unmapped_listings_count += 1
                # continue # uncomment this line to skip listings without a neighborhood ID

            listing_dict['neighborhood_id'] = neighborhood_id
            processed_listings_count += 1
            listings_to_insert_update.append(listing_dict)

        # --- DEBUGGING CODE for TypeError (KEEP THIS UNTIL TypeError IS SOLVED) ---
        if listings_to_insert_update:
            # ... (The debugging print/log statements for TypeError) ...
            listing_cols = [
                'order_id', 'token', 'neighborhood_id', 'property_condition_id',
                'subcategory_id', 'category_id', 'ad_type', 'price',
                'property_type', 'rooms_count', 'square_meter',
                'cover_image_url', 'video_url', 'city', 'area',
                'neighborhood_text', 'street', 'house_number', 'floor',
                'longitude', 'latitude'
            ]
            listing_tuples = [[l.get(col) for col in listing_cols] for l in listings_to_insert_update]
            cols_sql = ", ".join(listing_cols)
            placeholders = ", ".join(["%s"] * len(listing_cols))
            update_set_sql = ", ".join([f"{col} = EXCLUDED.{col}" for col in listing_cols if col != 'order_id']) + ", updated_at = NOW()"
            sql_listings = f"""
                INSERT INTO listings ({cols_sql}) VALUES ({placeholders})
                ON CONFLICT (order_id) DO UPDATE SET {update_set_sql}
            """

            logger.debug(f"Number of columns defined in listing_cols: {len(listing_cols)}")
            logger.debug(f"Number of placeholders (%s) in SQL query: {sql_listings.count('%s')}")
            if listing_tuples:
                logger.debug(f"Length of first data tuple: {len(listing_tuples[0])}")
                logger.debug(f"Content of first data tuple: {listing_tuples[0]}")
                # ... (rest of debug prints) ...
            # --- END DEBUGGING ---

            try:
                cursor.executemany(sql_listings, listing_tuples)
                logger.info(f"Upserted {processed_listings_count} listings ({unmapped_listings_count} remain unmapped).")
            except (psycopg2.Error, TypeError) as e:
                 conn.rollback() 
                 logger.exception(f"Error during listing upsert: {e}")

                 if isinstance(e, TypeError):
                     logger.error(f"Review listing_cols count ({len(listing_cols)}) vs data tuple length (example: {len(listing_tuples[0]) if listing_tuples else 'N/A'})")
                     logger.error(f"Problematic tuple example (first one): {listing_tuples[0] if listing_tuples else 'N/A'}")
                 return 

        # Insert Images and Listing-Tags (only if listings were processed successfully)
        if images_list:
             logger.info(f"Inserting {len(images_list)} image records...")
             img_tuples = [(i.get('listing_order_id'), i.get('image_url'))
                           for i in images_list if i.get('listing_order_id') and i.get('image_url')]
             if img_tuples:
                 execute_values(cursor,
                                "INSERT INTO images (listing_order_id, image_url) VALUES %s ON CONFLICT DO NOTHING",
                                img_tuples, page_size=500)
                 logger.debug("Image insertion attempt complete.")

        if listing_tags_list:
            logger.info(f"Inserting {len(listing_tags_list)} listing-tag relationships...")
            lt_tuples = [(lt.get('listing_order_id'), lt.get('tag_id'), lt.get('priority'))
                         for lt in listing_tags_list if lt.get('listing_order_id') and lt.get('tag_id')]
            if lt_tuples:
                execute_values(cursor,
                                "INSERT INTO listing_tags (listing_order_id, tag_id, priority) VALUES %s ON CONFLICT (listing_order_id, tag_id) DO NOTHING",
                                lt_tuples, page_size=1000)
                logger.debug("Listing-tag insertion attempt complete.")


        conn.commit() # Commit all changes for listings, images, tags
        logger.info("Listing, image, and tag data committed successfully.")

    # except (psycopg2.Error, KeyError, TypeError) as e: # לכדה שגיאות כלליות יותר
    #     conn.rollback()
    #     logger.exception(f"Error updating listing data: {e}")
    finally:
        if cursor:
            cursor.close()

# --- Main Execution Block ---
if __name__ == "__main__":
    connection = get_db_connection()
    if connection:
        try:
            # 1. Populate/Update lookup tables (run once or periodically)
            populate_lookups(connection)

            # 2. Populate/Update neighborhoods (requires CSV and JSON mapping files)
            neighborhoods_updated = populate_neighborhoods(connection)

            # 3. Populate/Update listings (requires processed listing data and updated neighborhoods table)
            # Only run if neighborhood update was successful (or considered up-to-date)
            if neighborhoods_updated:
                 populate_listings(connection)
            else:
                 logger.warning("Skipping listing population because neighborhood population failed or found no data.")

        finally:
            connection.close()
            logger.info("Database connection closed.")
    else:
        logger.error("Script finished: Could not establish database connection.")