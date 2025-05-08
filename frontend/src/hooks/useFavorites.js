import { useState, useEffect, useCallback } from 'react';
import { useAuth } from './useAuth';
import { BACKEND_URL } from '../config/constants';

export const useFavorites = () => {
    const [favorites, setFavorites] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const { idToken, loading: authLoading } = useAuth();

    const fetchFavorites = useCallback(async () => {
        if (!idToken) return;
        
        setLoading(true);
        setError(null);
        
        try {
            const response = await fetch(`${BACKEND_URL}/favorites/`, {
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
            setFavorites(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error("Failed to fetch favorites:", err);
            setError(err.message || 'Failed to load favorites');
            setFavorites([]);
        } finally {
            setLoading(false);
        }
    }, [idToken]);

    const addFavorite = async (listingId) => {
        if (!idToken) return null;

        const payload = { listing_id: listingId };
        console.log("Sending favorite payload:", payload);
        
        try {
            const response = await fetch(`${BACKEND_URL}/favorites/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${idToken}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ listing_id: listingId }),
            });

            console.log("Response status:", response.status);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: `HTTP error! status: ${response.status}` }));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            
            const newFavorite = await response.json();
            
            setFavorites(prev => [...prev, newFavorite]);
            return newFavorite;
        } catch (err) {
            console.error("Failed to add favorite:", err);
            setError(err.message || 'Failed to add favorite');
            return null;
        }
    };

    const removeFavorite = async (listingId) => {
        if (!idToken) return false;
        
        try {
            const response = await fetch(`${BACKEND_URL}/favorites/${listingId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${idToken}`,
                    'Content-Type': 'application/json',
                },
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: `HTTP error! status: ${response.status}` }));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            
            setFavorites(prev => prev.filter(fav => fav.listing_id !== listingId));
            return true;
        } catch (err) {
            console.error("Failed to remove favorite:", err);
            setError(err.message || 'Failed to remove favorite');
            return false;
        }
    };

    useEffect(() => {
        if (authLoading) return;
        
        if (idToken) {
            fetchFavorites();
        } else {
            setFavorites([]);
            setLoading(false);
        }
    }, [idToken, authLoading, fetchFavorites]);


    return { 
        favorites, 
        loading, 
        error, 
        addFavorite, 
        removeFavorite, 
        refresh: fetchFavorites
    };
};
