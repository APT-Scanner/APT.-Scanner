import React, { useState, useRef, useEffect } from 'react';
import { Swiper, SwiperSlide } from 'swiper/react';
import { EffectCards } from 'swiper/modules';
import 'swiper/css';
import 'swiper/css/effect-cards';
import { useDrag } from '@use-gesture/react'; 
import { useApartments } from '../hooks/useApartments';
import { useAuth } from '../hooks/useAuth';
import styles from '../styles/ApartmentSwipePage.module.css';
import ApartmentDetailSheet from './ApartmentDetailSheet';
import { Heart, X } from 'lucide-react';
import logo from "../assets/logo-swipe-screen.jpeg";

const safeSwiperAction = (swiperRef, action) => {
    if (swiperRef.current && swiperRef.current.swiper) {
        action(swiperRef.current.swiper);
    } else {
        console.warn("Swiper instance not available yet.");
    }
};

const SWIPE_UP_THRESHOLD = -5; 

const ApartmentSwipePage = () => {
    const { apartments: initialApartments, loading, error } = useApartments();
    const { idtoken } = useAuth();
    const [apartments, setApartments] = useState([]);
    const swiperRef = useRef(null);
    const [isDetailSheetOpen, setIsDetailSheetOpen] = useState(false);
    const [detailedApartmentIndex, setDetailedApartmentIndex] = useState(null);

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
        // You could potentially load more apartments here
    };

    // Function triggered by Like/Dislike buttons
    const triggerSwipe = (direction) => {
        const currentApartment = apartments[swiperRef.current?.swiper?.activeIndex];
        if (!currentApartment) {
            console.log("No current apartment found or Swiper not ready.");
            return;
        }
    }

    const openDetailSheet = (index) => {
        if (index !== undefined && index !== null && index >= 0 && index < apartments.length) {
            console.log(`Opening details for apartment index: ${index}`);
            setDetailedApartmentIndex(index);
            setIsDetailSheetOpen(true);
        } else {
            console.warn("Attempted to open details with invalid index:", index);
        }
    };

    // פונקציה לסגירת חלון הפרטים
    const closeDetailSheet = () => {
        setIsDetailSheetOpen(false);
        // אפשר להוסיף השהיה קטנה לפני איפוס האינדקס כדי לאפשר לאנימציה להסתיים
        // setTimeout(() => setDetailedApartmentIndex(null), 300);
    };

    
    // Hook לזיהוי החלקה למעלה - מוחל על כל העמוד
    const bind = useDrag(({ active, movement: [, my], direction: [, dy], cancel, event }) => {
        // מניעת הפעלה אם הגרירה מתחילה על הכפתורים
        const targetElement = event.target;
        const buttonsContainer = targetElement.closest(`.${styles.buttonsContainer}`);
        if (buttonsContainer) {
            // אם רוצים לבטל את הגרירה לגמרי כשהיא מתחילה על הכפתור
            // if (cancel) cancel();
            return;
        }

        const isSwipeUp = !active && dy < 0 && my < SWIPE_UP_THRESHOLD;

        if (isSwipeUp) {
            // קבל את האינדקס הנוכחי מה-Swiper
            const currentSwiperIndex = swiperRef.current?.swiper?.activeIndex;
            console.log(`Swipe Up detected on page, current swiper index: ${currentSwiperIndex}`);
            openDetailSheet(currentSwiperIndex); // פתח פרטים עבור השקופית הנוכחית
            if (cancel) cancel();
        }
    }, {
        axis: 'y',
        filterTaps: true,
        enabled: !isDetailSheetOpen, // (*) מופעל רק אם חלון הפרטים סגור
        // אפשר להוסיף eventOptions אם יש בעיות עם stopPropagation/preventDefault
        // eventOptions: { passive: false },
    });

    if (loading) return <div className={styles.message}>Loading apartments...</div>;
    if (error) return <div className={`${styles.message} ${styles.error}`}>Error: {error}</div>;

    // קבל את הדירה הנוכחית להצגה בפרטים (אם יש)
    const currentDetailedApartment = detailedApartmentIndex !== null && detailedApartmentIndex < apartments.length
        ? apartments[detailedApartmentIndex]
        : null;

    return (
        // החלת bind על העטיפה הראשית של העמוד
        <div
            {...bind()} // (*) החל את bind כאן
            className={`${styles.pageWrapper} ${isDetailSheetOpen ? styles.detailsActive : ''}`}
            // נדרש כדי לאפשר גלילה אנכית על ידי הדפדפן, אחרת useDrag עשוי לחסום אותה
             style={{ touchAction: 'pan-y' }}
        >
            {/* שים לב: אם pageWrapper לא עוטף את הכל, החל את bind על pageContainer */}
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
                            {apartments.map((apartment, index) => (
                                <SwiperSlide key={apartment.id} className={styles.swipe}>
                                    {/* (*) הסרנו את bind מכאן */}
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

                {/* כפתורי לייק/דיסלייק */}
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
            </div> {/* סוף pageContainer */}

             {/* רינדור חלון הפרטים */}
              {currentDetailedApartment && (
                 <ApartmentDetailSheet
                    apartment={currentDetailedApartment}
                    isOpen={isDetailSheetOpen}
                    onClose={closeDetailSheet}
                />
            )}

        </div> // סוף pageWrapper
    );
};

export default ApartmentSwipePage;