import {useState, useEffect} from 'react';
import { useAuth } from './useAuth';
import { BACKEND_URL } from '../config/constants';

export const useApartment = (listing_id) => {
    const [apartment, setApartment] = useState(null);
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
            setApartment(null);
            return;
        }

        const fetchApartment = async () => {
            setLoading(true);
            setError(null);
            try {
                const response = await fetch(`${BACKEND_URL}/listings/${listing_id}`, {
                    method: 'GET',
                    headers: {
                        'Authorization': `Bearer ${idToken}`,
                        'Content-Type': 'application/json',
                    },
                })

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: `HTTP error! status: ${response.status}` }));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            setApartment(data);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchApartment();
    }, [idToken, listing_id, authLoading]);

    return { apartment, loading, error };
};
        
