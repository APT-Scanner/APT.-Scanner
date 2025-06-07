import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useApartments } from '../hooks/useApartments';
import { useViewHistory } from '../hooks/useViewHistory';
import { useFilters } from '../hooks/useFilters';
import styles from '../styles/ApartmentSwipePage.module.css';
import ApartmentDetailSheet from './ApartmentDetailSheet';
import { Heart, X, ChevronUp, ChevronDown, Loader, Filter, Menu } from 'lucide-react';
import logo from "../assets/logo-swipe-screen.jpeg";
import HomeIcon from '../assets/home_pressed.svg';
import HeartOutlineIcon from '../assets/heart_not_pressed.svg';
import SettingsIcon from '../assets/settings_not_pressed.svg';
import { useFavorites } from '../hooks/useFavorites';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence, useMotionValue, animate } from 'framer-motion';
import { useDrag } from '@use-gesture/react';
import { LoadingSpinner } from '../components/LoadingSpinner';
import AnimatedApartmentCard from '../components/AnimatedApartmentCard';


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