import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useFavorites } from '../hooks/useFavorites';
import { useListings } from '../hooks/useListings'; 
import styles from '../styles/FavoritesPage.module.css';
import HomeIcon from '../assets/home_not_pressed.svg';
import HeartIcon from '../assets/heart_pressed.svg';
import SettingsIcon from '../assets/settings_not_pressed.svg';
import { Menu, Filter } from 'lucide-react';

const FavoritesPage = () => {
    const { favorites, loading: favoritesLoading, error: favoritesError, removeFavorite } = useFavorites();
    const { listings, getListing, loading: listingsLoading } = useListings();
    const [isEditing, setIsEditing] = useState(false);
    const navigate = useNavigate();

    useEffect(() => {
        if (favorites.length > 0) {
            favorites.forEach(favorite => {
                if (!listings[favorite.listing_id]) {
                    getListing(favorite.listing_id);
                }
            });
        }
    }, [favorites, getListing, listings]);

    if (favoritesLoading) return <div className={styles.loadingContainer}>Loading favorites...</div>;
    if (favoritesError) return <div className={styles.errorContainer}>Error: {favoritesError}</div>;

    console.log("Favorites:", favorites);
    console.log("Listings details:", listings);

    return (
        <div className={styles.pageWrapper}>
            <div className={styles.header}>
                <button className={styles.iconButton}>
                    <Menu size={24} color="#000"/>
                </button>
                <h1>Favorites</h1>
                <button className={styles.iconButton}>
                    <Filter size={24} color="#000"/>
                </button>
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
                            <div key={favorite.id} className={styles.favoriteCard}>
                                <div 
                                    className={styles.favoriteImage} 
                                    style={{ 
                                        backgroundImage: listing 
                                            ? `url(${listing.cover_image_url || listing.image || '/assets/apartment-placeholder.jpg'})` 
                                            : 'url(/assets/apartment-placeholder.jpg)'
                                    }}
                                >
                                    {isEditing && (
                                        <button 
                                            onClick={() => removeFavorite(favorite.listing_id)}
                                            className={styles.removeButton}
                                        >
                                            ×
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
                                            <h3>{`${listing.street}, ${listing.city}`}</h3>
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
            
            {/* Rest of component remains the same */}
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
                    onClick={() => navigate('/settings')}
                >
                    <img src={SettingsIcon} alt="Settings" />
                </button>
            </div>
        </div>
    );
};

export default FavoritesPage;