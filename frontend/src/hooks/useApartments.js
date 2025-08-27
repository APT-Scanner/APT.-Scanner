import { useState, useEffect, useRef } from 'react';
import { useAuth } from './useAuth';

export const useApartments = (options = {}) => {
    const [apartments, setApartments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const { idToken, loading: authLoading } = useAuth();
    
    // Create a ref to store the current filterParams string representation
    // to avoid unnecessary re-fetches
    const lastFilterParamsRef = useRef('');
    
    // Default options
    const { 
        filterViewed = true,
        filterParams = null,
        refreshTrigger = 0,  // Can be incremented to force a refresh
        filtersReady = true  // Whether filters are fully loaded and ready
    } = options;

    useEffect(() => {
        if (authLoading) {
            return; 
        }

        if (!idToken) {
             setLoading(false);
             setError("User not authenticated.");
             setApartments([]);
             return;
         }

        // Don't fetch apartments until filters are ready
        if (!filtersReady) {
            setLoading(true);
            return;
        }
        
        // Convert filterParams to string for comparison
        let currentFilterParamsString = '';
        try {
            if (filterParams) {
                currentFilterParamsString = filterParams.toString();
            }
        } catch (e) {
            console.error("Error converting filterParams to string:", e);
        }
        
        // Don't refetch if filter params haven't changed and it's not forced via refreshTrigger
        if (
            lastFilterParamsRef.current === currentFilterParamsString && 
            lastFilterParamsRef.current !== '' &&
            refreshTrigger === 0
        ) {
            return;
        }
        
        // Store the current filter params for future comparison
        lastFilterParamsRef.current = currentFilterParamsString;

        const fetchApartments = async () => {
            setLoading(true);
            setError(null);
            try {
                // Base URL
                const baseUrl = import.meta.env.VITE_API_URL || window.location.origin;
                const url = new URL(`/api/v1/listings/`, baseUrl);
                
                // Add filter_viewed query parameter
                url.searchParams.append('filter_viewed', filterViewed);
                
                // Add any additional filter parameters from useFilters
                if (filterParams) {
                    filterParams.forEach((value, key) => {
                        url.searchParams.append(key, value);
                    });
                }
                
                console.log("🏠 Fetching apartments with URL:", url.toString());
                console.log("🔍 Filter params being sent:", {
                    filterViewed,
                    filterParams: filterParams ? Array.from(filterParams.entries()) : null
                });
                
                const response = await fetch(url.toString(), {
                    method: 'GET',
                    headers: {
                        'Authorization': `Bearer ${idToken}`,
                    },
                });
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({ detail: `HTTP error! status: ${response.status}` }));
                    throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                setApartments(Array.isArray(data) ? data : []);
            } catch (err) {
                console.error("Failed to fetch apartments:", err);
                setError(err.message || 'Failed to load apartments.');
                setApartments([]);
            }
            finally {
                setLoading(false);
            }
        };
        fetchApartments();
    }, [idToken, authLoading, filterViewed, filterParams, refreshTrigger, filtersReady]);
    
    return { apartments, loading, error };    
};
   


