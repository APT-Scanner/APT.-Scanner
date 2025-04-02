
-- Drop tables in reverse order of dependency to avoid foreign key errors
DROP TABLE IF EXISTS listing_tags;
DROP TABLE IF EXISTS images;
DROP TABLE IF EXISTS listings;
DROP TABLE IF EXISTS neighborhoods;
DROP TABLE IF EXISTS tags;
DROP TABLE IF EXISTS property_conditions;
DROP FUNCTION IF EXISTS trigger_set_timestamp();

-- Lookup Table: Property Conditions
CREATE TABLE property_conditions (
    condition_id INT PRIMARY KEY,
    condition_name_he VARCHAR(100),
    condition_name_en VARCHAR(100)
);

COMMENT ON TABLE property_conditions IS 'Lookup table for property condition descriptions.';

-- Lookup Table: Tags
CREATE TABLE tags (
    tag_id INT PRIMARY KEY,
    tag_name VARCHAR(100) NOT NULL UNIQUE
);

COMMENT ON TABLE tags IS 'Lookup table for unique listing tags.';

-- Main Table: Neighborhoods
CREATE TABLE neighborhoods (
    yad2_hood_id INT PRIMARY KEY,             -- Yad2 ID as the unique primary key
    hebrew_name VARCHAR(150) UNIQUE NOT NULL, -- Hebrew name (from mapping & CSV) - must be unique
    english_name VARCHAR(150) UNIQUE,         -- English name (from CSV)
    avg_purchase_price DECIMAL(15, 2),        -- Average purchase price (from CSV)
    avg_rent_price DECIMAL(10, 2),            -- Average rent price (from CSV)
    socioeconomic_index FLOAT,                -- Socioeconomic index (from CSV)
    avg_school_rating FLOAT,                  -- Average school rating (from CSV)
    general_overview TEXT,                    -- General overview (from CSV)
    bars_count INT DEFAULT 0,                 -- Counts (from CSV), default 0 if missing
    restaurants_count INT DEFAULT 0,
    clubs_count INT DEFAULT 0,
    shopping_malls_count INT DEFAULT 0,
    unique_entertainment_count INT DEFAULT 0,
    primary_schools_count INT DEFAULT 0,
    elementary_schools_count INT DEFAULT 0,
    secondary_schools_count INT DEFAULT 0,
    high_schools_count INT DEFAULT 0,
    universities_count INT DEFAULT 0,
    closest_beach_distance_km FLOAT,          -- Distance to beach (from CSV)
    latitude FLOAT,                           -- Coordinates (from CSV)
    longitude FLOAT,
    yad2_city_id INT,                         -- Additional info from Yad2 mapping
    yad2_area_id INT,
    yad2_top_area_id INT,
    yad2_doc_count INT,                       -- Maybe listing count? (from mapping)
    created_at TIMESTAMPTZ DEFAULT NOW(),     -- Record creation timestamp
    updated_at TIMESTAMPTZ DEFAULT NOW()      -- Record last update timestamp
);

COMMENT ON TABLE neighborhoods IS 'Stores detailed information about neighborhoods, linked by Yad2 hood ID.';
COMMENT ON COLUMN neighborhoods.yad2_doc_count IS 'Possibly the number of listings found by Yad2 for this neighborhood at the time of mapping.';


-- Main Table: Listings
CREATE TABLE listings (
    order_id BIGINT PRIMARY KEY,              -- Yad2 orderId as the primary key
    token VARCHAR(10) UNIQUE NOT NULL,        -- Yad2 short token

    -- Foreign key to neighborhoods table
    neighborhood_id INT,                      -- Will hold yad2_hood_id

    -- Foreign key to property conditions
    property_condition_id INT,

    -- Other listing details from Yad2 data
    subcategory_id INT,
    category_id INT,
    ad_type VARCHAR(20),
    price DECIMAL(10, 2),                     -- Use DECIMAL for currency
    property_type VARCHAR(50),
    rooms_count DECIMAL(3, 1),                -- Allows for half rooms like 2.5
    square_meter INT,
    cover_image_url TEXT,
    video_url TEXT,
    priority INT,

    -- Listing-specific address details
    city VARCHAR(100),
    area VARCHAR(100),                        -- Area text as it appears in the listing
    neighborhood_text VARCHAR(150),           -- Neighborhood text as it appears in the listing (for display/reference)
    street VARCHAR(150),
    house_number VARCHAR(20),                 -- Use VARCHAR to allow non-standard numbering like '10א'
    floor INT,
    longitude FLOAT,                          -- Listing-specific coordinates
    latitude FLOAT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Define Foreign Key constraints
    FOREIGN KEY (neighborhood_id) REFERENCES neighborhoods(yad2_hood_id) ON DELETE SET NULL, -- Or ON DELETE RESTRICT if a neighborhood shouldn't be deleted if listings exist
    FOREIGN KEY (property_condition_id) REFERENCES property_conditions(condition_id) ON DELETE SET NULL -- Set condition to NULL if the condition type is deleted
);

COMMENT ON TABLE listings IS 'Stores individual apartment listings from Yad2.';
COMMENT ON COLUMN listings.neighborhood_id IS 'FK referencing the neighborhoods table using yad2_hood_id.';
COMMENT ON COLUMN listings.neighborhood_text IS 'The raw neighborhood name text as it appeared in the source listing data.';


-- Table: Images (One-to-Many relationship with listings)
CREATE TABLE images (
    image_id SERIAL PRIMARY KEY,              -- Auto-incrementing ID for each image
    listing_order_id BIGINT NOT NULL,
    image_url TEXT NOT NULL,

    -- If a listing is deleted, delete its associated images
    FOREIGN KEY (listing_order_id) REFERENCES listings(order_id) ON DELETE CASCADE,
    UNIQUE (listing_order_id, image_url)
);

COMMENT ON TABLE images IS 'Stores image URLs associated with listings.';


-- Junction Table: Listing Tags (Many-to-Many relationship)
CREATE TABLE listing_tags (
    listing_order_id BIGINT NOT NULL,
    tag_id INT NOT NULL,

    -- Composite primary key ensures a tag is linked only once per listing
    PRIMARY KEY (listing_order_id, tag_id),

    -- If a listing is deleted, delete its tag associations
    FOREIGN KEY (listing_order_id) REFERENCES listings(order_id) ON DELETE CASCADE,
    -- If a tag is deleted (from tags table), delete its associations
    FOREIGN KEY (tag_id) REFERENCES tags(tag_id) ON DELETE CASCADE
);

COMMENT ON TABLE listing_tags IS 'Junction table linking listings and tags (Many-to-Many).';

-- Trigger Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply the trigger to update updated_at on UPDATE operations for main tables
CREATE TRIGGER set_timestamp_neighborhoods
BEFORE UPDATE ON neighborhoods
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

CREATE TRIGGER set_timestamp_listings
BEFORE UPDATE ON listings
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();
