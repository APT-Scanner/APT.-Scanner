import React from 'react';
import styles from '../styles/FavoritesApartmentDetails.module.css';
import { useParams, useNavigate } from 'react-router-dom';
import { useApartment } from '../hooks/useApartment';
import ApartmentDetailSheet from './ApartmentDetailSheet';
import { ArrowLeft } from 'lucide-react';
import { AnimatePresence } from 'framer-motion';
import AnimatedApartmentCard from '../components/AnimatedApartmentCard';
import logo from "../assets/logo-swipe-screen.jpeg";
import { LoadingSpinner } from '../components/LoadingSpinner';


const FavoritesApartmentDetails = () => {
    const { listing_id } = useParams();
    const navigate = useNavigate();
    const { apartment, loading, error } = useApartment(listing_id);

    console.log("Apartment details:", apartment);

    if (loading) {
        return <LoadingSpinner />;
    }

    if (error) {
        return <div className={styles.errorContainer}>Error: {error}</div>;
    }

    if (!apartment) {
        return <div className={styles.errorContainer}>No apartment found with this ID</div>;
    }

    const handleBackButtonClick = () => {
        navigate('/favorites');
    };

    return (
        <div className={styles.pageWrapper}>
            <div className={styles.header}>
                <button className={styles.backButton}>
                    <ArrowLeft size={24} onClick={() => handleBackButtonClick()}/>
                </button>
                <img src={logo} alt="APT.Scanner logo" className={styles.logo} />
            </div>     
            <div className={styles.cardContainer}>
                <AnimatePresence mode="popLayout">
                    {apartment && (
                        <AnimatedApartmentCard
                            key={apartment.listing_id}
                            apartment={apartment}
                            disableSwipe={true}
                        />
                    )}
                </AnimatePresence>
            </div>
            <div className={styles.detailsContainer}>
                <ApartmentDetailSheet 
                    apartment={apartment} 
                />
            </div>
        </div>
    );
};

export default FavoritesApartmentDetails;
