import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, RefreshCw, AlertCircle } from 'lucide-react';
import { useRecommendations } from '../hooks/useRecommendations';
import styles from '../styles/RecommendationsPage.module.css';

const RecommendationsPage = () => {
    const navigate = useNavigate();
    const { 
        recommendations, 
        loading, 
        error, 
        refreshRecommendations,
        hasRecommendations 
    } = useRecommendations();

    const handleBack = () => navigate(-1);

    const handleNeighborhoodClick = (neighborhood) => {
        // Navigate to apartment swipe filtered by neighborhood
        navigate('/apartment-swipe', { 
            state: { 
                neighborhoodId: neighborhood.id,
                neighborhoodName: neighborhood.name 
            } 
        });
    };

    const handleManualBrowse = () => {
        navigate('/apartment-swipe');
    };

    if (loading) {
        return (
            <div className={styles.pageContainer}>
                <button className={styles.backButton} onClick={handleBack} aria-label="Go Back">
                    <ArrowLeft size={24} color="#371b34" />
                </button>
                
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
                <span 
                    className={styles.manualLink} 
                    onClick={handleManualBrowse}
                >
                    or browse all apartments
                </span>
            </div>
        </div>
    );
};

export default RecommendationsPage;