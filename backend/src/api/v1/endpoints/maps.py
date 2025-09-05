from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import requests
import logging
import json
from datetime import datetime, timedelta
from src.config.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)

def get_monday_noon_reference_time() -> str:
    """
    Get the next Monday at 12:00 PM as a consistent reference time for travel calculations.
    This ensures travel time calculations are consistent across requests.
    
    Returns:
        str: ISO formatted datetime string for the next Monday at 12:00 PM
    """
    now = datetime.now()
    # Calculate days until next Monday (0 = Monday, 6 = Sunday)
    days_until_monday = (7 - now.weekday()) % 7
    if days_until_monday == 0:
        # If today is Monday, use next Monday to avoid past times
        days_until_monday = 7
    
    next_monday = now + timedelta(days=days_until_monday)
    monday_noon = next_monday.replace(hour=12, minute=0, second=0, microsecond=0)
    
    return monday_noon.strftime("%Y-%m-%dT%H:%M:%SZ")

class DistanceMatrixRequest(BaseModel):
    origins: List[Dict[str, float]] = Field(..., description="List of origin coordinates with lat and lng")
    destinations: List[str] = Field(..., description="List of destination place IDs")
    mode: str = Field("driving", description="Travel mode: driving, walking, bicycling, transit")

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

@router.post("/distance-matrix")
async def distance_matrix(request: DistanceMatrixRequest):
    """
    Secure Google Routes API proxy endpoint (computeRouteMatrix).
    Calculates travel times between neighborhoods (origins) and user POIs (destinations).
    Uses the new Routes API which replaces the legacy Distance Matrix API.
    """
    if not settings.GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="Google Maps API key not configured")
    
    # Validate inputs
    if not request.origins or not request.destinations:
        raise HTTPException(status_code=400, detail="Origins and destinations are required")
    
    if len(request.origins) > 25 or len(request.destinations) > 25:
        raise HTTPException(status_code=400, detail="Maximum 25 origins and 25 destinations allowed")
    
    if request.mode not in ['driving', 'walking', 'bicycling', 'transit']:
        raise HTTPException(status_code=400, detail="Invalid travel mode. Must be: driving, walking, bicycling, or transit")
    
    try:
        # Convert travel mode to Routes API format
        travel_mode_map = {
            'driving': 'DRIVE',
            'walking': 'WALK',
            'bicycling': 'BICYCLE',
            'transit': 'TRANSIT'
        }
        routes_mode = travel_mode_map.get(request.mode, 'DRIVE')
        
        # Prepare waypoints for Routes API v2 (correct format)
        origin_waypoints = []
        for origin in request.origins:
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
        for dest_place_id in request.destinations:
            destination_waypoints.append({
                "waypoint": {
                    "placeId": dest_place_id
                }
            })
        
        # Get consistent reference time for all travel calculations
        reference_time = get_monday_noon_reference_time()
        
        # Prepare request body for Routes API v2
        request_body = {
            "origins": origin_waypoints,
            "destinations": destination_waypoints,
            "travelMode": routes_mode,
            "units": "METRIC",
            "departureTime": reference_time  # Set consistent reference time for all modes
        }
        
        # Set routing preference based on travel mode
        if routes_mode == "TRANSIT":
            request_body["transitPreferences"] = {
                "allowedTravelModes": ["BUS", "SUBWAY", "TRAIN", "LIGHT_RAIL"],
                "routingPreference": "FEWER_TRANSFERS"
            }
        else:
            request_body["routingPreference"] = "TRAFFIC_AWARE_OPTIMAL"
        
        # Routes API endpoint
        url = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
        
        headers = {
            "X-Goog-Api-Key": settings.GOOGLE_API_KEY,
            "X-Goog-FieldMask": "originIndex,destinationIndex,status,condition,distanceMeters,duration",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Making Routes API request with {len(request.origins)} origins and {len(request.destinations)} destinations")
        logger.debug(f"Request body: {json.dumps(request_body, indent=2)}")
        
        response = requests.post(url, json=request_body, headers=headers)
        
        if response.status_code != 200:
            error_text = response.text
            logger.error(f"Google Routes API error {response.status_code}: {error_text}")
            raise HTTPException(
                status_code=400,
                detail=f"Google Routes API error: {response.status_code}"
            )
        
        data = response.json()
        logger.info(f"Routes API response received successfully")
        logger.debug(f"Response data: {json.dumps(data, indent=2)}")
        
        # Convert Routes API response to Distance Matrix format for compatibility
        logger.debug(f"Converting Routes API response structure: {type(data)} with keys: {data.keys() if isinstance(data, dict) else 'array'}")
        converted_response = _convert_routes_to_distance_matrix_format(data, request.origins, request.destinations)
        logger.debug(f"Converted response status: {converted_response.get('status')}")
        
        if converted_response.get('status') != 'OK':
            logger.error(f"Routes API error: {converted_response.get('status')}")
            raise HTTPException(
                status_code=400, 
                detail=f"Google Routes API error: {converted_response.get('status')}"
            )
        
        return converted_response
        
    except requests.RequestException as e:
        logger.error(f"Routes API request failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch route matrix from Google Routes API")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in route matrix: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

def _convert_routes_to_distance_matrix_format(routes_response: dict, origins: list, destinations: list) -> dict:
    """
    Convert Routes API response format to Distance Matrix API format for compatibility.
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
                    logger.debug(f"Processing {len(elements_list)} route elements for origin {origin_idx}, dest {dest_idx}")
                    for route_element in elements_list:
                        if (route_element.get("originIndex") == origin_idx and 
                            route_element.get("destinationIndex") == dest_idx):
                            
                            logger.debug(f"Found match for origin {origin_idx}, dest {dest_idx}: {route_element}")
                            
                            # Routes API v2 uses condition and empty status object, not status="OK"
                            condition = route_element.get("condition")
                            has_valid_route = condition == "ROUTE_EXISTS"
                            logger.debug(f"Route condition: {condition}, valid: {has_valid_route}")
                            
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
                                
                                # Routes API sometimes returns duration=0s, treat as no valid route
                                if (duration_seconds is not None and duration_seconds > 0 and 
                                    distance_meters is not None and distance_meters > 0):
                                    element = {
                                        "status": "OK",
                                        "duration": {
                                            "text": f"{duration_seconds // 60} mins",
                                            "value": duration_seconds
                                        },
                                        "distance": {
                                            "text": f"{distance_meters / 1000:.1f} km",
                                            "value": distance_meters
                                        }
                                    }
                                else:
                                    element = {"status": "ZERO_RESULTS"}
                            else:
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