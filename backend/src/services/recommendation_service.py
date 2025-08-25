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
import json
import aiohttp
import requests
import hashlib
from datetime import datetime
from src.config.settings import settings

from src.database.models import Listing, Neighborhood, NeighborhoodMetrics, NeighborhoodMetadata, ListingMetadata, UserFilters
from src.services.questionnaire_service import QuestionnaireService
from src.database.models import NeighborhoodFeatures, UserPreferenceVector
from src.utils.cache.redis_client import get_cache, set_cache, delete_cache

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
        
        # Cache settings
        self.cache_ttl = 3600  # 1 hour cache
    
    def _generate_cache_key(self, user_id: str, user_responses: Optional[Dict] = None, 
                           user_price_filters: Optional[Dict] = None, 
                           preference_vector: Optional[np.ndarray] = None) -> str:
        """
        Generate a unique cache key based on user preferences, price filters, and POIs.
        
        Args:
            user_id: User's Firebase UID
            user_responses: User questionnaire responses
            user_price_filters: User price filters
            preference_vector: User preference vector
            
        Returns:
            Unique cache key string
        """
        # Create a dictionary with all factors that affect recommendations
        cache_data = {
            'user_id': user_id,
            'price_filters': user_price_filters or {},
            'preference_vector': preference_vector.tolist() if preference_vector is not None else None,
        }
        
        # Add POIs from responses if available
        if user_responses and 'points_of_interest' in user_responses:
            pois = user_responses['points_of_interest']
            if isinstance(pois, str):
                try:
                    pois = json.loads(pois)
                except:
                    pois = []
            cache_data['pois'] = pois
        
        # Create hash of the data for unique key
        cache_string = json.dumps(cache_data, sort_keys=True)
        cache_hash = hashlib.md5(cache_string.encode()).hexdigest()
        
        return f"recommendations:{user_id}:{cache_hash}"
    
    def _get_cached_recommendations(self, cache_key: str, top_k: int) -> Optional[List[Dict]]:
        """
        Get cached recommendations and return only top_k results.
        
        Args:
            cache_key: The cache key to look up
            top_k: Number of recommendations to return
            
        Returns:
            Cached recommendations (limited to top_k) or None if not found
        """
        try:
            cached_data = get_cache(cache_key)
            if cached_data and 'recommendations' in cached_data:
                recommendations = cached_data['recommendations']
                logger.info(f"📦 Cache hit! Found {len(recommendations)} cached recommendations")
                
                # Return only the requested number of recommendations
                return recommendations[:top_k]
            
            return None
        except Exception as e:
            logger.error(f"Error retrieving cached recommendations: {e}")
            return None
    
    def _cache_recommendations(self, cache_key: str, recommendations: List[Dict]) -> bool:
        """
        Cache the recommendations for future use.
        
        Args:
            cache_key: The cache key to store under
            recommendations: The recommendations to cache
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cache_data = {
                'recommendations': recommendations,
                'cached_at': json.dumps(datetime.now(), default=str),
                'total_count': len(recommendations)
            }
            
            success = set_cache(cache_key, cache_data, ttl=self.cache_ttl)
            if success:
                logger.info(f"💾 Cached {len(recommendations)} recommendations for 1 hour")
            
            return success
        except Exception as e:
            logger.error(f"Error caching recommendations: {e}")
            return False
        
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
            'Yes': 0.9,
            'Yes, I\'m willing to compromise': 0.1,
            'No, I want a safe neighborhood': 0.9
        }
    
    async def get_neighborhood_recommendations(
        self, 
        db: AsyncSession, 
        user_id: str, 
        top_k: int = 3,
        use_cache: bool = True
    ) -> List[Dict]:
        """
        Get top neighborhood recommendations for a user based on their questionnaire responses and budget.
        
        Args:
            db: Database session
            user_id: User's Firebase UID
            top_k: Number of recommendations to return (3 or 10)
            use_cache: Whether to use Redis caching
            
        Returns:
            List of recommended neighborhoods with scores and sample listings
        """
        try:
            # Get user's price preferences
            user_price_filters = await self._get_user_price_filters(db, user_id)
            
            # Get preference vector (cached or calculated)
            preference_vector = await self._get_cached_preference_vector(db, user_id)
            user_responses = None
            
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
                # Get responses for POI data even if we have cached vector
                user_responses = await self.questionnaire_service.get_user_responses(db, user_id)
                logger.info(f"Using cached preference vector for user {user_id}: {preference_vector}")
            
            # Generate cache key based on all user preferences
            cache_key = self._generate_cache_key(user_id, user_responses, user_price_filters, preference_vector)
            
            # Try to get from cache first
            if use_cache:
                cached_recommendations = self._get_cached_recommendations(cache_key, top_k)
                if cached_recommendations is not None:
                    logger.info(f"🚀 Returning {len(cached_recommendations)} cached recommendations for user {user_id}")
                    return cached_recommendations
            
            logger.info(f"🔄 Cache miss - calculating fresh recommendations for user {user_id}")
            
            # Get user's points of interest
            user_pois = self._get_user_pois(user_responses) if user_responses else []
            logger.info(f"Found {len(user_pois)} POIs for user {user_id}: {user_pois}")
            
            # Get neighborhood features from database
            neighborhood_features = await self._get_neighborhood_features_with_prices(db)
            if not neighborhood_features:
                logger.error("No neighborhood features found in database")
                return []
            
            # Calculate location scores if user has POIs
            location_scores = {}
            if user_pois:
                logger.info(f"Calculating location scores for {len(user_pois)} POIs")
                try:
                    location_scores = await self._get_location_scores(neighborhood_features, user_pois)
                    if location_scores:
                        logger.info(f"Generated location scores for {len(location_scores)} neighborhoods")
                    else:
                        logger.warning("Location scoring failed - continuing with feature and price scoring only")
                except Exception as e:
                    logger.error(f"Error in location scoring: {e} - continuing without location scores")
                    location_scores = {}
            else:
                logger.info("No POIs found, skipping location scoring")
            
            # Score neighborhoods with enhanced algorithm including location scores
            scored_neighborhoods = self._score_neighborhoods(
                neighborhood_features, 
                preference_vector, 
                user_price_filters,
                location_scores
            )
            
            # Get ALL top recommendations (we'll cache more than requested for future use)
            all_top_neighborhoods = sorted(scored_neighborhoods, key=lambda x: x['total_score'], reverse=True)[:10]
            
            # Enrich with listings and additional info
            all_recommendations = await self._enrich_recommendations(db, all_top_neighborhoods)
            
            # Cache the top 10 recommendations for future use
            if use_cache and len(all_recommendations) > 0:
                self._cache_recommendations(cache_key, all_recommendations)
            
            # Return only the requested number
            recommendations = all_recommendations[:top_k]
            
            logger.info(f"Generated {len(recommendations)} recommendations for user {user_id} (cached {len(all_recommendations)} total)")
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
                'price_min': 500,
                'price_max': 20000,
                'type': 'rent'
            }
            
        except Exception as e:
            logger.error(f"Error fetching user price filters for {user_id}: {e}")
            return {'price_min': 500, 'price_max': 20000, 'type': 'rent'}
    
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
    
    def _get_user_pois(self, responses: Dict) -> List[Dict]:
        """
        Extract and validate user's points of interest from responses.
        
        Args:
            responses: User questionnaire responses
            
        Returns:
            List of validated POI dictionaries with place_id, max_time, and mode
        """
        if not responses or 'points_of_interest' not in responses:
            return []
        
        try:
            poi_answer = responses['points_of_interest']
            if not poi_answer:
                return []
            
            # Handle both JSON string and already parsed list
            if isinstance(poi_answer, str):
                pois = json.loads(poi_answer)
            elif isinstance(poi_answer, list):
                pois = poi_answer
            else:
                logger.warning(f"Unexpected POI data type: {type(poi_answer)}")
                return []
            
            # Validate and clean POI data
            validated_pois = []
            for poi in pois:
                if isinstance(poi, dict) and all(key in poi for key in ['place_id', 'max_time', 'mode']):
                    if poi['place_id'] and poi['max_time'] > 0:
                        validated_pois.append({
                            'place_id': poi['place_id'],
                            'max_time': int(poi['max_time']),
                            'mode': poi['mode'],
                            'description': poi.get('description', '')
                        })
            
            logger.info(f"Extracted {len(validated_pois)} valid POIs from responses")
            return validated_pois
            
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.warning(f"Error parsing POI data from responses: {e}")
            return []
    


    async def _get_neighborhood_features_with_prices(self, db: AsyncSession) -> List[Dict]:
        """Get neighborhood features with average rental prices from database."""
        try:
            # Join NeighborhoodFeatures with Neighborhood and NeighborhoodMetrics to get prices and coordinates
            result = await db.execute(
                select(
                    NeighborhoodFeatures,
                    Neighborhood.hebrew_name,
                    Neighborhood.latitude,
                    Neighborhood.longitude,
                    NeighborhoodMetrics.avg_rental_price
                )
                .join(Neighborhood, NeighborhoodFeatures.neighborhood_id == Neighborhood.id)
                .join(NeighborhoodMetrics, Neighborhood.id == NeighborhoodMetrics.neighborhood_id, isouter=True)
            )
            features_with_data = result.fetchall()
            
            neighborhood_data = []
            for feature, hebrew_name, latitude, longitude, avg_rental_price in features_with_data:
                if feature.feature_vector and latitude and longitude:
                    neighborhood_data.append({
                        'neighborhood_id': feature.neighborhood_id,
                        'hebrew_name': hebrew_name,
                        'latitude': float(latitude),
                        'longitude': float(longitude),
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

        buffer = 0.2  # 20% buffer zone

        if avg_rental_price < user_min:
            limit = user_min * (1 - buffer)
            if avg_rental_price >= limit:
                underrun = (user_min - avg_rental_price) / user_min
                return max(0.75, 1.0 - underrun * 0.25)
            underrun = (limit - avg_rental_price) / user_min
            return max(0.05, 0.6 - underrun * 0.55)

        else:
            limit = user_max * (1 + buffer)
            if avg_rental_price <= limit:
                overrun = (avg_rental_price - user_max) / user_max
                return max(0.75, 1.0 - overrun * 0.25)
            overrun = (avg_rental_price - limit) / user_max
            return max(0.05, 0.6 - overrun * 0.55)

    def _call_google_routes_api(self, origins: List[Dict], destinations: List[str], mode: str) -> Optional[Dict]:
        """
        Call Google Routes API (computeRouteMatrix) - the new replacement for Distance Matrix API.
        
        Args:
            origins: List of origin coordinates with lat and lng
            destinations: List of destination place IDs
            mode: Travel mode
            
        Returns:
            Routes API response converted to Distance Matrix format, or None if error
        """
        if not settings.GOOGLE_API_KEY:
            logger.error("Google Maps API key not configured")
            return None
        
        try:
            # Convert travel mode to Routes API format
            travel_mode_map = {
                'driving': 'DRIVE',
                'walking': 'WALK',
                'bicycling': 'BICYCLE',
                'transit': 'TRANSIT',
                'public_transport': 'TRANSIT'  # Add mapping for public_transport
            }
            routes_mode = travel_mode_map.get(mode, 'DRIVE')
            
            # Prepare waypoints for Routes API v2 (correct format)
            origin_waypoints = []
            for origin in origins:
                origin_waypoints.append({
                    "waypoint": {
                        "location": {
                            "latLng": {
                                "latitude": origin['lat'],
                                "longitude": origin['lng']
                            }
                        }
                    }
                })
            
            destination_waypoints = []
            for dest_place_id in destinations:
                destination_waypoints.append({
                    "waypoint": {
                        "placeId": dest_place_id
                    }
                })
            
            # Prepare request body for Routes API v2
            request_body = {
                "origins": origin_waypoints,
                "destinations": destination_waypoints,
                "travelMode": routes_mode,
                "units": "METRIC"
            }
            
            # Add routing preference based on mode
            if routes_mode == "TRANSIT":
                # For transit, DO NOT set routingPreference - it's not allowed for TRANSIT mode
                # Configure transit to return more realistic/average times
                import datetime
                
                # Set departure time to current time + 30 minutes to get realistic scheduling
                # This accounts for waiting times and real schedule constraints
                current_time = datetime.datetime.now()
                departure_time = current_time + datetime.timedelta(minutes=30)
                
                request_body["transitPreferences"] = {
                    "allowedTravelModes": ["BUS", "SUBWAY", "TRAIN", "LIGHT_RAIL"],
                    "routingPreference": "FEWER_TRANSFERS"  # Changed from LESS_WALKING to FEWER_TRANSFERS for more realistic routes
                }
                
                # Add departure time for more realistic transit times
                request_body["departureTime"] = departure_time.strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                # Only set routingPreference for non-transit modes
                request_body["routingPreference"] = "TRAFFIC_AWARE_OPTIMAL"
            
            # Routes API endpoint
            url = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
            
            # Use different field masks for transit vs other modes
            if routes_mode == "TRANSIT":
                # For transit, we need additional fields
                field_mask = "originIndex,destinationIndex,status,condition,distanceMeters,duration,localizedValues"
            else:
                field_mask = "originIndex,destinationIndex,status,condition,distanceMeters,duration"
            
            headers = {
                "X-Goog-Api-Key": settings.GOOGLE_API_KEY,
                "X-Goog-FieldMask": field_mask,
                "Content-Type": "application/json"
            }
            
            logger.info(f"Calling Google Routes API (computeRouteMatrix) for mode {mode}")
            
            response = requests.post(url, json=request_body, headers=headers, timeout=30)
            
            if response.status_code != 200:
                error_text = response.text
                logger.error(f"Google Routes API error {response.status_code}: {error_text}")
                
                # Try to parse error details
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_message = error_data["error"].get("message", "Unknown error")
                        logger.error(f"Google Routes API detailed error: {error_message}")
                        
                        # For transit routes, if there's an error, log it but don't fail completely
                        if routes_mode == "TRANSIT":
                            logger.warning(f"Transit routing failed, this might be due to limited transit data for the area")
                except:
                    pass
                    
                return None
            
            data = response.json()
            logger.info(f"Google Routes API response received successfully for {routes_mode} mode")
            
            # Convert Routes API response to Distance Matrix format for compatibility
            converted_response = self._convert_routes_to_distance_matrix_format(data, origins, destinations)
            return converted_response
                
        except requests.RequestException as e:
            logger.error(f"Error calling Google Routes API: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error calling Google Routes API: {e}")
            return None

    def _convert_routes_to_distance_matrix_format(self, routes_response: Dict, origins: List[Dict], destinations: List[str]) -> Dict:
        """
        Convert Routes API response format to Distance Matrix API format for compatibility.
        
        Args:
            routes_response: Response from Routes API
            origins: Original origins list
            destinations: Original destinations list
            
        Returns:
            Response in Distance Matrix API format
        """
        try:
            # Initialize Distance Matrix format response
            distance_matrix_response = {
                "status": "OK",
                "origin_addresses": [f"{o['lat']},{o['lng']}" for o in origins],
                "destination_addresses": destinations,
                "rows": []
            }
            
            # Debug logging
            logger.debug(f"Converting Routes response with {len(origins)} origins, {len(destinations)} destinations")
            logger.debug(f"Routes response type: {type(routes_response)}")
            
            # Create rows for each origin
            for origin_idx in range(len(origins)):
                row = {"elements": []}
                
                for dest_idx in range(len(destinations)):
                    # Find the corresponding element in Routes API response
                    element = {"status": "NOT_FOUND"}
                    
                    # Routes API response can be either a dict with "elements" or direct array
                    elements_list = routes_response.get("elements", routes_response) if isinstance(routes_response, dict) else routes_response
                    
                    if isinstance(elements_list, list):
                        for route_element in elements_list:
                            if (route_element.get("originIndex") == origin_idx and 
                                route_element.get("destinationIndex") == dest_idx):
                                
                                # Routes API v2 can use either condition field or status object
                                condition = route_element.get("condition")
                                status_obj = route_element.get("status", {})
                                
                                # Check different ways to determine if route is valid
                                has_valid_route = False
                                error_message = None
                                
                                # Method 1: Check condition field
                                if condition:
                                    valid_conditions = ["ROUTE_EXISTS", "OK"]
                                    has_valid_route = condition in valid_conditions
                                
                                # Method 2: Check status object
                                if not has_valid_route and isinstance(status_obj, dict):
                                    if not status_obj:
                                        # Empty status object means success
                                        has_valid_route = True
                                    elif "code" in status_obj:
                                        # Status codes: 0 = OK, other codes are errors
                                        status_code = status_obj.get("code", -1)
                                        error_message = status_obj.get("message", "Unknown error")
                                        
                                        if status_code == 0:
                                            has_valid_route = True
                                        else:
                                            # Log important errors only
                                            if status_code == 5:
                                                logger.warning(f"Place ID not found: {error_message}")
                                            elif status_code == 3:
                                                logger.warning(f"Invalid API request: {error_message}")
                                
                                if has_valid_route:
                                    duration_seconds = None
                                    distance_meters = None
                                    
                                    # Extract duration
                                    if "duration" in route_element:
                                        duration_str = route_element["duration"]
                                        # Remove 's' suffix and convert to int
                                        if duration_str.endswith('s'):
                                            try:
                                                duration_seconds = int(float(duration_str[:-1]))
                                            except (ValueError, TypeError):
                                                logger.warning(f"Could not parse duration: {duration_str}")
                                                duration_seconds = None
                                    
                                    # Extract distance
                                    if "distanceMeters" in route_element:
                                        distance_meters = route_element["distanceMeters"]
                                    
                                    # For transit routes, accept routes even with 0 distance if duration > 0
                                    # Transit routes sometimes return distance=0 but valid duration
                                    is_transit_route = route_element.get("travelMode") == "TRANSIT" or "transitDuration" in route_element
                                    
                                    if duration_seconds is not None and duration_seconds > 0:
                                        # Valid route if duration > 0, distance check depends on route type
                                        if not is_transit_route and (distance_meters is None or distance_meters <= 0):
                                            # Non-transit routes need distance
                                            logger.debug(f"Non-transit route missing distance: {distance_meters}")
                                            element = {"status": "ZERO_RESULTS"}
                                        else:
                                            # For transit routes, add realistic buffer to account for real-world delays
                                            adjusted_duration = duration_seconds
                                            if is_transit_route:
                                                # Add modest buffer for transit delays and real-world conditions
                                                # Since we now use realistic departure times and routing preferences,
                                                # we need less artificial buffering
                                                buffer_factor = 1.10  # 10% buffer for minor delays and rounding
                                                adjusted_duration = int(duration_seconds * buffer_factor)
                                                
                                                logger.debug(f"Transit buffer adjustment: {duration_seconds}s -> {adjusted_duration}s (+{int((buffer_factor-1)*100)}%)")
                                            
                                            # Create successful response
                                            element = {
                                                "status": "OK",
                                                "duration": {
                                                    "text": f"{adjusted_duration // 60} mins" if adjusted_duration >= 60 else f"{adjusted_duration} secs",
                                                    "value": adjusted_duration
                                                },
                                                "distance": {
                                                    "text": f"{distance_meters / 1000:.1f} km" if distance_meters and distance_meters > 0 else "N/A",
                                                    "value": distance_meters if distance_meters else 0
                                                }
                                            }
                                            logger.debug(f"Successfully parsed route: {adjusted_duration}s (original: {duration_seconds}s), {distance_meters}m")
                                    else:
                                        logger.debug(f"Invalid duration for route: {duration_seconds}")
                                        element = {"status": "ZERO_RESULTS"}
                                else:
                                    logger.debug(f"No valid route found for origin {origin_idx} to dest {dest_idx}: condition={condition}")
                                    element = {"status": "NOT_FOUND"}
                                break
                    else:
                        logger.warning(f"Expected elements_list to be a list, got {type(elements_list)}: {elements_list}")
                    
                    row["elements"].append(element)
                
                distance_matrix_response["rows"].append(row)
            
            return distance_matrix_response
            
        except Exception as e:
            logger.error(f"Error converting Routes API response: {e}")
            return {"status": "UNKNOWN_ERROR", "rows": []}

    async def _get_location_scores(self, neighborhoods: List[Dict], user_pois: List[Dict]) -> Dict:
        """
        Calculate location scores based on commute times to user POIs.
        
        Args:
            neighborhoods: List of neighborhood data with coordinates
            user_pois: List of user points of interest
            
        Returns:
            Dict mapping neighborhood_id to location score and details
        """
        location_scores = {}
        
        try:
            # Group POIs by travel mode
            pois_by_mode = {}
            for poi in user_pois:
                mode = poi['mode']
                if mode not in pois_by_mode:
                    pois_by_mode[mode] = []
                pois_by_mode[mode].append(poi)
            
            # Get origins (neighborhood coordinates)
            origins = []
            neighborhood_id_to_index = {}
            for i, neighborhood in enumerate(neighborhoods):
                if neighborhood.get('latitude') and neighborhood.get('longitude'):
                    origins.append({
                        'lat': neighborhood['latitude'],
                        'lng': neighborhood['longitude']
                    })
                    neighborhood_id_to_index[neighborhood['neighborhood_id']] = i
                else:
                    logger.warning(f"Neighborhood {neighborhood.get('neighborhood_id')} missing coordinates: lat={neighborhood.get('latitude')}, lng={neighborhood.get('longitude')}")
            
            logger.info(f"Found {len(origins)} neighborhoods with coordinates out of {len(neighborhoods)} total neighborhoods")
            
            if not origins:
                logger.warning("No neighborhood coordinates found for distance matrix calculation")
                return {}
            
            # Calculate scores for each travel mode
            all_results = {}
            
            for mode, pois in pois_by_mode.items():
                if not pois:
                    continue
                
                destinations = [poi['place_id'] for poi in pois]
                logger.info(f"Processing {len(destinations)} destinations for mode {mode}")
                
                # Log POI details for debugging
                for poi in pois:
                    logger.info(f"POI: place_id={poi['place_id']}, description={poi.get('description', 'N/A')}, max_time={poi['max_time']} min, mode={poi['mode']}")
                
                # Call Google Routes API
                data = self._call_google_routes_api(origins, destinations, mode)
                
                if data:
                    all_results[mode] = {
                        'data': data,
                        'pois': pois
                    }
                    logger.info(f"Successfully got route matrix for mode {mode}")
                else:
                    logger.error(f"Failed to get route matrix for mode {mode}")
            
            if not all_results:
                logger.warning("No route matrix results available - location details will be empty")
                logger.warning("Make sure the Google Routes API is enabled and has billing configured in your Google Cloud Console")
                logger.warning("Note: Distance Matrix API (Legacy) is no longer available for new projects")
                
                # For transit routes specifically, this is often due to limited transit data
                transit_modes = [mode for mode in pois_by_mode.keys() if mode in ['transit', 'public_transport']]
                if transit_modes:
                    logger.warning(f"Transit modes {transit_modes} failed - this may be due to limited public transport data for the area")
                    logger.warning("Consider checking if the POI locations have good public transport coverage")
                
                return {}
            
            # Process results and calculate scores
            for neighborhood in neighborhoods:
                neighborhood_id = neighborhood['neighborhood_id']
                if neighborhood_id not in neighborhood_id_to_index:
                    continue
                
                neighborhood_index = neighborhood_id_to_index[neighborhood_id]
                poi_scores = []
                location_details = []
                
                for mode, result_data in all_results.items():
                    data = result_data['data']
                    pois = result_data['pois']
                    
                    if 'rows' in data and len(data['rows']) > neighborhood_index:
                        row = data['rows'][neighborhood_index]
                        elements = row.get('elements', [])
                        
                        for poi_index, element in enumerate(elements):
                            if poi_index >= len(pois):
                                continue
                                
                            poi = pois[poi_index]
                            
                            if element.get('status') == 'OK' and 'duration' in element:
                                # Extract travel time in minutes
                                duration_seconds = element['duration']['value']
                                travel_time_minutes = duration_seconds / 60
                                max_time = poi['max_time']
                                
                                # Calculate score based on travel time vs max time
                                if travel_time_minutes <= max_time:
                                    score = 1.0
                                else:
                                    # Penalize based on how much over the limit
                                    excess_ratio = (travel_time_minutes - max_time) / max_time
                                    score = max(0.0, 1.0 - excess_ratio)
                                
                                poi_scores.append(score)
                                
                                # Create detail string
                                mode_display = mode.replace('_', ' ').replace('public transport', 'transit').title()
                                location_details.append(
                                    f"{int(travel_time_minutes)} min by {mode_display.lower()} to {poi.get('description', 'location')}"
                                )
                                
                            else:
                                # If no route found or error, give neutral score but provide more helpful message
                                poi_scores.append(0.3)
                                element_status = element.get('status', 'UNKNOWN')
                                mode_display = mode.replace('_', ' ').replace('public transport', 'transit').title()
                                poi_description = poi.get('description', 'location')
                                
                                if element_status == 'ZERO_RESULTS':
                                    location_details.append(f"No {mode_display.lower()} route found to {poi_description}")
                                elif element_status == 'NOT_FOUND':
                                    location_details.append(f"Location not accessible by {mode_display.lower()}: {poi_description}")
                                else:
                                    location_details.append(f"Route to {poi_description} unavailable ({mode_display.lower()})")
                
                # Calculate final location score as average of all POI scores
                if poi_scores:
                    final_score = sum(poi_scores) / len(poi_scores)
                else:
                    final_score = 0.5  # Neutral score if no POI data
                
                location_scores[neighborhood_id] = {
                    'score': final_score,
                    'details': location_details[:3]  # Limit to top 3 details
                }
            
            logger.info(f"Calculated location scores for {len(location_scores)} neighborhoods")
            return location_scores
            
        except Exception as e:
            logger.error(f"Error calculating location scores: {e}", exc_info=True)
            return {}

        
    def _score_neighborhoods(
        self, 
        neighborhoods: List[Dict], 
        user_preferences: np.ndarray, 
        user_price_range: Optional[Dict],
        location_scores: Optional[Dict] = None
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
        
        # Weights for balancing feature score, price score, and location score
        if location_scores:
            feature_weight = 0.50  # 50% feature matching
            price_weight = 0.20    # 20% price affordability  
            location_weight = 0.30 # 30% location/commute scoring
        else:
            feature_weight = 0.7   # 70% feature matching
            price_weight = 0.3     # 30% price affordability
            location_weight = 0.0  # 0% location scoring
        
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
            # feature_score = feature_score * 1.1  # Boost by 10%
            # feature_score = min(1.0, feature_score)  # Cap at 100%
            
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
            
            # Get location score for this neighborhood
            location_score = 0.5  # Default neutral score
            location_details = []
            if location_scores and neighborhood['neighborhood_id'] in location_scores:
                location_data = location_scores[neighborhood['neighborhood_id']]
                location_score = location_data['score']
                location_details = location_data['details']
            
            # Combined total score
            total_score = (feature_score * feature_weight) + (price_score * price_weight) + (location_score * location_weight)
            
            # Ensure total score is valid
            if np.isnan(total_score) or np.isinf(total_score):
                total_score = 0.5  # Default to 50% - neutral score
                logger.warning(f"Invalid total score for neighborhood {neighborhood.get('neighborhood_id')}, using default")
            
            scored_neighborhoods.append({
                'neighborhood_id': neighborhood['neighborhood_id'],
                'hebrew_name': neighborhood['hebrew_name'],
                'feature_score': float(feature_score),
                'price_score': float(price_score),
                'location_score': float(location_score),
                'location_details': location_details,
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
        
        # Add debug logging to track price analysis
        logger.debug(f"Price analysis: rental_price={avg_rental_price}, user_range={user_min}-{user_max}")
        
        # Buffer zone (20% above/below user range)
        buffer_percentage = 0.2
        lower_buffer = user_min * (1 - buffer_percentage)  # 20% below min
        upper_buffer = user_max * (1 + buffer_percentage)  # 20% above max
        
        if user_min <= avg_rental_price <= user_max:
            # Within user's specified range
            percentage_of_budget = (avg_rental_price / user_max) * 100
            return {
                'status': 'affordable',
                'message': f'Within budget (₪{avg_rental_price:,.0f})',
                'affordability': 'perfect' if percentage_of_budget <= 80 else 'good',
                'budget_percentage': round(percentage_of_budget, 1)
            }
        elif avg_rental_price < user_min:
            if avg_rental_price >= lower_buffer:
                # In lower buffer zone - slightly below range
                return {
                    'status': 'slightly_below_range',
                    'message': f'Slightly below range (₪{avg_rental_price:,.0f})',
                    'affordability': 'very_affordable',
                    'savings_potential': user_min - avg_rental_price
                }
            else:
                # Well below range
                return {
                    'status': 'below_range',
                    'message': f'Below expected range (₪{avg_rental_price:,.0f})',
                    'affordability': 'very_affordable',
                    'savings_potential': user_min - avg_rental_price
                }
        else:
            # Above user's maximum
            if avg_rental_price <= upper_buffer:
                # In upper buffer zone - slightly above budget
                excess = avg_rental_price - user_max
                excess_percentage = (excess / user_max) * 100
                return {
                    'status': 'slightly_above_budget',
                    'message': f'Slightly above budget (₪{avg_rental_price:,.0f})',
                    'affordability': 'slightly_expensive',
                    'excess_amount': excess,
                    'excess_percentage': round(excess_percentage, 1)
                }
            else:
                # Well above budget - outside buffer zone
                excess = avg_rental_price - user_max
                excess_percentage = (excess / user_max) * 100
                return {
                    'status': 'out_of_budget',
                    'message': f'Out of budget (₪{avg_rental_price:,.0f})',
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
                    'location_score': neighborhood.get('location_score', 0.5),
                    'location_details': neighborhood.get('location_details', []),
                    'avg_rental_price': neighborhood['avg_rental_price'],
                    'price_analysis': neighborhood.get('price_analysis'),
                    'match_details': neighborhood['match_details'],
                    'individual_scores': neighborhood['individual_scores'],
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
    top_k: int = 3,
    use_cache: bool = True
) -> List[Dict]:
    """
    Convenience function to get neighborhood recommendations for a user.
    
    Args:
        db: Database session
        user_id: User's Firebase UID
        top_k: Number of recommendations to return (default: 3, max: 10)
        use_cache: Whether to use Redis caching (default: True)
        
    Returns:
        List of recommended neighborhoods with scores and sample listings
    """
    service = NeighborhoodRecommendationService()
    return await service.get_neighborhood_recommendations(db, user_id, top_k, use_cache)
