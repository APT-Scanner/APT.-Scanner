import { useState, useEffect, useCallback } from 'react';
import { useAuth } from './useAuth';
import { BACKEND_URL } from '../config/constants';

const LOCAL_VIEW_HISTORY_KEY = 'apt_scanner_view_history';

export const useViewHistory = () => {
    const [viewHistory, setViewHistory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const { idToken, loading: authLoading } = useAuth();

    useEffect(() => {
        try {
            const storedHistory = localStorage.getItem(LOCAL_VIEW_HISTORY_KEY);
            if (storedHistory) {
                const parsedHistory = JSON.parse(storedHistory);
                // Only keep views that are less than a day old
                const oneDayAgo = Date.now() - 24 * 60 * 60 * 1000;
                const recentViews = parsedHistory.filter(
                    view => new Date(view.timestamp).getTime() > oneDayAgo
                );
                
                setViewHistory(recentViews);
                // If we filtered out old views, update localStorage
                if (recentViews.length !== parsedHistory.length) {
                    localStorage.setItem(LOCAL_VIEW_HISTORY_KEY, JSON.stringify(recentViews));
                }
            }
        } catch (err) {
            console.error("Error loading view history from localStorage:", err);
            // If there's an error, just reset the localStorage
            localStorage.removeItem(LOCAL_VIEW_HISTORY_KEY);
        } finally {
            setLoading(false);
        }
    }, []);

    // Fetch server view history when authenticated
    useEffect(() => {
        if (authLoading || !idToken) {
            return;
        }

        const fetchViewHistory = async () => {
            try {
                const response = await fetch(`${BACKEND_URL}/listings/views`, {
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
                
                // Merge with local history (consider doing this more intelligently)
                // For now, we'll prioritize the server's view history
                setViewHistory(prev => {
                    const serverListingIds = new Set(data.map(item => item.listing_id));
                    const localOnlyViews = prev.filter(
                        item => !serverListingIds.has(item.listing_id)
                    );
                    
                    // Convert server records to local format
                    const serverViews = data.map(item => ({
                        listing_id: item.listing_id,
                        timestamp: new Date(item.viewed_at).getTime()
                    }));
                    
                    return [...serverViews, ...localOnlyViews];
                });
            } catch (err) {
                console.error("Failed to fetch view history:", err);
                setError(err.message || 'Failed to load view history.');
            }
        };

        fetchViewHistory();
    }, [idToken, authLoading]);

    // Record a view (both locally and on the server)
    const recordView = useCallback(async (listingId) => {
        if (!listingId) return;
        
        // Add to local view history immediately
        const timestamp = Date.now();
        const newView = { listing_id: listingId, timestamp };
        
        setViewHistory(prevHistory => {
            // Remove any previous view of this listing
            const filteredHistory = prevHistory.filter(
                item => item.listing_id !== listingId
            );
            
            // Add the new view
            const updatedHistory = [...filteredHistory, newView];
            
            // Update localStorage
            localStorage.setItem(LOCAL_VIEW_HISTORY_KEY, JSON.stringify(updatedHistory));
            
            return updatedHistory;
        });
        
        // Record view on the server if authenticated
        if (idToken) {
            try {
                await fetch(`${BACKEND_URL}/listings/views`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${idToken}`,
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ listing_id: listingId }),
                });
            } catch (err) {
                console.error("Failed to record view on server:", err);
                // We don't set any error state here, as the local recording succeeded
            }
        }
    }, [idToken]);

    // Check if an apartment has been viewed recently (within the last day)
    const hasBeenViewedRecently = useCallback((listingId) => {
        if (!listingId) return false;
        
        const oneDayAgo = Date.now() - 24 * 60 * 60 * 1000;
        return viewHistory.some(
            view => view.listing_id === listingId && 
                   new Date(view.timestamp).getTime() > oneDayAgo
        );
    }, [viewHistory]);

    // Filter an array of apartments to remove recently viewed ones
    const filterViewedApartments = useCallback((apartments) => {
        if (!apartments || !Array.isArray(apartments)) return [];
        
        return apartments.filter(
            apartment => !hasBeenViewedRecently(apartment.listing_id)
        );
    }, [hasBeenViewedRecently]);

    // Clear view history (both local and server)
    const clearViewHistory = useCallback(async () => {
        // Clear local storage
        localStorage.removeItem(LOCAL_VIEW_HISTORY_KEY);
        setViewHistory([]);
        
        // Clear server history if authenticated
        if (idToken) {
            try {
                await fetch(`${BACKEND_URL}/listings/views`, {
                    method: 'DELETE',
                    headers: {
                        'Authorization': `Bearer ${idToken}`,
                        'Content-Type': 'application/json',
                    },
                });
            } catch (err) {
                console.error("Failed to clear view history on server:", err);
                setError(err.message || 'Failed to clear view history on server.');
            }
        }
    }, [idToken]);

    return {
        viewHistory,
        loading,
        error,
        recordView,
        hasBeenViewedRecently,
        filterViewedApartments,
        clearViewHistory,
    };
}; 