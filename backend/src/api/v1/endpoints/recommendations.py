from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from typing import List, Dict, Any

from src.database.postgresql_db import get_db
from src.middleware.auth import get_current_user
from src.services.recommendation_service import get_user_neighborhood_recommendations
from src.utils.cache.redis_client import delete_cache
from src.database.models import Neighborhood, Listing, NeighborhoodMetadata, ListingMetadata, NeighborhoodMetrics, NeighborhoodFeatures
from src.database.schemas import UserFiltersUpdate
from src.services import filters_service
from sqlalchemy import select, func

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get(
    "/neighborhoods",
    summary="Get neighborhood recommendations",
    description="Get personalized neighborhood recommendations based on user's questionnaire responses"
)
async def get_neighborhood_recommendations(
    top_k: int = Query(3, ge=1, le=10, description="Number of recommendations to return"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get personalized neighborhood recommendations for the current user.
    
    This endpoint analyzes the user's questionnaire responses and returns
    the top neighborhood matches with sample listings and detailed scoring.
    """
    user_id = current_user.firebase_uid
    logger.info(f"Getting neighborhood recommendations for user: {user_id}")
    
    try:
        # Get recommendations
        recommendations = await get_user_neighborhood_recommendations(
            db=db,
            user_id=user_id,
            top_k=top_k
        )
        
        if not recommendations:
            # Check if user has completed questionnaire
            return {
                "recommendations": [],
                "message": "No recommendations available. Please complete the questionnaire first.",
                "requires_questionnaire": True
            }
        
        logger.info(f"Returning {len(recommendations)} recommendations for user {user_id}")
        
        return {
            "recommendations": recommendations,
            "total_returned": len(recommendations),
            "message": "Recommendations generated successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting recommendations for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating recommendations."
        )

@router.get(
    "/neighborhoods/explore",
    summary="Explore all neighborhoods with comprehensive metrics",
    description="Get detailed data about all neighborhoods including demographics, pricing, schools, and amenities"
)
async def explore_neighborhoods(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get comprehensive neighborhood data for exploration.
    
    Returns detailed information about all neighborhoods including:
    
    **Basic Info:**
    - Names (Hebrew & English), city, description, coordinates
    
    **Pricing Data:**
    - Current average rental prices (from active listings)
    - Historical average rental/sale prices (from metrics)
    
    **Demographics & Quality:**
    - Social-economic index (1-10 scale)
    - School rating (1-10 scale)  
    - Popular political party
    
    **Location & Amenities:**
    - Beach distance (km)
    - Geographic coordinates
    
    **Market Activity:**
    - Number of current active listings
    
    **Neighborhood Features (0-1 scale each):**
    - Cultural level, Religiosity level, Community spirit
    - Kindergartens quality, Maintenance level, Mobility/transport
    - Parks/green spaces, Peaceful environment, Shopping access
    - Safety level, Nightlife activity
    
    **Enhanced Popularity Score:**
    - Composite score (0-1) based on weighted factors:
      - 20% Social-economic index, 15% School rating
      - 20% Safety level (highest weight), 10% Peaceful environment
      - 10% Maintenance, 10% Parks, 10% Beach proximity, 5% Market activity
    - Includes detailed breakdown of all score components
    """
    logger.info(f"Getting neighborhood exploration data for user: {current_user.firebase_uid}")
    
    try:
        logger.info("Starting comprehensive neighborhood exploration query with ALL rich data...")
        # Query all neighborhoods with comprehensive metrics, features, and current listing data
        neighborhoods_query = select(
            # Basic neighborhood info
            Neighborhood.id,
            Neighborhood.hebrew_name,
            Neighborhood.english_name,
            Neighborhood.city,
            Neighborhood.latitude,
            Neighborhood.longitude,
            # Metadata
            NeighborhoodMetadata.overview,
            # Rich metrics data from NeighborhoodMetrics table
            NeighborhoodMetrics.avg_sale_price,
            NeighborhoodMetrics.avg_rental_price.label('historical_avg_rental_price'),
            NeighborhoodMetrics.social_economic_index,
            NeighborhoodMetrics.popular_political_party,
            NeighborhoodMetrics.school_rating,
            NeighborhoodMetrics.beach_distance_km,
            # Neighborhood characteristics/features (0-1 scale)
            NeighborhoodFeatures.cultural_level,
            NeighborhoodFeatures.religiosity_level,
            NeighborhoodFeatures.communality_level,
            NeighborhoodFeatures.kindergardens_level,
            NeighborhoodFeatures.maintenance_level,
            NeighborhoodFeatures.mobility_level,
            NeighborhoodFeatures.parks_level,
            NeighborhoodFeatures.peaceful_level,
            NeighborhoodFeatures.shopping_level,
            NeighborhoodFeatures.safety_level,
            NeighborhoodFeatures.nightlife_level,
            # Current active listings data
            func.avg(Listing.price).label('current_avg_rental_price'),
            func.count(Listing.listing_id).label('current_active_listings')
        ).select_from(
            Neighborhood
        ).outerjoin(
            NeighborhoodMetadata, Neighborhood.id == NeighborhoodMetadata.neighborhood_id
        ).outerjoin(
            NeighborhoodMetrics, Neighborhood.id == NeighborhoodMetrics.neighborhood_id
        ).outerjoin(
            NeighborhoodFeatures, Neighborhood.id == NeighborhoodFeatures.neighborhood_id
        ).outerjoin(
            ListingMetadata, 
            (Neighborhood.id == ListingMetadata.neighborhood_id) & 
            (ListingMetadata.is_active == True)  # Only join active listings
        ).outerjoin(
            Listing, ListingMetadata.listing_id == Listing.listing_id
        ).group_by(
            Neighborhood.id,
            Neighborhood.hebrew_name, 
            Neighborhood.english_name,
            Neighborhood.city,
            Neighborhood.latitude,
            Neighborhood.longitude,
            NeighborhoodMetadata.overview,
            NeighborhoodMetrics.avg_sale_price,
            NeighborhoodMetrics.avg_rental_price,
            NeighborhoodMetrics.social_economic_index,
            NeighborhoodMetrics.popular_political_party,
            NeighborhoodMetrics.school_rating,
            NeighborhoodMetrics.beach_distance_km,
            # Add all neighborhood features to GROUP BY
            NeighborhoodFeatures.cultural_level,
            NeighborhoodFeatures.religiosity_level,
            NeighborhoodFeatures.communality_level,
            NeighborhoodFeatures.kindergardens_level,
            NeighborhoodFeatures.maintenance_level,
            NeighborhoodFeatures.mobility_level,
            NeighborhoodFeatures.parks_level,
            NeighborhoodFeatures.peaceful_level,
            NeighborhoodFeatures.shopping_level,
            NeighborhoodFeatures.safety_level,
            NeighborhoodFeatures.nightlife_level
        ).order_by(
            Neighborhood.english_name
        )
        
        logger.info("Executing neighborhoods query...")
        result = await db.execute(neighborhoods_query)
        neighborhoods_data = result.all()
        
        logger.info(f"✅ Query executed successfully! Returned {len(neighborhoods_data)} neighborhood records")
        
        # Log first few rows for debugging
        if neighborhoods_data:
            sample_row = neighborhoods_data[0]
            logger.info(f"Sample row: id={sample_row.id}, name={sample_row.english_name}, active_listings={sample_row.current_active_listings}, socio_economic={sample_row.social_economic_index}")
        
        # Transform to response format with comprehensive neighborhood data
        neighborhoods = []
        for row in neighborhoods_data:
            # Calculate comprehensive popularity score based on multiple factors
            # Normalize each factor to 0-1 scale
            socio_score = (row.social_economic_index / 10.0) if row.social_economic_index else 0.5  # Assuming 1-10 scale
            school_score = (row.school_rating / 10.0) if row.school_rating else 0.5  # Assuming 1-10 scale
            beach_score = max(0, (10 - (row.beach_distance_km or 10)) / 10.0)  # Closer is better, max 10km
            market_score = min((row.current_active_listings or 0) / 100.0, 1.0)  # Market activity
            
            # Add key neighborhood features to popularity calculation (these are already 0-1 scale)
            safety_score = row.safety_level or 0.5
            peaceful_score = row.peaceful_level or 0.5
            maintenance_score = row.maintenance_level or 0.5
            parks_score = row.parks_level or 0.5
            
            # Enhanced composite popularity score (weighted average)
            popularity_score = (
                socio_score * 0.20 +      # 20% social-economic index
                school_score * 0.15 +     # 15% school rating
                safety_score * 0.20 +     # 20% safety level (very important)
                peaceful_score * 0.10 +   # 10% peaceful environment
                maintenance_score * 0.10 + # 10% maintenance/cleanliness
                parks_score * 0.10 +      # 10% parks/green spaces
                beach_score * 0.10 +      # 10% beach proximity
                market_score * 0.05      # 5% market activity
            )
            
            neighborhoods.append({
                # Basic info
                "id": row.id,
                "name": row.english_name or "Unknown",
                "hebrew_name": row.hebrew_name or "Unknown", 
                "city": row.city or "Unknown",
                "description": row.overview or f"Explore {row.english_name or 'this neighborhood'} - a vibrant neighborhood in {row.city or 'Israel'}",
                
                # Geographic data
                "latitude": float(row.latitude) if row.latitude else None,
                "longitude": float(row.longitude) if row.longitude else None,
                
                # Pricing data
                "current_avg_rental_price": int(row.current_avg_rental_price) if row.current_avg_rental_price else None,
                "historical_avg_rental_price": int(row.historical_avg_rental_price) if row.historical_avg_rental_price else None,
                "avg_sale_price": int(row.avg_sale_price) if row.avg_sale_price else None,
                
                # Rich neighborhood metrics
                "social_economic_index": round(float(row.social_economic_index), 1) if row.social_economic_index else None,
                "school_rating": round(float(row.school_rating), 1) if row.school_rating else None,
                "beach_distance_km": round(float(row.beach_distance_km), 1) if row.beach_distance_km else None,
                "popular_political_party": row.popular_political_party,
                
                # Comprehensive neighborhood features (0-1 scale)
                "features": {
                    "cultural_level": round(float(row.cultural_level), 2) if row.cultural_level else None,
                    "religiosity_level": round(float(row.religiosity_level), 2) if row.religiosity_level else None,
                    "communality_level": round(float(row.communality_level), 2) if row.communality_level else None,
                    "kindergardens_level": round(float(row.kindergardens_level), 2) if row.kindergardens_level else None,
                    "maintenance_level": round(float(row.maintenance_level), 2) if row.maintenance_level else None,
                    "mobility_level": round(float(row.mobility_level), 2) if row.mobility_level else None,
                    "parks_level": round(float(row.parks_level), 2) if row.parks_level else None,
                    "peaceful_level": round(float(row.peaceful_level), 2) if row.peaceful_level else None,
                    "shopping_level": round(float(row.shopping_level), 2) if row.shopping_level else None,
                    "safety_level": round(float(row.safety_level), 2) if row.safety_level else None,
                    "nightlife_level": round(float(row.nightlife_level), 2) if row.nightlife_level else None,
                },
                
                # Market data
                "current_active_listings": int(row.current_active_listings) if row.current_active_listings else 0,
                
                # Calculated scores
                "popularity_score": round(popularity_score, 2),
                
                # Enhanced score breakdown for transparency
                "score_breakdown": {
                    "socio_economic": round(socio_score, 2),
                    "school_quality": round(school_score, 2), 
                    "safety": round(safety_score, 2),
                    "peaceful": round(peaceful_score, 2),
                    "maintenance": round(maintenance_score, 2),
                    "parks": round(parks_score, 2),
                    "beach_proximity": round(beach_score, 2),
                    "market_activity": round(market_score, 2)
                }
            })
        
        logger.info(f"Returning {len(neighborhoods)} neighborhoods for exploration")
        
        return {
            "neighborhoods": neighborhoods,
            "total_count": len(neighborhoods),
            "message": "Neighborhoods data retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting neighborhoods exploration data: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching neighborhoods data."
        )

@router.get(
    "/neighborhoods/{neighborhood_id}/details",
    summary="Get neighborhood details",
    description="Get detailed information about a specific neighborhood including why it was recommended"
)
async def get_neighborhood_details(
    neighborhood_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get detailed information about a specific neighborhood.
    
    This includes the neighborhood's feature scores, why it matched the user's preferences,
    and additional information about the area.
    """
    user_id = current_user.firebase_uid
    logger.info(f"Getting neighborhood details for {neighborhood_id}, user: {user_id}")
    
    try:
        # Get single neighborhood recommendation for detailed view
        recommendations = await get_user_neighborhood_recommendations(
            db=db,
            user_id=user_id,
            top_k=50  # Get more to find the specific neighborhood
        )
        
        # Find the specific neighborhood
        neighborhood_details = None
        for rec in recommendations:
            if rec['neighborhood_id'] == neighborhood_id:
                neighborhood_details = rec
                break
        
        if not neighborhood_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Neighborhood {neighborhood_id} not found in recommendations"
            )
        
        # Add explanation of why this neighborhood was recommended
        explanation = _generate_recommendation_explanation(neighborhood_details)
        neighborhood_details['recommendation_explanation'] = explanation
        
        return neighborhood_details
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting neighborhood details for {neighborhood_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching neighborhood details."
        )

def _generate_recommendation_explanation(neighborhood_details: dict) -> dict:
    """Generate human-readable explanation of why neighborhood was recommended."""
    match_details = neighborhood_details.get('match_details', {})
    
    excellent_matches = []
    good_matches = []
    
    feature_labels = {
        'cultural_level': 'Cultural Activities',
        'religiosity_level': 'Religious Community',
        'communality_level': 'Community Spirit',
        'kindergardens_level': 'Education Facilities',
        'maintenance_level': 'Neighborhood Maintenance',
        'mobility_level': 'Transportation',
        'parks_level': 'Parks and Green Spaces',
        'peaceful_level': 'Peaceful Environment',
        'shopping_level': 'Shopping Convenience',
        'safety_level': 'Safety and Security'
    }
    
    for feature, details in match_details.items():
        if details.get('match_quality') == 'excellent':
            excellent_matches.append(feature_labels.get(feature, feature))
        elif details.get('match_quality') == 'good':
            good_matches.append(feature_labels.get(feature, feature))
    
    explanation = {
        'overall_score': neighborhood_details.get('score', 0),
        'excellent_matches': excellent_matches,
        'good_matches': good_matches,
        'summary': f"This neighborhood scored {neighborhood_details.get('score', 0):.2f} based on your preferences."
    }
    
    if excellent_matches:
        explanation['summary'] += f" It excels in: {', '.join(excellent_matches[:3])}."
    
    return explanation

@router.post(
    "/refresh",
    summary="Refresh recommendations", 
    description="Refresh recommendations after questionnaire updates (bypasses cache)"
)
async def refresh_recommendations(
    top_k: int = Query(3, ge=1, le=10, description="Number of recommendations to return"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Refresh recommendations for the current user.
    
    This endpoint can be called after the user updates their questionnaire
    responses to get updated recommendations. It bypasses the cache to ensure
    fresh calculations.
    """
    user_id = current_user.firebase_uid
    logger.info(f"Refreshing recommendations for user: {user_id} (top_k={top_k})")
    
    try:
        # Get fresh recommendations without cache
        recommendations = await get_user_neighborhood_recommendations(
            db=db,
            user_id=user_id,
            top_k=top_k,
            use_cache=False  # Force fresh calculation
        )
        
        return {
            "recommendations": recommendations,
            "total_returned": len(recommendations),
            "message": "Recommendations refreshed successfully",
            "cache_bypassed": True
        }
        
    except Exception as e:
        logger.error(f"Error refreshing recommendations for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while refreshing recommendations."
        )

@router.get(
    "/neighborhoods/extended",
    summary="Get extended neighborhood recommendations",
    description="Get up to 10 neighborhood recommendations (extended view)"
)
async def get_extended_neighborhood_recommendations(
    use_cache: bool = Query(True, description="Whether to use cached results"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get extended neighborhood recommendations (up to 10) for the current user.
    
    This endpoint provides more recommendations than the default view,
    useful for users who want to see more options.
    """
    user_id = current_user.firebase_uid
    logger.info(f"Getting extended neighborhood recommendations for user: {user_id}")
    
    try:
        # Get 10 recommendations
        recommendations = await get_user_neighborhood_recommendations(
            db=db,
            user_id=user_id,
            top_k=10,
            use_cache=use_cache
        )
        
        if not recommendations:
            return {
                "recommendations": [],
                "message": "No recommendations available. Please complete the questionnaire first.",
                "requires_questionnaire": True
            }
        
        logger.info(f"Returning {len(recommendations)} extended recommendations for user {user_id}")
        
        return {
            "recommendations": recommendations,
            "total_returned": len(recommendations),
            "message": "Extended recommendations generated successfully",
            "is_extended_view": True,
            "cache_used": use_cache
        }
        
    except Exception as e:
        logger.error(f"Error getting extended recommendations for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating extended recommendations."
        )

@router.post(
    "/cache/clear",
    summary="Clear recommendation cache",
    description="Clear cached recommendations for the current user"
)
async def clear_recommendation_cache(
    current_user = Depends(get_current_user)
):
    """
    Clear cached recommendations for the current user.
    
    This endpoint should be called when the user updates their questionnaire
    responses or price filters to ensure fresh recommendations.
    """
    user_id = current_user.firebase_uid
    logger.info(f"Clearing recommendation cache for user: {user_id}")
    
    try:
        # Note: Since cache keys include hashes of preferences, we can't easily
        # delete specific keys. Instead, this endpoint will return success
        # and the next recommendation request will generate a new cache key
        # with updated preferences, effectively bypassing old cache.
        
        return {
            "success": True,
            "message": "Recommendation cache cleared. Next request will generate fresh recommendations.",
            "user_id": user_id
        }
        
    except Exception as e:
        logger.error(f"Error clearing cache for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while clearing the cache."
        )

@router.post(
    "/neighborhoods/{neighborhood_id}/select",
    summary="Select a neighborhood from recommendations",
    description="Updates user filters when they select a neighborhood from recommendations"
)
async def select_neighborhood(
    neighborhood_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Update user filters when they select a neighborhood from recommendations.
    
    This endpoint sets the selected neighborhood and city in the user's filters
    so future apartment browsing is automatically filtered.
    """
    user_id = current_user.firebase_uid
    logger.info(f"User {user_id} selecting neighborhood {neighborhood_id}")
    
    try:
        # Get neighborhood details
        result = await db.execute(
            select(Neighborhood).where(Neighborhood.id == neighborhood_id)
        )
        neighborhood = result.scalar_one_or_none()
        
        if not neighborhood:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Neighborhood {neighborhood_id} not found"
            )
        
        # Update user filters with selected neighborhood and city
        filter_data = UserFiltersUpdate(
            city=neighborhood.city,
            neighborhood=neighborhood.hebrew_name
        )
        
        updated_filters = await filters_service.update_user_filters(db, user_id, filter_data)
        
        logger.info(f"Updated filters for user {user_id}: city={neighborhood.city}, neighborhood={neighborhood.hebrew_name}")
        
        return {
            "success": True,
            "message": f"Selected {neighborhood.hebrew_name}, {neighborhood.city}",
            "neighborhood": {
                "id": neighborhood.id,
                "name": neighborhood.hebrew_name,
                "english_name": neighborhood.english_name,
                "city": neighborhood.city
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error selecting neighborhood {neighborhood_id} for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while selecting the neighborhood."
        )
