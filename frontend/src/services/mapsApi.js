import { BACKEND_URL } from '../config/constants';

/**
 * Fetch place suggestions from Google Maps Places API via secure backend proxy
 * @param {string} input - The input text to search for
 * @param {string} types - Place types to search for (default: 'geocode,establishment')
 * @returns {Promise<Array>} Array of place predictions
 */
export const fetchPlaceSuggestions = async (input) => {
    try {
        // Validate input
        if (!input || input.trim().length < 1) {
            throw new Error('Input must be at least 1 character long');
        }

        const params = new URLSearchParams({
            input: input.trim(),
            components: 'country:IL'
        });

        const response = await fetch(`${BACKEND_URL}/maps/places/autocomplete?${params}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.status !== 'OK' && data.status !== 'ZERO_RESULTS') {
            const errorMsg = data.error_message || data.status;
            throw new Error(`Google Maps API error: ${errorMsg}`);
        }
        
        return data.predictions || [];
    } catch (error) {
        console.error('Error fetching place suggestions:', error);
        throw error;
    }
};

/**
 * Fetch detailed information about a specific place via secure backend proxy
 * @param {string} placeId - Google Place ID
 * @returns {Promise<Object>} Place details object
 */
export const fetchPlaceDetails = async (placeId) => {
    try {
        const params = new URLSearchParams({
            place_id: placeId
        });

        const response = await fetch(`${BACKEND_URL}/v1/maps/places/details?${params}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.status !== 'OK') {
            throw new Error(`Google Maps API error: ${data.status}`);
        }
        
        return data;
    } catch (error) {
        console.error('Error fetching place details:', error);
        throw error;
    }
}; 