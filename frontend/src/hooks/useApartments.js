import {useState, useEffect} from 'react';
import { useAuth } from './useAuth';
import { BACKEND_URL } from '../config/constants';

export const useApartments = (options = {}) => {
    const [apartments, setApartments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const { idToken, loading: authLoading } = useAuth();
    
    // Default options
    const { filterViewed = true } = options;

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

        const fetchApartments = async () => {
            setLoading(true);
            setError(null);
            try {
                // Add filter_viewed query parameter
                const url = new URL(`${BACKEND_URL}/listings/all`);
                url.searchParams.append('filter_viewed', filterViewed);
                
                const response = await fetch(url.toString(), {
                    method: 'GET',
                    headers: {
                        'Authorization': `Bearer ${idToken}`,
                        'Content-Type': 'application/json',
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
    }, [idToken, authLoading, filterViewed]);
    
    return { apartments, loading, error };    
};
   


