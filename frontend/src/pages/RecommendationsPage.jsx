import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, RefreshCw, AlertCircle, Search } from 'lucide-react';
import { useRecommendations } from '../hooks/useRecommendations';
import { useAuth } from '../hooks/useAuth';
import { useFilters } from '../hooks/useFilters';
import { BACKEND_URL } from '../config/constants';
import styles from '../styles/RecommendationsPage.module.css';

const RecommendationsPage = () => {
    const navigate = useNavigate();
    const { idToken } = useAuth();
    const { updateFilterAsync } = useFilters();
    const { 
        recommendations, 
        loading, 
        error, 
        refreshRecommendations,
        hasRecommendations 
    } = useRecommendations();

    const handleBack = () => navigate(-1);

    const handleNeighborhoodClick = async (neighborhood) => {
        try {
            // Call API to update user filters with selected neighborhood
            const response = await fetch(`${BACKEND_URL}/recommendations/neighborhoods/${neighborhood.id}/select`, {
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
        }
    };

    const handleManualBrowse = async () => {
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
        }
    };

    const handleManualSearch = () => {
        navigate('/filter');
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
                            >
                                <RefreshCw size={20} /> Try Again
                            </button>
                        )}
                        
                        <button 
                            className={styles.secondaryButton}
                            onClick={handleManualBrowse}
                        >
                            Browse All Apartments
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
                        >
                            <RefreshCw size={20} /> Refresh
                        </button>
                        
                        <button 
                            className={styles.secondaryButton}
                            onClick={handleManualBrowse}
                        >
                            Browse All Apartments
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
                
                <button 
                    className={styles.refreshButton}
                    onClick={refreshRecommendations}
                    title="Refresh recommendations"
                    aria-label="Refresh recommendations"
                >
                    <RefreshCw size={20} />
                </button>
            </div>

            <h1 className={styles.mainTitle}>
                Your<br />Recommendations<br />Are Ready!
            </h1>

            <p className={styles.description}>
                Based on your questionnaire, we've found the top neighborhoods that suit your lifestyle preferences:
            </p>

            <section className={styles.listContainer}>
                {recommendations.map((rec) => (
                    <div
                        key={rec.id}
                        className={styles.listItem}
                        onClick={() => handleNeighborhoodClick(rec)}
                    >
                        <div className={styles.itemContent}>
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
                                {rec.location_details && rec.location_details.length > 0 && (
                                    <div className={styles.commuteHighlights}>
                                        <div className={styles.commuteTitle}>Commute Highlights</div>
                                        {rec.location_details.slice(0, 2).map((detail, index) => (
                                            <div key={index} className={styles.commuteDetail}>
                                                ✓ {detail}
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                            <div className={styles.matchInfo}>
                                <span className={styles.matchScore}>{rec.match}%</span>
                                <span className={styles.matchLabel}>Match</span>
                            </div>
                        </div>
                    </div>
                ))}
            </section>

            <div className={styles.footer}>
                <p className={styles.hintText}>
                    Click on a neighborhood to start swiping
                </p>
                <div className={styles.footerActions}>
                    <span 
                        className={styles.manualLink} 
                        onClick={handleManualBrowse}
                    >
                        browse all apartments
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