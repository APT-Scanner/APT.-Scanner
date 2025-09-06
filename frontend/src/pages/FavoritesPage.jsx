import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useFavorites } from '../hooks/useFavorites';
import { useListings } from '../hooks/useListings'; 
import styles from '../styles/FavoritesPage.module.css';
import HomeIcon from '../assets/home_not_pressed.svg';
import HeartIcon from '../assets/heart_pressed.svg';
import { Menu, Filter, X, Loader, MapPin } from 'lucide-react';

// Add a LoadingSpinner component
const LoadingSpinner = () => (
  <div className={styles.loadingContainer}>
    <div className={styles.spinner}>
      <Loader size={40} className={styles.spinnerIcon} />
      <p>Loading favorites...</p>
    </div>
  </div>
);

const FavoritesPage = () => {
    const { favorites, loading: favoritesLoading, error: favoritesError, removeFavorite } = useFavorites();
    const { listings, getListing, loading: listingsLoading } = useListings();
    const [isEditing, setIsEditing] = useState(false);
    const navigate = useNavigate();

    useEffect(() => {
        window.scrollTo(0, 0);
        
        if (favorites.length > 0) {
            favorites.forEach(favorite => {
                if (!listings[favorite.listing_id]) {
                    getListing(favorite.listing_id);
                }
            });
        }
    }, [favorites, getListing, listings]);

    if (favoritesLoading) return <LoadingSpinner />;
    if (favoritesError) return <div className={styles.errorContainer}>Error: {favoritesError}</div>;

    console.log("Favorites:", favorites);
    console.log("Listings details:", listings);

    const handleCardClick = (listing) => {
        if (listing && listing.yad2_url_token && !isEditing) {
            navigate(`/favorites/${listing.listing_id}`);
        }
    };

    return (
        <div className={styles.pageWrapper}>
            <div className={styles.header}>
                <h1>Favorites</h1>
            </div>
            
            <div className={styles.savedCount}>
                {favorites.length} Apartments Saved
            </div>
            
            <div className={styles.favoritesGrid}>
                {favorites.length > 0 ? (
                    favorites.map(favorite => {
                        const listing = listings[favorite.listing_id];
                        const isLoading = listingsLoading[favorite.listing_id];
                        
                        return (
                            <div 
                                key={favorite.id} 
                                className={styles.favoriteCard}
                                onClick={() => handleCardClick(listing)}
                                style={{ cursor: isEditing ? 'default' : 'pointer' }}
                            >
                                <div 
                                    className={styles.favoriteImage} 
                                    style={{ 
                                        backgroundImage: listing 
                                            ? `url(${listing.cover_image_url || listing.image || '/assets/apartment-placeholder.jpg'})` 
                                            : 'url(/assets/apartment-placeholder.jpg)'
                                    }}
                                >
                                    {console.log(listing)}
                                    {listing && !listing.is_active && (
                                        <div className={styles.inactiveOverlay}>
                                            This listing is no longer active
                                        </div>
                                    )}
                                    {isEditing && (
                                        <button 
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                removeFavorite(favorite.listing_id);
                                            }}
                                            className={styles.removeButton}
                                        >
                                            X
                                        </button>
                                    )}
                                    {isLoading && (
                                        <div className={styles.loadingOverlay}>
                                            Loading...
                                        </div>
                                    )}
                                </div>
                                <div className={styles.favoriteInfo}>
                                    {listing ? (
                                        <>
                                            <h3>{`${listing.street}, ${listing.neighborhood.city}`}</h3>
                                            <p>{Math.floor(listing.price)}₪/month</p>
                                        </>
                                    ) : (
                                        <p>Apartment #{favorite.listing_id}</p>
                                    )}
                                </div>
                            </div>
                        );
                    })
                ) : (
                    <div className={styles.emptyState}>
                        <p>No favorites yet. Start swiping to add some!</p>
                    </div>
                )}
            </div>
            
            {favorites.length > 0 && (
                <div className={styles.editButtonContainer}>
                    <button 
                        className={styles.editButton}
                        onClick={() => setIsEditing(!isEditing)}
                    >
                        {isEditing ? 'Done' : 'Edit'}
                    </button>
                </div>
            )}

            <div className={styles.bottomBar}>
                <button 
                    className={styles.bottomBarButton} 
                    onClick={() => navigate('/apartment-swipe')}
                >
                    <img src={HomeIcon} alt="Home" />
                </button>
                <button className={`${styles.bottomBarButton} ${styles.active}`}>
                    <img src={HeartIcon} alt="Favorites" />
                </button>
                <button 
                    className={styles.bottomBarButton}
                    onClick={() => navigate('/neighborhoods')}
                >
                    <MapPin size={24} alt="Neighborhoods" style={{ width: '28px', height: '28px', stroke: '#371b34', strokeWidth: '1.5' }} />
                </button>
            </div>
        </div>
    );
};

export default FavoritesPage;