from fastapi import APIRouter, HTTPException, Query
import requests
import logging
from src.config.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/places/autocomplete")
async def places_autocomplete(
    input: str = Query(..., description="The text input for place search"),
):
    """
    Secure Google Maps Places Autocomplete API proxy endpoint.
    This endpoint handles Google Maps API calls server-side to keep the API key secure.
    """
    if not settings.GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="Google Maps API key not configured")
    
    # Validate input
    if not input or len(input.strip()) < 1:
        raise HTTPException(status_code=400, detail="Input parameter must be at least 1 character long")
    
    try:
        url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
        params = {
            "input": input.strip(),
            "key": settings.GOOGLE_API_KEY,
            "components": "country:IL"
        }
        
        logger.info(f"Making Google Maps API request with params: {params}")
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"Google Maps API response status: {data.get('status')}")
        if data.get('status') not in ['OK', 'ZERO_RESULTS']:
            logger.error(f"Google Maps API error: {data.get('status')} - {data.get('error_message', 'No error message')}")
            # Return the actual error from Google Maps API
            return {
                "predictions": [],
                "status": data.get('status'),
                "error_message": data.get('error_message', 'Unknown error')
            }
        
        # Transform the response to include only necessary field 
        predictions = []
        for prediction in data.get("predictions", []):
            predictions.append({
                "description": prediction.get("description"),
                "place_id": prediction.get("place_id"),
                "structured_formatting": prediction.get("structured_formatting", {}),
            })
        
        return {
            "predictions": predictions,
            "status": data.get("status")
        }
        
    except requests.RequestException as e:
        logger.error(f"Google Maps API request failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch places from Google Maps API")
    except Exception as e:
        logger.error(f"Unexpected error in places autocomplete: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/places/details")
async def place_details(
    place_id: str = Query(..., description="Google Place ID")
):
    """
    Secure Google Maps Place Details API proxy endpoint.
    Fetches detailed information about a specific place.
    """
    if not settings.GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="Google Maps API key not configured")
    
    try:
        url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "place_id": place_id,
            "key": settings.GOOGLE_API_KEY,
            "fields": "name,formatted_address,geometry,place_id"
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("status") == "OK":
            result = data.get("result", {})
            return {
                "name": result.get("name"),
                "formatted_address": result.get("formatted_address"),
                "geometry": result.get("geometry"),
                "place_id": result.get("place_id"),
                "status": data.get("status")
            }
        else:
            raise HTTPException(status_code=400, detail=f"Google Maps API error: {data.get('status')}")
        
    except requests.RequestException as e:
        logger.error(f"Google Maps API request failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch place details from Google Maps API")
    except Exception as e:
        logger.error(f"Unexpected error in place details: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") 