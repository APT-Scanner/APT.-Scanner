import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from './useAuth';
import API_BASE from '../config/api.js';

export const useRecommendations = (options = {}) => {
    const [recommendations, setRecommendations] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const retryCountRef = useRef(0);
    const { idToken, authLoading } = useAuth();
    
    const { 
        topK = 3, 
        autoFetch = true,
        refreshTrigger = 0 
    } = options;

    const fetchRecommendations = useCallback(async (resetRetry = false) => {
        if (!idToken) {
            setError('User not authenticated');
            return;
        }

        setLoading(true);
        setError(null);
        
        // Reset retry count for new fetch attempts
        if (resetRetry) {
            retryCountRef.current = 0;
        }
        
        try {
            const url = `${API_BASE}/api/v1/recommendations/neighborhoods?top_k=${topK}`;
            
            // Add timeout to prevent hanging requests
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 15000); // 15 second timeout
            
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${idToken}`,
                    'Content-Type': 'application/json',
                },
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ 
                    detail: `HTTP error! status: ${response.status}` 
                }));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('Recommendations API response:', data);
            
            if (data.requires_questionnaire) {
                // If this is the first attempt and questionnaire completion might be processing, retry once
                if (retryCountRef.current === 0) {
                    console.log('Questionnaire completion may be processing, retrying in 2 seconds...');
                    retryCountRef.current = 1;
                    setTimeout(() => {
                        fetchRecommendations();
                    }, 2000);
                    return;
                } else {
                    setError('Please complete the questionnaire first to get recommendations');
                    setRecommendations([]);
                }
            } else {
                // Reset retry count on successful response
                retryCountRef.current = 0;
                
                // Transform API data to frontend format
                const transformedRecommendations = data.recommendations?.map(rec => ({
                    id: rec.neighborhood_id,
                    name: rec.hebrew_name,
                    englishName: rec.english_name,
                    city: rec.neighborhood_info?.city || 'Tel Aviv',
                    score: rec.score,
                    match: Math.round(rec.score * 100), // Convert 0-1 score to percentage
                    totalListings: rec.total_available_listings,
                    sampleListings: rec.sample_listings,
                    individualScores: rec.individual_scores,
                    matchDetails: rec.match_details,
                    neighborhoodInfo: rec.neighborhood_info,
                    locationDetails: rec.location_details,
                    priceAnalysis: rec.price_analysis,
                    featureScore: rec.feature_score,
                    locationScore: rec.location_score,
                    priceScore: rec.price_score,
                    totalScore: rec.total_score,
                    avgRentalPrice: rec.avg_rental_price
                })) || [];
                
                setRecommendations(transformedRecommendations);
            }
        } catch (err) {
            console.error("Failed to fetch recommendations:", err);
            if (err.name === 'AbortError') {
                setError('Request timed out. Please try again.');
            } else {
                setError(err.message || 'Failed to load recommendations.');
            }
            setRecommendations([]);
        } finally {
            setLoading(false);
        }
    }, [idToken, topK]);

    const refreshRecommendations = async () => {
        if (!idToken) {
            setError('User not authenticated');
            return;
        }

        try {
            // Add timeout to prevent hanging requests
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 15000); // 15 second timeout
            
            const response = await fetch(`${API_BASE}/api/v1/recommendations/refresh`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${idToken}`,
                    'Content-Type': 'application/json',
                },
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ 
                    detail: `HTTP error! status: ${response.status}` 
                }));
                throw new Error(errorData.detail || 'Failed to refresh recommendations');
            }

            // After refresh, fetch new recommendations
            await fetchRecommendations(true);
        } catch (err) {
            console.error("Failed to refresh recommendations:", err);
            if (err.name === 'AbortError') {
                setError('Refresh request timed out. Please try again.');
            } else {
                setError(err.message || 'Failed to refresh recommendations.');
            }
        }
    };

    // Auto fetch on mount and when dependencies change
    useEffect(() => {
        if (authLoading) return;
        
        if (autoFetch && idToken) {
            fetchRecommendations(true); // Reset retry count for new attempts
        }
    }, [idToken, authLoading, autoFetch, topK, refreshTrigger, fetchRecommendations]);

    return {
        recommendations,
        loading,
        error,
        fetchRecommendations: () => fetchRecommendations(true),
        refreshRecommendations,
        hasRecommendations: recommendations.length > 0
    };
}; 