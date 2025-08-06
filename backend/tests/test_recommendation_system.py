#!/usr/bin/env python3
"""
Test script for the neighborhood recommendation system.
"""

import asyncio
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.database.postgresql_db import async_session_local
from src.services.recommendation_service import get_user_neighborhood_recommendations
from src.services.questionnaire_service import QuestionnaireService

async def test_recommendation_system():
    """Test the complete recommendation system."""
    print("=== Testing Neighborhood Recommendation System ===")
    
    async with async_session_local() as db:
        # Test user ID (you'll need to replace with actual user ID)
        test_user_id = "test_user_123"
        
        # First, let's create some mock questionnaire responses
        questionnaire_service = QuestionnaireService()
        
        # Mock responses for a family with children
        mock_responses = {
            'housing_purpose': ['With family (and children)'],
            'religious_community_importance': 'Not important',
            'safety_priority': 'Very important',
            'children_ages': ['School-age children (7-12 years)'],
            'proximity_to_shopping_centers': 'Very important',
            'proximity_to_green_spaces': 'Somewhat important',
            'family_activities_nearby': 'Very important',
            'nightlife_proximity': 'As far as possible',
            'community_involvement_preference': 'Very important - I want an active, connected community',
            'neighborhood_quality_importance': 'Very important',
            'quiet_hours_importance': 'Very important - I need a quiet area',
            'pet_ownership': 'No'
        }
        
        print(f"Mock questionnaire responses: {len(mock_responses)} questions")
        
        # Note: In real usage, responses would be stored via the questionnaire API
        # For testing, we'll simulate the recommendation process
        
        try:
            # Test the recommendation service directly
            from src.services.recommendation_service import NeighborhoodRecommendationService
            
            service = NeighborhoodRecommendationService()
            
            # Test preference vector creation
            preference_vector = service._create_preference_vector(mock_responses)
            print(f"\nGenerated preference vector: {preference_vector}")
            print("Feature preferences:")
            for i, feature in enumerate(service.feature_names):
                print(f"  {feature}: {preference_vector[i]:.2f}")
            
            # Test neighborhood features loading
            neighborhood_features = await service._get_neighborhood_features(db)
            print(f"\nLoaded {len(neighborhood_features)} neighborhoods with features")
            
            if neighborhood_features:
                # Test scoring
                scored_neighborhoods = service._score_neighborhoods(neighborhood_features, preference_vector)
                print(f"Scored {len(scored_neighborhoods)} neighborhoods")
                
                # Show top 5 scores
                top_5 = sorted(scored_neighborhoods, key=lambda x: x['score'], reverse=True)[:5]
                print("\nTop 5 neighborhood scores:")
                for i, neighborhood in enumerate(top_5, 1):
                    print(f"{i}. {neighborhood['hebrew_name']}: {neighborhood['score']:.3f}")
                
                # Test match details for top neighborhood
                if top_5:
                    top_match = top_5[0]
                    print(f"\nMatch details for top recommendation ({top_match['hebrew_name']}):")
                    for feature, details in top_match['match_details'].items():
                        print(f"  {feature}: {details['match_quality']} (neighborhood: {details['neighborhood_score']:.2f}, user: {details['user_importance']:.2f})")
            
            print("\n✅ Recommendation system test completed successfully!")
            
        except Exception as e:
            print(f"❌ Error testing recommendation system: {e}")
            import traceback
            traceback.print_exc()

async def test_api_simulation():
    """Simulate API call flow."""
    print("\n=== Simulating API Call Flow ===")
    
    # This would normally be called via the API endpoint
    # For testing, we simulate the process
    
    async with async_session_local() as db:
        try:
            # Simulate getting recommendations (would need real user with questionnaire data)
            print("API endpoint would call: get_user_neighborhood_recommendations()")
            print("Expected response format:")
            print("""
            {
                "recommendations": [
                    {
                        "neighborhood_id": 1520,
                        "hebrew_name": "לב העיר",
                        "english_name": "City Center",
                        "score": 0.85,
                        "match_details": {...},
                        "sample_listings": [...],
                        "total_available_listings": 45,
                        "neighborhood_info": {...}
                    }
                ],
                "total_returned": 3,
                "filters_applied": {},
                "message": "Recommendations generated successfully"
            }
            """)
            
            print("✅ API simulation completed")
            
        except Exception as e:
            print(f"❌ Error in API simulation: {e}")

async def main():
    """Run all tests."""
    await test_recommendation_system()
    await test_api_simulation()

if __name__ == "__main__":
    asyncio.run(main())
