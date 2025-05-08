import json
import csv
import os
import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
import logging
from dotenv import load_dotenv
from typing import Set
        
# Load environment variables
load_dotenv()
        
# --- Database Connection Details ---
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

# --- File Names ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
NEIGHBORHOOD_VARIANTS_MAP_JSON = os.path.join(BASE_DIR, "data", "sources", "neighborhood_variants_map.json")
YAD2_HOOD_MAPPING_JSON = os.path.join(BASE_DIR, "data", "sources", "yad2_hood_mapping.json")
NEIGHBORHOOD_DETAILS_CSV = os.path.join(BASE_DIR, "data", "sources", "neighborhood_details.csv")


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)


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
            (1, 'לא משופץ', 'Not Renovated'),
            (2, 'משופץ', 'Renovated'),
            (3, 'מצב טוב', 'Good Condition'),
            (6, 'חדש מקבלן', 'New from Contractor'),
            (4, 'שמור', 'Well-Kept'),
            (5, 'דורש שיפוץ', 'Needs Renovation')
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
            (1093, 'ייחודי'), (1016, 'אחריי להתחדשות עירונית'), (1000, 'חדש מקבלן'),
            (1008, '4 כיווני אוויר'),(1001, 'נכס חדש'),(1011, '4 חדרי מקלחת')
        ]
        execute_values(cursor,
                       "INSERT INTO tags (tag_id, tag_name) VALUES %s ON CONFLICT (tag_id) DO NOTHING",
                       tags)
        logger.debug(f"Processed {len(tags)} tags.")
        logger.debug(f"Tags: {tags}")

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
    conn = get_db_connection()
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

        yad2_hood_lookup = {item['neigborhood_name']: item for item in yad2_mapping_list if 'neigborhood_name' in item}
        logger.info(f"Found mapping for {len(yad2_hood_lookup)} neighborhoods.")

        logger.info(f"Loading neighborhood details from {NEIGHBORHOOD_DETAILS_CSV}...")
        neighborhood_data_to_insert = []
        processed_count = 0
        skipped_count = 0

        with open(NEIGHBORHOOD_DETAILS_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                hebrew_name = row.get('Hebrew Neighborhood Name')
                if not hebrew_name:
                    logger.warning(f"Skipping row {i+1} in CSV: Missing 'Hebrew Neighborhood Name'.")
                    skipped_count += 1
                    continue

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

                data = (
                    yad2_hood_id,
                    hebrew_name,
                    row.get('English Neighborhood Name'),
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
                    updated_at = NOW()
            """
            execute_values(cursor, sql, neighborhood_data_to_insert, page_size=500)
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
        if conn:
            conn.close()

def map_neighborhood_variants(listings_data):
    """Loads neighborhood variant mapping and maps variants to canonical names."""
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
    return variant_to_canonical_map

def create_neighborhood_lookup(conn):
    """Creates a lookup dictionary for neighborhood ID by canonical Hebrew name."""
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
    return neighborhood_name_to_id

def get_neighborhood_id_from_listing(listing_dict, neighborhood_name_to_id, variant_to_canonical_map, unmapped_listings_count):
    """Parses the neighborhood name from the listing dictionary."""
    raw_hood_name = listing_dict.get('neighborhood_text')
    neighborhood_id = None

    if raw_hood_name:
        neighborhood_id = neighborhood_name_to_id.get(raw_hood_name)
        if not neighborhood_id:
            canonical_name_from_map = variant_to_canonical_map.get(raw_hood_name)
            if canonical_name_from_map:
                neighborhood_id = neighborhood_name_to_id.get(canonical_name_from_map)
                if not neighborhood_id:
                    logger.warning(f"Mapped canonical name '{canonical_name_from_map}' for variant '{raw_hood_name}' not found in DB lookup (listing {listing_dict.get('order_id')}). Setting neighborhood_id to NULL.")

    if neighborhood_id is None:
        if raw_hood_name: 
            logger.warning(f"Neighborhood ID not found for raw name '{raw_hood_name}' (listing {listing_dict.get('order_id')}) after checking direct match and variant map. Setting neighborhood_id to NULL.")
        else:
                logger.warning(f"Raw neighborhood name was missing for listing {listing_dict.get('order_id')}. Setting neighborhood_id to NULL.")
        unmapped_listings_count += 1
    return neighborhood_id, unmapped_listings_count

def fetch_existing_ids(conn, table, column) -> Set:
    """Fetches all existing IDs from a table for a given column."""
    with conn.cursor() as cur:
        cur.execute(f"SELECT {column} FROM {table}")
        return {row[0] for row in cur.fetchall()}
    
def insert_listings(cursor, listings_list, neighborhood_name_to_id, listing_tags_list, conn, variant_to_canonical_map):
    """Inserts listings into the database."""
    logger.info(f"Processing {len(listings_list)} listings for DB update/insert...")
    listings_to_insert_update = []
    processed_listings_count = 0
    unmapped_listings_count = 0 

    for listing_dict in listings_list:
        listing_dict['neighborhood_id'], unmapped_listings_count = get_neighborhood_id_from_listing(listing_dict, neighborhood_name_to_id, variant_to_canonical_map, unmapped_listings_count)
        processed_listings_count += 1
        listings_to_insert_update.append(listing_dict)

    if listings_to_insert_update:
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

        try:
            cursor.executemany(sql_listings, listing_tuples)
            logger.info(f"Upserted {processed_listings_count} listings ({unmapped_listings_count} remain unmapped).")
        except (psycopg2.Error, TypeError) as e:
            conn.rollback()
            logger.exception(f"Error during listing upsert: {e}")

            if "violates foreign key constraint" in str(e):
                logger.warning("Foreign key violation detected. Attempting to fix...")

                if "property_condition_id" in str(e):
                    try:
                        valid_ids = fetch_existing_ids(conn, "property_conditions", "condition_id")
                        for l in listings_to_insert_update:
                            if l.get("property_condition_id") not in valid_ids:
                                logger.info(f"Nullifying invalid property_condition_id in listing {l.get('order_id')}")
                                l["property_condition_id"] = None
                    except Exception as ce:
                        logger.exception("Error fixing property_condition_id: {ce}")

                elif "tag_id" in str(e):
                    try:
                        valid_ids = fetch_existing_ids(conn, "tags", "tag_id")
                        listing_tags_list[:] = [lt for lt in listing_tags_list if lt.get("tag_id") in valid_ids]
                    except Exception as ce:
                        logger.exception("Error fixing tag_id: {ce}")

                # Attempt second insert
                listing_tuples = [[l.get(col) for col in listing_cols] for l in listings_to_insert_update]
                try:
                    cursor.executemany(sql_listings, listing_tuples)
                    conn.commit()
                    logger.info("Retry successful after FK fix.")
                except Exception as retry_e:
                    conn.rollback()
                    logger.exception("Retry after FK fix failed.")
            elif isinstance(e, TypeError):
                logger.error("Likely column count mismatch.")
                logger.debug(f"Tuple: {listing_tuples[0] if listing_tuples else 'N/A'}")

def insert_images(cursor, images_list):
    """Inserts images into the database."""
    if images_list:
        logger.info(f"Inserting {len(images_list)} image records...")
        img_tuples = [(i.get('listing_order_id'), i.get('image_url'))
                    for i in images_list if i.get('listing_order_id') and i.get('image_url')]
        if img_tuples:
            execute_values(cursor,
                        "INSERT INTO images (listing_order_id, image_url) VALUES %s ON CONFLICT DO NOTHING",
                        img_tuples, page_size=500)
            logger.debug("Image insertion attempt complete.")

def insert_listing_tags(cursor, listing_tags_list):
    """Inserts listing-tag relationships into the database."""
    if listing_tags_list:
        logger.info(f"Inserting {len(listing_tags_list)} listing-tag relationships...")
        lt_tuples = [(lt.get('listing_order_id'), lt.get('tag_id'))
                        for lt in listing_tags_list if lt.get('listing_order_id') and lt.get('tag_id')]
        if lt_tuples:
            try:
                execute_values(cursor,
                                "INSERT INTO listing_tags (listing_order_id, tag_id) VALUES %s ON CONFLICT (listing_order_id, tag_id) DO NOTHING",
                                lt_tuples, page_size=1000)
                logger.debug("Listing-tag insertion attempt complete.")
            except Exception as e:
                logger.exception(f"Error during listing-tag insertion: {e}")
                logger.debug(f"Second attempt to insert listing-tag relationships: {lt_tuples}")
                execute_values(cursor,
                                "INSERT INTO listing_tags (listing_order_id, tag_id) VALUES %s ON CONFLICT (listing_order_id, tag_id) DO NOTHING",
                                lt_tuples, page_size=1000)


def populate_listings(listings_data):
    """Loads listing data and populates listings, images, and listing_tags tables, using pre-mapping for variants."""

    conn = get_db_connection()
    if not conn:
        logger.error("Cannot populate listings: No database connection.")
        return

    listings_list = listings_data.get('listings', [])
    images_list = listings_data.get('images', [])
    listing_tags_list = listings_data.get('listing_tags', [])

    if not listings_list:
        logger.info("No valid listing data found to process.")
        return
        
    logger.info("Ensuring all neighborhoods in listings exist in the database...")
    ensure_neighborhoods_exist(conn, listings_data)

    variant_to_canonical_map = map_neighborhood_variants(listings_data)
    neighborhood_name_to_id = create_neighborhood_lookup(conn)

    cursor = conn.cursor()
    try:
        insert_listings(cursor, listings_list, neighborhood_name_to_id, listing_tags_list, conn, variant_to_canonical_map)
        insert_images(cursor, images_list)
        insert_listing_tags(cursor, listing_tags_list)
        conn.commit() 
        logger.info("Listing, image, and tag data committed successfully.")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_db_connection():
    """Creates and returns a database connection using psycopg2."""
    logger.info("Attempting to connect to the database...")
    try:
        db_url = DATABASE_URL
        if db_url.startswith('postgresql+asyncpg://'):
            db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
        
        conn = psycopg2.connect(
            db_url,
            sslmode='require'
        )
        logger.info("Database connection successful.")
        return conn
    except psycopg2.Error as e:
        logger.exception(f"Error connecting to the database: {e}")
        return None

def ensure_neighborhoods_exist(conn, listings_data):
    """
    Ensures that all neighborhoods mentioned in listings exist in the neighborhoods table.
    Creates simple placeholder entries for any missing neighborhoods.
    """
    if not conn or not listings_data:
        return
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("SELECT yad2_hood_id, hebrew_name FROM neighborhoods")
        db_neighborhoods = {row['hebrew_name']: row['yad2_hood_id'] for row in cursor.fetchall()}
        logger.info(f"Found {len(db_neighborhoods)} existing neighborhoods in database")
        
        unique_neighborhoods = set()
        for listing in listings_data.get('listings', []):
            if listing.get('neighborhood_text'):
                unique_neighborhoods.add(listing.get('neighborhood_text'))
        
        missing_neighborhoods = unique_neighborhoods - set(db_neighborhoods.keys())
        
        if missing_neighborhoods:
            logger.info(f"Found {len(missing_neighborhoods)} neighborhoods in listings that are missing from database")
            logger.debug(f"Missing neighborhoods: {sorted(missing_neighborhoods)}")
            
            cursor.execute("SELECT COALESCE(MAX(yad2_hood_id), 100000) FROM neighborhoods")
            max_id = cursor.fetchone()['coalesce']
            next_id = max_id + 1
            
            neighborhoods_to_insert = []
            for i, neighborhood in enumerate(missing_neighborhoods):
                neighborhoods_to_insert.append((
                    next_id + i,
                    neighborhood,
                    None,
                ))
            
            if neighborhoods_to_insert:
                execute_values(cursor,
                           "INSERT INTO neighborhoods (yad2_hood_id, hebrew_name, english_name) VALUES %s ON CONFLICT (yad2_hood_id) DO NOTHING",
                           neighborhoods_to_insert)
                conn.commit()
                logger.info(f"Added {len(neighborhoods_to_insert)} missing neighborhoods to the database")
        else:
            logger.info("All neighborhoods in listings already exist in the database")
            
    except (psycopg2.Error, Exception) as e:
        conn.rollback()
        logger.exception(f"Error ensuring neighborhoods exist: {e}")
    finally:
        if cursor:
            cursor.close()
