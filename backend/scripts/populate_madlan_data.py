#!/usr/bin/env python3
"""
Script to populate neighborhoods table with Madlan metrics data.
This script will:
1. Load neighborhood data from the JSON mapping file
2. Use MadlanScraper to get metrics for each neighborhood
3. Update the database with the scraped metrics
"""

import os
import sys
import json
from datetime import datetime, UTC
from typing import Dict, Any, Optional

# Add the parent directory to sys.path to import modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.database.models import Neighborhood
from data.scrapers.madlan_scraper import MadlanScraper
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create synchronous database connection for scripts
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

# Convert async URL to sync for scripts
if DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
elif DATABASE_URL.startswith("postgresql://"):
    pass  # Already sync
else:
    raise ValueError("Unsupported database URL format")

# Create sync engine and session for scripts
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def parse_madlan_metrics(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Parse and extract specific metrics from the raw Madlan data."""
    parsed = {
        "overview": metrics.get("סקירה כללית"),
        "avg_price_per_sqm": None,
        "price_trend": None,
        "demand_level": None,
        "supply_level": None
    }
    
    # Try to extract numeric values from price-related metrics
    for key, value in metrics.items():
        if "מחיר" in key and "מ״ר" in key:  # Price per sqm
            # Extract numbers from Hebrew text
            import re
            numbers = re.findall(r'[\d,]+', str(value))
            if numbers:
                try:
                    # Remove commas and convert to float
                    parsed["avg_price_per_sqm"] = float(numbers[0].replace(',', ''))
                except (ValueError, IndexError):
                    pass
        
        if "מגמת מחירים" in key or "מגמה" in key:  # Price trend
            parsed["price_trend"] = str(value)[:50]  # Limit to 50 chars
            
        if "ביקוש" in key:  # Demand
            parsed["demand_level"] = str(value)[:50]
            
        if "היצע" in key:  # Supply
            parsed["supply_level"] = str(value)[:50]
    
    return parsed


def update_neighborhood_madlan_data(
    db: Session, 
    neighborhood_id: int, 
    madlan_name: Optional[str],
    scraped_data: Dict[str, Any],
    scraped_with_madlan_name: bool
) -> bool:
    """Update a neighborhood record with Madlan data."""
    try:
        neighborhood = db.query(Neighborhood).filter(
            Neighborhood.yad2_hood_id == neighborhood_id
        ).first()
        
        if not neighborhood:
            print(f"Neighborhood with ID {neighborhood_id} not found in database")
            return False
        
        # Parse the metrics
        parsed_metrics = parse_madlan_metrics(scraped_data)
        
        # Update the neighborhood record
        neighborhood.madlan_name = madlan_name
        neighborhood.madlan_metrics = scraped_data
        neighborhood.madlan_overview = parsed_metrics["overview"]
        neighborhood.madlan_avg_price_per_sqm = parsed_metrics["avg_price_per_sqm"]
        neighborhood.madlan_price_trend = parsed_metrics["price_trend"]
        neighborhood.madlan_demand_level = parsed_metrics["demand_level"]
        neighborhood.madlan_supply_level = parsed_metrics["supply_level"]
        neighborhood.madlan_last_scraped = datetime.now(UTC)
        
        db.commit()
        
        source_name = "Madlan name" if scraped_with_madlan_name else "regular name"
        print(f"Updated {neighborhood.hebrew_name} (scraped with {source_name})")
        return True
        
    except Exception as e:
        print(f"Error updating neighborhood {neighborhood_id}: {e}")
        db.rollback()
        return False


def populate_madlan_data():
    """Main function to populate all neighborhoods with Madlan data."""
    
    # Check for API key
    api_key = os.getenv("SCRAPEOWL_API_KEY")
    if not api_key:
        print("Error: SCRAPEOWL_API_KEY environment variable is required")
        return False
    
    # Initialize scraper
    scraper = MadlanScraper(api_key=api_key)
    
    # Load neighborhood mappings
    mapping_file = os.path.join(os.path.dirname(__file__), "..", "data", "sources", "yad2_hood_mapping.json")
    
    try:
        with open(mapping_file, "r", encoding='utf-8') as f:
            neighborhoods = json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find mapping file at {mapping_file}")
        return False
    
    # Create database session
    db = SessionLocal()
    
    try:
        successful_updates = 0
        failed_updates = 0
        
        for i, neighborhood in enumerate(neighborhoods, 1):
            print(f"\nProcessing neighborhood {i}/{len(neighborhoods)}")
            
            # Use madlan_name if available, otherwise use regular neighborhood_name
            neighborhood_name = neighborhood.get("madlan_name", neighborhood["neigborhood_name"])
            city_name = neighborhood["city_name"]
            country = "ישראל"
            
            print(f"Scraping data for {neighborhood_name}, {city_name}...")
            
            try:
                # Scrape data from Madlan
                scraped_data = scraper.scrape(
                    neighborhood=neighborhood_name, 
                    city=city_name, 
                    country=country
                )
                
                # Check if scraping was successful
                if "error" in scraped_data:
                    print(f"Scraping failed: {scraped_data['error']}")
                    failed_updates += 1
                    continue
                
                # Update database
                if update_neighborhood_madlan_data(
                    db=db,
                    neighborhood_id=neighborhood["hoodId"],
                    madlan_name=neighborhood.get("madlan_name"),
                    scraped_data=scraped_data,
                    scraped_with_madlan_name="madlan_name" in neighborhood
                ):
                    successful_updates += 1
                else:
                    failed_updates += 1
                    
            except Exception as e:
                print(f"Failed to process {neighborhood_name}: {e}")
                failed_updates += 1
        
        print(f"\n=== SUMMARY ===")
        print(f"Successfully updated: {successful_updates} neighborhoods")
        print(f"Failed to update: {failed_updates} neighborhoods")
        print(f"Total processed: {len(neighborhoods)} neighborhoods")
        
        return successful_updates > 0
        
    finally:
        db.close()


if __name__ == "__main__":
    print("Starting Madlan data population process...")
    success = populate_madlan_data()
    
    if success:
        print("\nMadlan data population completed successfully!")
    else:
        print("\nMadlan data population failed or had no updates!")
        sys.exit(1) 