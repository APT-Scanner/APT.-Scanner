import React from 'react';
import styles from '../styles/FavoritesApartmentDetails.module.css';
import { useParams } from 'react-router-dom';
import { useApartment } from '../hooks/useApartment';
import ApartmentDetailSheet from './ApartmentDetailSheet';
import { Loader, ArrowLeft } from 'lucide-react';
import { AnimatePresence } from 'framer-motion';
import {AnimatedApartmentCard} from './ApartmentSwipePage';
import logo from "../assets/logo-swipe-screen.jpeg";
import { useNavigate } from 'react-router-dom';
const LoadingSpinner = () => (
  <div className={styles.loadingContainer}>
    <div className={styles.spinner}>
      <Loader size={40} className={styles.spinnerIcon} />
      <p>Loading apartment details...</p>
    </div>
  </div>
);

const FavoritesApartmentDetails = () => {
    const { token } = useParams();
    const navigate = useNavigate();
    const { apartment, loading, error } = useApartment(token);

    console.log("Apartment details:", apartment);

    if (loading) {
        return <LoadingSpinner />;
    }

    if (error) {
        return <div className={styles.errorContainer}>Error: {error}</div>;
    }

    if (!apartment) {
        return <div className={styles.errorContainer}>No apartment found with this token</div>;
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
                            key={apartment.order_id}
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
