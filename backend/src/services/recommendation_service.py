"""
Neighborhood Recommendation Service
Provides neighborhood recommendations based on user questionnaire responses and price preferences.
"""

import numpy as np
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
import logging

from src.database.models import Listing, Neighborhood, NeighborhoodMetrics, NeighborhoodMetadata, ListingMetadata, UserFilters
from src.services.questionnaire_service import QuestionnaireService
from src.database.models import NeighborhoodFeatures, UserPreferenceVector

logger = logging.getLogger(__name__)

class NeighborhoodRecommendationService:
    """Service for generating neighborhood recommendations based on user preferences and budget."""
    
    def __init__(self):
        self.questionnaire_service = QuestionnaireService()
        
        # Feature names in order (matching the NeighborhoodFeatures model)
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
            'safety_level',             # 9
            'nightlife_level'           # 10 - Added from the updated model
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
        Get top neighborhood recommendations for a user based on their questionnaire responses and budget.
        
        Args:
            db: Database session
            user_id: User's Firebase UID
            top_k: Number of recommendations to return
            
        Returns:
            List of recommended neighborhoods with scores and sample listings
        """
        try:
            # Get user's price preferences
            user_price_filters = await self._get_user_price_filters(db, user_id)
            
            # Get preference vector (cached or calculated)
            preference_vector = await self._get_cached_preference_vector(db, user_id)
            
            if preference_vector is None:
                # Fallback: Get user's questionnaire responses and calculate vector
                user_responses = await self.questionnaire_service.get_user_responses(db, user_id)
                if not user_responses:
                    logger.warning(f"No questionnaire responses found for user {user_id}")
                    return []
                
                # Convert responses to preference vector
                preference_vector = self._create_preference_vector(user_responses)
                logger.info(f"Calculated preference vector from responses for user {user_id}: {preference_vector}")
            else:
                logger.info(f"Using cached preference vector for user {user_id}: {preference_vector}")
            
            # Get neighborhood features from database
            neighborhood_features = await self._get_neighborhood_features_with_prices(db)
            if not neighborhood_features:
                logger.error("No neighborhood features found in database")
                return []
            
            # Score neighborhoods with enhanced algorithm
            scored_neighborhoods = self._score_neighborhoods_with_price(
                neighborhood_features, 
                preference_vector, 
                user_price_filters
            )
            
            # Get top recommendations
            top_neighborhoods = sorted(scored_neighborhoods, key=lambda x: x['total_score'], reverse=True)[:top_k]
            
            # Enrich with listings and additional info
            recommendations = await self._enrich_recommendations(db, top_neighborhoods)
            
            logger.info(f"Generated {len(recommendations)} recommendations for user {user_id}")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations for user {user_id}: {e}", exc_info=True)
            return []

    async def _get_user_price_filters(self, db: AsyncSession, user_id: str) -> Optional[Dict]:
        """Get user's price preferences from UserFilters."""
        try:
            result = await db.execute(
                select(UserFilters).where(UserFilters.user_id == user_id)
            )
            filters = result.scalar_one_or_none()
            
            if filters:
                return {
                    'price_min': filters.price_min,
                    'price_max': filters.price_max,
                    'type': filters.type or 'rent'
                }
            
            # Default price range if no filters set
            return {
                'price_min': 4000,
                'price_max': 7000,
                'type': 'rent'
            }
            
        except Exception as e:
            logger.error(f"Error fetching user price filters for {user_id}: {e}")
            return {'price_min': 2000, 'price_max': 8000, 'type': 'rent'}
    
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
        
        # Nightlife -> nightlife_level and peaceful_level (inverse)
        if 'nightlife_proximity' in responses:
            response = responses['nightlife_proximity']
            if response == 'Yes, I want to be in the center of the action':
                preferences['nightlife_level'] = max(preferences['nightlife_level'], 0.9)
                preferences['cultural_level'] = max(preferences['cultural_level'], 0.9)
                preferences['peaceful_level'] = min(preferences['peaceful_level'], 0.3)
            elif response == 'Close but not too close':
                preferences['nightlife_level'] = max(preferences['nightlife_level'], 0.6)
                preferences['cultural_level'] = max(preferences['cultural_level'], 0.6)
                preferences['peaceful_level'] = 0.6
            elif response == 'As far as possible':
                preferences['nightlife_level'] = min(preferences['nightlife_level'], 0.2)
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
            preferences['nightlife_level'] = max(preferences['nightlife_level'], 0.6)
            
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
            preferences['nightlife_level'] = min(preferences['nightlife_level'], 0.3)  # Families typically avoid nightlife areas
            
        elif 'With roommates' in housing_purpose:
            preferences['cultural_level'] = max(preferences['cultural_level'], 0.7)
            preferences['shopping_level'] = max(preferences['shopping_level'], 0.6)
            preferences['mobility_level'] = max(preferences['mobility_level'], 0.7)
            preferences['nightlife_level'] = max(preferences['nightlife_level'], 0.7)
    
    async def _get_neighborhood_features_with_prices(self, db: AsyncSession) -> List[Dict]:
        """Get neighborhood features with average rental prices from database."""
        try:
            # Join NeighborhoodFeatures with Neighborhood and NeighborhoodMetrics to get prices
            result = await db.execute(
                select(
                    NeighborhoodFeatures,
                    Neighborhood.hebrew_name,
                    NeighborhoodMetrics.avg_rental_price
                )
                .join(Neighborhood, NeighborhoodFeatures.neighborhood_id == Neighborhood.id)
                .join(NeighborhoodMetrics, Neighborhood.id == NeighborhoodMetrics.neighborhood_id, isouter=True)
            )
            features_with_data = result.fetchall()
            
            neighborhood_data = []
            for feature, hebrew_name, avg_rental_price in features_with_data:
                if feature.feature_vector:
                    neighborhood_data.append({
                        'neighborhood_id': feature.neighborhood_id,
                        'hebrew_name': hebrew_name,
                        'feature_vector': np.array(feature.feature_vector),
                        'avg_rental_price': float(avg_rental_price) if avg_rental_price else None,
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
                            'safety_level': feature.safety_level,
                            'nightlife_level': feature.nightlife_level  # Added nightlife level
                        }
                    })
            
            return neighborhood_data
            
        except Exception as e:
            logger.error(f"Error fetching neighborhood features with prices: {e}", exc_info=True)
            return []
        
    def _calculate_price_affordability_score(
        self,
        avg_rental_price: Optional[float],
        user_price_range: Dict[str, float]
    ) -> float:
        if not avg_rental_price:
            return 0.3  # neutral when no price data

        user_min = user_price_range["price_min"]
        user_max = user_price_range["price_max"]
        user_mid = (user_min + user_max) / 2
        user_range = user_max - user_min or 1

        # Perfect zone
        if user_min <= avg_rental_price <= user_max:
            distance_from_mid = abs(avg_rental_price - user_mid)
            normalized_distance = distance_from_mid / (user_range / 2)
            return max(0.75, 1.0 - normalized_distance * 0.25)

        buffer = 0.2  # 20% buffer zone, still penalized harder now

        if avg_rental_price < user_min:
            limit = user_min * (1 - buffer)
            if avg_rental_price >= limit:
                # now penalize more even in buffer zone
                underrun = (user_min - avg_rental_price) / user_min
                return max(0.4, 0.6 - underrun * 1.2)
            underrun = (limit - avg_rental_price) / user_min
            return max(0.05, 0.4 - underrun * 1.5)

        else:
            limit = user_max * (1 + buffer)
            if avg_rental_price <= limit:
                overrun = (avg_rental_price - user_max) / user_max
                return max(0.4, 0.6 - overrun * 1.2)
            overrun = (avg_rental_price - limit) / user_max
            return max(0.05, 0.4 - overrun * 1.5)


        
    def _score_neighborhoods_with_price(
        self, 
        neighborhoods: List[Dict], 
        user_preferences: np.ndarray, 
        user_price_range: Optional[Dict]
    ) -> List[Dict]:
        """Enhanced scoring that combines feature matching with price affordability."""
        scored_neighborhoods = []
        
        # Ensure user preferences are valid
        if np.sum(user_preferences) == 0 or np.any(np.isnan(user_preferences)):
            # Use default balanced preferences if user preferences are invalid
            user_preferences = np.full(len(self.feature_names), 0.5)
            logger.warning("Invalid user preferences detected, using default balanced preferences")
        
        # Keep original preferences for realistic weighting (don't normalize to sum=1)
        # Just ensure they're in 0-1 range
        user_preferences = np.clip(user_preferences, 0, 1)
        
        # Weight for balancing feature score vs price score
        feature_weight = 0.7  # 70% feature matching
        price_weight = 0.3    # 30% price affordability
        
        for neighborhood in neighborhoods:
            # Ensure feature vector is valid
            feature_vector = neighborhood.get('feature_vector', [])
            if len(feature_vector) == 0 or len(feature_vector) != len(user_preferences):
                # Create default feature vector if missing
                feature_vector = [0.5] * len(user_preferences)
                logger.warning(f"Invalid feature vector for neighborhood {neighborhood.get('neighborhood_id')}, using default")
            
            # Convert to numpy array and ensure no NaN values
            feature_vector = np.array(feature_vector)
            if np.any(np.isnan(feature_vector)):
                feature_vector = np.nan_to_num(feature_vector, nan=0.5)
            
            # Calculate realistic feature matching score
            # Use weighted average of how well each feature matches user preference
            feature_matches = []
            total_weight = 0
            
            for i, (neighborhood_val, user_pref) in enumerate(zip(feature_vector, user_preferences)):
                # Calculate match quality: 1.0 - |difference| gives us similarity
                match_quality = 1.0 - abs(neighborhood_val - user_pref)
                # Weight by user preference strength (higher pref = more important match)
                weight = user_pref if user_pref > 0.1 else 0.1  # Minimum weight to avoid zero
                feature_matches.append(match_quality * weight)
                total_weight += weight
            
            # Calculate weighted average match score
            if total_weight > 0:
                feature_score = sum(feature_matches) / total_weight
            else:
                feature_score = 0.5
            
            # Scale to make scores more meaningful (typically will be 0.7-1.0 range naturally)
            # Add slight boost to make good matches feel rewarding
            feature_score = feature_score * 1.1  # Boost by 10%
            feature_score = min(1.0, feature_score)  # Cap at 100%
            
            # Ensure feature score is valid
            if np.isnan(feature_score) or np.isinf(feature_score):
                feature_score = 0.5  # Default to 50% - neutral match
                logger.warning(f"Invalid feature score for neighborhood {neighborhood.get('neighborhood_id')}, using default")
            
            # Calculate price affordability score
            price_score = 1.0  # Default if no price range provided
            if user_price_range:
                price_score = self._calculate_price_affordability_score(
                    neighborhood['avg_rental_price'], 
                    user_price_range
                )
            
            # Combined total score
            total_score = (feature_score * feature_weight) + (price_score * price_weight)
            
            # Ensure total score is valid
            if np.isnan(total_score) or np.isinf(total_score):
                total_score = 0.5  # Default to 50% - neutral score
                logger.warning(f"Invalid total score for neighborhood {neighborhood.get('neighborhood_id')}, using default")
            
            scored_neighborhoods.append({
                'neighborhood_id': neighborhood['neighborhood_id'],
                'hebrew_name': neighborhood['hebrew_name'],
                'feature_score': float(feature_score),
                'price_score': float(price_score),
                'total_score': float(total_score),
                'avg_rental_price': neighborhood['avg_rental_price'],
                'individual_scores': neighborhood['individual_scores'],
                'user_preferences': user_preferences.tolist(),  # Keep original for debugging
                'match_details': self._get_match_details(neighborhood['individual_scores'], user_preferences),
                'price_analysis': self._get_price_analysis(
                    neighborhood['avg_rental_price'], 
                    user_price_range
                ) if user_price_range else None
            })
        
        return scored_neighborhoods
    
    def _get_price_analysis(self, avg_rental_price: Optional[float], user_price_range: Dict) -> Dict:
        """Get detailed price analysis for explanation."""
        if not avg_rental_price:
            return {
                'status': 'unknown',
                'message': 'Price data not available',
                'affordability': 'unknown'
            }
        
        user_min = user_price_range['price_min']
        user_max = user_price_range['price_max']
        
        if user_min <= avg_rental_price <= user_max:
            percentage_of_budget = (avg_rental_price / user_max) * 100
            return {
                'status': 'affordable',
                'message': f'Within budget (₪{avg_rental_price:,.0f})',
                'affordability': 'perfect' if percentage_of_budget <= 80 else 'good',
                'budget_percentage': round(percentage_of_budget, 1)
            }
        elif avg_rental_price < user_min:
            return {
                'status': 'below_range',
                'message': f'Below expected range (₪{avg_rental_price:,.0f})',
                'affordability': 'very_affordable',
                'savings_potential': user_min - avg_rental_price
            }
        else:
            excess = avg_rental_price - user_max
            excess_percentage = (excess / user_max) * 100
            return {
                'status': 'above_budget',
                'message': f'Above budget (₪{avg_rental_price:,.0f})',
                'affordability': 'expensive',
                'excess_amount': excess,
                'excess_percentage': round(excess_percentage, 1)
            }
    
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
                neighborhood_info = await self._get_neighborhood_info(db, neighborhood['neighborhood_id'])
                
                # Get sample listings
                sample_listings = await self._get_sample_listings(
                    db, neighborhood['neighborhood_id'], limit=3
                )
                
                # Count total available listings
                total_listings = await self._count_available_listings(
                    db, neighborhood['neighborhood_id']
                )
                
                enriched_recommendations.append({
                    'neighborhood_id': neighborhood['neighborhood_id'],
                    'hebrew_name': neighborhood['hebrew_name'],
                    'english_name': neighborhood_info.get('english_name') if neighborhood_info else None,
                    'score': neighborhood['total_score'],  # Frontend expects this field for match percentage
                    'total_score': neighborhood['total_score'],
                    'feature_score': neighborhood['feature_score'],
                    'price_score': neighborhood['price_score'],
                    'avg_rental_price': neighborhood['avg_rental_price'],
                    'price_analysis': neighborhood.get('price_analysis'),
                    'match_details': neighborhood['match_details'],
                    'individual_scores': neighborhood['individual_scores'],
                    'sample_listings': sample_listings,
                    'total_available_listings': total_listings,
                    'neighborhood_info': neighborhood_info
                })
                
            except Exception as e:
                logger.error(f"Error enriching neighborhood {neighborhood['neighborhood_id']}: {e}")
                continue
        
        return enriched_recommendations
    
    async def _get_neighborhood_info(self, db: AsyncSession, neighborhood_id: int) -> Optional[Dict]:
        """Get additional neighborhood information."""
        try:
            result = await db.execute(
                select(Neighborhood)
                .options(
                    selectinload(Neighborhood.metrics),
                    selectinload(Neighborhood.meta_data)
                )
                .where(Neighborhood.id == neighborhood_id)
            )
            neighborhood = result.scalar_one_or_none()
            
            if neighborhood:
                return {
                    'english_name': neighborhood.english_name,
                    'avg_rent_price': float(neighborhood.metrics.avg_rental_price) if neighborhood.metrics and neighborhood.metrics.avg_rental_price else None,
                    'avg_purchase_price': float(neighborhood.metrics.avg_sale_price) if neighborhood.metrics and neighborhood.metrics.avg_sale_price else None,
                    'overview': neighborhood.meta_data.overview if neighborhood.meta_data else None,
                    'latitude': neighborhood.latitude,
                    'longitude': neighborhood.longitude
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching neighborhood info for {neighborhood_id}: {e}")
            return None
    
    async def _get_sample_listings(
        self, 
        db: AsyncSession, 
        neighborhood_id: int, 
        limit: int = 3
    ) -> List[Dict]:
        """Get sample listings for a neighborhood."""
        try:
            # Join with ListingMetadata to get is_active and cover_image_url
            query = select(Listing, ListingMetadata).join(
                ListingMetadata, Listing.listing_id == ListingMetadata.listing_id, isouter=True
            ).join(
                Neighborhood, ListingMetadata.neighborhood_id == Neighborhood.id, isouter=True
            ).where(
                and_(
                    Neighborhood.id == neighborhood_id,
                    ListingMetadata.is_active == True
                )
            ).limit(limit)
            
            result = await db.execute(query)
            listing_data = result.fetchall()
            
            sample_listings = []
            for listing, metadata in listing_data:
                sample_listings.append({
                    'listing_id': listing.listing_id,
                    'yad2_url_token': listing.yad2_url_token,
                    'price': float(listing.price) if listing.price else None,
                    'rooms_count': float(listing.rooms_count) if listing.rooms_count else None,
                    'square_meter': listing.square_meter,
                    'cover_image_url': metadata.cover_image_url if metadata else None,
                    'street': listing.street,
                    'house_number': listing.house_number,
                    'floor': listing.floor
                })
            
            return sample_listings
            
        except Exception as e:
            logger.error(f"Error fetching sample listings for neighborhood {neighborhood_id}: {e}")
            return []
    
    async def _count_available_listings(
        self, 
        db: AsyncSession, 
        neighborhood_id: int, 
    ) -> int:
        """Count total available listings for a neighborhood."""
        try:
            query = select(func.count(Listing.listing_id)).join(
                ListingMetadata, Listing.listing_id == ListingMetadata.listing_id
            ).join(
                Neighborhood, ListingMetadata.neighborhood_id == Neighborhood.id
            ).where(
                and_(
                    Neighborhood.id == neighborhood_id,
                    ListingMetadata.is_active == True
                )
            )
            
            result = await db.execute(query)
            count = result.scalar()
            return count or 0
            
        except Exception as e:
            logger.error(f"Error counting listings for neighborhood {neighborhood_id}: {e}")
            return 0

    async def _get_cached_preference_vector(self, db: AsyncSession, user_id: str) -> Optional[np.ndarray]:
        """
        Get cached user preference vector from PostgreSQL.
        
        Args:
            db: Database session
            user_id: User's Firebase UID
            
        Returns:
            Preference vector as numpy array, or None if not found
        """
        try:
            result = await db.execute(
                select(UserPreferenceVector).where(UserPreferenceVector.user_id == user_id)
            )
            cached_vector = result.scalar_one_or_none()
            
            if cached_vector and cached_vector.preference_vector:
                return np.array(cached_vector.preference_vector)
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching cached preference vector for user {user_id}: {e}")
            return None

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
