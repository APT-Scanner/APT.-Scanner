#!/usr/bin/env python3
"""
Test script for neighborhood features functionality.
"""

import asyncio
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select
from src.database.postgresql_db import async_session_local
from scripts.create_neighborhood_features import NeighborhoodFeatures
import numpy as np

async def test_neighborhood_features():
    """Test the neighborhood features table."""
    print("Testing neighborhood features...")
    
    async with async_session_local() as session:
        # Get all neighborhoods with features
        result = await session.execute(
            select(NeighborhoodFeatures).limit(10)
        )
        neighborhoods = result.scalars().all()
        
        if not neighborhoods:
            print("No neighborhoods found in the features table")
            return
        
        print(f"Found {len(neighborhoods)} neighborhoods (showing first 10):")
        print("-" * 80)
        
        for neighborhood in neighborhoods:
            print(f"Name: {neighborhood.hebrew_name or 'Unknown'}")
            print(f"Yad2 ID: {neighborhood.yad2_hood_id}")
            print(f"Cultural Level: {neighborhood.cultural_level:.3f}" if neighborhood.cultural_level else "Cultural Level: None")
            print(f"Safety Level: {neighborhood.safety_level:.3f}" if neighborhood.safety_level else "Safety Level: None")
            print(f"Shopping Level: {neighborhood.shopping_level:.3f}" if neighborhood.shopping_level else "Shopping Level: None")
            print(f"Parks Level: {neighborhood.parks_level:.3f}" if neighborhood.parks_level else "Parks Level: None")
            print(f"Peaceful Level: {neighborhood.peaceful_level:.3f}" if neighborhood.peaceful_level else "Peaceful Level: None")
            
            if neighborhood.feature_vector:
                print(f"Feature Vector Length: {len(neighborhood.feature_vector)}")
                print(f"Feature Vector: {[f'{x:.3f}' for x in neighborhood.feature_vector[:5]]}")
            
            print("-" * 40)

async def test_similarity_calculation():
    """Test similarity calculation between neighborhoods."""
    print("\nTesting neighborhood similarity calculation...")
    
    async with async_session_local() as session:
        # Get neighborhoods for comparison
        result = await session.execute(
            select(NeighborhoodFeatures).limit(3)
        )
        neighborhoods = result.scalars().all()
        
        if len(neighborhoods) < 2:
            print("Need at least 2 neighborhoods for similarity test")
            return
        
        hood1, hood2 = neighborhoods[0], neighborhoods[1]
        
        if not all([hood1.feature_vector, hood2.feature_vector]):
            print("Feature vectors missing for comparison")
            return
        
        # Calculate cosine similarity
        def cosine_similarity(vec1, vec2):
            vec1, vec2 = np.array(vec1), np.array(vec2)
            return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        
        similarity = cosine_similarity(hood1.feature_vector, hood2.feature_vector)
        
        print(f"Similarity between:")
        print(f"  {hood1.hebrew_name or 'Unknown'} (ID: {hood1.yad2_hood_id})")
        print(f"  {hood2.hebrew_name or 'Unknown'} (ID: {hood2.yad2_hood_id})")
        print(f"  Cosine similarity: {similarity:.3f}")
        
        if len(neighborhoods) >= 3:
            hood3 = neighborhoods[2]
            if hood3.feature_vector:
                sim_1_3 = cosine_similarity(hood1.feature_vector, hood3.feature_vector)
                sim_2_3 = cosine_similarity(hood2.feature_vector, hood3.feature_vector)
                print(f"  {hood1.hebrew_name or 'Unknown'} vs {hood3.hebrew_name or 'Unknown'}: {sim_1_3:.3f}")
                print(f"  {hood2.hebrew_name or 'Unknown'} vs {hood3.hebrew_name or 'Unknown'}: {sim_2_3:.3f}")

async def test_feature_distribution():
    """Test the distribution of feature values."""
    print("\nTesting feature value distributions...")
    
    async with async_session_local() as session:
        result = await session.execute(select(NeighborhoodFeatures))
        neighborhoods = result.scalars().all()
        
        if not neighborhoods:
            print("No neighborhoods found")
            return
        
        # Collect all feature values
        features = {
            'cultural_level': [n.cultural_level for n in neighborhoods if n.cultural_level is not None],
            'safety_level': [n.safety_level for n in neighborhoods if n.safety_level is not None],
            'shopping_level': [n.shopping_level for n in neighborhoods if n.shopping_level is not None],
            'parks_level': [n.parks_level for n in neighborhoods if n.parks_level is not None],
            'peaceful_level': [n.peaceful_level for n in neighborhoods if n.peaceful_level is not None],
            'maintenance_level': [n.maintenance_level for n in neighborhoods if n.maintenance_level is not None],
            'mobility_level': [n.mobility_level for n in neighborhoods if n.mobility_level is not None],
            'communality_level': [n.communality_level for n in neighborhoods if n.communality_level is not None],
            'religiosity_level': [n.religiosity_level for n in neighborhoods if n.religiosity_level is not None],
            'kindergardens_level': [n.kindergardens_level for n in neighborhoods if n.kindergardens_level is not None]
        }
        
        print("Feature value distributions (from hood_ratings.json, 0-1 scale):")
        for feature_name, values in features.items():
            if values:
                min_val = min(values)
                max_val = max(values)
                mean_val = sum(values) / len(values)
                count = len(values)
                print(f"{feature_name}: min={min_val:.3f}, max={max_val:.3f}, mean={mean_val:.3f}, count={count}")

async def test_feature_completeness():
    """Test how complete the feature data is."""
    print("\nTesting feature data completeness...")
    
    async with async_session_local() as session:
        result = await session.execute(select(NeighborhoodFeatures))
        neighborhoods = result.scalars().all()
        
        if not neighborhoods:
            print("No neighborhoods found")
            return
        
        total_neighborhoods = len(neighborhoods)
        feature_names = [
            'cultural_level', 'safety_level', 'shopping_level', 'parks_level',
            'peaceful_level', 'maintenance_level', 'mobility_level', 
            'communality_level', 'religiosity_level', 'kindergardens_level'
        ]
        
        print(f"Data completeness for {total_neighborhoods} neighborhoods:")
        for feature_name in feature_names:
            non_null_count = sum(1 for n in neighborhoods if getattr(n, feature_name) is not None)
            percentage = (non_null_count / total_neighborhoods) * 100
            print(f"{feature_name}: {non_null_count}/{total_neighborhoods} ({percentage:.1f}%)")

async def main():
    """Run all tests."""
    await test_neighborhood_features()
    await test_similarity_calculation()
    await test_feature_distribution()
    await test_feature_completeness()
    print("\nTesting completed!")

if __name__ == "__main__":
    asyncio.run(main()) 