import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
    ArrowLeft, Search, MapPin, Users, DollarSign, Home, Loader2, TrendingUp, 
    GraduationCap, Waves, Activity, Shield, Heart, Wrench, Car, TreePine, 
    Volume2, ShoppingBag, Moon, Church, Baby 
} from 'lucide-react';
import styles from '../styles/NeighborhoodsExplorePage.module.css';
import { useAuth } from '../hooks/useAuth';
import API_BASE from '../config/api.js';
import HomeIcon from '../assets/home_not_pressed.svg';
import HeartOutlineIcon from '../assets/heart_not_pressed.svg';

const NeighborhoodsExplorePage = () => {
    const navigate = useNavigate();
    const { idToken } = useAuth();
    const [neighborhoods, setNeighborhoods] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedCity, setSelectedCity] = useState('');
    const [sortBy, setSortBy] = useState('name'); // name, avgPrice, popularity

    const fetchNeighborhoods = useCallback(async () => {
        if (!idToken) {
            setLoading(false);
            setError('Authentication required');
            return;
        }

        setLoading(true);
        setError(null);
        
        try {
            const response = await fetch(`${API_BASE}/api/v1/recommendations/neighborhoods/explore`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${idToken}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch neighborhoods data');
            }

            const data = await response.json();
            console.log('Neighborhoods API response:', data);
            setNeighborhoods(data.neighborhoods || []);
        } catch (err) {
            console.error('Error fetching neighborhoods:', err);
            const errorMessage = err.message.includes('Failed to fetch') 
                ? 'Unable to load neighborhoods. Please check your connection and try again.'
                : err.message;
            setError(errorMessage);
            // Fallback to empty array on error
            setNeighborhoods([]);
        } finally {
            setLoading(false);
        }
    }, [idToken]);

    useEffect(() => {
        if (idToken) {
            fetchNeighborhoods();
        }
    }, [idToken, fetchNeighborhoods]);

    const filteredNeighborhoods = neighborhoods.filter(neighborhood => {
        const matchesSearch = neighborhood.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                            neighborhood.hebrew_name.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesCity = selectedCity === '' || neighborhood.city === selectedCity;
        return matchesSearch && matchesCity;
    });

    const sortedNeighborhoods = [...filteredNeighborhoods].sort((a, b) => {
        switch (sortBy) {
            case 'avgPrice': {
                const priceA = a.current_avg_rental_price || a.historical_avg_rental_price || 0;
                const priceB = b.current_avg_rental_price || b.historical_avg_rental_price || 0;
                return priceA - priceB;
            }
            case 'popularity':
                return b.popularity_score - a.popularity_score;
            case 'listings':
                return (b.current_active_listings || 0) - (a.current_active_listings || 0);
            case 'schools':
                return (b.school_rating || 0) - (a.school_rating || 0);
            case 'socioeconomic':
                return (b.social_economic_index || 0) - (a.social_economic_index || 0);
            case 'safety':
                return (b.features?.safety_level || 0) - (a.features?.safety_level || 0);
            case 'culture':
                return (b.features?.cultural_level || 0) - (a.features?.cultural_level || 0);
            case 'parks':
                return (b.features?.parks_level || 0) - (a.features?.parks_level || 0);
            default:
                return a.name.localeCompare(b.name);
        }
    });

    const handleNeighborhoodClick = (neighborhood) => {
        navigate('/apartment-swipe', {
            state: {
                neighborhoodId: neighborhood.id,
                neighborhoodName: neighborhood.name
            }
        });
    };

    const uniqueCities = [...new Set(neighborhoods.map(n => n.city))];

    if (loading) {
        return (
            <div className={styles.pageContainer}>
                <div className={styles.loadingContainer}>
                    <Loader2 size={48} className={styles.spinner} />
                    <h2>Loading Neighborhoods</h2>
                    <p>Discovering the best places to live...</p>
                </div>
            </div>
        );
    }

    return (
        <div className={styles.pageContainer}>
            {/* Header */}
            <div className={styles.header}>
                <button className={styles.backButton} onClick={() => navigate(-1)}>
                    <ArrowLeft size={24} />
                </button>
                <h1 className={styles.title}>Explore Neighborhoods</h1>
            </div>

            {/* Search and Filter Bar */}
            <div className={styles.searchSection}>
                <div className={styles.searchInputContainer}>
                    <Search size={20} className={styles.searchIcon} />
                    <input
                        type="text"
                        placeholder="Search neighborhoods..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className={styles.searchInput}
                    />
                </div>
                
                <div className={styles.filtersRow}>
                    <select 
                        value={selectedCity} 
                        onChange={(e) => setSelectedCity(e.target.value)}
                        className={styles.cityFilter}
                        aria-label="Select city"
                    >
                        <option value="">All Cities</option>
                        {uniqueCities.map(city => (
                            <option key={city} value={city}>{city}</option>
                        ))}
                    </select>
                    
                    <select 
                        value={sortBy} 
                        onChange={(e) => setSortBy(e.target.value)}
                        className={styles.sortFilter}
                        aria-label="Select sort order"
                    >
                        <option value="name">Sort by Name</option>
                        <option value="popularity">Sort by Overall Score</option>
                        <option value="safety">Sort by Safety Level</option>
                        <option value="schools">Sort by School Rating</option>
                        <option value="socioeconomic">Sort by Quality Index</option>
                        <option value="culture">Sort by Cultural Level</option>
                        <option value="parks">Sort by Parks & Nature</option>
                        <option value="avgPrice">Sort by Rent Price</option>
                        <option value="listings">Sort by Active Listings</option>
                    </select>
                </div>
            </div>

            {/* Neighborhoods List */}
            <div className={styles.neighborhoodsList}>
                {error && (
                    <div className={styles.errorMessage}>
                        <p>Unable to load neighborhoods data: {error}</p>
                    </div>
                )}
                
                {sortedNeighborhoods.map(neighborhood => (
                    <div 
                        key={neighborhood.id}
                        className={styles.neighborhoodCard}
                        onClick={() => handleNeighborhoodClick(neighborhood)}
                    >
                        <div className={styles.cardContent}>
                            <div className={styles.cardHeader}>
                                <div className={styles.nameContainer}>
                                    <h3 className={styles.neighborhoodName}>{neighborhood.name}</h3>
                                    <p className={styles.hebrewName}>{neighborhood.hebrew_name}</p>
                                    <span className={styles.cityName}>{neighborhood.city}</span>
                                </div>
                                <div className={styles.priceContainer}>
                                    <span className={styles.price}>
                                        ₪{(neighborhood.current_avg_rental_price || neighborhood.historical_avg_rental_price || 0).toLocaleString()}
                                    </span>
                                    <span className={styles.priceLabel}>
                                        {neighborhood.current_avg_rental_price ? 'current avg.' : 'historical avg.'}
                                    </span>
                                </div>
                            </div>

                            <p className={styles.description}>{neighborhood.description}</p>

                            {/* Comprehensive neighborhood features display */}
                            <div className={styles.featuresContainer}>
                                {/* Core Metrics Row */}
                                <div className={styles.coreMetrics}>
                                    <div className={styles.metric}>
                                        <Activity size={16} />
                                        <span>{neighborhood.current_active_listings || 0} active</span>
                                    </div>
                                    {neighborhood.school_rating && (
                                        <div className={styles.metric}>
                                            <GraduationCap size={16} />
                                            <span>{neighborhood.school_rating}/10 schools</span>
                                        </div>
                                    )}
                                    {neighborhood.social_economic_index && (
                                        <div className={styles.metric}>
                                            <Users size={16} />
                                            <span>{neighborhood.social_economic_index}/10 quality</span>
                                        </div>
                                    )}
                                </div>

                                {/* Rich Features Grid */}
                                {neighborhood.features && (
                                    <div className={styles.featuresGrid}>
                                        <div className={styles.featureCategory}>
                                            <h4 className={styles.categoryTitle}>Safety & Environment</h4>
                                            <div className={styles.featureItems}>
                                                {neighborhood.features.safety_level && (
                                                    <div className={styles.featureItem}>
                                                        <Shield size={14} />
                                                        <span>Safety: {Math.round(neighborhood.features.safety_level * 100)}%</span>
                                                    </div>
                                                )}
                                                {neighborhood.features.peaceful_level && (
                                                    <div className={styles.featureItem}>
                                                        <Volume2 size={14} />
                                                        <span>Quiet: {Math.round(neighborhood.features.peaceful_level * 100)}%</span>
                                                    </div>
                                                )}
                                                {neighborhood.features.maintenance_level && (
                                                    <div className={styles.featureItem}>
                                                        <Wrench size={14} />
                                                        <span>Maintenance: {Math.round(neighborhood.features.maintenance_level * 100)}%</span>
                                                    </div>
                                                )}
                                            </div>
                                        </div>

                                        <div className={styles.featureCategory}>
                                            <h4 className={styles.categoryTitle}>Amenities & Lifestyle</h4>
                                            <div className={styles.featureItems}>
                                                {neighborhood.features.parks_level && (
                                                    <div className={styles.featureItem}>
                                                        <TreePine size={14} />
                                                        <span>Parks: {Math.round(neighborhood.features.parks_level * 100)}%</span>
                                                    </div>
                                                )}
                                                {neighborhood.features.shopping_level && (
                                                    <div className={styles.featureItem}>
                                                        <ShoppingBag size={14} />
                                                        <span>Shopping: {Math.round(neighborhood.features.shopping_level * 100)}%</span>
                                                    </div>
                                                )}
                                                {neighborhood.features.mobility_level && (
                                                    <div className={styles.featureItem}>
                                                        <Car size={14} />
                                                        <span>Transport: {Math.round(neighborhood.features.mobility_level * 100)}%</span>
                                                    </div>
                                                )}
                                                {neighborhood.features.nightlife_level && (
                                                    <div className={styles.featureItem}>
                                                        <Moon size={14} />
                                                        <span>Nightlife: {Math.round(neighborhood.features.nightlife_level * 100)}%</span>
                                                    </div>
                                                )}
                                            </div>
                                        </div>

                                        <div className={styles.featureCategory}>
                                            <h4 className={styles.categoryTitle}>Community & Culture</h4>
                                            <div className={styles.featureItems}>
                                                {neighborhood.features.communality_level && (
                                                    <div className={styles.featureItem}>
                                                        <Heart size={14} />
                                                        <span>Community: {Math.round(neighborhood.features.communality_level * 100)}%</span>
                                                    </div>
                                                )}
                                                {neighborhood.features.cultural_level && (
                                                    <div className={styles.featureItem}>
                                                        <Users size={14} />
                                                        <span>Culture: {Math.round(neighborhood.features.cultural_level * 100)}%</span>
                                                    </div>
                                                )}
                                                {neighborhood.features.kindergardens_level && (
                                                    <div className={styles.featureItem}>
                                                        <Baby size={14} />
                                                        <span>Kindergartens: {Math.round(neighborhood.features.kindergardens_level * 100)}%</span>
                                                    </div>
                                                )}
                                                {neighborhood.features.religiosity_level && (
                                                    <div className={styles.featureItem}>
                                                        <Church size={14} />
                                                        <span>Religiosity: {Math.round(neighborhood.features.religiosity_level * 100)}%</span>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* Location & Distance */}
                                {neighborhood.beach_distance_km && (
                                    <div className={styles.locationInfo}>
                                        <div className={styles.metric}>
                                            <Waves size={16} />
                                            <span>{neighborhood.beach_distance_km}km to beach</span>
                                        </div>
                                    </div>
                                )}

                                {/* Overall Popularity Score */}
                                <div className={styles.popularityScore}>
                                    <TrendingUp size={16} />
                                    <span>Overall Score: {Math.round(neighborhood.popularity_score * 100)}%</span>
                                    {neighborhood.score_breakdown && (
                                        <div className={styles.scoreBreakdown}>
                                            <small>
                                                Safety: {Math.round(neighborhood.score_breakdown.safety * 100)}% | 
                                                Quality: {Math.round(neighborhood.score_breakdown.socio_economic * 100)}% | 
                                                Schools: {Math.round(neighborhood.score_breakdown.school_quality * 100)}%
                                            </small>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                ))}
                
                {sortedNeighborhoods.length === 0 && !loading && (
                    <div className={styles.emptyState}>
                        <MapPin size={48} color="#ccc" />
                        <h3>No neighborhoods found</h3>
                        <p>Try adjusting your search or filters</p>
                    </div>
                )}
            </div>

            {/* Bottom Navigation */}
            <div className={styles.bottomBar}>
                <button 
                    className={styles.bottomBarButton} 
                    onClick={() => navigate('/apartment-swipe')}
                >
                    <img src={HomeIcon} alt="Home" />
                </button>
                <button 
                    className={styles.bottomBarButton}
                    onClick={() => navigate('/favorites')}
                >
                    <img src={HeartOutlineIcon} alt="Favorites" />
                </button>
                <button className={`${styles.bottomBarButton} ${styles.active}`}>
                    <MapPin size={24} alt="Neighborhoods" style={{ width: '28px', height: '28px', stroke: '#371b34', strokeWidth: '1.5' }} />
                </button>
            </div>
        </div>
    );
};

export default NeighborhoodsExplorePage;
