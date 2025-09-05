import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Search, MapPin, Users, DollarSign, Home, Loader2, TrendingUp } from 'lucide-react';
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

    useEffect(() => {
        fetchNeighborhoods();
    }, []);

    const fetchNeighborhoods = async () => {
        setLoading(true);
        setError(null);
        
        try {
            const response = await fetch(`${API_BASE}/api/v1/neighborhoods/explore`, {
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
            setNeighborhoods(data.neighborhoods || []);
        } catch (err) {
            console.error('Error fetching neighborhoods:', err);
            setError(err.message);
            // Mock data for now until API is implemented
            setNeighborhoods([
                {
                    id: 1,
                    name: 'Tel Aviv Center',
                    hebrew_name: 'מרכז תל אביב',
                    city: 'Tel Aviv',
                    avg_rental_price: 8500,
                    total_listings: 245,
                    popularity_score: 0.95,
                    description: 'The heart of Tel Aviv with vibrant nightlife, restaurants, and cultural attractions.',
                    image: '/src/assets/neighbourhoods/tel-aviv-center.jpg'
                },
                {
                    id: 2,
                    name: 'Florentin',
                    hebrew_name: 'פלורנטין',
                    city: 'Tel Aviv',
                    avg_rental_price: 7200,
                    total_listings: 187,
                    popularity_score: 0.88,
                    description: 'Trendy neighborhood known for its street art, bars, and young professional community.',
                    image: '/src/assets/neighbourhoods/florentin.jpg'
                },
                {
                    id: 3,
                    name: 'Neve Tzedek',
                    hebrew_name: 'נווה צדק',
                    city: 'Tel Aviv',
                    avg_rental_price: 12000,
                    total_listings: 89,
                    popularity_score: 0.92,
                    description: 'Historic and upscale neighborhood with beautiful architecture and boutique shops.',
                    image: '/src/assets/neighbourhoods/neve-tzedek.jpg'
                }
            ]);
        } finally {
            setLoading(false);
        }
    };

    const filteredNeighborhoods = neighborhoods.filter(neighborhood => {
        const matchesSearch = neighborhood.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                            neighborhood.hebrew_name.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesCity = selectedCity === '' || neighborhood.city === selectedCity;
        return matchesSearch && matchesCity;
    });

    const sortedNeighborhoods = [...filteredNeighborhoods].sort((a, b) => {
        switch (sortBy) {
            case 'avgPrice':
                return a.avg_rental_price - b.avg_rental_price;
            case 'popularity':
                return b.popularity_score - a.popularity_score;
            case 'listings':
                return b.total_listings - a.total_listings;
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
                    >
                        <option value="name">Sort by Name</option>
                        <option value="avgPrice">Sort by Price</option>
                        <option value="popularity">Sort by Popularity</option>
                        <option value="listings">Sort by Listings</option>
                    </select>
                </div>
            </div>

            {/* Neighborhoods List */}
            <div className={styles.neighborhoodsList}>
                {error && (
                    <div className={styles.errorMessage}>
                        <p>Unable to load live data. Showing sample neighborhoods:</p>
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
                                    <span className={styles.price}>₪{neighborhood.avg_rental_price?.toLocaleString()}</span>
                                    <span className={styles.priceLabel}>avg. rent</span>
                                </div>
                            </div>

                            <p className={styles.description}>{neighborhood.description}</p>

                            <div className={styles.statsRow}>
                                <div className={styles.stat}>
                                    <Home size={16} />
                                    <span>{neighborhood.total_listings} listings</span>
                                </div>
                                <div className={styles.stat}>
                                    <TrendingUp size={16} />
                                    <span>{Math.round(neighborhood.popularity_score * 100)}% popular</span>
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
                    <MapPin size={24} />
                </button>
            </div>
        </div>
    );
};

export default NeighborhoodsExplorePage;
