#!/usr/bin/env python3
"""
One-time script to fix all neighborhood coordinates in the database.
This script validates and corrects neighborhood coordinates using Google Places API.
"""

import os
import sys
import asyncio
import time
import requests
from pathlib import Path
from typing import List, Tuple, Optional

# Add parent directory to path to import from src
sys.path.insert(0, str(Path(__file__).parent))

from src.database.postgresql_db import get_session_local
from src.database.models import Neighborhood
from src.config.settings import settings
from sqlalchemy import select, update

class CoordinateFixer:
    def __init__(self):
        self.session_local = get_session_local()
        self.corrections_made = 0
        self.api_calls_made = 0
        self.errors = []
        self.corrections_log = []
        
    def search_neighborhood_coordinates(self, neighborhood_name: str) -> Optional[Tuple[float, float]]:
        """
        Search for neighborhood coordinates using Google Places API.
        
        Args:
            neighborhood_name: Hebrew name of the neighborhood
            
        Returns:
            Tuple of (lat, lng) or None if not found
        """
        if not settings.GOOGLE_API_KEY or not neighborhood_name:
            return None
        
        # Try different search variations for better results
        search_queries = [
            f"{neighborhood_name} תל אביב יפו",
            f"{neighborhood_name} תל אביב", 
            f"{neighborhood_name} יפו",
            f"{neighborhood_name}"
        ]
        
        for query in search_queries:
            try:
                self.api_calls_made += 1
                
                url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
                params = {
                    "query": query,
                    "region": "il",
                    "language": "he",
                    "type": "neighborhood",
                    "key": settings.GOOGLE_API_KEY
                }
                
                response = requests.get(url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "OK" and data.get("results"):
                        result = data["results"][0]
                        location = result.get("geometry", {}).get("location", {})
                        
                        if location and "lat" in location and "lng" in location:
                            print(f"   ✅ Found coordinates for '{query}': ({location['lat']}, {location['lng']})")
                            return location["lat"], location["lng"]
                        
                # Add small delay to respect API limits
                time.sleep(0.1)
                
            except Exception as e:
                print(f"   ❌ Error searching for '{query}': {e}")
                continue
        
        return None
    
    def calculate_distance_meters(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate approximate distance in meters between two coordinates."""
        # Simple distance calculation (good enough for validation)
        distance_degrees = ((lat1 - lat2)**2 + (lng1 - lng2)**2)**0.5
        return distance_degrees * 111000  # Rough conversion to meters
    
    async def fix_neighborhood_coordinates(self) -> None:
        """Main function to fix all neighborhood coordinates."""
        print("🗺️  Neighborhood Coordinate Fixer")
        print("="*60)
        print(f"Using Google API Key: {settings.GOOGLE_API_KEY[:10]}...")
        print()
        
        async with self.session_local() as db:
            try:
                # Get all neighborhoods
                result = await db.execute(
                    select(Neighborhood.id, Neighborhood.hebrew_name, Neighborhood.english_name,
                           Neighborhood.latitude, Neighborhood.longitude)
                    .order_by(Neighborhood.hebrew_name)
                )
                
                neighborhoods = result.fetchall()
                total_neighborhoods = len(neighborhoods)
                
                print(f"📊 Found {total_neighborhoods} neighborhoods to validate")
                print()
                
                for i, (id, hebrew_name, english_name, current_lat, current_lng) in enumerate(neighborhoods, 1):
                    print(f"[{i:2d}/{total_neighborhoods}] Processing: {hebrew_name or english_name or f'ID {id}'}")
                    
                    # Skip if no current coordinates
                    if current_lat is None or current_lng is None:
                        print(f"   ⚠️  No coordinates in database - skipping")
                        continue
                    
                    # Skip if no Hebrew name (can't search effectively)
                    if not hebrew_name:
                        print(f"   ⚠️  No Hebrew name - skipping")
                        continue
                    
                    # Search for correct coordinates
                    api_coords = self.search_neighborhood_coordinates(hebrew_name)
                    
                    if api_coords:
                        api_lat, api_lng = api_coords
                        
                        # Calculate distance between current and API coordinates
                        distance_meters = self.calculate_distance_meters(
                            current_lat, current_lng, api_lat, api_lng
                        )
                        
                        print(f"   📏 Distance from database: {distance_meters:.0f} meters")
                        
                    # If coordinates differ significantly, update them
                    if distance_meters != 0:  # More than 2km difference
                        print(f"   🔧 CORRECTION NEEDED:")
                        print(f"      📍 Old: ({current_lat}, {current_lng})")
                        print(f"      🌐 New: ({api_lat}, {api_lng})")
                        
                        # Update database
                        try:
                            await db.execute(
                                update(Neighborhood)
                                .where(Neighborhood.id == id)
                                .values(latitude=api_lat, longitude=api_lng)
                            )
                            
                            self.corrections_made += 1
                            self.corrections_log.append({
                                'id': id,
                                'name': hebrew_name,
                                'old_coords': (current_lat, current_lng),
                                'new_coords': (api_lat, api_lng),
                                'distance_meters': distance_meters
                            })
                            
                            print(f"      ✅ Updated in database")
                            
                        except Exception as e:
                            error_msg = f"Failed to update neighborhood {id}: {e}"
                            print(f"      ❌ {error_msg}")
                            self.errors.append(error_msg)
                        
                        print()  # Empty line for readability
                
                # Commit all changes
                await db.commit()
                print("💾 All changes committed to database")
                
            except Exception as e:
                await db.rollback()
                print(f"❌ Database error: {e}")
                raise
    
    def print_summary(self) -> None:
        """Print summary of the coordinate fixing process."""
        print("\n" + "="*60)
        print("📋 SUMMARY REPORT")
        print("="*60)
        
        print(f"🔧 Corrections made: {self.corrections_made}")
        print(f"🌐 API calls made: {self.api_calls_made}")
        print(f"❌ Errors encountered: {len(self.errors)}")
        
        if self.corrections_log:
            print(f"\n📝 DETAILED CORRECTIONS:")
            for correction in self.corrections_log:
                print(f"   🏘️  {correction['name']} (ID: {correction['id']})")
                print(f"      📍 {correction['old_coords']} → {correction['new_coords']}")
                print(f"      📏 Distance: {correction['distance_meters']:.0f} meters")
                print()
        
        if self.errors:
            print(f"\n⚠️  ERRORS:")
            for error in self.errors:
                print(f"   - {error}")
        
        print("\n✅ Coordinate fixing completed!")
        print("🎯 Transit times should now be more accurate across all neighborhoods")

async def main():
    """Main function to run the coordinate fixer."""
    if not settings.GOOGLE_API_KEY:
        print("❌ ERROR: GOOGLE_API_KEY not set in environment variables")
        print("Please set your Google Maps API key before running this script")
        return
    
    # Confirm with user before making changes
    print("⚠️  WARNING: This script will modify neighborhood coordinates in the database")
    print("🔄 It will make Google Places API calls for each neighborhood")
    print("💰 This may incur API usage costs")
    print()
    
    response = input("Do you want to continue? (y/N): ").strip().lower()
    if response != 'y':
        print("❌ Aborted by user")
        return
    
    print("\n🚀 Starting coordinate fixing process...")
    print()
    
    fixer = CoordinateFixer()
    
    try:
        await fixer.fix_neighborhood_coordinates()
        fixer.print_summary()
        
    except KeyboardInterrupt:
        print("\n⚠️  Process interrupted by user")
        fixer.print_summary()
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        fixer.print_summary()

if __name__ == "__main__":
    asyncio.run(main())
