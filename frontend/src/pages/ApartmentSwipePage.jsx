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
    const { apartments: initialApartments, loading, error: useApartmentsError } = useApartments();
    const [apartments, setApartments] = useState([]);
    const swiperRef = useRef(null);
    const [isDetailSheetOpen, setIsDetailSheetOpen] = useState(false);
    const [detailedApartmentIndex, setDetailedApartmentIndex] = useState(null);
    const { addFavorite } = useFavorites();
    const navigate = useNavigate();
    const [swipeIntent, setSwipeIntent] = useState(null); // Stores { swipedApartmentOrderId: string, actionType: 'like' | 'dislike' }

    useEffect(() => {
        if (initialApartments && initialApartments.length > 0 && apartments.length === 0) {
            setApartments(initialApartments);
        }
    }, [initialApartments, apartments.length]);

    useEffect(() => {
        const swiperInstance = swiperRef.current?.swiper;
        if (swiperInstance && !swiperInstance.destroyed) {
            swiperInstance.update();
            // console.log("Swiper updated due to apartments change. New slide count:", swiperInstance.slides.length);
        }
    }, [apartments]);

    const currentDetailedApartment = (detailedApartmentIndex !== null && detailedApartmentIndex < apartments.length && apartments[detailedApartmentIndex])
        ? apartments[detailedApartmentIndex]
        : null;

    const handleApartmentAction = async (apartmentOrderId, actionType) => {
        const apartmentToAction = apartments.find(apt => apt.order_id === apartmentOrderId);
        if (!apartmentToAction) {
            console.warn("Apartment for action not found in current list:", apartmentOrderId);
            return;
        }

        console.log(`Performing action '${actionType}' on apartment:`, apartmentToAction.order_id);

        if (actionType === 'like') {
            try {
                await addFavorite(apartmentToAction.order_id);
                console.log("Successfully added to favorites:", apartmentToAction.order_id);
            } catch (err) {
                console.error("Failed to add to favorites:", err);
            }
        }

        setApartments(prevApartments => prevApartments.filter(apt => apt.order_id !== apartmentOrderId));
        
        if (isDetailSheetOpen && currentDetailedApartment && currentDetailedApartment.order_id === apartmentOrderId) {
            closeDetailSheet();
        }
    };

    const handleSlideChange = (swiper) => {
        console.log(`Slide changed to index: ${swiper.activeIndex}. Total slides: ${swiper.slides.length}`);
    };

    const handleReachEnd = () => {
        console.log("Reached the end of available apartments in Swiper! fetching more apartments...");
    };

    const triggerSwipe = async (direction) => {
        const currentSwiper = swiperRef.current?.swiper;
        if (!currentSwiper) {
            console.log("Swiper not ready for button action.");
            return;
        }

        const currentVisibleIndex = currentSwiper.activeIndex;
        if (currentVisibleIndex < 0 || currentVisibleIndex >= apartments.length) {
            console.log("No apartment at current swiper index or apartments list is empty.");
            return;
        }
        
        const apartmentToProcess = apartments[currentVisibleIndex];
        if (!apartmentToProcess) {
            console.log("No current apartment found for button action (apartmentToProcess is null/undefined).");
            return;
        }
        
        console.log("Button action for apartment:", apartmentToProcess.order_id, "Direction:", direction);
        const actionType = direction === 'right' ? 'like' : 'dislike';
        await handleApartmentAction(apartmentToProcess.order_id, actionType);
    };
    
    const recordSwipeIntent = (swiper) => {
        // Ensure there's a swipe direction and the activeIndex is valid for the current apartments array.
        if (!swiper.swipeDirection || swiper.activeIndex < 0 || swiper.activeIndex >= apartments.length) {
            setSwipeIntent(null); 
            // console.log("Swipe intent cleared: no direction or activeIndex out of bounds.", swiper.swipeDirection, swiper.activeIndex, apartments.length);
            return;
        }

        const swipedApartment = apartments[swiper.activeIndex]; // Get the apartment using the current activeIndex
        if (!swipedApartment) {
            console.warn(`Swipe gesture intent: no apartment found at activeIndex ${swiper.activeIndex}.`);
            setSwipeIntent(null);
            return;
        }

        // User-defined mapping: 'next' (swipe right) is 'dislike', 'prev' (swipe left) is 'like'.
        const actionType = swiper.swipeDirection === 'next' ? 'dislike' : 'like'; 
        console.log(`Swipe intent recorded: ${actionType} for apartment ${swipedApartment.order_id} (index ${swiper.activeIndex})`);
        setSwipeIntent({
            swipedApartmentOrderId: swipedApartment.order_id,
            actionType: actionType
            // fromIndex is no longer stored
        });
    };

    const processSwipeAction = (swiper) => {
        if (swipeIntent && swipeIntent.swipedApartmentOrderId) {
            const { swipedApartmentOrderId, actionType } = swipeIntent;
            console.log(`TransitionEnd: Processing action '${actionType}' for apartment ${swipedApartmentOrderId}`);
            handleApartmentAction(swipedApartmentOrderId, actionType);
            setSwipeIntent(null); // Clear intent after processing
        } else if (swipeIntent) {
            // If swipeIntent exists but is somehow invalid (e.g., missing order_id), clear it.
            // console.log("TransitionEnd: swipeIntent present but invalid, clearing.");
            setSwipeIntent(null);
        }
    };

    const openDetailSheet = (index) => {
        const apartmentForDetail = apartments[index];
        if (apartmentForDetail) {
             console.log(`Opening details for apartment ID: ${apartmentForDetail.order_id} at index: ${index}`);
            setDetailedApartmentIndex(index);
            setIsDetailSheetOpen(true);
        } else {
            console.warn("Attempted to open details with invalid index or apartment not found:", index);
        }
    };

    const closeDetailSheet = () => {
        setIsDetailSheetOpen(false);
        setDetailedApartmentIndex(null);
    };
    
    const bind = useDrag(({ active, movement: [, my], direction: [, dy], cancel, event }) => {
        const targetElement = event.target;
        const buttonsContainer = targetElement.closest(`.${styles.buttonsContainer}`);
        if (buttonsContainer) {
            return;
        }

        const isSwipeUp = !active && dy < 0 && my < SWIPE_UP_THRESHOLD;

        if (isSwipeUp) {
            const currentSwiper = swiperRef.current?.swiper;
            if (currentSwiper) {
                const currentSwiperIndex = currentSwiper.activeIndex;
                 console.log(`Swipe Up detected on page, current swiper index: ${currentSwiperIndex}`);
                openDetailSheet(currentSwiperIndex);
            } else {
                console.log("Swipe Up detected, but Swiper not ready.");
            }
            if (cancel) cancel();
        }
    }, {
        axis: 'y',
        filterTaps: true,
        enabled: !isDetailSheetOpen,
    });

    if (loading && apartments.length === 0) return <div className={styles.message}>Loading apartments...</div>;
    if (useApartmentsError) return <div className={`${styles.message} ${styles.error}`}>Error: {useApartmentsError}</div>;

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
                            onTouchEnd={recordSwipeIntent}
                            onTransitionEnd={processSwipeAction}
                        >
                            {apartments.map((apartment) => (
                                <SwiperSlide key={apartment.order_id} className={styles.swipe}>
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