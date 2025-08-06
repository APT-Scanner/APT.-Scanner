#!/usr/bin/env python3
"""
Test script for Madlan integration.
Tests with a small subset of neighborhoods to validate the implementation.
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
import ssl

# Load environment variables
load_dotenv()

# Create synchronous database connection for testing
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

# Convert async URL to sync for testing
if DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
elif DATABASE_URL.startswith("postgresql://"):
    pass  # Already sync
else:
    raise ValueError("Unsupported database URL format")

# Create sync engine for testing
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


def test_madlan_integration():
    """Test Madlan integration with a few neighborhoods."""
    
    # Check for API key
    api_key = os.getenv("SCRAPEOWL_API_KEY")
    if not api_key:
        print("Warning: SCRAPEOWL_API_KEY not found. Testing with mock data...")
        return test_with_mock_data()
    
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
    
    # Test with first 3 neighborhoods (mix of with/without madlan_name)
    test_neighborhoods = neighborhoods[:3]
    
    print("Testing with the following neighborhoods:")
    for i, hood in enumerate(test_neighborhoods, 1):
        has_madlan_name = "madlan_name" in hood
        madlan_name = hood.get("madlan_name", "N/A")
        print(f"{i}. {hood['neigborhood_name']} (Madlan name: {madlan_name}) - Has madlan_name: {has_madlan_name}")
    
    # Create database session
    db = SessionLocal()
    
    try:
        results = []
        
        for i, neighborhood in enumerate(test_neighborhoods, 1):
            print(f"\n--- Testing neighborhood {i}/3: {neighborhood['neigborhood_name']} ---")
            
            # Use madlan_name if available, otherwise use regular neighborhood_name
            neighborhood_name = neighborhood.get("madlan_name", neighborhood["neigborhood_name"])
            city_name = neighborhood["city_name"]
            country = "ישראל"
            
            print(f"Scraping: {neighborhood_name}, {city_name}")
            print(f"Using {'Madlan name' if 'madlan_name' in neighborhood else 'regular name'}")
            
            try:
                # Test scraping
                scraped_data = scraper.scrape(
                    neighborhood=neighborhood_name, 
                    city=city_name, 
                    country=country
                )
                
                # Check if scraping was successful
                if "error" in scraped_data:
                    print(f"❌ Scraping failed: {scraped_data['error']}")
                    results.append({
                        "neighborhood": neighborhood['neigborhood_name'],
                        "status": "scraping_failed",
                        "error": scraped_data['error']
                    })
                    continue
                
                print(f"✅ Scraping successful. Found {len(scraped_data)} metrics")
                print(f"Sample metrics: {list(scraped_data.keys())[:3]}...")
                
                # Test parsing
                parsed_metrics = parse_madlan_metrics(scraped_data)
                print(f"✅ Parsing successful. Overview: {bool(parsed_metrics['overview'])}")
                print(f"Price per sqm: {parsed_metrics['avg_price_per_sqm']}")
                
                # Test database update
                db_update_success = update_neighborhood_madlan_data(
                    db=db,
                    neighborhood_id=neighborhood["hoodId"],
                    madlan_name=neighborhood.get("madlan_name"),
                    scraped_data=scraped_data,
                    scraped_with_madlan_name="madlan_name" in neighborhood
                )
                
                if db_update_success:
                    print("✅ Database update successful")
                    results.append({
                        "neighborhood": neighborhood['neigborhood_name'],
                        "status": "success",
                        "metrics_count": len(scraped_data),
                        "has_overview": bool(parsed_metrics['overview']),
                        "has_price": parsed_metrics['avg_price_per_sqm'] is not None
                    })
                else:
                    print("❌ Database update failed")
                    results.append({
                        "neighborhood": neighborhood['neigborhood_name'],
                        "status": "db_update_failed"
                    })
                    
            except Exception as e:
                print(f"❌ Test failed for {neighborhood_name}: {e}")
                results.append({
                    "neighborhood": neighborhood['neigborhood_name'],
                    "status": "error",
                    "error": str(e)
                })
        
        # Print summary
        print(f"\n{'='*50}")
        print("TEST SUMMARY")
        print(f"{'='*50}")
        
        successful_tests = [r for r in results if r["status"] == "success"]
        failed_tests = [r for r in results if r["status"] != "success"]
        
        print(f"✅ Successful tests: {len(successful_tests)}")
        print(f"❌ Failed tests: {len(failed_tests)}")
        
        if successful_tests:
            print("\nSuccessful neighborhoods:")
            for result in successful_tests:
                print(f"  - {result['neighborhood']} ({result['metrics_count']} metrics)")
        
        if failed_tests:
            print("\nFailed neighborhoods:")
            for result in failed_tests:
                error = result.get('error', result['status'])
                print(f"  - {result['neighborhood']}: {error}")
        
        # Verify database records
        print(f"\n{'='*50}")
        print("DATABASE VERIFICATION")
        print(f"{'='*50}")
        
        for neighborhood in test_neighborhoods:
            db_neighborhood = db.query(Neighborhood).filter(
                Neighborhood.yad2_hood_id == neighborhood["hoodId"]
            ).first()
            
            if db_neighborhood:
                print(f"✅ {db_neighborhood.hebrew_name}:")
                print(f"  - Madlan name: {db_neighborhood.madlan_name}")
                print(f"  - Has metrics: {bool(db_neighborhood.madlan_metrics)}")
                print(f"  - Has overview: {bool(db_neighborhood.madlan_overview)}")
                print(f"  - Last scraped: {db_neighborhood.madlan_last_scraped}")
            else:
                print(f"❌ {neighborhood['neigborhood_name']}: Not found in database")
        
        return len(successful_tests) > 0
        
    finally:
        db.close()


def test_with_mock_data():
    """Test with mock data when API key is not available."""
    print("Testing with mock Madlan data...")
    
    mock_scraped_data = {
        "סקירה כללית": "זהו טקסט סקירה כללית לדוגמה",
        "מחיר ממוצע למ״ר": "15,000 ₪",
        "מגמת מחירים": "עולה",
        "רמת ביקוש": "גבוהה",
        "רמת היצע": "נמוכה"
    }
    
    # Test parsing
    parsed_metrics = parse_madlan_metrics(mock_scraped_data)
    print(f"✅ Mock parsing successful:")
    print(f"  - Overview: {bool(parsed_metrics['overview'])}")
    print(f"  - Price per sqm: {parsed_metrics['avg_price_per_sqm']}")
    print(f"  - Price trend: {parsed_metrics['price_trend']}")
    print(f"  - Demand level: {parsed_metrics['demand_level']}")
    print(f"  - Supply level: {parsed_metrics['supply_level']}")
    
    print("\n✅ Mock test completed successfully!")
    print("To run full test, set the SCRAPEOWL_API_KEY environment variable.")
    return True


if __name__ == "__main__":
    print("Starting Madlan integration test...")
    success = test_madlan_integration()
    
    if success:
        print("\n🎉 Test completed successfully!")
    else:
        print("\n❌ Test failed!")
        sys.exit(1) 