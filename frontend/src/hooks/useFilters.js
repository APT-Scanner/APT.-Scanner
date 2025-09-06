import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from './useAuth';
import API_BASE from '../config/api.js';

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

/**
 * Custom hook for managing apartment filters with race condition protection
 * 
 * Race condition prevention mechanisms:
 * - loadRequestToken: Ensures only the latest loadFilters response updates state
 * - saveVersionCounter: Prevents out-of-order saveFilters responses from overwriting newer data
 * - dirtyRef: Prevents late-arriving load responses from overriding user modifications
 * - debounceTimer: Reduces backend request spam when user changes filters rapidly
 */
export const useFilters = () => {
    const { user, idToken } = useAuth();
    // userId serves as the primary key for filter storage
    const userId = user?.uid || null;

    /**
     * Request token to prevent race conditions in loadFilters
     * Only responses with the current token can update state
     */
    const loadRequestTokenRef = useRef(0);
    
    /**
     * Sequential version counter for saveFilters operations
     * Only the highest version response is allowed to update state
     */
    const saveVersionRef = useRef(0);
    
    /**
     * Tracks whether user has modified filters after initial load
     * Prevents late load responses from overriding user changes
     */
    const dirtyRef = useRef(false);
    
    /**
     * Debounce timer for backend saves
     * Prevents spamming backend with rapid filter changes
     */
    const debounceTimerRef = useRef(null);

    /**
     * Cache for computed query parameters
     * Invalidated when filters change to force recalculation
     */
    const queryParamsCacheRef = useRef(null);

    // Initialize state with the initial filters
    const [filters, setFilters] = useState(defaultFilters);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    /**
     * Load filters for the user (from backend or as fallback to localStorage)
     * Uses request token to prevent race conditions where late responses override newer state
     */
    const loadFilters = useCallback(async () => {
        if (!userId || !idToken) {
            setLoading(false);
            return;
        }

        // Generate a new request token for this load operation
        const currentToken = ++loadRequestTokenRef.current;
        console.log(`🔄 Starting loadFilters with token ${currentToken}`);

        try {
            // Try to load from backend first
            const response = await fetch(`${API_BASE}/api/v1/filters/`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${idToken}`,
                    'Content-Type': 'application/json',
                },
            });

            // Check if this is still the latest request
            if (currentToken !== loadRequestTokenRef.current) {
                console.log(`🚫 Ignoring stale loadFilters response (token ${currentToken}, current: ${loadRequestTokenRef.current})`);
                return;
            }

            if (response.ok) {
                const backendFilters = await response.json();
                
                // Check token again after async operation
                if (currentToken !== loadRequestTokenRef.current) {
                    console.log(`🚫 Ignoring stale loadFilters data (token ${currentToken}, current: ${loadRequestTokenRef.current})`);
                    return;
                }

                // Don't override user changes with late-arriving load response
                if (dirtyRef.current) {
                    console.log('🚫 Ignoring load response - user has made changes (dirty state)');
                    return;
                }

                // Convert backend format to frontend format
                const frontendFilters = {
                    type: backendFilters.type || defaultFilters.type,
                    city: backendFilters.city || defaultFilters.city,
                    neighborhood: backendFilters.neighborhood || defaultFilters.neighborhood,
                    propertyType: backendFilters.property_type || defaultFilters.propertyType,
                    // Handle both backend format (price_min) and alias format (priceMin)
                    priceMin: backendFilters.priceMin || backendFilters.price_min || defaultFilters.priceMin,
                    priceMax: backendFilters.priceMax || backendFilters.price_max || defaultFilters.priceMax,
                    roomsMin: backendFilters.roomsMin || backendFilters.rooms_min || defaultFilters.roomsMin,
                    roomsMax: backendFilters.roomsMax || backendFilters.rooms_max || defaultFilters.roomsMax,
                    sizeMin: backendFilters.sizeMin || backendFilters.size_min || defaultFilters.sizeMin,
                    sizeMax: backendFilters.sizeMax || backendFilters.size_max || defaultFilters.sizeMax,
                    options: backendFilters.options 
                        ? (typeof backendFilters.options === 'string' 
                            ? backendFilters.options.split(',').filter(Boolean)
                            : backendFilters.options)
                        : defaultFilters.options
                };
                
                console.log('📨 Backend returned priceMax:', backendFilters.priceMax);
                console.log('🔄 Converted to frontend priceMax:', frontendFilters.priceMax);
                setFilters(frontendFilters);
                queryParamsCacheRef.current = null; // Invalidate cache
                console.log(`✓ Loaded filters from backend (token ${currentToken}):`, frontendFilters);
            } else {
                // Fallback to localStorage - but only if user hasn't made changes
                if (!dirtyRef.current) {
                    const storageKey = `apartmentFilters-${userId}`;
                    const saved = localStorage.getItem(storageKey);
                    if (saved) {
                        const parsed = JSON.parse(saved);
                        setFilters(parsed);
                        queryParamsCacheRef.current = null; // Invalidate cache
                        console.log(`✓ Loaded filters from localStorage (token ${currentToken}):`, parsed);
                    }
                }
            }
        } catch (err) {
            console.error('Error loading filters:', err);
            
            // Check token before setting error
            if (currentToken !== loadRequestTokenRef.current) {
                return;
            }
            
            setError('Failed to load filters');
            
            // Fallback to localStorage - but only if user hasn't made changes
            if (!dirtyRef.current) {
                const storageKey = `apartmentFilters-${userId}`;
                const saved = localStorage.getItem(storageKey);
                if (saved) {
                    try {
                        const parsed = JSON.parse(saved);
                        setFilters(parsed);
                        queryParamsCacheRef.current = null; // Invalidate cache
                    } catch (parseErr) {
                        console.error('Error parsing localStorage filters:', parseErr);
                        setFilters(defaultFilters);
                        queryParamsCacheRef.current = null; // Invalidate cache
                    }
                } else {
                    setFilters(defaultFilters);
                    queryParamsCacheRef.current = null; // Invalidate cache
                }
            }
        } finally {
            // Only update loading state for the latest request
            if (currentToken === loadRequestTokenRef.current) {
                setLoading(false);
            }
        }
    }, [userId, idToken]);

    /**
     * Save filters with debouncing and version control to prevent race conditions
     * - Immediate localStorage save for instant feedback
     * - Debounced backend saves to reduce API calls
     * - Version counter ensures only latest save result updates state
     */
    const debouncedBackendSave = useCallback(async (filtersToSave, saveVersion) => {
        if (!userId || !idToken) return;

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

        console.log(`💾 Saving to backend (version ${saveVersion}) - price_max:`, backendFilters.price_max);
        
        try {
            // Save to backend
            const response = await fetch(`${API_BASE}/api/v1/filters/`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${idToken}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(backendFilters),
            });

            // Only process response if this is still the latest save operation
            if (saveVersion >= saveVersionRef.current) {
                if (response.ok) {
                    console.log(`✓ Filters saved to backend successfully (version ${saveVersion})`);
                } else {
                    console.warn(`✗ Failed to save filters to backend (version ${saveVersion}), using localStorage fallback`);
                    console.log('Response status:', response.status);
                    const responseText = await response.text();
                    console.log('Response text:', responseText);
                }
            } else {
                console.log(`🚫 Ignoring stale backend save response (version ${saveVersion}, current: ${saveVersionRef.current})`);
            }
        } catch (err) {
            console.error(`Error saving filters to backend (version ${saveVersion}):`, err);
        }
    }, [userId, idToken]);

    /**
     * Save filters for the user (to backend and localStorage as fallback)
     * Implements immediate localStorage save and debounced backend saves
     */
    const saveFilters = useCallback(async (filtersToSave) => {
        if (!userId || !idToken) return;

        // Mark filters as dirty (user has made changes)
        dirtyRef.current = true;
        
        // Increment save version for race condition protection
        const saveVersion = ++saveVersionRef.current;
        console.log(`🔄 Starting saveFilters (version ${saveVersion})`);

        try {
            // Always save to localStorage immediately for instant feedback
            const storageKey = `apartmentFilters-${userId}`;
            localStorage.setItem(storageKey, JSON.stringify(filtersToSave));
            queryParamsCacheRef.current = null; // Invalidate cache
            console.log(`✓ Filters saved to localStorage (version ${saveVersion})`);
        } catch (err) {
            console.error('Error saving filters to localStorage:', err);
            setError('Failed to save filters');
        }

        // Debounce backend saves (300ms) to prevent API spam
        if (debounceTimerRef.current) {
            clearTimeout(debounceTimerRef.current);
        }
        
        debounceTimerRef.current = setTimeout(() => {
            debouncedBackendSave(filtersToSave, saveVersion);
        }, 300);

    }, [userId, idToken, debouncedBackendSave]);

    /**
     * Load filters on component mount or when user changes
     * Resets dirty state on new user to allow fresh loads
     */
    useEffect(() => {
        if (userId && idToken) {
            setLoading(true);
            dirtyRef.current = false; // Reset dirty state for new loads
            loadFilters();
        } else if (!userId) {
            setLoading(false);
            dirtyRef.current = false; // Reset dirty state when no user
        }
    }, [userId, idToken, loadFilters]);

    /**
     * Update filter function with race condition protection
     * Synchronously updates state and triggers debounced backend save
     */
    const updateFilter = useCallback((newFilter) => {
        console.log("🔄 updateFilter called - priceMax:", newFilter.priceMax);
        setFilters((prev) => {
            const updated = { ...prev, ...newFilter };
            console.log("✅ Updated filters - priceMax:", updated.priceMax);
            saveFilters(updated);
            queryParamsCacheRef.current = null; // Invalidate cache
            return updated;
        });
    }, [saveFilters]);

    /**
     * Async update filter function that resolves immediately after state update
     * Note: Does not wait for backend save due to debouncing - use for immediate UI feedback
     */
    const updateFilterAsync = useCallback(async (newFilter) => {
        console.log("🔄 updateFilterAsync called");
        return new Promise((resolve) => {
            setFilters((prev) => {
                const updated = { ...prev, ...newFilter };
                console.log("✅ Updated filters async");
                saveFilters(updated);
                queryParamsCacheRef.current = null; // Invalidate cache
                resolve(updated);
                return updated;
            });
        });
    }, [saveFilters]);

    /**
     * Reset filters to default values and clear stored data
     * Cancels any pending debounced saves
     */
    const resetFilters = useCallback(() => {
        // Cancel any pending saves
        if (debounceTimerRef.current) {
            clearTimeout(debounceTimerRef.current);
            debounceTimerRef.current = null;
        }
        
        // Reset state and mark as dirty
        setFilters(defaultFilters);
        dirtyRef.current = true;
        
        // Clear storage
        if (userId) {
            const storageKey = `apartmentFilters-${userId}`;
            localStorage.removeItem(storageKey);
        }
        
        // Invalidate cache and trigger save of reset filters
        queryParamsCacheRef.current = null;
        if (userId && idToken) {
            saveFilters(defaultFilters);
        }
    }, [userId, idToken, saveFilters]);

    /**
     * Convert filters to query parameters with caching for performance
     * Cache is invalidated whenever filters change to ensure fresh data
     */
    const getFilterQueryParams = useCallback(() => {
        // Return cached result if available
        if (queryParamsCacheRef.current) {
            console.log('🚀 Returning cached query params');
            return queryParamsCacheRef.current;
        }

        console.log('🔧 Generating filterParams with filters:', filters, 'loading:', loading);

        const queryParams = new URLSearchParams();

        // Add user_id as primary key for backend filtering
        if (userId) queryParams.append('user_id', userId);
        if (filters.type) queryParams.append('type', filters.type);
        if (filters.city) {
            console.log('📍 Adding city filter:', filters.city, 'type:', typeof filters.city);
            queryParams.append('city', filters.city);
        }
        if (filters.neighborhood) {
            console.log('🏘️ Adding neighborhood filter:', filters.neighborhood, 'type:', typeof filters.neighborhood);
            queryParams.append('neighborhood', filters.neighborhood);
        }
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

        // Cache the result
        queryParamsCacheRef.current = queryParams;
        return queryParams;
    }, [filters, userId, loading]);

    /**
     * Cleanup function to cancel pending operations on unmount
     */
    useEffect(() => {
        return () => {
            // Cancel pending debounced saves on cleanup
            if (debounceTimerRef.current) {
                clearTimeout(debounceTimerRef.current);
            }
        };
    }, []);
    
    return { 
        filters, 
        updateFilter,
        updateFilterAsync, 
        resetFilters, 
        getFilterQueryParams,
        loading,
        error
    };
};