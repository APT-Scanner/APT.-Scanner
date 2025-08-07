import csv  
import json
import logging
import sys
import os
from decimal import Decimal

# Add the backend directory to the Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey, DECIMAL, TEXT, TIMESTAMP, DateTime, text
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase, Mapped, mapped_column
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ARRAY
from dotenv import load_dotenv
from typing import Optional, List
from datetime import datetime
import ssl

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

try:
    from populate_madlan_data import parse_madlan_metrics
except ImportError:
    logger.warning("populate_madlan_data not found, will use basic CSV data only")
    parse_madlan_metrics = None

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define simplified base and models for population only
class Base(DeclarativeBase):
    pass

class Neighborhood(Base):
    """Simplified neighborhood model for population."""
    __tablename__ = "neighborhoods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hebrew_name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    english_name: Mapped[Optional[str]] = mapped_column(String(150), unique=True)
    city: Mapped[Optional[str]] = mapped_column(String(100))
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

class NeighborhoodMetrics(Base):
    """Simplified metrics model for population."""
    __tablename__ = "neighborhood_metrics"

    neighborhood_id: Mapped[int] = mapped_column(Integer, ForeignKey("neighborhoods.id", ondelete="CASCADE"), primary_key=True)
    avg_sale_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(15, 2))
    avg_rental_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 2))
    social_economic_index: Mapped[Optional[float]] = mapped_column(Float)
    popular_political_party: Mapped[Optional[str]] = mapped_column(String(100))
    school_rating: Mapped[Optional[float]] = mapped_column(Float)
    beach_distance_km: Mapped[Optional[float]] = mapped_column(DECIMAL(10, 2))
    
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

class NeighborhoodMetadata(Base):
    """Simplified metadata model for population."""
    __tablename__ = "neighborhood_metadata"

    neighborhood_id: Mapped[int] = mapped_column(Integer, ForeignKey("neighborhoods.id", ondelete="CASCADE"), primary_key=True)
    overview: Mapped[Optional[str]] = mapped_column(TEXT)
    external_city_id: Mapped[Optional[int]] = mapped_column(Integer)
    external_area_id: Mapped[Optional[int]] = mapped_column(Integer)
    external_top_area_id: Mapped[Optional[int]] = mapped_column(Integer)
    
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

class NeighborhoodFeatures(Base):
    """Simplified features model for population."""
    __tablename__ = "neighborhood_features"
    
    neighborhood_id: Mapped[int] = mapped_column(Integer, ForeignKey("neighborhoods.id", ondelete="CASCADE"), primary_key=True)
    
    # Individual feature scores (0-1 scale)
    cultural_level: Mapped[Optional[float]] = mapped_column(Float)
    religiosity_level: Mapped[Optional[float]] = mapped_column(Float)
    communality_level: Mapped[Optional[float]] = mapped_column(Float)
    kindergardens_level: Mapped[Optional[float]] = mapped_column(Float)
    maintenance_level: Mapped[Optional[float]] = mapped_column(Float)
    mobility_level: Mapped[Optional[float]] = mapped_column(Float)
    parks_level: Mapped[Optional[float]] = mapped_column(Float)
    peaceful_level: Mapped[Optional[float]] = mapped_column(Float)
    shopping_level: Mapped[Optional[float]] = mapped_column(Float)
    safety_level: Mapped[Optional[float]] = mapped_column(Float)
    nightlife_level: Mapped[Optional[float]] = mapped_column(Float)
    
    # Combined feature vector for ML calculations
    feature_vector: Mapped[Optional[List[float]]] = mapped_column(ARRAY(Float))
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())

def get_sync_db_session() -> Session:
    """Create a synchronous database session for script usage."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    # Convert async URL to sync URL
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    # Create SSL context
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    # Create synchronous engine
    engine = create_engine(
        database_url,
        echo=False,  # Set to True for SQL debugging
        connect_args={"sslmode": "require"}
    )
    
    # Create session
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()

def clear_neighborhood_data(db: Session):
    """Clear all existing neighborhood data from the database."""
    try:
        logger.info("Clearing existing neighborhood data...")
        
        # Delete in correct order due to foreign key constraints
        db.execute(text("DELETE FROM neighborhood_features"))
        db.execute(text("DELETE FROM neighborhood_metadata"))
        db.execute(text("DELETE FROM neighborhood_metrics"))
        db.execute(text("DELETE FROM neighborhoods"))
        
        db.commit()
        logger.info("Successfully cleared all neighborhood data.")
        
    except Exception as e:
        logger.error(f"Error clearing neighborhood data: {e}")
        db.rollback()
        raise

def safe_decimal(value):
    """Safely convert value to Decimal, handling empty/null values."""
    if not value or str(value).strip() == '':
        return None
    try:
        return Decimal(str(value))
    except (ValueError, TypeError):
        return None

def safe_float(value):
    """Safely convert value to float, handling empty/null values."""
    if not value or str(value).strip() == '':
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def safe_int(value):
    """Safely convert value to int, handling empty/null values."""
    if not value or str(value).strip() == '':
        return None
    try:
        return int(float(value))  # Handle decimal strings like "1.0"
    except (ValueError, TypeError):
        return None
    
def safe_str(value):
    """Safely convert value to str, handling empty/null values."""
    if not value or str(value).strip() == '':
        return None
    try:
        return str(value)
    except (ValueError, TypeError):
        return None

def get_metrics_data(row):
    """Extract metrics data from row, prioritizing madlan_metrics if available."""
    madlan_metrics_raw = row.get("madlan_metrics", "")
    
    # Try to parse madlan metrics first
    if madlan_metrics_raw and madlan_metrics_raw.strip() and parse_madlan_metrics:
        try:
            # Check if the madlan_metrics is a valid JSON-like structure
            if madlan_metrics_raw.startswith("{") and madlan_metrics_raw.endswith("}"):
                metrics_dict = json.loads(madlan_metrics_raw)
                madlan_data = parse_madlan_metrics(metrics_dict)
                # Ensure madlan_data is a dictionary
                if isinstance(madlan_data, dict):
                    return {
                        "avg_sale_price": safe_decimal(madlan_data.get("avg_sale_price")),
                        "avg_rental_price": safe_decimal(madlan_data.get("avg_rental_price")), 
                        "social_economic_index": safe_float(madlan_data.get("social_economic_index")),
                        "school_rating": safe_float(madlan_data.get("school_rating")),
                        "popular_political_party": safe_str(madlan_data.get("popular_political_party")),
                        "beach_distance_km": safe_decimal(row.get("closest_beach_distance_km")),
                        "overview": madlan_data.get("overview", "").strip() if madlan_data.get("overview") else None
                    }
        except Exception as e:
            # Don't log every single parsing error - just fall back silently
            pass
    
    # Fall back to basic CSV data
    overview = row.get("general_overview", "") or row.get("madlan_overview", "")
    return {
        "avg_sale_price": safe_decimal(row.get("avg_purchase_price")),
        "avg_rental_price": safe_decimal(row.get("avg_rent_price")),
        "social_economic_index": safe_float(row.get("socioeconomic_index")),
        "school_rating": safe_float(row.get("avg_school_rating")),
        "beach_distance_km": safe_decimal(row.get("closest_beach_distance_km")),
        "overview": overview.strip() if overview else None
    }

def populate_neighborhoods():
    """Populate neighborhood tables from CSV data."""
    db = get_sync_db_session()
    
    try:
        # Clear existing data first
        clear_neighborhood_data(db)
        
        # Use absolute path relative to the script location
        csv_file_path = os.path.join(backend_dir, "data", "sources", "Neighborhoods_Data.csv")
        
        with open(csv_file_path, "r", encoding='utf-8') as f:
            reader = csv.DictReader(f)
            total_rows = 0
            processed_rows = 0
            batch_size = 5  # Process in batches for better performance
            
            logger.info("Starting neighborhood data population...")
            
            # Since we cleared all data, no need to check existing IDs
            existing_ids = set()
            
            for row in reader:
                total_rows += 1
                
                try:
                    neighborhood_id = safe_int(row["yad2_hood_id"])
                    if not neighborhood_id:
                        logger.warning(f"Invalid neighborhood ID for row {total_rows}, skipping...")
                        continue
                    
                    # Get metrics data (madlan or fallback to CSV)
                    metrics_data = get_metrics_data(row)
                    
                    # Create Neighborhood record
                    neighborhood = Neighborhood(
                        id=neighborhood_id,
                        hebrew_name=row["hebrew_name"].strip() if row["hebrew_name"] else None,
                        english_name=row["english_name"].strip() if row["english_name"] else None,
                        city=row["city"].strip() if row["city"] else None,
                        latitude=safe_float(row["latitude"]),
                        longitude=safe_float(row["longitude"])
                    )
                    db.add(neighborhood)
                    
                    # Create NeighborhoodMetrics record
                    metrics = NeighborhoodMetrics(
                        neighborhood_id=neighborhood_id,
                        avg_sale_price=metrics_data["avg_sale_price"],
                        avg_rental_price=metrics_data["avg_rental_price"],
                        social_economic_index=metrics_data["social_economic_index"],
                        popular_political_party=metrics_data["popular_political_party"],
                        school_rating=metrics_data["school_rating"],
                        beach_distance_km=metrics_data["beach_distance_km"]
                    )
                    db.add(metrics)
                    
                    # Create NeighborhoodMetadata record
                    metadata = NeighborhoodMetadata(
                        neighborhood_id=neighborhood_id,
                        overview=metrics_data["overview"],
                        external_city_id=safe_int(row.get("yad2_city_id")),
                        external_area_id=safe_int(row.get("yad2_area_id")),
                        external_top_area_id=safe_int(row.get("yad2_top_area_id")),
                    )
                    db.add(metadata)
                    
                    # Create NeighborhoodFeatures record for recommendation system
                    features = NeighborhoodFeatures(
                        neighborhood_id=neighborhood_id,
                        # Initialize features with default values - these should be calculated separately
                        cultural_level=None,
                        religiosity_level=None,
                        communality_level=None,
                        kindergardens_level=None,
                        maintenance_level=None,
                        mobility_level=None,
                        parks_level=None,
                        peaceful_level=None,
                        shopping_level=None,
                        safety_level=None,
                        nightlife_level=None,
                        feature_vector=None
                    )
                    db.add(features)
                    
                    # Add to existing set
                    existing_ids.add(neighborhood_id)
                    processed_rows += 1
                    
                    # Batch commit every batch_size records
                    if processed_rows % batch_size == 0:
                        try:
                            db.commit()
                            logger.info(f"Processed {processed_rows} neighborhoods...")
                        except Exception as e:
                            logger.error(f"Error committing batch: {e}")
                            db.rollback()
                            continue
                    
                except IntegrityError as e:
                    logger.warning(f"Integrity error for neighborhood {row.get('hebrew_name', 'unknown')}: {e}")
                    db.rollback()
                    continue
                except Exception as e:
                    logger.error(f"Error processing neighborhood {row.get('hebrew_name', 'unknown')}: {e}")
                    db.rollback()
                    continue
            
            # Commit any remaining records
            if processed_rows % batch_size != 0:
                try:
                    db.commit()
                except Exception as e:
                    logger.error(f"Error committing final batch: {e}")
                    db.rollback()
            
            logger.info(f"Population completed. Processed {processed_rows}/{total_rows} neighborhoods successfully.")
            
    except FileNotFoundError:
        logger.error(f"CSV file not found: {csv_file_path}")
    except Exception as e:
        logger.error(f"Unexpected error during population: {e}")
        db.rollback()
    finally:
        db.close()

def populate_neighborhoods_features():
    """Populate neighborhood features from CSV data."""
    db = get_sync_db_session()
    
    try:
        # Use absolute path relative to the script location
        csv_file_path = os.path.join(backend_dir, "data", "sources", "Neighborhood_Features.csv")
        
        with open(csv_file_path, "r", encoding='utf-8') as f:
            reader = csv.DictReader(f)
            total_rows = 0
            processed_rows = 0
            batch_size = 10  # Process in batches for better performance
            
            logger.info("Starting neighborhood features population...")
            
            for row in reader:
                total_rows += 1
                
                try:
                    neighborhood_id = safe_int(row["yad2_hood_id"])
                    if not neighborhood_id:
                        logger.warning(f"Invalid neighborhood ID for row {total_rows}, skipping...")
                        continue
                    
                    # Check if neighborhood exists
                    existing_neighborhood = db.query(Neighborhood).filter_by(id=neighborhood_id).first()
                    if not existing_neighborhood:
                        logger.warning(f"Neighborhood {neighborhood_id} not found, skipping features...")
                        continue
                    
                    # Check if features already exist and update or create
                    existing_features = db.query(NeighborhoodFeatures).filter_by(neighborhood_id=neighborhood_id).first()
                    
                    if existing_features:
                        # Update existing features
                        existing_features.cultural_level = safe_float(row.get("cultural_level"))
                        existing_features.religiosity_level = safe_float(row.get("religiosity_level"))
                        existing_features.communality_level = safe_float(row.get("communality_level"))
                        existing_features.kindergardens_level = safe_float(row.get("kindergardens_level"))
                        existing_features.maintenance_level = safe_float(row.get("maintenance_level"))
                        existing_features.mobility_level = safe_float(row.get("mobility_level"))
                        existing_features.parks_level = safe_float(row.get("parks_level"))
                        existing_features.peaceful_level = safe_float(row.get("peaceful_level"))
                        existing_features.shopping_level = safe_float(row.get("shopping_level"))
                        existing_features.safety_level = safe_float(row.get("safety_level"))
                        existing_features.nightlife_level = safe_float(row.get("nightlife_level"))
                        
                        # Create feature vector from individual scores
                        features_list = [
                            existing_features.cultural_level or 0,
                            existing_features.religiosity_level or 0,
                            existing_features.communality_level or 0,
                            existing_features.kindergardens_level or 0,
                            existing_features.maintenance_level or 0,
                            existing_features.mobility_level or 0,
                            existing_features.parks_level or 0,
                            existing_features.peaceful_level or 0,
                            existing_features.shopping_level or 0,
                            existing_features.safety_level or 0,
                            existing_features.nightlife_level or 0
                        ]
                        existing_features.feature_vector = features_list
                    else:
                        # Create new NeighborhoodFeatures record
                        cultural_level = safe_float(row.get("cultural_level"))
                        religiosity_level = safe_float(row.get("religiosity_level"))
                        communality_level = safe_float(row.get("communality_level"))
                        kindergardens_level = safe_float(row.get("kindergardens_level"))
                        maintenance_level = safe_float(row.get("maintenance_level"))
                        mobility_level = safe_float(row.get("mobility_level"))
                        parks_level = safe_float(row.get("parks_level"))
                        peaceful_level = safe_float(row.get("peaceful_level"))
                        shopping_level = safe_float(row.get("shopping_level"))
                        safety_level = safe_float(row.get("safety_level"))
                        nightlife_level = safe_float(row.get("nightlife_level"))
                        
                        # Create feature vector from individual scores
                        features_list = [
                            cultural_level or 0,
                            religiosity_level or 0,
                            communality_level or 0,
                            kindergardens_level or 0,
                            maintenance_level or 0,
                            mobility_level or 0,
                            parks_level or 0,
                            peaceful_level or 0,
                            shopping_level or 0,
                            safety_level or 0,
                            nightlife_level or 0
                        ]
                        
                        features = NeighborhoodFeatures(
                            neighborhood_id=neighborhood_id,
                            cultural_level=cultural_level,
                            religiosity_level=religiosity_level,
                            communality_level=communality_level,
                            kindergardens_level=kindergardens_level,
                            maintenance_level=maintenance_level,
                            mobility_level=mobility_level,
                            parks_level=parks_level,
                            peaceful_level=peaceful_level,
                            shopping_level=shopping_level,
                            safety_level=safety_level,
                            nightlife_level=nightlife_level,
                            feature_vector=features_list
                        )
                        db.add(features)
                    
                    processed_rows += 1
                    
                    # Batch commit every batch_size records
                    if processed_rows % batch_size == 0:
                        try:
                            db.commit()
                            logger.info(f"Processed {processed_rows} neighborhood features...")
                        except Exception as e:
                            logger.error(f"Error committing batch: {e}")
                            db.rollback()
                            continue
                    
                except IntegrityError as e:
                    logger.warning(f"Integrity error for neighborhood {row.get('hebrew_name', 'unknown')}: {e}")
                    db.rollback()
                    continue
                except Exception as e:
                    logger.error(f"Error processing neighborhood features {row.get('hebrew_name', 'unknown')}: {e}")
                    db.rollback()
                    continue
            
            # Commit any remaining records
            if processed_rows % batch_size != 0:
                try:
                    db.commit()
                except Exception as e:
                    logger.error(f"Error committing final batch: {e}")
                    db.rollback()
            
            logger.info(f"Features population completed. Processed {processed_rows}/{total_rows} neighborhoods successfully.")
            
    except FileNotFoundError:
        logger.error(f"Features CSV file not found: {csv_file_path}")
    except Exception as e:
        logger.error(f"Unexpected error during features population: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # First populate neighborhoods
    populate_neighborhoods()
    
    # Then populate features
    populate_neighborhoods_features()







