#!/usr/bin/env python3
"""
Script to create and populate a neighborhood feature vectors table.
This table will store normalized feature vectors for all Tel Aviv neighborhoods
using only data from hood_ratings.json.
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional
from sqlalchemy import Column, Integer, String, Float, ARRAY, TIMESTAMP, text
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession

# Add the parent directory to the path to import from src
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.database.postgresql_db import Base, engine, async_session_local

class NeighborhoodFeatures(Base):
    """Model for neighborhood feature vectors based on hood ratings."""
    __tablename__ = "neighborhood_features"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    yad2_hood_id = Column(Integer, unique=True, nullable=False, index=True)
    hebrew_name = Column(String(150), nullable=True)
    
    # Quality of life ratings from hood_ratings.json (normalized 0-1)
    cultural_level = Column(Float, nullable=True)          # High_culturallevel
    religiosity_level = Column(Float, nullable=True)       # High_religiositylevel  
    communality_level = Column(Float, nullable=True)       # High_communalitylevel
    kindergardens_level = Column(Float, nullable=True)     # High_kindergardenslevel
    maintenance_level = Column(Float, nullable=True)       # High_maintnancelevel
    mobility_level = Column(Float, nullable=True)          # High_mobilitylevel
    parks_level = Column(Float, nullable=True)             # High_parkslevel
    peaceful_level = Column(Float, nullable=True)          # High_peacfullevel
    shopping_level = Column(Float, nullable=True)          # High_shoppinglevel
    safety_level = Column(Float, nullable=True)            # High_saftylevel
    
    # Combined feature vector as array for ML algorithms
    feature_vector = Column(ARRAY(Float), nullable=True)
    
    # Metadata
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

class NeighborhoodFeaturesCreator:
    """Creates and populates the neighborhood features table using only hood_ratings.json."""
    
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / "data" / "sources"
        self.hood_data = {}
        self.hood_name_mapping = {}
        
    async def create_table(self):
        """Create the neighborhood features table."""
        print("Creating neighborhood_features table...")
        async with engine.begin() as conn:
            await conn.run_sync(NeighborhoodFeatures.metadata.create_all)
        print("Table created successfully!")
    
    def load_hood_name_mapping(self):
        """Load neighborhood name mapping from yad2_hood_mapping.json."""
        mapping_path = self.data_dir / "yad2_hood_mapping.json"
        if not mapping_path.exists():
            print(f"Warning: {mapping_path} not found, will use hood IDs only")
            return
        
        with open(mapping_path, 'r', encoding='utf-8') as f:
            mapping_data = json.load(f)
        
        for entry in mapping_data:
            hood_id = str(entry.get('hoodId', ''))
            hood_name = entry.get('neigborhood_name', '')
            if hood_id and hood_name:
                self.hood_name_mapping[hood_id] = hood_name
        
        print(f"Loaded name mapping for {len(self.hood_name_mapping)} neighborhoods")
    
    def load_hood_ratings(self):
        """Load quality of life ratings from hood_ratings.json."""
        ratings_path = self.data_dir / "hood_ratings.json"
        if not ratings_path.exists():
            raise FileNotFoundError(f"Required file not found: {ratings_path}")
        
        with open(ratings_path, 'r', encoding='utf-8') as f:
            ratings_data = json.load(f)
        
        print(f"Loaded ratings for {len(ratings_data)} neighborhoods")
        
        # Mapping of rating titles to feature names
        rating_mapping = {
            'High_culturallevel': 'cultural_level',
            'High_religiositylevel': 'religiosity_level',
            'High_communalitylevel': 'communality_level',
            'High_kindergardenslevel': 'kindergardens_level',
            'High_maintnancelevel': 'maintenance_level',
            'High_mobilitylevel': 'mobility_level',
            'High_parkslevel': 'parks_level',
            'High_peacfullevel': 'peaceful_level',
            'High_shoppinglevel': 'shopping_level',
            'High_saftylevel': 'safety_level'
        }
        
        # Process each neighborhood's ratings
        for hood_id, ratings in ratings_data.items():
            hood_features = {
                'yad2_hood_id': int(hood_id),
                'hebrew_name': self.hood_name_mapping.get(hood_id, ''),
            }
            
            # Initialize all features to None
            for feature_name in rating_mapping.values():
                hood_features[feature_name] = None
            
            # Process ratings for this neighborhood
            for rating in ratings:
                # Skip malformed entries (some entries contain error strings)
                if not isinstance(rating, dict):
                    continue
                    
                title = rating.get('title', '')
                score = rating.get('score', 0.0)
                
                if title in rating_mapping:
                    feature_name = rating_mapping[title]
                    hood_features[feature_name] = float(score)
            
            self.hood_data[hood_id] = hood_features
        
        print(f"Processed ratings for {len(self.hood_data)} neighborhoods")
    
    def create_feature_vectors(self):
        """Create feature vectors from the ratings."""
        print("Creating feature vectors...")
        
        # Feature order for the vector
        feature_order = [
            'cultural_level',
            'religiosity_level', 
            'communality_level',
            'kindergardens_level',
            'maintenance_level',
            'mobility_level',
            'parks_level',
            'peaceful_level',
            'shopping_level',
            'safety_level'
        ]
        
        for hood_id, data in self.hood_data.items():
            # Create feature vector in consistent order
            feature_vector = []
            for feature_name in feature_order:
                value = data.get(feature_name, 0.0)
                # Handle None values by setting to 0.0
                feature_vector.append(value if value is not None else 0.0)
            
            data['feature_vector'] = feature_vector
        
        print("Feature vectors created successfully!")
    
    async def populate_table(self):
        """Populate the neighborhood features table."""
        print("Populating neighborhood_features table...")
        
        async with async_session_local() as session:
            # Clear existing data
            await session.execute(text("DELETE FROM neighborhood_features"))
            
            inserted_count = 0
            for hood_id, data in self.hood_data.items():
                neighborhood_features = NeighborhoodFeatures(
                    yad2_hood_id=data['yad2_hood_id'],
                    hebrew_name=data.get('hebrew_name'),
                    cultural_level=data.get('cultural_level'),
                    religiosity_level=data.get('religiosity_level'),
                    communality_level=data.get('communality_level'),
                    kindergardens_level=data.get('kindergardens_level'),
                    maintenance_level=data.get('maintenance_level'),
                    mobility_level=data.get('mobility_level'),
                    parks_level=data.get('parks_level'),
                    peaceful_level=data.get('peaceful_level'),
                    shopping_level=data.get('shopping_level'),
                    safety_level=data.get('safety_level'),
                    feature_vector=data.get('feature_vector')
                )
                
                session.add(neighborhood_features)
                inserted_count += 1
            
            await session.commit()
            print(f"Successfully inserted {inserted_count} neighborhood feature records")
    
    async def run(self):
        """Run the complete process."""
        print("Starting neighborhood features creation process...")
        print("Using only data from hood_ratings.json")
        
        # Load data sources
        self.load_hood_name_mapping()
        self.load_hood_ratings()
        
        # Create feature vectors
        self.create_feature_vectors()
        
        # Create table and populate
        await self.create_table()
        await self.populate_table()
        
        print("Neighborhood features creation completed successfully!")
        print(f"Created feature vectors with {len(self.hood_data)} neighborhoods")
        print("Each feature vector contains 10 quality of life ratings:")
        print("  1. Cultural Level")
        print("  2. Religiosity Level") 
        print("  3. Communality Level")
        print("  4. Kindergardens Level")
        print("  5. Maintenance Level")
        print("  6. Mobility Level")
        print("  7. Parks Level")
        print("  8. Peaceful Level")
        print("  9. Shopping Level")
        print("  10. Safety Level")

async def main():
    """Main function."""
    creator = NeighborhoodFeaturesCreator()
    await creator.run()

if __name__ == "__main__":
    asyncio.run(main()) 