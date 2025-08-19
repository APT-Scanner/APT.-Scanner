import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from './useAuth';
import { BACKEND_URL } from '../config/constants';

const defaultFilters = {
    type: 'rent', // 'rent' or 'sale'
    city: '',
    neighborhood: '',
    propertyType: '',
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

    // Initialize state with the initial filters
    const [filters, setFilters] = useState(defaultFilters);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Load filters for the user (from backend or as fallback to localStorage)
    const loadFilters = useCallback(async () => {
        if (!userId || !idToken) {
            setLoading(false);
            return;
        }

        try {
            // Try to load from backend first
            const response = await fetch(`${BACKEND_URL}/filters/`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${idToken}`,
                    'Content-Type': 'application/json',
                },
            });

            if (response.ok) {
                const backendFilters = await response.json();
                // Convert backend format to frontend format
                const frontendFilters = {
                    type: backendFilters.type || defaultFilters.type,
                    city: backendFilters.city || defaultFilters.city,
                    neighborhood: backendFilters.neighborhood || defaultFilters.neighborhood,
                    propertyType: backendFilters.property_type || defaultFilters.propertyType,
                    priceMin: backendFilters.price_min || defaultFilters.priceMin,
                    priceMax: backendFilters.price_max || defaultFilters.priceMax,
                    roomsMin: backendFilters.rooms_min || defaultFilters.roomsMin,
                    roomsMax: backendFilters.rooms_max || defaultFilters.roomsMax,
                    sizeMin: backendFilters.size_min || defaultFilters.sizeMin,
                    sizeMax: backendFilters.size_max || defaultFilters.sizeMax,
                    options: backendFilters.options 
                        ? (typeof backendFilters.options === 'string' 
                            ? backendFilters.options.split(',').filter(Boolean)
                            : backendFilters.options)
                        : defaultFilters.options
                };
                setFilters(frontendFilters);
                console.log('Loaded filters from backend:', frontendFilters);
            } else {
                // Fallback to localStorage
                const storageKey = `apartmentFilters-${userId}`;
                const saved = localStorage.getItem(storageKey);
                if (saved) {
                    const parsed = JSON.parse(saved);
                    setFilters(parsed);
                    console.log('Loaded filters from localStorage:', parsed);
                }
            }
        } catch (err) {
            console.error('Error loading filters:', err);
            setError('Failed to load filters');
            
            // Fallback to localStorage
            const storageKey = `apartmentFilters-${userId}`;
            const saved = localStorage.getItem(storageKey);
            if (saved) {
                try {
                    const parsed = JSON.parse(saved);
                    setFilters(parsed);
                } catch (parseErr) {
                    console.error('Error parsing localStorage filters:', parseErr);
                    setFilters(defaultFilters);
                }
            } else {
                setFilters(defaultFilters);
            }
        } finally {
            setLoading(false);
        }
    }, [userId, idToken]);

    // Save filters for the user (to backend and localStorage as fallback)
    const saveFilters = useCallback(async (filtersToSave) => {
        if (!userId || !idToken) return;

        try {
            // Convert frontend format to backend format
            const backendFilters = {
                type: filtersToSave.type,
                city: filtersToSave.city,
                neighborhood: filtersToSave.neighborhood,
                property_type: filtersToSave.propertyType,
                price_min: filtersToSave.priceMin,
                price_max: filtersToSave.priceMax,
                rooms_min: filtersToSave.roomsMin,
                rooms_max: filtersToSave.roomsMax,
                size_min: filtersToSave.sizeMin,
                size_max: filtersToSave.sizeMax,
                options: Array.isArray(filtersToSave.options) 
                    ? filtersToSave.options.join(',')
                    : filtersToSave.options
            };

            // Try to save to backend first
            const response = await fetch(`${BACKEND_URL}/filters/`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${idToken}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(backendFilters),
            });

            if (response.ok) {
                console.log('Filters saved to backend successfully');
            } else {
                console.warn('Failed to save filters to backend, using localStorage fallback');
            }
        } catch (err) {
            console.error('Error saving filters to backend:', err);
        }

        try {
            // Always save to localStorage as fallback
            const storageKey = `apartmentFilters-${userId}`;
            localStorage.setItem(storageKey, JSON.stringify(filtersToSave));
            // Invalidate cached params when filters change
            filterParamsRef.current = null;
        } catch (err) {
            console.error('Error saving filters to localStorage:', err);
            setError('Failed to save filters');
        }
    }, [userId, idToken]);

    // Load filters on component mount or when user changes
    useEffect(() => {
        if (userId && idToken) {
            setLoading(true);
            loadFilters();
        } else if (!userId) {
            setLoading(false);
        }
    }, [userId, idToken, loadFilters]);

    // Update filter function
    const updateFilter = useCallback((newFilter) => {
        setFilters((prev) => {
            const updated = { ...prev, ...newFilter };
            saveFilters(updated);
            // Invalidate cached params when filters change
            filterParamsRef.current = null;
            return updated;
        });
    }, [saveFilters]);

    // Reset filters
    const resetFilters = useCallback(() => {
        setFilters(defaultFilters);
        if (userId) {
            const storageKey = `apartmentFilters-${userId}`;
            localStorage.removeItem(storageKey);
        }
        filterParamsRef.current = null;
    }, [userId]);

    // Convert filters to query parameters
    const getFilterQueryParams = useCallback(() => {
        console.log('Generating filterParams with filters:', filters, 'loading:', loading);

        const queryParams = new URLSearchParams();

        // Add user_id as primary key for backend filtering
        if (userId) queryParams.append('user_id', userId);
        if (filters.type) queryParams.append('type', filters.type);
        if (filters.city) queryParams.append('city', filters.city);
        if (filters.neighborhood) queryParams.append('neighborhood', filters.neighborhood);
        queryParams.append('priceMin', filters.priceMin.toString());
        queryParams.append('priceMax', filters.priceMax.toString());
        queryParams.append('roomsMin', filters.roomsMin.toString());
        queryParams.append('roomsMax', filters.roomsMax.toString());
        queryParams.append('sizeMin', filters.sizeMin.toString());
        queryParams.append('sizeMax', filters.sizeMax.toString());
        if (filters.options && filters.options.length > 0) {
            const optionsString = Array.isArray(filters.options) 
                ? filters.options.join(',') 
                : filters.options;
            queryParams.append('options', optionsString);
        }

        return queryParams;
    }, [filters, userId, loading]);
    
    return { 
        filters, 
        updateFilter, 
        resetFilters, 
        getFilterQueryParams,
        loading,
        error
    };
};
    
    