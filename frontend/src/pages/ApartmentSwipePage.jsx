import React, { useState, useEffect, useCallback, useRef, forwardRef, useMemo } from 'react';
import { motion, AnimatePresence, useMotionValue, useTransform, animate } from 'framer-motion';
import { useDrag } from '@use-gesture/react';
import { useApartments } from '../hooks/useApartments';
import { useViewHistory } from '../hooks/useViewHistory';
import { useFilters } from '../hooks/useFilters';
import styles from '../styles/ApartmentSwipePage.module.css';
import ApartmentDetailSheet from './ApartmentDetailSheet';
import { Heart, X, ChevronUp, ChevronDown, Image as ImageIcon, Loader, Filter, Menu, Maximize, Minimize, ChevronLeft, ChevronRight } from 'lucide-react';
import logo from "../assets/logo-swipe-screen.jpeg";
import HomeIcon from '../assets/home_pressed.svg';
import HeartOutlineIcon from '../assets/heart_not_pressed.svg';
import SettingsIcon from '../assets/settings_not_pressed.svg';
import { useFavorites } from '../hooks/useFavorites';
import { useNavigate } from 'react-router-dom';
import PropTypes from 'prop-types';


export const AnimatedApartmentCard = forwardRef(({ apartment, onSwipeComplete, disableSwipe = false }, ref) => {
    const [currentImageIndex, setCurrentImageIndex] = useState(0);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const x = useMotionValue(0);
    const rotate = useTransform(x, [-200, 0, 200], [-25, 0, 25], { clamp: false });
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
                            if (onSwipeComplete) {
                                onSwipeComplete(swipeDirection, apartment.order_id);
                            }
                        },
                    });
                } else {
                    animate(x, 0, { type: 'spring', stiffness: 500, damping: 30 });
                }
            }
        },
        { filterTaps: true, rubberband: 0.2, from: () => [x.get(), 0] }
    );
    const images = React.useMemo(() => {
        const availableImages = [];
        
        if (apartment.cover_image_url && apartment.cover_image_url.trim() !== '') {
            availableImages.push(apartment.cover_image_url);
        }
        
        if (apartment.images && Array.isArray(apartment.images)) {
            console.log(apartment.images);
            apartment.images.forEach(img => {
                if (img.image_url && img.image_url.trim() !== '' && !availableImages.includes(img.image_url)) {
                    availableImages.push(img.image_url);
                }
            });
        }
        
        if (availableImages.length === 0) {
            availableImages.push('');
        }
        
        return availableImages;
    }, [apartment]);

    const handleImageClick = (e) => {
        e.stopPropagation();
        e.preventDefault();
        
        setCurrentImageIndex((prevIndex) => (prevIndex + 1) % images.length);
    };
    
    const toggleFullscreen = (e) => {
        e.stopPropagation();
        e.preventDefault();
        setIsFullscreen(prev => !prev);
        
        // Prevent body scroll when in fullscreen
        if (!isFullscreen) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = '';
        }
    };
    
    const nextImage = () => {
        setCurrentImageIndex((prevIndex) => (prevIndex + 1) % images.length);
    };
    
    const prevImage = () => {
        setCurrentImageIndex((prevIndex) => (prevIndex - 1 + images.length) % images.length);
    };
    
    // Clean up overflow style when component unmounts or when exiting fullscreen
    useEffect(() => {
        return () => {
            document.body.style.overflow = '';
        };
    }, []);
    
    // Handle keyboard navigation in fullscreen mode
    useEffect(() => {
        const handleKeyDown = (e) => {
            if (!isFullscreen) return;
            
            if (e.key === 'Escape') {
                setIsFullscreen(false);
                document.body.style.overflow = '';
            } else if (e.key === 'ArrowRight') {
                nextImage();
            } else if (e.key === 'ArrowLeft') {
                prevImage();
            }
        };
        
        window.addEventListener('keydown', handleKeyDown);
        return () => {
            window.removeEventListener('keydown', handleKeyDown);
        };
    }, [isFullscreen, images.length]);
    
    return (
        <>
            <motion.div
                ref={ref}
                {...(disableSwipe ? {} : gestureBind())}
                className={styles.animatedCardWrapper}
                style={{
                    x: disableSwipe ? 0 : x,
                    rotate: disableSwipe ? 0 : rotate,
                    touchAction: 'none',
                }}
                initial={{ scale: 0.9, opacity: 0, y: 30 }}
                animate={{ scale: 1, opacity: 1, y: 0, transition: { type: 'spring', stiffness: 400, damping: 25, duration: 0.3 } }}
                exit={{
                    x: disableSwipe ? 0 : (x.get() > 0 ? 300 : (x.get() < 0 ? -300 : 0)),
                    opacity: 0,
                    scale: 0.8,
                    transition: { duration: 0.3, ease: "easeIn" }
                }}
            >
                <div 
                    style={{ backgroundImage: `url(${images[currentImageIndex]})` }} 
                    className={styles.cardContentVisual}
                    onClick={handleImageClick}
                >
                    <button 
                        className={styles.fullscreenButton}
                        onClick={toggleFullscreen}
                        aria-label="View full-screen"
                    >
                        <Maximize size={20} stroke="white" fill="white" />
                    </button>
                    
                    {images.length > 1 && (
                        <div className={styles.imageCounter}>
                            <ImageIcon size={14} />
                            <span>{currentImageIndex + 1}/{images.length}</span>
                        </div>
                    )}
                    <div className={styles.cardInfo}>
                        <h3>{`${apartment.street}, ${apartment.city}`}</h3>
                        <p>{Math.floor(apartment.price)}₪/month</p>
                    </div>
                </div>
            </motion.div>
            
            {/* Fullscreen Gallery Modal */}
            {isFullscreen && (
                <div className={styles.fullscreenOverlay}>
                    <button 
                        className={`${styles.fullscreenButton} ${styles.close}`}
                        onClick={toggleFullscreen}
                        aria-label="Close full-screen"
                    >
                        <X size={24} />
                    </button>
                    
                    <img 
                        src={images[currentImageIndex]} 
                        alt={`${apartment.street}, ${apartment.city}`} 
                        className={styles.fullscreenImage}
                        onClick={handleImageClick}
                    />
                    
                    <div className={styles.fullscreenControls}>
                        <button 
                            className={styles.fullscreenNavButton}
                            onClick={prevImage}
                            aria-label="Previous image"
                        >
                            <ChevronLeft size={24} />
                        </button>
                        
                        <div className={styles.fullscreenCounter}>
                            {currentImageIndex + 1} / {images.length}
                        </div>
                        
                        <button 
                            className={styles.fullscreenNavButton}
                            onClick={nextImage}
                            aria-label="Next image"
                        >
                            <ChevronRight size={24} />
                        </button>
                    </div>
                </div>
            )}
        </>
    );
});


AnimatedApartmentCard.displayName = 'AnimatedApartmentCard';

AnimatedApartmentCard.propTypes = {
    apartment: PropTypes.object.isRequired,
    onSwipeComplete: function(props, propName, componentName) {
        if (!props.disableSwipe && (props[propName] === undefined)) {
            return new Error(
                `The prop ${propName} is required when disableSwipe is false in ${componentName}.`
            );
        }
    },
    disableSwipe: PropTypes.bool,
};

const LoadingSpinner = () => (
  <div className={styles.loadingContainer}>
    <div className={styles.spinner}>
      <Loader size={40} className={styles.spinnerIcon} />
      <p>Loading apartments...</p>
    </div>
  </div>
);

const ApartmentSwipePage = () => {
    const { getFilterQueryParams } = useFilters();
    
    const filterParams = useMemo(() => getFilterQueryParams(), [getFilterQueryParams]);
    
    const [refreshTrigger, setRefreshTrigger] = useState(0);
    
    const { apartments: fetchedApartments, loading: apartmentsLoading, error: useApartmentsError } = useApartments({ 
        filterViewed: true,
        filterParams,
        refreshTrigger,
    });
    
    const { recordView, filterViewedApartments, loading: viewHistoryLoading } = useViewHistory();
    
    const [apartments, setApartments] = useState([]);
    const [detailsExpanded, setDetailsExpanded] = useState(false);
    const { addFavorite } = useFavorites();
    const navigate = useNavigate();
    
    const detailsPanelRef = useRef(null);
    const detailsPanelY = useMotionValue(0);
    
    const [windowHeight, setWindowHeight] = useState(typeof window !== 'undefined' ? window.innerHeight : 0);


    useEffect(() => {
        const handleResize = () => {
            setWindowHeight(window.innerHeight);
        };
        
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    useEffect(() => {
        if (fetchedApartments && fetchedApartments.length > 0 && !viewHistoryLoading) {
            const filteredApartments = filterViewedApartments(fetchedApartments);
            
            if (filteredApartments.length === 0 && fetchedApartments.length > 0) {
                setApartments(fetchedApartments);
            } else {
                setApartments(filteredApartments);
            }
        }
    }, [fetchedApartments, viewHistoryLoading, filterViewedApartments]);

    const currentApartment = apartments.length > 0 ? apartments[0] : null;

    const handleSwipeAction = useCallback((actionType, apartmentOrderId) => {
        setApartments(prev => prev.filter(apt => apt.order_id !== apartmentOrderId));
        
        recordView(apartmentOrderId);
        
        setDetailsExpanded(false);
        
        if (actionType === 'like') {
            addFavorite(apartmentOrderId).catch(() => {});
        }
    }, [addFavorite, recordView]);

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
        if (!detailsExpanded && detailsPanelRef.current) {
            const detailsContent = detailsPanelRef.current.querySelector(`.${styles.detailsContent}`);
            if (detailsContent) {
                detailsContent.scrollTop = 0;
            }
        }
        
        setDetailsExpanded(!detailsExpanded);
        
        animate(detailsPanelY, 0, {
            type: 'spring',
            stiffness: 400,
            damping: 40
        });
    };

    const detailsPanelDrag = useDrag(
        ({ active, movement: [_, my], direction: [__, dy], velocity: [___, vy], cancel }) => {
            if (active) {
                const newY = detailsExpanded 
                    ? Math.max(0, my) 
                    : Math.min(0, my); 
                detailsPanelY.set(newY);
            } else {
                const significantDrag = Math.abs(my) > 80 || Math.abs(vy) > 0.5;
                
                if (significantDrag) {
                    if ((detailsExpanded && dy > 0) || (!detailsExpanded && dy < 0)) {
                        toggleDetailsPanel();
                    } else {
                        animate(detailsPanelY, 0, {
                            type: 'spring',
                            stiffness: 400,
                            damping: 40
                        });
                    }
                } else {
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
            bounds: { top: -300, bottom: 300 } 
        }
    );

    const expandedPanelHeight = windowHeight - 80; 
    const collapsedPanelHeight = 120; 

    const loading = apartmentsLoading || viewHistoryLoading;
    
    const handleNavigateToFilter = () => {
        navigate('/filter');
    };

    useEffect(() => {
        const handleVisibilityChange = () => {
            if (document.visibilityState === 'visible') {
                setRefreshTrigger(prev => prev + 1);
            }
        };
        
        document.addEventListener('visibilitychange', handleVisibilityChange);
        
        return () => {
            document.removeEventListener('visibilitychange', handleVisibilityChange);
        };
    }, []);

    if (loading && apartments.length === 0 && fetchedApartments.length === 0) return <LoadingSpinner />;
    if (useApartmentsError) return <div className={styles.errorContainer}>Error: {useApartmentsError.message || String(useApartmentsError)}</div>;

    return (
        <div className={styles.pageWrapper}>
            {/* Header for Menu Icon and Filter Icon */}
            <div className={styles.swipePageHeader}>
                <button className={styles.menuButton} >
                    <Menu size={28} color="#333" />
                </button>
                <div className={styles.logo}>
                    <img src={logo} alt="APT.Scanner logo" style={{ maxWidth: '80%', height: 'auto' }} />
                </div>
                <button 
                    className={styles.filterButton}
                    onClick={handleNavigateToFilter}
                    aria-label="Filter apartments"
                >
                    <Filter size={24} />
                </button>
            </div>

            <div className={`${styles.pageContainer} ${detailsExpanded ? styles.detailsActive : ''}`}>
                {useApartmentsError && <div className={styles.errorContainer}>Error: {useApartmentsError.message || String(useApartmentsError)}</div>}
                
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
                    {loading && apartments.length > 0 && (
                        <div className={styles.inlineLoadingIndicator}>
                            <Loader size={24} className={styles.spinnerIcon} />
                        </div>
                    )}
                    {!loading && !currentApartment && (
                        <div className={`${styles.message} ${styles.noMoreApartmentsMessage}`}>
                            There are no more apartments to swipe right now...
                        </div>
                    )}
                    
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
                </div>
                
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