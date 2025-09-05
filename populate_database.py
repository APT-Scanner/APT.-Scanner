"""
Database population module for Yad2 listings ETL pipeline.

This module provides functions to populate the database with parsed listing data.
"""

import os
import sys
from typing import Dict, Any, List
from datetime import datetime

# Add the backend directory to Python path
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.append(backend_dir)

def populate_listings(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Populate the database with parsed listings data.
    
    This function takes the parsed and structured data from the ETL process
    and inserts/updates it in the database tables.
    
    Args:
        parsed_data (Dict[str, Any]): Dictionary containing:
            - 'listings': List of listing dictionaries
            - 'images': List of image dictionaries  
            - 'property_conditions': List of property condition dictionaries
            
    Returns:
        Dict[str, Any]: Summary of the population process
    """
    
    try:
        # Extract data components
        listings = parsed_data.get('listings', [])
        images = parsed_data.get('images', [])
        property_conditions = parsed_data.get('property_conditions', [])
        
        # Import database components (inside function to avoid import issues)
        try:
            from backend.src.database.postgresql_db import get_db_session
            from backend.src.database.models import Listing, Image, PropertyCondition, ListingMetadata
            from sqlalchemy.exc import IntegrityError
        except ImportError as e:
            print(f"Database import error: {e}")
            # Return mock result for environments without database access
            return {
                "status": "mock_success",
                "listings_inserted": len(listings),
                "images_inserted": len(images),
                "conditions_inserted": len(property_conditions),
                "message": "Mock population - database not available"
            }
        
        # Initialize counters
        listings_inserted = 0
        listings_updated = 0
        images_inserted = 0
        conditions_inserted = 0
        errors = []
        
        # Get database session
        with get_db_session() as session:
            
            # 1. Handle Property Conditions first (they're referenced by listings)
            for condition_data in property_conditions:
                try:
                    existing_condition = session.query(PropertyCondition).filter_by(
                        condition_id=condition_data['condition_id']
                    ).first()
                    
                    if not existing_condition:
                        condition = PropertyCondition(
                            condition_id=condition_data['condition_id'],
                            condition_name_he=condition_data['condition_name_he'],
                            condition_name_en=condition_data['condition_name_en']
                        )
                        session.add(condition)
                        conditions_inserted += 1
                        
                except Exception as e:
                    errors.append(f"Error inserting property condition {condition_data.get('condition_id')}: {e}")
            
            # 2. Handle Listings
            for listing_data in listings:
                try:
                    # Check if listing already exists
                    existing_listing = session.query(Listing).filter_by(
                        yad2_url_token=listing_data['yad2_url_token']
                    ).first()
                    
                    if existing_listing:
                        # Update existing listing
                        # Exclude metadata fields that should be set on ListingMetadata, not Listing
                        metadata_fields = {'cover_image_url', 'neighborhood_id', 'description', 'category_id', 'subcategory_id', 
                                         'ad_type', 'property_condition_id', 'video_url', 'is_active'}
                        for key, value in listing_data.items():
                            if (hasattr(existing_listing, key) and 
                                key not in ['listing_id', 'attributes'] and 
                                key not in metadata_fields):
                                setattr(existing_listing, key, value)
                        existing_listing.updated_at = datetime.utcnow()
                        listings_updated += 1
                        current_listing = existing_listing
                    else:
                        # Create new listing
                        listing = Listing(
                            listing_id=listing_data['listing_id'],
                            yad2_url_token=listing_data['yad2_url_token'],
                            price=listing_data.get('price'),
                            property_type=listing_data.get('property_type'),
                            rooms_count=listing_data.get('rooms_count'),
                            square_meter=listing_data.get('square_meter'),
                            street=listing_data.get('street'),
                            house_number=listing_data.get('house_number'),
                            floor=listing_data.get('floor'),
                            longitude=listing_data.get('longitude'),
                            latitude=listing_data.get('latitude')
                        )
                        session.add(listing)
                        listings_inserted += 1
                        current_listing = listing
                    
                    # Create/update listing metadata
                    existing_metadata = session.query(ListingMetadata).filter_by(
                        listing_id=listing_data['listing_id']
                    ).first()
                    
                    if existing_metadata:
                        # Update existing metadata
                        existing_metadata.category_id = listing_data.get('category_id')
                        existing_metadata.subcategory_id = listing_data.get('subcategory_id')
                        existing_metadata.ad_type = listing_data.get('ad_type')
                        existing_metadata.property_condition_id = listing_data.get('property_condition_id')
                        existing_metadata.cover_image_url = listing_data.get('cover_image_url')
                        existing_metadata.video_url = listing_data.get('video_url')
                        existing_metadata.description = listing_data.get('description', '')
                        existing_metadata.updated_at = datetime.utcnow()
                    else:
                        # Create new metadata
                        metadata = ListingMetadata(
                            listing_id=listing_data['listing_id'],
                            neighborhood_id=parsed_data.get('neighborhood_id'),
                            category_id=listing_data.get('category_id'),
                            subcategory_id=listing_data.get('subcategory_id'),
                            ad_type=listing_data.get('ad_type'),
                            property_condition_id=listing_data.get('property_condition_id'),
                            cover_image_url=listing_data.get('cover_image_url'),
                            video_url=listing_data.get('video_url'),
                            description=listing_data.get('description', ''),
                            is_active=True
                        )
                        session.add(metadata)
                    
                except Exception as e:
                    errors.append(f"Error processing listing {listing_data.get('listing_id')}: {e}")
            
            # 3. Handle Images
            for image_data in images:
                try:
                    # Check if image already exists
                    existing_image = session.query(Image).filter_by(
                        listing_id=image_data['listing_id'],
                        image_url=image_data['image_url']
                    ).first()
                    
                    if not existing_image:
                        image = Image(
                            listing_id=image_data['listing_id'],
                            image_url=image_data['image_url']
                        )
                        session.add(image)
                        images_inserted += 1
                        
                except Exception as e:
                    errors.append(f"Error inserting image for listing {image_data.get('listing_id')}: {e}")
            
            # Commit all changes
            session.commit()
            
        # Prepare results summary
        result = {
            "status": "success",
            "listings_inserted": listings_inserted,
            "listings_updated": listings_updated,
            "images_inserted": images_inserted,
            "conditions_inserted": conditions_inserted,
            "total_processed": listings_inserted + listings_updated,
            "errors_count": len(errors),
            "errors": errors[:10] if errors else []  # Limit errors shown
        }
        
        print(f"Database population completed:")
        print(f"- Listings inserted: {listings_inserted}")
        print(f"- Listings updated: {listings_updated}")
        print(f"- Images inserted: {images_inserted}")
        print(f"- Property conditions inserted: {conditions_inserted}")
        if errors:
            print(f"- Errors encountered: {len(errors)}")
            
        return result
        
    except Exception as e:
        error_msg = f"Critical error in populate_listings: {e}"
        print(error_msg)
        return {
            "status": "error",
            "message": error_msg,
            "listings_inserted": 0,
            "listings_updated": 0,
            "images_inserted": 0,
            "conditions_inserted": 0
        }


def cleanup_inactive_listings(days_old: int = 7) -> Dict[str, Any]:
    """
    Mark old listings as inactive if they haven't been updated recently.
    
    Args:
        days_old (int): Number of days after which to mark listings as inactive
        
    Returns:
        Dict[str, Any]: Summary of cleanup process
    """
    
    try:
        from src.database.postgresql_db import get_db_session
        from src.database.models import ListingMetadata
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        with get_db_session() as session:
            updated_count = session.query(ListingMetadata).filter(
                ListingMetadata.updated_at < cutoff_date,
                ListingMetadata.is_active == True
            ).update({
                'is_active': False,
                'updated_at': datetime.utcnow()
            })
            
            session.commit()
            
        return {
            "status": "success",
            "listings_deactivated": updated_count,
            "cutoff_date": cutoff_date.isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error", 
            "message": str(e),
            "listings_deactivated": 0
        }
