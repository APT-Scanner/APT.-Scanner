import { useState, useEffect } from 'react';
import { useAuth } from './useAuth';
import { BACKEND_URL } from '../config/constants';

export const useRecommendations = (options = {}) => {
    const [recommendations, setRecommendations] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const { idToken, authLoading } = useAuth();
    
    const { 
        topK = 3, 
        autoFetch = true,
        refreshTrigger = 0 
    } = options;

    const fetchRecommendations = async () => {
        if (!idToken) {
            setError('User not authenticated');
            return;
        }

        setLoading(true);
        setError(null);
        
        try {
            const url = `${BACKEND_URL}/recommendations/neighborhoods?top_k=${topK}`;
            
            const response = await fetch(url, {
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
            console.log('Recommendations API response:', data);
            
            if (data.requires_questionnaire) {
                setError('Please complete the questionnaire first');
                setRecommendations([]);
            } else {
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
                    neighborhoodInfo: rec.neighborhood_info
                })) || [];
                
                setRecommendations(transformedRecommendations);
            }
        } catch (err) {
            console.error("Failed to fetch recommendations:", err);
            setError(err.message || 'Failed to load recommendations.');
            setRecommendations([]);
        } finally {
            setLoading(false);
        }
    };

    const refreshRecommendations = async () => {
        if (!idToken) {
            setError('User not authenticated');
            return;
        }

        try {
            const response = await fetch(`${BACKEND_URL}/recommendations/refresh`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${idToken}`,
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ 
                    detail: `HTTP error! status: ${response.status}` 
                }));
                throw new Error(errorData.detail || 'Failed to refresh recommendations');
            }

            // After refresh, fetch new recommendations
            await fetchRecommendations();
        } catch (err) {
            console.error("Failed to refresh recommendations:", err);
            setError(err.message || 'Failed to refresh recommendations.');
        }
    };

    // Auto fetch on mount and when dependencies change
    useEffect(() => {
        if (authLoading) return;
        
        if (autoFetch && idToken) {
            fetchRecommendations();
        }
    }, [idToken, authLoading, autoFetch, topK, refreshTrigger]);

    return {
        recommendations,
        loading,
        error,
        fetchRecommendations,
        refreshRecommendations,
        hasRecommendations: recommendations.length > 0
    };
}; 