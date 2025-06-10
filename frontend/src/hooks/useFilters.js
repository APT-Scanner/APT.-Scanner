import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from './useAuth';

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
    const { user } = useAuth();
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
        const storageKey = `apartmentFilters-${userId}`;
        const saved = localStorage.getItem(storageKey);
        if (!saved) {
            // No saved filters; mark load complete and stop
            setLoading(false);
            return;
        }

        try {
            const parsed = JSON.parse(saved);
            // Only update if parsed filters differ from current filters
            if (JSON.stringify(parsed) !== JSON.stringify(filters)) {
                setFilters(parsed);
            }
        } catch (err) {
            console.error('Error loading filters:', err);
            setError('Failed to load filters');
            setFilters(defaultFilters);
        } finally {
            setLoading(false);
        }
    }, [userId, filters]);

    // Save filters for the user (to backend and localStorage as fallback)
    const saveFilters = useCallback(async (filtersToSave) => {
        if (!userId) return;

        try {
            // Implement backend saving here if needed
            const storageKey = `apartmentFilters-${userId}`;
            localStorage.setItem(storageKey, JSON.stringify(filtersToSave));
            // Invalidate cached params when filters change
            filterParamsRef.current = null;
        } catch (err) {
            console.error('Error saving filters:', err);
            setError('Failed to save filters');
        }
    }, [userId]);

    // Load filters on component mount or when user changes
    useEffect(() => {
        if (userId) {
            setLoading(true);
            loadFilters();
        }
    }, [userId, loadFilters]);

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
        queryParams.append('price_min', filters.priceMin.toString());
        queryParams.append('price_max', filters.priceMax.toString());
        queryParams.append('rooms_min', filters.roomsMin.toString());
        queryParams.append('rooms_max', filters.roomsMax.toString());
        queryParams.append('size_min', filters.sizeMin.toString());
        queryParams.append('size_max', filters.sizeMax.toString());
        if (filters.options && filters.options.length > 0) {
            queryParams.append('options', filters.options.join(','));
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
    
    