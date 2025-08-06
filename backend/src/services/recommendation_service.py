"""
Neighborhood Recommendation Service
Provides neighborhood recommendations based on user questionnaire responses.
"""

import numpy as np
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import logging

from src.database.models import Listing, Neighborhood
from src.services.questionnaire_service import QuestionnaireService
from src.database.models import NeighborhoodFeatures

logger = logging.getLogger(__name__)

class NeighborhoodRecommendationService:
    """Service for generating neighborhood recommendations based on user preferences."""
    
    def __init__(self):
        self.questionnaire_service = QuestionnaireService()
        
        # Feature names in order (matching create_neighborhood_features.py)
        self.feature_names = [
            'cultural_level',           # 0
            'religiosity_level',        # 1  
            'communality_level',        # 2
            'kindergardens_level',      # 3
            'maintenance_level',        # 4
            'mobility_level',           # 5
            'parks_level',              # 6
            'peaceful_level',           # 7
            'shopping_level',           # 8
            'safety_level'              # 9
        ]
        
        # Importance scale mapping
        self.importance_scale = {
            'Very important': 0.9,
            'Somewhat important': 0.6,
            'Not important': 0.1,
            'Yes, I want to be in the center of the action': 0.9,
            'Close but not too close': 0.6,
            'As far as possible': 0.1,
            'No preference': 0.5,
            'Walking distance': 0.9,
            'Short drive or public transport ride': 0.6,
            'Very important - I want well-maintained buildings': 0.9,
            'Not important - I don\'t mind older/less maintained areas': 0.1,
            'Very important - I need a quiet area': 0.9,
            'Not important - I don\'t mind noise': 0.1,
            'Very important - I want an active, connected community': 0.9,
            'Not important - I prefer privacy': 0.2,
            'No': 0.1,
            'Yes': 0.9
        }
    
    async def get_neighborhood_recommendations(
        self, 
        db: AsyncSession, 
        user_id: str, 
        top_k: int = 3
    ) -> List[Dict]:
        """
        Get top neighborhood recommendations for a user based on their questionnaire responses.
        
        Args:
            db: Database session
            user_id: User's Firebase UID
            top_k: Number of recommendations to return
            
        Returns:
            List of recommended neighborhoods with scores and sample listings
        """
        try:
            # Get user's questionnaire responses
            user_responses = await self.questionnaire_service.get_user_responses(db, user_id)
            if not user_responses:
                logger.warning(f"No questionnaire responses found for user {user_id}")
                return []
            
            # Convert responses to preference vector
            preference_vector = self._create_preference_vector(user_responses)
            logger.info(f"Generated preference vector for user {user_id}: {preference_vector}")
            
            # Get neighborhood features from database
            neighborhood_features = await self._get_neighborhood_features(db)
            if not neighborhood_features:
                logger.error("No neighborhood features found in database")
                return []
            
            # Score neighborhoods
            scored_neighborhoods = self._score_neighborhoods(neighborhood_features, preference_vector)
            
            # Get top recommendations
            top_neighborhoods = sorted(scored_neighborhoods, key=lambda x: x['score'], reverse=True)[:top_k]
            
            # Enrich with listings and additional info
            recommendations = await self._enrich_recommendations(db, top_neighborhoods)
            
            logger.info(f"Generated {len(recommendations)} recommendations for user {user_id}")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations for user {user_id}: {e}", exc_info=True)
            return []
    
    def _create_preference_vector(self, responses: Dict[str, any]) -> np.ndarray:
        """Convert questionnaire responses to preference vector."""
        preferences = {feature: 0.5 for feature in self.feature_names}  # Default neutral
        
        # Apply mapping logic
        self._map_basic_questions(responses, preferences)
        self._map_dynamic_questions(responses, preferences)
        self._apply_persona_logic(responses, preferences)
        
        # Convert to array
        preference_vector = np.array([preferences[feature] for feature in self.feature_names])
        return preference_vector
    
    def _map_basic_questions(self, responses: Dict, preferences: Dict):
        """Map basic information questions."""
        if 'religious_community_importance' in responses:
            importance = self.importance_scale.get(responses['religious_community_importance'], 0.5)
            preferences['religiosity_level'] = importance
        
        if 'safety_priority' in responses:
            importance = self.importance_scale.get(responses['safety_priority'], 0.5)
            preferences['safety_level'] = importance
        
        if 'commute_pref' in responses:
            commute_type = responses['commute_pref']
            if commute_type in ['Public transport', 'Walking']:
                preferences['mobility_level'] = 0.8
            elif commute_type in ['Bicycle / scooter']:
                preferences['mobility_level'] = 0.7
            elif commute_type == 'Private car':
                preferences['mobility_level'] = 0.4
    
    def _map_dynamic_questions(self, responses: Dict, preferences: Dict):
        """Map dynamic questionnaire questions."""
        # Children ages -> affects multiple features
        if 'children_ages' in responses:
            children_ages = responses['children_ages']
            if isinstance(children_ages, list):
                children_ages = children_ages[0] if children_ages else 'No children'
            
            if 'No children' not in children_ages:
                preferences['safety_level'] = max(preferences['safety_level'], 0.8)
                preferences['kindergardens_level'] = max(preferences['kindergardens_level'], 0.7)
                preferences['peaceful_level'] = max(preferences['peaceful_level'], 0.7)
        
        # Learning spaces -> cultural_level
        if 'learning_space_nearby' in responses:
            importance = self.importance_scale.get(responses['learning_space_nearby'], 0.5)
            preferences['cultural_level'] = max(preferences['cultural_level'], importance)
        
        # Shopping centers -> shopping_level
        if 'proximity_to_shopping_centers' in responses:
            importance = self.importance_scale.get(responses['proximity_to_shopping_centers'], 0.5)
            preferences['shopping_level'] = importance
        
        # Green spaces -> parks_level
        if 'proximity_to_green_spaces' in responses:
            importance = self.importance_scale.get(responses['proximity_to_green_spaces'], 0.5)
            preferences['parks_level'] = importance
        
        # Family activities -> communality_level
        if 'family_activities_nearby' in responses:
            importance = self.importance_scale.get(responses['family_activities_nearby'], 0.5)
            preferences['communality_level'] = max(preferences['communality_level'], importance)
        
        # Nightlife -> cultural_level and peaceful_level (inverse)
        if 'nightlife_proximity' in responses:
            response = responses['nightlife_proximity']
            if response == 'Yes, I want to be in the center of the action':
                preferences['cultural_level'] = max(preferences['cultural_level'], 0.9)
                preferences['peaceful_level'] = min(preferences['peaceful_level'], 0.3)
            elif response == 'Close but not too close':
                preferences['cultural_level'] = max(preferences['cultural_level'], 0.6)
                preferences['peaceful_level'] = 0.6
            elif response == 'As far as possible':
                preferences['cultural_level'] = min(preferences['cultural_level'], 0.2)
                preferences['peaceful_level'] = max(preferences['peaceful_level'], 0.9)
        
        # Community involvement -> communality_level
        if 'community_involvement_preference' in responses:
            importance = self.importance_scale.get(responses['community_involvement_preference'], 0.5)
            preferences['communality_level'] = max(preferences['communality_level'], importance)
        
        # Cultural activities -> cultural_level
        if 'cultural_activities_importance' in responses:
            importance = self.importance_scale.get(responses['cultural_activities_importance'], 0.5)
            preferences['cultural_level'] = max(preferences['cultural_level'], importance)
        
        # Neighborhood quality -> maintenance_level
        if 'neighborhood_quality_importance' in responses:
            importance = self.importance_scale.get(responses['neighborhood_quality_importance'], 0.5)
            preferences['maintenance_level'] = importance
        
        # Building condition -> maintenance_level
        if 'building_condition_preference' in responses:
            importance = self.importance_scale.get(responses['building_condition_preference'], 0.5)
            preferences['maintenance_level'] = max(preferences['maintenance_level'], importance)
        
        # Quiet hours -> peaceful_level
        if 'quiet_hours_importance' in responses:
            importance = self.importance_scale.get(responses['quiet_hours_importance'], 0.5)
            preferences['peaceful_level'] = max(preferences['peaceful_level'], importance)
        
        # Pet ownership -> parks_level
        if 'pet_ownership' in responses:
            if responses['pet_ownership'] == 'Yes':
                preferences['parks_level'] = max(preferences['parks_level'], 0.7)
    
    def _apply_persona_logic(self, responses: Dict, preferences: Dict):
        """Apply logic based on housing purpose (user persona)."""
        if 'housing_purpose' not in responses:
            return
        
        housing_purpose = responses['housing_purpose']
        if isinstance(housing_purpose, list):
            housing_purpose = housing_purpose[0] if housing_purpose else ''
        
        # Adjust preferences based on persona
        if 'Just me' in housing_purpose:
            preferences['cultural_level'] = max(preferences['cultural_level'], 0.6)
            preferences['shopping_level'] = max(preferences['shopping_level'], 0.6)
            preferences['mobility_level'] = max(preferences['mobility_level'], 0.6)
            
        elif 'With a partner' in housing_purpose:
            preferences['cultural_level'] = max(preferences['cultural_level'], 0.6)
            preferences['peaceful_level'] = max(preferences['peaceful_level'], 0.6)
            preferences['shopping_level'] = max(preferences['shopping_level'], 0.6)
            
        elif 'With family (and children)' in housing_purpose:
            preferences['safety_level'] = max(preferences['safety_level'], 0.8)
            preferences['kindergardens_level'] = max(preferences['kindergardens_level'], 0.7)
            preferences['parks_level'] = max(preferences['parks_level'], 0.7)
            preferences['peaceful_level'] = max(preferences['peaceful_level'], 0.7)
            preferences['communality_level'] = max(preferences['communality_level'], 0.6)
            
        elif 'With roommates' in housing_purpose:
            preferences['cultural_level'] = max(preferences['cultural_level'], 0.7)
            preferences['shopping_level'] = max(preferences['shopping_level'], 0.6)
            preferences['mobility_level'] = max(preferences['mobility_level'], 0.7)
    
    async def _get_neighborhood_features(self, db: AsyncSession) -> List[Dict]:
        """Get neighborhood features from database."""
        try:
            result = await db.execute(select(NeighborhoodFeatures))
            features = result.scalars().all()
            
            neighborhood_data = []
            for feature in features:
                if feature.feature_vector:
                    neighborhood_data.append({
                        'yad2_hood_id': feature.yad2_hood_id,
                        'hebrew_name': feature.hebrew_name,
                        'feature_vector': np.array(feature.feature_vector),
                        'individual_scores': {
                            'cultural_level': feature.cultural_level,
                            'religiosity_level': feature.religiosity_level,
                            'communality_level': feature.communality_level,
                            'kindergardens_level': feature.kindergardens_level,
                            'maintenance_level': feature.maintenance_level,
                            'mobility_level': feature.mobility_level,
                            'parks_level': feature.parks_level,
                            'peaceful_level': feature.peaceful_level,
                            'shopping_level': feature.shopping_level,
                            'safety_level': feature.safety_level
                        }
                    })
            
            return neighborhood_data
            
        except Exception as e:
            logger.error(f"Error fetching neighborhood features: {e}", exc_info=True)
            return []
    
    def _score_neighborhoods(self, neighborhoods: List[Dict], user_preferences: np.ndarray) -> List[Dict]:
        """Score neighborhoods based on user preferences."""
        scored_neighborhoods = []
        
        # Normalize user preferences to sum to 1
        normalized_preferences = user_preferences / np.sum(user_preferences)
        
        for neighborhood in neighborhoods:
            # Calculate weighted score using dot product
            score = np.dot(neighborhood['feature_vector'], normalized_preferences)
            
            scored_neighborhoods.append({
                'yad2_hood_id': neighborhood['yad2_hood_id'],
                'hebrew_name': neighborhood['hebrew_name'],
                'score': float(score),
                'individual_scores': neighborhood['individual_scores'],
                'user_preferences': user_preferences.tolist(),
                'match_details': self._get_match_details(neighborhood['individual_scores'], user_preferences)
            })
        
        return scored_neighborhoods
    
    def _get_match_details(self, neighborhood_scores: Dict, user_preferences: np.ndarray) -> Dict:
        """Get detailed match information for explanation."""
        match_details = {}
        
        for i, feature_name in enumerate(self.feature_names):
            neighborhood_score = neighborhood_scores.get(feature_name, 0.5)
            user_preference = user_preferences[i]
            
            # Calculate how well this feature matches user preference
            if user_preference > 0.7:  # User considers this very important
                if neighborhood_score and neighborhood_score > 0.6:
                    match_quality = "excellent"
                elif neighborhood_score and neighborhood_score > 0.4:
                    match_quality = "good"
                else:
                    match_quality = "poor"
            else:
                match_quality = "neutral"
            
            match_details[feature_name] = {
                'neighborhood_score': neighborhood_score,
                'user_importance': float(user_preference),
                'match_quality': match_quality
            }
        
        return match_details
    
    async def _enrich_recommendations(
        self, 
        db: AsyncSession, 
        neighborhoods: List[Dict], 
    ) -> List[Dict]:
        """Enrich recommendations with listings and additional info."""
        enriched_recommendations = []
        
        for neighborhood in neighborhoods:
            try:
                # Get neighborhood info
                neighborhood_info = await self._get_neighborhood_info(db, neighborhood['yad2_hood_id'])
                
                # Count total available listings
                total_listings = await self._count_available_listings(
                    db, neighborhood['yad2_hood_id']
                )
                
                enriched_recommendations.append({
                    'neighborhood_id': neighborhood['yad2_hood_id'],
                    'hebrew_name': neighborhood['hebrew_name'],
                    'english_name': neighborhood_info.get('english_name') if neighborhood_info else None,
                    'score': neighborhood['score'],
                    'match_details': neighborhood['match_details'],
                    'individual_scores': neighborhood['individual_scores'],
                    'total_available_listings': total_listings,
                    'neighborhood_info': neighborhood_info
                })
                
            except Exception as e:
                logger.error(f"Error enriching neighborhood {neighborhood['yad2_hood_id']}: {e}")
                continue
        
        return enriched_recommendations
    
    async def _get_neighborhood_info(self, db: AsyncSession, yad2_hood_id: int) -> Optional[Dict]:
        """Get additional neighborhood information."""
        try:
            result = await db.execute(
                select(Neighborhood).where(Neighborhood.yad2_hood_id == yad2_hood_id)
            )
            neighborhood = result.scalar_one_or_none()
            
            if neighborhood:
                return {
                    'english_name': neighborhood.english_name,
                    'avg_rent_price': float(neighborhood.avg_rent_price) if neighborhood.avg_rent_price else None,
                    'avg_purchase_price': float(neighborhood.avg_purchase_price) if neighborhood.avg_purchase_price else None,
                    'general_overview': neighborhood.general_overview,
                    'latitude': neighborhood.latitude,
                    'longitude': neighborhood.longitude
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching neighborhood info for {yad2_hood_id}: {e}")
            return None
    
    async def _get_sample_listings(
        self, 
        db: AsyncSession, 
        yad2_hood_id: int, 
        limit: int = 3
    ) -> List[Dict]:
        """Get sample listings for a neighborhood."""
        try:
            query = select(Listing).where(
                and_(
                    Listing.neighborhood_id == yad2_hood_id,
                    Listing.is_active == True
                )
            )
            
            query = query.limit(limit)
            result = await db.execute(query)
            listings = result.scalars().all()
            
            sample_listings = []
            for listing in listings:
                sample_listings.append({
                    'order_id': listing.order_id,
                    'token': listing.token,
                    'price': float(listing.price) if listing.price else None,
                    'rooms_count': float(listing.rooms_count) if listing.rooms_count else None,
                    'square_meter': listing.square_meter,
                    'cover_image_url': listing.cover_image_url,
                    'street': listing.street,
                    'house_number': listing.house_number,
                    'floor': listing.floor
                })
            
            return sample_listings
            
        except Exception as e:
            logger.error(f"Error fetching sample listings for neighborhood {yad2_hood_id}: {e}")
            return []
    
    async def _count_available_listings(
        self, 
        db: AsyncSession, 
        yad2_hood_id: int, 
    ) -> int:
        """Count total available listings for a neighborhood."""
        try:
            from sqlalchemy import func
            
            query = select(func.count(Listing.order_id)).where(
                and_(
                    Listing.neighborhood_id == yad2_hood_id,
                    Listing.is_active == True
                )
            )
            
            result = await db.execute(query)
            count = result.scalar()
            return count or 0
            
        except Exception as e:
            logger.error(f"Error counting listings for neighborhood {yad2_hood_id}: {e}")
            return 0

# Convenience function for direct usage
async def get_user_neighborhood_recommendations(
    db: AsyncSession, 
    user_id: str, 
    top_k: int = 3
) -> List[Dict]:
    """
    Convenience function to get neighborhood recommendations for a user.
    
    Args:
        db: Database session
        user_id: User's Firebase UID
        top_k: Number of recommendations to return (default: 3)
        
    Returns:
        List of recommended neighborhoods with scores and sample listings
    """
    service = NeighborhoodRecommendationService()
    return await service.get_neighborhood_recommendations(db, user_id, top_k)
