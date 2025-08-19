import json
import csv
import os
import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
import logging
from dotenv import load_dotenv
from typing import Set
        
# Load environment variables
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../backend
env_path = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=env_path)

        
# --- Database Connection Details ---
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

# --- File Names ---
# BASE_DIR already defined above for .env loading 
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
        # Existing manual tags  
        existing_tags = [
            (1007, '3 כיווני אוויר'), (1023, 'קרוב לפארק'), (1091, 'בהזדמנות'),
            (1006, 'נוף פתוח לעיר'), (1002, 'נכס עורפי'), (1019, 'משופצת אדריכלית'),
            (1018, 'בניין משופץ'), (1020, 'מטבח גדול'), (1092, 'חבל לפספס'),
            (1009, 'ממ"ד'), (1004, 'נוף פתוח לים'), (1005, 'נוף פתוח לפארק'),
            (1017, 'קרוב לים'), (1003, 'חניה'), (1012, '2 מרפסות'),
            (1021, 'גמיש במחיר'), (1010, '3 חדרי מקלחת'),
            (1093, 'ייחודי'), (1016, 'אחריי להתחדשות עירונית'), (1000, 'חדש מקבלן'),
            (1008, '4 כיווני אוויר'),(1001, 'נכס חדש'),(1011, '4 חדרי מקלחת')
        ]
        
        # Additional Yad2 feature tags (using IDs from 2000+ to avoid conflicts)
        yad2_feature_tags = [
            (2001, 'מעלית'),           # elevator  
            (2002, 'מיזוג'),           # airConditioner
            (2003, 'מרפסת'),          # balcony
            (2004, 'סורגים'),         # bars  
            (2005, 'מחסן'),           # warehouse
            (2006, 'גישה לנכים'),     # accessibility
            (2007, 'משופץ'),          # renovated (general)
            (2008, 'מרוהט'),          # furniture
            (2009, 'חיות מחמד'),      # pets  
            (2010, 'לשותפים'),        # forPartners
            (2011, 'נכס בלעדי'),      # assetExclusive
        ]
        
        # Combine all tags
        tags = existing_tags + yad2_feature_tags
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
    """Loads data from CSV and JSON mapping, populates the neighborhoods, neighborhood_metrics, and neighborhood_metadata tables."""
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
        metrics_data_to_insert = []
        metadata_data_to_insert = []
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

                # Main neighborhoods table data (matches models.py Neighborhood)
                neighborhood_data = (
                    yad2_hood_id,  # Using yad2_hood_id as primary key for now
                    hebrew_name,
                    row.get('English Neighborhood Name'),
                    row.get('City'),  # Adding city field
                    safe_float(row.get('Latitude')),
                    safe_float(row.get('Longitude'))
                )
                neighborhood_data_to_insert.append(neighborhood_data)

                # Metrics table data (matches models.py NeighborhoodMetrics)
                metrics_data = (
                    yad2_hood_id,  # neighborhood_id FK
                    safe_float(row.get('Average Purchase Price')),  # avg_sale_price
                    safe_float(row.get('Average Rent Price')),      # avg_rental_price
                    safe_float(row.get('Socioeconomic Index')),     # social_economic_index
                    None,  # popular_political_party (not in CSV)
                    safe_float(row.get('School Rating')),           # school_rating
                    safe_float(row.get('Closest_Beach_Distance_km')) # beach_distance_km
                )
                metrics_data_to_insert.append(metrics_data)

                # Metadata table data (matches models.py NeighborhoodMetadata)
                metadata_data = (
                    yad2_hood_id,  # neighborhood_id FK
                    row.get('General Overview'),       # overview
                    safe_int(yad2_info.get('cityId')), # external_city_id
                    safe_int(yad2_info.get('areaId')), # external_area_id
                    safe_int(yad2_info.get('topAreaId')) # external_top_area_id
                )
                metadata_data_to_insert.append(metadata_data)
                processed_count += 1

        logger.info(f"Updating {processed_count} neighborhoods in the database (skipped {skipped_count})...")
        
        if neighborhood_data_to_insert:
            # Insert neighborhoods table
            neighborhood_cols = ['id', 'hebrew_name', 'english_name', 'city', 'latitude', 'longitude']
            neighborhood_cols_sql = ", ".join(neighborhood_cols)
            neighborhood_sql = f"""
                INSERT INTO neighborhoods ({neighborhood_cols_sql}) VALUES %s
                ON CONFLICT (id) DO UPDATE SET
                    hebrew_name = EXCLUDED.hebrew_name,
                    english_name = EXCLUDED.english_name,
                    city = EXCLUDED.city,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    updated_at = NOW()
            """
            execute_values(cursor, neighborhood_sql, neighborhood_data_to_insert, page_size=500)
            
            # Insert neighborhood_metrics table
            metrics_cols = ['neighborhood_id', 'avg_sale_price', 'avg_rental_price', 'social_economic_index', 'popular_political_party', 'school_rating', 'beach_distance_km']
            metrics_cols_sql = ", ".join(metrics_cols)
            metrics_sql = f"""
                INSERT INTO neighborhood_metrics ({metrics_cols_sql}) VALUES %s
                ON CONFLICT (neighborhood_id) DO UPDATE SET
                    avg_sale_price = EXCLUDED.avg_sale_price,
                    avg_rental_price = EXCLUDED.avg_rental_price,
                    social_economic_index = EXCLUDED.social_economic_index,
                    popular_political_party = EXCLUDED.popular_political_party,
                    school_rating = EXCLUDED.school_rating,
                    beach_distance_km = EXCLUDED.beach_distance_km,
                    updated_at = NOW()
            """
            execute_values(cursor, metrics_sql, metrics_data_to_insert, page_size=500)
            
            # Insert neighborhood_metadata table
            metadata_cols = ['neighborhood_id', 'overview', 'external_city_id', 'external_area_id', 'external_top_area_id']
            metadata_cols_sql = ", ".join(metadata_cols)
            metadata_sql = f"""
                INSERT INTO neighborhood_metadata ({metadata_cols_sql}) VALUES %s
                ON CONFLICT (neighborhood_id) DO UPDATE SET
                    overview = EXCLUDED.overview,
                    external_city_id = EXCLUDED.external_city_id,
                    external_area_id = EXCLUDED.external_area_id,
                    external_top_area_id = EXCLUDED.external_top_area_id,
                    updated_at = NOW()
            """
            execute_values(cursor, metadata_sql, metadata_data_to_insert, page_size=500)
            
            conn.commit()
            logger.info("Neighborhoods, metrics, and metadata tables updated successfully.")
            return True
        else:
            logger.info("No valid neighborhood data found to update.")
            return False

    except (psycopg2.Error, FileNotFoundError, json.JSONDecodeError, csv.Error, KeyError) as e:
        conn.rollback()
        logger.exception(f"Error updating neighborhoods tables: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def map_neighborhood_variants():
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
        cursor.execute("SELECT id, hebrew_name FROM neighborhoods WHERE hebrew_name IS NOT NULL")
        rows = cursor.fetchall()
        for row in rows:
            neighborhood_name_to_id[row['hebrew_name']] = row['id']
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
                    logger.warning(f"Mapped canonical name '{canonical_name_from_map}' for variant '{raw_hood_name}' not found in DB lookup (listing {listing_dict.get('listing_id')}). Setting neighborhood_id to NULL.")

    if neighborhood_id is None:
        if raw_hood_name: 
            logger.warning(f"Neighborhood ID not found for raw name '{raw_hood_name}' (listing {listing_dict.get('listing_id')}) after checking direct match and variant map. Setting neighborhood_id to NULL.")
        else:
                logger.warning(f"Raw neighborhood name was missing for listing {listing_dict.get('listing_id')}. Setting neighborhood_id to NULL.")
        unmapped_listings_count += 1
    return neighborhood_id, unmapped_listings_count

def fetch_existing_ids(conn, table, column) -> Set:
    """Fetches all existing IDs from a table for a given column."""
    with conn.cursor() as cur:
        cur.execute(f"SELECT {column} FROM {table}")
        return {row[0] for row in cur.fetchall()}
    
def insert_listings(cursor, listings_list, neighborhood_name_to_id, listing_tags_list, conn, variant_to_canonical_map):
    """Inserts listings into the database using the new schema with separate Listing and ListingMetadata tables."""
    logger.info(f"Processing {len(listings_list)} listings for DB update/insert...")
    listings_to_insert_update = []
    processed_listings_count = 0
    unmapped_listings_count = 0 

    for listing_dict in listings_list:
        listing_dict['neighborhood_id'], unmapped_listings_count = get_neighborhood_id_from_listing(listing_dict, neighborhood_name_to_id, variant_to_canonical_map, unmapped_listings_count)
        listing_dict['is_active'] = True
        processed_listings_count += 1
        listings_to_insert_update.append(listing_dict)

    if listings_to_insert_update:
        # Prepare data for main listings table
        listing_cols = [
            'listing_id', 'yad2_url_token', 'price', 'property_type', 
            'rooms_count', 'square_meter', 'street', 'house_number', 
            'floor', 'longitude', 'latitude'
        ]
        listing_tuples = [[l.get(col) for col in listing_cols] for l in listings_to_insert_update]
        
        # Prepare data for listing_metadata table
        metadata_cols = [
            'listing_id', 'neighborhood_id', 'category_id', 'subcategory_id',
            'ad_type', 'property_condition_id', 'cover_image_url', 'video_url', 'is_active'
        ]
        metadata_tuples = [[l.get(col) for col in metadata_cols] for l in listings_to_insert_update]
        
        try:
            # Insert into main listings table
            listing_cols_sql = ", ".join(listing_cols)
            listing_placeholders = ", ".join(["%s"] * len(listing_cols))
            listing_update_set_sql = ", ".join(
                [f"{col} = EXCLUDED.{col}" for col in listing_cols if col != 'listing_id']
            ) + ", updated_at = NOW()"
            sql_listings = f"""
                INSERT INTO listings ({listing_cols_sql}) VALUES ({listing_placeholders})
                ON CONFLICT (listing_id) DO UPDATE SET {listing_update_set_sql}
            """
            cursor.executemany(sql_listings, listing_tuples)
            
            # Insert into listing_metadata table
            metadata_cols_sql = ", ".join(metadata_cols)
            metadata_placeholders = ", ".join(["%s"] * len(metadata_cols))
            metadata_update_set_sql = ", ".join(
                [f"{col} = EXCLUDED.{col}" for col in metadata_cols if col != 'listing_id']
            ) + ", updated_at = NOW()"
            sql_metadata = f"""
                INSERT INTO listing_metadata ({metadata_cols_sql}) VALUES ({metadata_placeholders})
                ON CONFLICT (listing_id) DO UPDATE SET {metadata_update_set_sql}
            """
            cursor.executemany(sql_metadata, metadata_tuples)
            
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
                                logger.info(f"Nullifying invalid property_condition_id in listing {l.get('listing_id')}")
                                l["property_condition_id"] = None
                    except Exception as ce:
                        logger.exception(f"Error fixing property_condition_id: {ce}")

                elif "tag_id" in str(e):
                    try:
                        valid_ids = fetch_existing_ids(conn, "tags", "tag_id")
                        listing_tags_list[:] = [lt for lt in listing_tags_list if lt.get("tag_id") in valid_ids]
                    except Exception as ce:
                        logger.exception(f"Error fixing tag_id: {ce}")

                # Attempt second insert with fixed data
                listing_tuples = [[l.get(col) for col in listing_cols] for l in listings_to_insert_update]
                metadata_tuples = [[l.get(col) for col in metadata_cols] for l in listings_to_insert_update]
                try:
                    cursor.executemany(sql_listings, listing_tuples)
                    cursor.executemany(sql_metadata, metadata_tuples)
                    conn.commit()
                    logger.info("Retry successful after FK fix.")
                except Exception as retry_e:
                    conn.rollback()
                    logger.exception("Retry after FK fix failed.")
            elif isinstance(e, TypeError):
                logger.error("Likely column count mismatch.")
                logger.debug(f"Listing tuple: {listing_tuples[0] if listing_tuples else 'N/A'}")
                logger.debug(f"Metadata tuple: {metadata_tuples[0] if metadata_tuples else 'N/A'}")

def insert_images(cursor, images_list):
    """Inserts images into the database."""
    if images_list:
        logger.info(f"Inserting {len(images_list)} image records...")
        img_tuples = [(i.get('listing_id'), i.get('image_url'))
                    for i in images_list if i.get('listing_id') and i.get('image_url')]
        if img_tuples:
            execute_values(cursor,
                        "INSERT INTO images (listing_id, image_url) VALUES %s ON CONFLICT DO NOTHING",
                        img_tuples, page_size=500)
            logger.debug("Image insertion attempt complete.")

def insert_listing_tags(cursor, listing_tags_list):
    """Inserts listing-tag relationships into the database using the association table."""
    if listing_tags_list:
        logger.info(f"Inserting {len(listing_tags_list)} listing-tag relationships...")
        lt_tuples = [(lt.get('listing_id'), lt.get('tag_id'))
                        for lt in listing_tags_list if lt.get('listing_id') and lt.get('tag_id')]
        if lt_tuples:
            try:
                execute_values(cursor,
                                "INSERT INTO listing_tags (listing_id, tag_id) VALUES %s ON CONFLICT (listing_id, tag_id) DO NOTHING",
                                lt_tuples, page_size=1000)
                logger.debug("Listing-tag insertion attempt complete.")
            except Exception as e:
                logger.exception(f"Error during listing-tag insertion: {e}")
                logger.debug(f"Second attempt to insert listing-tag relationships: {lt_tuples}")
                execute_values(cursor,
                                "INSERT INTO listing_tags (listing_id, tag_id) VALUES %s ON CONFLICT (listing_id, tag_id) DO NOTHING",
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
        
    # Load variant mapping first
    variant_to_canonical_map = map_neighborhood_variants()
    
    logger.info("Ensuring all neighborhoods in listings exist in the database...")
    ensure_neighborhoods_exist(conn, listings_data, variant_to_canonical_map)

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

def ensure_neighborhoods_exist(conn, listings_data, variant_to_canonical_map):
    """
    Ensures that all neighborhoods mentioned in listings exist in the neighborhoods table.
    Creates simple placeholder entries for any missing canonical neighborhoods.
    Uses variant mapping to convert variant names to canonical names before checking.
    """
    if not conn or not listings_data:
        return
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("SELECT id, hebrew_name FROM neighborhoods")
        db_neighborhoods = {row['hebrew_name']: row['id'] for row in cursor.fetchall()}
        logger.info(f"Found {len(db_neighborhoods)} existing neighborhoods in database")
        
        canonical_neighborhoods = set()
        for listing in listings_data.get('listings', []):
            raw_hood_name = listing.get('neighborhood_text')
            if raw_hood_name:
                # Try to get canonical name from variant mapping
                canonical_name = variant_to_canonical_map.get(raw_hood_name, raw_hood_name)
                canonical_neighborhoods.add(canonical_name)
        
        logger.info(f"Found {len(canonical_neighborhoods)} unique canonical neighborhoods in listings")
        
        missing_neighborhoods = canonical_neighborhoods - set(db_neighborhoods.keys())
        
        if missing_neighborhoods:
            logger.info(f"Found {len(missing_neighborhoods)} canonical neighborhoods missing from database")
            logger.debug(f"Missing canonical neighborhoods: {sorted(missing_neighborhoods)}")
            
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
                logger.info(f"Added {len(neighborhoods_to_insert)} missing canonical neighborhoods to the database")
        else:
            logger.info("All canonical neighborhoods in listings already exist in the database")
            
    except (psycopg2.Error, Exception) as e:
        conn.rollback()
        logger.exception(f"Error ensuring neighborhoods exist: {e}")
    finally:
        if cursor:
            cursor.close()
