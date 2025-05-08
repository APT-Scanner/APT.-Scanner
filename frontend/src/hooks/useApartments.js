import {useState, useEffect} from 'react';
import { useAuth } from './useAuth';
import { BACKEND_URL } from '../config/constants';

export const useApartments = () => {
    const [apartments, setApartments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const { idToken, loading: authLoading } = useAuth();

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
                const response = await fetch(`${BACKEND_URL}/listings/all`,{
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
    }, [idToken, authLoading]);
    
    return { apartments, loading, error };    
};
   


