import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, RefreshCw, AlertCircle, Search, ChevronDown, ArrowUp, ArrowDown, Loader2 } from 'lucide-react';
import { useRecommendations } from '../hooks/useRecommendations';
import { useAuth } from '../hooks/useAuth';
import { useFilters } from '../hooks/useFilters';
import styles from '../styles/RecommendationsPage.module.css';
import API_BASE from '../config/api.js';

const RecommendationsPage = () => {
    const navigate = useNavigate();
    const { idToken } = useAuth();
    const { updateFilterAsync } = useFilters();
    
    // State for managing expanded cards
    const [expandedCards, setExpandedCards] = useState(new Set());
    
    // State for managing extended view (3 vs 10 recommendations)
    const [showExtended, setShowExtended] = useState(false);
    
    // Loading states for different actions
    const [loadingNeighborhood, setLoadingNeighborhood] = useState(null); // Track which neighborhood is loading
    const [loadingManualBrowse, setLoadingManualBrowse] = useState(false);
    const [loadingViewToggle, setLoadingViewToggle] = useState(false);
    
    const { 
        recommendations, 
        loading, 
        error, 
        refreshRecommendations,
        hasRecommendations
    } = useRecommendations({
        topK: showExtended ? 10 : 3
    });

    // Helper function to toggle card expansion
    const toggleCardExpansion = (cardId, event) => {
        event.stopPropagation(); // Prevent card click navigation
        setExpandedCards(prev => {
            const newSet = new Set(prev);
            if (newSet.has(cardId)) {
                newSet.delete(cardId);
            } else {
                newSet.add(cardId);
            }
            return newSet;
        });
    };

    // Helper function to format feature scores
    const getTopFeatures = (individualScores) => {
        if (!individualScores) return [];
        
        return Object.entries(individualScores)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 3)
            .map(([feature, score]) => ({
                name: feature.replace('_level', '').replace('_', ' '),
                score: Math.round(score * 100)
            }));
    };

    const handleBack = () => navigate(-1);

    const handleNeighborhoodClick = async (neighborhood) => {
        setLoadingNeighborhood(neighborhood.id); // Set loading state for this specific neighborhood
        
        try {
            // Call API to update user filters with selected neighborhood
            const response = await fetch(`${API_BASE}/api/v1/recommendations/neighborhoods/${neighborhood.id}/select`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${idToken}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                console.log('Neighborhood selected:', data);
                
                // Navigate to apartment swipe filtered by neighborhood
                navigate('/apartment-swipe', { 
                    state: { 
                        neighborhoodId: neighborhood.id,
                        neighborhoodName: neighborhood.name 
                    } 
                });
            } else {
                console.error('Failed to select neighborhood:', response.statusText);
                // Still navigate even if the API call fails
                navigate('/apartment-swipe', { 
                    state: { 
                        neighborhoodId: neighborhood.id,
                        neighborhoodName: neighborhood.name 
                    } 
                });
            }
        } catch (error) {
            console.error('Error selecting neighborhood:', error);
            // Still navigate even if there's an error
            navigate('/apartment-swipe', { 
                state: { 
                    neighborhoodId: neighborhood.id,
                    neighborhoodName: neighborhood.name 
                } 
            });
        } finally {
            setLoadingNeighborhood(null); // Clear loading state
        }
    };

    const handleManualBrowse = async () => {
        setLoadingManualBrowse(true); // Set loading state
        
        try {
            // Clear neighborhood and city filters to browse all apartments
            await updateFilterAsync({
                city: '',
                neighborhood: ''
            });
            console.log('Filters cleared, navigating to apartment swipe');
            navigate('/apartment-swipe');
        } catch (error) {
            console.error('Error clearing filters:', error);
            // Navigate anyway in case of error
            navigate('/apartment-swipe');
        } finally {
            setLoadingManualBrowse(false); // Clear loading state
        }
    };

    const handleManualSearch = () => {
        navigate('/filter');
    };

    const toggleExtendedView = async () => {
        setLoadingViewToggle(true); // Set loading state
        setShowExtended(!showExtended);
        
        // Add a small delay to show the loading state since recommendations update automatically
        setTimeout(() => {
            setLoadingViewToggle(false);
        }, 1000); // Give enough time for the recommendations to load
        
        // Note: The recommendations will automatically update due to the topK change in useRecommendations
    };

    if (loading) {
        return (
            <div className={styles.pageContainer}>  
                <div className={styles.loadingContainer}>
                    <div className={styles.spinner}></div>
                    <h2>Generating Your Recommendations</h2>
                    <p>Analyzing your preferences to find the perfect neighborhoods...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className={styles.pageContainer}>
                <button className={styles.backButton} onClick={handleBack} aria-label="Go Back">
                    <ArrowLeft size={24} color="#371b34" />
                </button>
                
                <div className={styles.errorContainer}>
                    <AlertCircle size={48} color="#e74c3c" />
                    <h2>Unable to Load Recommendations</h2>
                    <p className={styles.errorMessage}>{error}</p>
                    
                    <div className={styles.errorActions}>
                        {error.includes('questionnaire') ? (
                            <button 
                                className={styles.primaryButton}
                                onClick={() => navigate('/questionnaire')}
                            >
                                Complete Questionnaire
                            </button>
                        ) : (
                            <button 
                                className={styles.primaryButton}
                                onClick={refreshRecommendations}
                                disabled={loading}
                            >
                                {loading ? (
                                    <><Loader2 size={20} className={styles.spinner} /> Loading...</>
                                ) : (
                                    <><RefreshCw size={20} /> Try Again</>
                                )}
                            </button>
                        )}
                        
                        <button 
                            className={styles.secondaryButton}
                            onClick={handleManualBrowse}
                            disabled={loadingManualBrowse}
                            style={{ opacity: loadingManualBrowse ? 0.7 : 1 }}
                        >
                            {loadingManualBrowse ? (
                                <><Loader2 size={20} className={styles.spinner} /> Loading...</>
                            ) : (
                                'Browse All Apartments'
                            )}
                        </button>

                        <button 
                            className={styles.secondaryButton}
                            onClick={handleManualSearch}
                        >
                            <Search size={20} /> Manual Search
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    if (!hasRecommendations) {
        return (
            <div className={styles.pageContainer}>
                <button className={styles.backButton} onClick={handleBack} aria-label="Go Back">
                    <ArrowLeft size={24} color="#371b34" />
                </button>
                
                <div className={styles.emptyContainer}>
                    <h2>No Recommendations Available</h2>
                    <p>We couldn't find any neighborhoods matching your preferences at the moment.</p>
                    
                    <div className={styles.emptyActions}>
                        <button 
                            className={styles.primaryButton}
                            onClick={refreshRecommendations}
                            disabled={loading}
                        >
                            {loading ? (
                                <><Loader2 size={20} className={styles.spinner} /> Loading...</>
                            ) : (
                                <><RefreshCw size={20} /> Refresh</>
                            )}
                        </button>
                        
                        <button 
                            className={styles.secondaryButton}
                            onClick={handleManualBrowse}
                            disabled={loadingManualBrowse}
                            style={{ opacity: loadingManualBrowse ? 0.7 : 1 }}
                        >
                            {loadingManualBrowse ? (
                                <><Loader2 size={20} className={styles.spinner} /> Loading...</>
                            ) : (
                                'Browse All Apartments'
                            )}
                        </button>

                        <button 
                            className={styles.secondaryButton}
                            onClick={handleManualSearch}
                        >
                            <Search size={20} /> Manual Search
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className={styles.pageContainer}>
            <div className={styles.header}>
                <button className={styles.backButton} onClick={handleBack} aria-label="Go Back">
                    <ArrowLeft size={24} color="#371b34" />
                </button>
            </div>

            <h1 className={styles.mainTitle}>
                Your<br />Recommendations<br />Are Ready!
            </h1>
            <p className={styles.description}>
                Click on a neighborhood to start swiping
            </p>

            <section className={styles.listContainer}>
                {recommendations.map((rec) => {
                    const isExpanded = expandedCards.has(rec.id);
                    const isLoadingThisNeighborhood = loadingNeighborhood === rec.id;
                    
                    return (
                        <div
                            key={rec.id}
                            className={`${styles.listItem} ${isLoadingThisNeighborhood ? styles.loading : ''}`}
                        >
                            <div className={styles.itemContent}>
                                {/* Main card header - always visible */}
                                <div 
                                    className={`${styles.itemHeader} ${isLoadingThisNeighborhood ? styles.headerLoading : ''}`}
                                    onClick={() => !isLoadingThisNeighborhood && handleNeighborhoodClick(rec)}
                                    style={{ 
                                        cursor: isLoadingThisNeighborhood ? 'not-allowed' : 'pointer',
                                        opacity: isLoadingThisNeighborhood ? 0.7 : 1 
                                    }}
                                >
                                    <div className={styles.itemInfo}>
                                        <span className={styles.itemName}>
                                            {rec.name}
                                            {rec.englishName && rec.englishName !== rec.name && (
                                                <span className={styles.englishName}> ({rec.englishName})</span>
                                            )}
                                        </span>
                                        <span className={styles.itemCity}>{rec.city}</span>
                                        {rec.totalListings > 0 && (
                                            <span className={styles.listingCount}>
                                                {rec.totalListings} available apartments
                                            </span>
                                        )}
                                    </div>
                                    <div className={styles.headerActions}>
                                        {isLoadingThisNeighborhood ? (
                                            <div className={styles.loadingIndicator}>
                                                <Loader2 size={20} className={styles.spinner} />
                                                <span className={styles.loadingText}>Loading...</span>
                                            </div>
                                        ) : (
                                            <>
                                                <div className={styles.matchInfo}>
                                                    <span className={styles.matchScore}>{rec.match}%</span>
                                                    <span className={styles.matchLabel}>Match</span>
                                                </div>
                                                <button
                                                    className={`${styles.expandButton} ${isExpanded ? styles.expanded : ''}`}
                                                    onClick={(e) => toggleCardExpansion(rec.id, e)}
                                                    aria-label={isExpanded ? "Collapse details" : "Expand details"}
                                                >
                                                    <ChevronDown size={20} />
                                                </button>
                                            </>
                                        )}
                                    </div>
                                </div>

                                {/* Collapsible detailed information */}
                                {isExpanded && (
                                    <div className={styles.expandedContent}>
                                        {/* Neighborhood Overview */}
                                        {rec.neighborhoodInfo?.overview && (
                                            <div className={styles.neighborhoodOverview}>
                                                <p className={styles.overviewText}>
                                                    {rec.neighborhoodInfo.overview.length > 150 
                                                        ? `${rec.neighborhoodInfo.overview.substring(0, 150)}...`
                                                        : rec.neighborhoodInfo.overview
                                                    }
                                                </p>
                                            </div>
                                        )}

                                        {/* Price Analysis */}
                                        {rec.priceAnalysis && (
                                            <div className={styles.priceAnalysis}>
                                                <div className={styles.priceInfo}>
                                                    <span className={styles.priceLabel}>Average Rent:</span>
                                                    <span className={styles.priceValue}>₪{rec.avgRentalPrice?.toLocaleString()}</span>
                                                    <span className={`${styles.affordabilityBadge} ${styles[rec.priceAnalysis.affordability]}`}>
                                                        {rec.priceAnalysis.message}
                                                    </span>
                                                </div>
                                            </div>
                                        )}


                                        {/* Top Features */}
                                        {rec.individualScores && (
                                            <div className={styles.topFeatures}>
                                                <h4 className={styles.featuresTitle}>Top Features:</h4>
                                                <div className={styles.featuresList}>
                                                    {getTopFeatures(rec.individualScores).map((feature, index) => (
                                                        <div key={index} className={styles.featureItem}>
                                                            <span className={styles.featureName}>{feature.name}</span>
                                                            <span className={styles.featureScore}>{feature.score}%</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {/* Commute Information */}
                                        {rec.locationDetails && rec.locationDetails.length > 0 && (
                                            <div className={styles.commuteHighlights}>
                                                <h4 className={styles.commuteTitle}>Commute Highlights:</h4>
                                                {rec.locationDetails.slice(0, 2).map((detail, index) => (
                                                    <div key={index} className={styles.commuteDetail}>
                                                        ✓ {detail}
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                    );
                })}
            </section>

            {/* Extended View Toggle */}
            <div className={styles.viewToggleContainer}>
                <div className={styles.viewToggleWrapper}>
                    <span className={styles.viewToggleLabel}>
                        Showing {showExtended ? '10' : '3'} recommendations
                    </span>
                    <button 
                        className={styles.viewToggleButton}
                        onClick={toggleExtendedView}
                        disabled={loading || loadingViewToggle}
                        style={{ opacity: loadingViewToggle ? 0.7 : 1 }}
                    >
                        {loadingViewToggle ? (
                            <>
                                <Loader2 size={20} className={styles.spinner} />
                                Loading...
                            </>
                        ) : showExtended ? (
                            <>Show Top 3 <span className={styles.buttonIcon}><ArrowUp size={20} /></span></>
                        ) : (
                            <>Show All 10 <span className={styles.buttonIcon}><ArrowDown size={20} /></span></>
                        )}
                    </button>
                </div>
            </div>

            <div className={styles.footer}>
                <div className={styles.footerActions}>
                    <span 
                        className={`${styles.manualLink} ${loadingManualBrowse ? styles.linkLoading : ''}`}
                        onClick={!loadingManualBrowse ? handleManualBrowse : undefined}
                        style={{ 
                            cursor: loadingManualBrowse ? 'not-allowed' : 'pointer',
                            opacity: loadingManualBrowse ? 0.7 : 1,
                            pointerEvents: loadingManualBrowse ? 'none' : 'auto'
                        }}
                    >
                        {loadingManualBrowse ? (
                            <>
                                <Loader2 size={14} className={styles.spinner} style={{ marginRight: '6px' }} />
                                loading...
                            </>
                        ) : (
                            'browse all apartments'
                        )}
                    </span>
                    <span className={styles.linkSeparator}>or</span>
                    <span 
                        className={styles.manualLink} 
                        onClick={handleManualSearch}
                    >
                        manual search
                    </span>
                </div>
            </div>
        </div>
    );
};

export default RecommendationsPage;