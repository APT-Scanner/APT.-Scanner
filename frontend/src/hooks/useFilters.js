import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from './useAuth';
import { BACKEND_URL } from '../config/constants';

const defaultFilters = {
    type: 'rent', // 'rent' or 'sale'
    city: '',
    neighborhood: '',
    priceMin: 500,
    priceMax: 15000,
    roomsMin: 1,
    roomsMax: 8,
    sizeMin: 10,
    sizeMax: 500,
    options: [] // For additional options like 'elevator', 'parking', etc.
};
  
export const useFilters = () => {
    const { user, idToken } = useAuth();
    // userId serves as the primary key for filter storage
    const userId = user?.uid || null;

    // Create a ref to store filterParams to avoid recreating it on every render
    const filterParamsRef = useRef(null);
    const [filters, setFilters] = useState(defaultFilters);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Load filters for the user (from backend or localStorage as fallback)
    const loadFilters = useCallback(async () => {
        if (!userId) {
            setFilters(defaultFilters);
            setLoading(false);
            return;
        }

        setLoading(true);
        setError(null);

        try {
            // TODO: Replace with actual backend call when implemented
            // This would be the place to load filters from backend using userId as primary key
            /*
            if (idToken) {
                const response = await fetch(`${BACKEND_URL}/filters/${userId}`, {
                    method: 'GET',
                    headers: {
                        'Authorization': `Bearer ${idToken}`,
                        'Content-Type': 'application/json',
                    },
                });
                
                if (response.ok) {
                    const data = await response.json();
                    setFilters(data);
                    setLoading(false);
                    return;
                }
            }
            */

            // Fallback to localStorage if backend call fails or not implemented
            const storageKey = `apartmentFilters-${userId}`;
            const savedFilters = localStorage.getItem(storageKey);
            if (savedFilters) {
                setFilters(JSON.parse(savedFilters));
            } else {
                setFilters(defaultFilters);
            }
        } catch (error) {
            console.error('Error loading filters:', error);
            setError('Failed to load filters');
            setFilters(defaultFilters);
        } finally {
            setLoading(false);
        }
    }, [userId]);

    // Save filters for the user (to backend and localStorage as fallback)
    const saveFilters = useCallback(async (filtersToSave) => {
        if (!userId) return;

        try {
            // TODO: Replace with actual backend call when implemented
            // This would be the place to save filters to backend using userId as primary key
            /*
            if (idToken) {
                await fetch(`${BACKEND_URL}/filters/${userId}`, {
                    method: 'PUT',
                    headers: {
                        'Authorization': `Bearer ${idToken}`,
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(filtersToSave),
                });
            }
            */

            // Save to localStorage as fallback
            const storageKey = `apartmentFilters-${userId}`;
            localStorage.setItem(storageKey, JSON.stringify(filtersToSave));
            
            // Invalidate cached params when filters change
            filterParamsRef.current = null;
        } catch (error) {
            console.error('Error saving filters:', error);
            setError('Failed to save filters');
        }
    }, [userId]);

    // Load filters on component mount or when user changes
    useEffect(() => {
        loadFilters();
    }, [userId, loadFilters]);

    // Update filter function
    const updateFilter = useCallback((newFilter) => {
        setFilters((prev) => {
            const updated = { ...prev, ...newFilter };
            saveFilters(updated);
            return updated;
        });
    }, [saveFilters]);

    // Reset filters
    const resetFilters = useCallback(() => {
        setFilters(defaultFilters);
        
        if (userId) {
            // TODO: Add backend reset call when implemented
            /*
            if (idToken) {
                fetch(`${BACKEND_URL}/filters/${userId}`, {
                    method: 'DELETE',
                    headers: {
                        'Authorization': `Bearer ${idToken}`,
                    },
                });
            }
            */
            
            // Remove from localStorage
            const storageKey = `apartmentFilters-${userId}`;
            localStorage.removeItem(storageKey);
        }
        
        filterParamsRef.current = null;
    }, [userId]);

    // Convert filters to query parameters
    const getFilterQueryParams = useCallback(() => {
        // Use cached params if available
        if (filterParamsRef.current) {
            return filterParamsRef.current;
        }

        const queryParams = new URLSearchParams();

        // Add user_id as primary key for backend filtering
        if (userId) queryParams.append('user_id', userId);
        
        if (filters.type) queryParams.append('type', filters.type);
        if (filters.city) queryParams.append('city', filters.city);
        if (filters.neighborhood) queryParams.append('neighborhood', filters.neighborhood);
        
        queryParams.append('price_min', filters.priceMin.toString());
        queryParams.append('price_max', filters.priceMax.toString());

        queryParams.append('rooms_min', filters.roomsMin.toString());
        queryParams.append('rooms_max', filters.roomsMax.toString());

        queryParams.append('size_min', filters.sizeMin.toString());
        queryParams.append('size_max', filters.sizeMax.toString());
        
        if (filters.options && filters.options.length > 0) {
            queryParams.append('options', filters.options.join(','));
        }

        // Cache the params
        filterParamsRef.current = queryParams;

        return queryParams;
    }, [filters, userId]);
    
    return { 
        filters, 
        updateFilter, 
        resetFilters, 
        getFilterQueryParams,
        loading,
        error
    };
};
    
    