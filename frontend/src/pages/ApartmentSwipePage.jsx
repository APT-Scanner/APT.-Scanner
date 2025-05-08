import React, { useState, useRef, useEffect } from 'react';
import { Swiper, SwiperSlide } from 'swiper/react';
import { EffectCards } from 'swiper/modules';
import 'swiper/css';
import 'swiper/css/effect-cards';
import { useDrag } from '@use-gesture/react'; 
import { useApartments } from '../hooks/useApartments';
import styles from '../styles/ApartmentSwipePage.module.css';
import ApartmentDetailSheet from './ApartmentDetailSheet';
import { Heart, X } from 'lucide-react';
import logo from "../assets/logo-swipe-screen.jpeg";
import HomeIcon from '../assets/home_pressed.svg';
import HeartOutlineIcon from '../assets/heart_not_pressed.svg';
import SettingsIcon from '../assets/settings_not_pressed.svg';
import { useFavorites } from '../hooks/useFavorites';
import { useNavigate } from 'react-router-dom';

const SWIPE_UP_THRESHOLD = -5; 

const ApartmentSwipePage = () => {
    const { apartments: initialApartments, loading, error } = useApartments();
    const [apartments, setApartments] = useState([]);
    const swiperRef = useRef(null);
    const [isDetailSheetOpen, setIsDetailSheetOpen] = useState(false);
    const [detailedApartmentIndex, setDetailedApartmentIndex] = useState(null);
    const { addFavorite } = useFavorites();
const navigate = useNavigate();

    useEffect(() => {
        if (initialApartments.length > 0) {
            setApartments(initialApartments);
        }
    }, [initialApartments]);

    const handleSlideChange = (swiper) => {
        console.log(`Slide changed to index: ${swiper.activeIndex}`);
        if (isDetailSheetOpen) {
            closeDetailSheet();
        }
    };

    const handleReachEnd = () => {
        console.log("Reached the end of apartments!");
    };

    const triggerSwipe = async (direction) => {
        const currentApartment = apartments[swiperRef.current?.swiper?.activeIndex];
        if (!currentApartment) {
            console.log("No current apartment found or Swiper not ready.");
            return;
        }
        
        // Log the apartment object to see its structure
        console.log("Current apartment:", currentApartment);
        
        // Add to favorites if swiped right
        if (direction === 'right') {
            try {
                // Use order_id instead of id (backend uses order_id as the primary key)
                await addFavorite(currentApartment.order_id);
                console.log("Added to favorites:", currentApartment.order_id);
            } catch (error) {
                console.error("Failed to add to favorites:", error);
            }
        }
        
        // Advance to next slide
        swiperRef.current?.swiper?.slideNext();
    };
    
    const openDetailSheet = (index) => {
        if (index !== undefined && index !== null && index >= 0 && index < apartments.length) {
            console.log(`Opening details for apartment index: ${index}`);
            setDetailedApartmentIndex(index);
            setIsDetailSheetOpen(true);
        } else {
            console.warn("Attempted to open details with invalid index:", index);
        }
    };

    const closeDetailSheet = () => {
        setIsDetailSheetOpen(false);
    };

    
    const bind = useDrag(({ active, movement: [, my], direction: [, dy], cancel, event }) => {
        const targetElement = event.target;
        const buttonsContainer = targetElement.closest(`.${styles.buttonsContainer}`);
        if (buttonsContainer) {
            return;
        }

        const isSwipeUp = !active && dy < 0 && my < SWIPE_UP_THRESHOLD;

        if (isSwipeUp) {
            const currentSwiperIndex = swiperRef.current?.swiper?.activeIndex;
            console.log(`Swipe Up detected on page, current swiper index: ${currentSwiperIndex}`);
            openDetailSheet(currentSwiperIndex);
            if (cancel) cancel();
        }
    }, {
        axis: 'y',
        filterTaps: true,
        enabled: !isDetailSheetOpen,
    });

    if (loading) return <div className={styles.message}>Loading apartments...</div>;
    if (error) return <div className={`${styles.message} ${styles.error}`}>Error: {error}</div>;

    const currentDetailedApartment = detailedApartmentIndex !== null && detailedApartmentIndex < apartments.length
        ? apartments[detailedApartmentIndex]
        : null;

    return (
        <div
            {...bind()}
            className={`${styles.pageWrapper} ${isDetailSheetOpen ? styles.detailsActive : ''}`}
            style={{ touchAction: 'pan-y' }}
        >
            <div className={styles.pageContainer}>
                <img src={logo} alt="APT.Scanner logo" className={styles.logo} />

                <div className={styles.cardContainer}>
                    {apartments.length > 0 ? (
                        <Swiper
                            ref={swiperRef}
                            modules={[EffectCards]}
                            effect={"cards"}
                            grabCursor={!isDetailSheetOpen}
                            centeredSlides={true}
                            slidesPerView={'auto'}
                            cardsEffect={{
                                perSlideOffset: 0,
                                perSlideRotate: 0,
                                rotate: false,
                                slideShadows: true,
                            }}
                            onSlideChange={handleSlideChange}
                            onReachEnd={handleReachEnd}
                            className={styles.swiperContainer}
                            allowTouchMove={!isDetailSheetOpen}
                        >
                            {apartments.map((apartment) => (
                                <SwiperSlide key={apartment.id} className={styles.swipe}>
                                    <div style={{ height: '100%', width: '100%' }}>
                                        <div style={{ backgroundImage: `url(${apartment.cover_image_url || apartment.image || ''})` }} className={styles.card}>
                                            <div className={styles.cardInfo}>
                                                <h3>{`${apartment.street}, ${apartment.city}`}</h3>
                                                <p>{Math.floor(apartment.price)}₪/month</p>
                                            </div>
                                        </div>
                                    </div>
                                </SwiperSlide>
                            ))}
                        </Swiper>
                    ) : (
                         !loading && (
                            <div className={styles.message}>
                                There are no more apartments to swipe right now...
                            </div>
                        )
                    )}
                </div>

                {apartments.length > 0 && (
                    <div className={`${styles.buttonsContainer} ${isDetailSheetOpen ? styles.buttonsHidden : ''}`}>
                        <button onClick={() => triggerSwipe('left')} className={`${styles.button} ${styles.dislike}`} disabled={isDetailSheetOpen}>
                            <X size={32} color="#ffffff" />
                        </button>
                        <button onClick={() => triggerSwipe('right')} className={`${styles.button} ${styles.like}`} disabled={isDetailSheetOpen}>
                            <Heart size={32} color="#ffffff" />
                        </button>
                    </div>
                )}
            </div> 

            {currentDetailedApartment && (
                <ApartmentDetailSheet
                    apartment={currentDetailedApartment}
                    isOpen={isDetailSheetOpen}
                    onClose={closeDetailSheet}
                />
            )}

            <div className={styles.bottomBar}>
            <button className={styles.bottomBarButton}
            onClick={() => navigate('/apartment-swipe')}>
                <img src={HomeIcon} alt="Home" className={styles.bottomBarButton} />
            </button>
            <button className={styles.bottomBarButton}
            onClick={() => navigate('/favorites')}>
                <img src={HeartOutlineIcon} alt="Heart" className={styles.bottomBarButton} />
            </button>
            <button className={styles.bottomBarButton}>
                <img src={SettingsIcon} alt="Settings" className={styles.bottomBarButton} />
            </button>
            </div>
        </div> 
    );
};

export default ApartmentSwipePage;