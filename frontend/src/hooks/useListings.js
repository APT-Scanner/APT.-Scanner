// src/hooks/useListings.js
import { useState, useCallback } from 'react';
import { useAuth } from './useAuth';
import { BACKEND_URL } from '../config/constants';

export const useListings = () => {
    const [listings, setListings] = useState({});
    const [loading, setLoading] = useState({});
    const [error, setError] = useState({});
    const { idToken } = useAuth();

    // Function to get a single listing by ID
    const getListing = useCallback(async (listingId) => {
        if (!idToken || !listingId) return null;
        
        // Set loading state for this specific listing
        setLoading(prev => ({ ...prev, [listingId]: true }));
        setError(prev => ({ ...prev, [listingId]: null }));
        
        try {
            const response = await fetch(`${BACKEND_URL}/listings/${listingId}`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${idToken}`,
                    'Content-Type': 'application/json',
                },
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ 
                    detail: `HTTP error! status: ${response.status}` 
                }));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            setListings(prev => ({ ...prev, [listingId]: data }));
            setLoading(prev => ({ ...prev, [listingId]: false }));
            return data;
        } catch (err) {
            console.error(`Failed to fetch listing ${listingId}:`, err);
            setError(prev => ({ ...prev, [listingId]: err.message || 'Failed to load listing' }));
            setLoading(prev => ({ ...prev, [listingId]: false }));
            return null;
        }
    }, [idToken]);

    return {
        listings,
        loading,
        error,
        getListing
    };
};