import { useState, useEffect, useCallback, useRef } from 'react';

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
    // Initialize from localStorage if available
    const [filters, setFilters] = useState(() => {
        try{
            const savedFilters = localStorage.getItem('apartmentFilters');
            return savedFilters ? JSON.parse(savedFilters) : defaultFilters;
        } catch (error) {
            console.error('Error loading filters from localStorage:', error);
            return defaultFilters;
        }
    });

    // Create a ref to store filterParams to avoid recreating it on every render
    const filterParamsRef = useRef(null);

    // Save filters to localStorage whenever they change
    useEffect(() => {
        try {
        localStorage.setItem('apartmentFilters', JSON.stringify(filters));
            // Invalidate cached params when filters change
            filterParamsRef.current = null;
        } catch (error) {
            console.error('Error saving filters to localStorage:', error);
        }
    }, [filters]);

    const updateFilter = useCallback((newFilter) => {
        setFilters((prev) => ({ ...prev, ...newFilter }));
    }, []);

    const resetFilters = useCallback(() => {
        setFilters(defaultFilters);
        localStorage.removeItem('apartmentFilters');
        filterParamsRef.current = null;
    }, []);

    const getFilterQueryParams = useCallback(() => {
        // Use cached params if available
        if (filterParamsRef.current) {
            return filterParamsRef.current;
        }

        const queryParams = new URLSearchParams();

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
    }, [filters]);
    
    return { filters, updateFilter, resetFilters, getFilterQueryParams };
};
    
    