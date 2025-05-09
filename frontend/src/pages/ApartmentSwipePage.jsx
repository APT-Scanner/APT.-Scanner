import React, { useState, useEffect, useCallback, useRef, forwardRef } from 'react';
import { motion, AnimatePresence, useMotionValue, useTransform, animate } from 'framer-motion';
import { useDrag } from '@use-gesture/react';
import { useApartments } from '../hooks/useApartments';
import styles from '../styles/ApartmentSwipePage.module.css';
import ApartmentDetailSheet from './ApartmentDetailSheet';
import { Heart, X, ChevronUp, ChevronDown } from 'lucide-react';
import logo from "../assets/logo-swipe-screen.jpeg";
import HomeIcon from '../assets/home_pressed.svg';
import HeartOutlineIcon from '../assets/heart_not_pressed.svg';
import SettingsIcon from '../assets/settings_not_pressed.svg';
import { useFavorites } from '../hooks/useFavorites';
import { useNavigate } from 'react-router-dom';
import PropTypes from 'prop-types';

const SWIPE_UP_THRESHOLD = -5;

// Wrap the component with forwardRef to properly handle refs from parent components
const AnimatedApartmentCard = forwardRef(({ apartment, onSwipeComplete }, ref) => {
    const x = useMotionValue(0);
    const rotate = useTransform(x, [-200, 0, 200], [-25, 0, 25], { clamp: false });
    // Use the forwarded ref directly for the gesture binding
    const gestureBind = useDrag(
        ({ active, movement: [mx], direction: [dx], velocity: [vx], cancel }) => {
            if (active) {
                x.set(mx);
            } else {
                if (Math.abs(mx) > 100 || (Math.abs(vx) > 0.4 && Math.abs(mx) > 40)) {
                    const swipeDirection = mx > 0 ? 'right' : 'left';
                    animate(x, swipeDirection === 'right' ? 500 : -500, {
                        type: 'spring',
                        stiffness: 400,
                        damping: 40,
                        onComplete: () => {
                            onSwipeComplete(swipeDirection, apartment.order_id);
                        },
                    });
                } else {
                    animate(x, 0, { type: 'spring', stiffness: 500, damping: 30 });
                }
            }
        },
        { filterTaps: true, rubberband: 0.2, from: () => [x.get(), 0] }
    );
    return (
        <motion.div
            ref={ref}
            {...gestureBind()}
            className={styles.animatedCardWrapper}
            style={{
                x,
                rotate,
                touchAction: 'none',
            }}
            initial={{ scale: 0.9, opacity: 0, y: 30 }}
            animate={{ scale: 1, opacity: 1, y: 0, transition: { type: 'spring', stiffness: 400, damping: 25, duration: 0.3 } }}
            exit={{
                x: x.get() > 0 ? 300 : (x.get() < 0 ? -300 : 0),
                opacity: 0,
                scale: 0.8,
                transition: { duration: 0.3, ease: "easeIn" }
            }}
        >
            <div style={{ backgroundImage: `url(${apartment.cover_image_url || apartment.image || ''})` }} className={styles.cardContentVisual}>
                <div className={styles.cardInfo}>
                    <h3>{`${apartment.street}, ${apartment.city}`}</h3>
                    <p>{Math.floor(apartment.price)}₪/month</p>
                </div>
            </div>
        </motion.div>
    );
});

// Add display name for better debugging
AnimatedApartmentCard.displayName = 'AnimatedApartmentCard';

AnimatedApartmentCard.propTypes = {
    apartment: PropTypes.object.isRequired,
    onSwipeComplete: PropTypes.func.isRequired,
};

const ApartmentSwipePage = () => {
    const { apartments: initialApartments, loading, error: useApartmentsError } = useApartments();
    const [apartments, setApartments] = useState([]);
    const [detailsExpanded, setDetailsExpanded] = useState(false);
    const { addFavorite } = useFavorites();
    const navigate = useNavigate();
    
    // Reference for the details panel for drag gestures
    const detailsPanelRef = useRef(null);
    // Motion value for the sliding animation
    const detailsPanelY = useMotionValue(0);
    
    // Calculate window height for dynamic panel sizing
    const [windowHeight, setWindowHeight] = useState(typeof window !== 'undefined' ? window.innerHeight : 0);
    
    useEffect(() => {
        const handleResize = () => {
            setWindowHeight(window.innerHeight);
        };
        
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    useEffect(() => {
        if (initialApartments && initialApartments.length > 0 && apartments.length === 0) {
            setApartments(initialApartments);
        }
    }, [initialApartments, apartments.length]);

    const currentApartment = apartments.length > 0 ? apartments[0] : null;

    const handleSwipeAction = useCallback((actionType, apartmentOrderId) => {
        setApartments(prev => prev.filter(apt => apt.order_id !== apartmentOrderId));
        setDetailsExpanded(false); // Reset details panel when swiping
        if (actionType === 'like') {
            addFavorite(apartmentOrderId).catch(() => {});
        }
    }, [addFavorite]);

    const handleCardSwipeComplete = (direction, apartmentOrderId) => {
        const actionType = direction === 'right' ? 'like' : 'dislike';
        handleSwipeAction(actionType, apartmentOrderId);
    };

    const triggerButtonSwipe = (direction) => {
        if (!currentApartment) return;
        const actionType = direction === 'right' ? 'like' : 'dislike';
        handleSwipeAction(actionType, currentApartment.order_id);
    };

    const toggleDetailsPanel = () => {
        // When expanding, scroll to top to ensure a good starting point
        if (!detailsExpanded && detailsPanelRef.current) {
            const detailsContent = detailsPanelRef.current.querySelector(`.${styles.detailsContent}`);
            if (detailsContent) {
                detailsContent.scrollTop = 0;
            }
        }
        
        setDetailsExpanded(!detailsExpanded);
        
        // Animate the panel to the appropriate position
        animate(detailsPanelY, 0, {
            type: 'spring',
            stiffness: 400,
            damping: 40
        });
    };

    const detailsPanelDrag = useDrag(
        ({ active, movement: [_, my], direction: [__, dy], velocity: [___, vy], cancel }) => {
            // Don't allow dragging beyond certain bounds
            if (active) {
                const newY = detailsExpanded 
                    ? Math.max(0, my) // When expanded, only allow dragging down
                    : Math.min(0, my); // When collapsed, only allow dragging up
                detailsPanelY.set(newY);
            } else {
                // When released, check if it was a significant drag
                const significantDrag = Math.abs(my) > 80 || Math.abs(vy) > 0.5;
                
                if (significantDrag) {
                    // If dragging down while expanded, or up while collapsed
                    if ((detailsExpanded && dy > 0) || (!detailsExpanded && dy < 0)) {
                        toggleDetailsPanel();
                    } else {
                        // If the drag was in the wrong direction, animate back
                        animate(detailsPanelY, 0, {
                            type: 'spring',
                            stiffness: 400,
                            damping: 40
                        });
                    }
                } else {
                    // For small drags, snap back to current state
                    animate(detailsPanelY, 0, {
                        type: 'spring',
                        stiffness: 400,
                        damping: 40
                    });
                }
            }
        },
        {
            axis: 'y',
            filterTaps: true,
            from: () => [0, detailsPanelY.get()],
            bounds: { top: -300, bottom: 300 } // Allow enough drag in both directions
        }
    );

    // Calculate expanded panel height based on window size
    const expandedPanelHeight = windowHeight - 120; // Leave space for the top area and padding
    const collapsedPanelHeight = 120; // Height when collapsed

    if (loading && apartments.length === 0) return <div className={styles.message}>Loading apartments...</div>;
    if (useApartmentsError) return <div className={`${styles.message} ${styles.error}`}>Error: {useApartmentsError.message || String(useApartmentsError)}</div>;

    return (
        <div className={styles.pageWrapper}>
            <div className={`${styles.pageContainer} ${detailsExpanded ? styles.detailsActive : ''}`}>
                <img src={logo} alt="APT.Scanner logo" className={styles.logo} />
                <div className={styles.cardStackContainer}>
                    <AnimatePresence mode="popLayout">
                        {currentApartment && !detailsExpanded && (
                            <AnimatedApartmentCard
                                key={currentApartment.order_id}
                                apartment={currentApartment}
                                onSwipeComplete={handleCardSwipeComplete}
                            />
                        )}
                    </AnimatePresence>
                    {!loading && !currentApartment && (
                        <div className={`${styles.message} ${styles.noMoreApartmentsMessage}`}>
                            There are no more apartments to swipe right now...
                        </div>
                    )}
                </div>
                
                {currentApartment && !detailsExpanded && (
                    <div className={styles.buttonsContainer}>
                        <button onClick={() => triggerButtonSwipe('left')} className={`${styles.button} ${styles.dislike}`}>
                            <X size={32} color="#ffffff" />
                        </button>
                        <button onClick={() => triggerButtonSwipe('right')} className={`${styles.button} ${styles.like}`}>
                            <Heart size={32} color="#ffffff" />
                        </button>
                    </div>
                )}
                
                {currentApartment && (
                    <motion.div 
                        ref={detailsPanelRef}
                        className={styles.detailsContainer}
                        {...detailsPanelDrag()}
                        style={{
                            y: detailsPanelY,
                            height: detailsExpanded ? expandedPanelHeight : collapsedPanelHeight,
                            touchAction: 'none',
                        }}
                        initial={false}
                        animate={{
                            height: detailsExpanded ? expandedPanelHeight : collapsedPanelHeight,
                            transition: { 
                                type: 'spring',
                                stiffness: 300, 
                                damping: 30,
                                duration: 0.4
                            }
                        }}
                    >
                        <div 
                            className={styles.detailsHandle}
                            onClick={toggleDetailsPanel}
                        >
                            {detailsExpanded ? 
                                <ChevronDown size={24} className={styles.handleIcon} /> : 
                                <ChevronUp size={24} className={styles.handleIcon} />
                            }
                            <span>{detailsExpanded ? 'Close Details' : 'See All Details'}</span>
                        </div>
                        
                        <motion.div 
                            className={styles.detailsContent}
                            animate={{
                                opacity: detailsExpanded ? 1 : 0.8,
                                transition: { duration: 0.2 }
                            }}
                        >
                            {currentApartment && (
                                <>  
                                    {/* Always render the full details, they'll be scrollable when expanded */}
                                    <ApartmentDetailSheet apartment={currentApartment} />
                                </>
                            )}
                        </motion.div>
                    </motion.div>
                )}
            </div>
            
            <div className={`${styles.bottomBar} ${detailsExpanded ? styles.bottomBarHidden : ''}`}>
                <button className={styles.bottomBarButton} onClick={() => navigate('/apartment-swipe')}>
                    <img src={HomeIcon} alt="Home" />
                </button>
                <button className={styles.bottomBarButton} onClick={() => navigate('/favorites')}>
                    <img src={HeartOutlineIcon} alt="Heart" />
                </button>
                <button className={styles.bottomBarButton}>
                    <img src={SettingsIcon} alt="Settings" />
                </button>
            </div>
        </div>
    );
};

export default ApartmentSwipePage;