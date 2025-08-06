from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from src.database.postgresql_db import get_db
from src.middleware.auth import get_current_user
from src.services.recommendation_service import get_user_neighborhood_recommendations

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
    description="Refresh recommendations after questionnaire updates"
)
async def refresh_recommendations(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Refresh recommendations for the current user.
    
    This endpoint can be called after the user updates their questionnaire
    responses to get updated recommendations.
    """
    user_id = current_user.firebase_uid
    logger.info(f"Refreshing recommendations for user: {user_id}")
    
    try:
        # Get fresh recommendations
        recommendations = await get_user_neighborhood_recommendations(
            db=db,
            user_id=user_id,
            top_k=3
        )
        
        return {
            "recommendations": recommendations,
            "total_returned": len(recommendations),
            "message": "Recommendations refreshed successfully"
        }
        
    except Exception as e:
        logger.error(f"Error refreshing recommendations for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while refreshing recommendations."
        )
