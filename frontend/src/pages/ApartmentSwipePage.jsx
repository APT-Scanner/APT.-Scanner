import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useApartments } from '../hooks/useApartments';
import { useViewHistory } from '../hooks/useViewHistory';
import { useFilters } from '../hooks/useFilters';
import styles from '../styles/ApartmentSwipePage.module.css';
import ApartmentDetailSheet from './ApartmentDetailSheet';
import { Heart, X, ChevronUp, ChevronDown, Loader, Filter, Menu, LogOut, Target, ClipboardList, MapPin } from 'lucide-react';
import logo from "../assets/logo-swipe-screen.jpeg";
import HomeIcon from '../assets/home_pressed.svg';
import HeartOutlineIcon from '../assets/heart_not_pressed.svg';
import { useFavorites } from '../hooks/useFavorites';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence, useMotionValue, animate } from 'framer-motion';
import { useDrag } from '@use-gesture/react';
import { LoadingSpinner } from '../components/LoadingSpinner';
import AnimatedApartmentCard from '../components/AnimatedApartmentCard';
import { signOut } from 'firebase/auth';
import { auth } from '../config/firebase';


const ApartmentSwipePage = () => {
    const { getFilterQueryParams, filters, loading: filtersLoading } = useFilters();
    
    const filterParams = useMemo(() => {
        if (filtersLoading) return null;
        return getFilterQueryParams();
    }, [filters, getFilterQueryParams, filtersLoading]);  // Include all dependencies
    
    const [refreshTrigger, setRefreshTrigger] = useState(0);
    
    const { apartments: fetchedApartments, loading: apartmentsLoading, error: useApartmentsError } = useApartments({ 
        filterViewed: true,
        filterParams,
        refreshTrigger,
        filtersReady: !filtersLoading
    });
    
    const { recordView, filterViewedApartments, loading: viewHistoryLoading } = useViewHistory();
    
    const [apartments, setApartments] = useState([]);
    const [detailsExpanded, setDetailsExpanded] = useState(false);
    const [menuOpen, setMenuOpen] = useState(false);
    const { addFavorite } = useFavorites();
    const navigate = useNavigate();
    
    const detailsPanelRef = useRef(null);
    const detailsPanelY = useMotionValue(0);
    const menuRef = useRef(null);
    const menuButtonRef = useRef(null);
    
    const [windowHeight, setWindowHeight] = useState(typeof window !== 'undefined' ? window.innerHeight : 0);


    useEffect(() => {
        const handleResize = () => {
            setWindowHeight(window.innerHeight);
        };
        
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    const processedApartments = useMemo(() => {
        if (!fetchedApartments || fetchedApartments.length === 0 || viewHistoryLoading) {
            return [];
        }

        const filteredApartments = filterViewedApartments(fetchedApartments);
        
        if (filteredApartments.length === 0 && fetchedApartments.length > 0) {
            return fetchedApartments;
        } else {
            return filteredApartments;
        }
    }, [fetchedApartments, viewHistoryLoading, filterViewedApartments]);

    useEffect(() => {
        if (processedApartments) {
            setApartments(processedApartments);
        }
    }, [processedApartments]);

    const currentApartment = apartments.length > 0 ? apartments[0] : null;

    const handleSwipeAction = useCallback((actionType, apartmentOrderId) => {
        setApartments(prev => prev.filter(apt => apt.listing_id !== apartmentOrderId));
        
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
        handleSwipeAction(actionType, currentApartment.listing_id);
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
        ({ active, movement: [, my], direction: [, dy], velocity: [, vy] }) => {
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

    const loading = apartmentsLoading || viewHistoryLoading || filtersLoading;
    
    const handleNavigateToFilter = () => {
        navigate('/filter');
    };

    const handleMenuToggle = () => {
        setMenuOpen(!menuOpen);
    };

    const handleSignOut = async () => {
        try {
            await signOut(auth);
            navigate('/'); // Redirect to login page after signout
        } catch (error) {
            console.error('Error signing out:', error);
        }
    };

    const handleBackToRecommendations = () => {
        setMenuOpen(false); // Close the menu
        navigate('/recommendations');
    };

    const handleQuestionnaireEdit = () => {
        setMenuOpen(false); // Close the menu
        navigate('/questionnaire-edit');
    };

    // Close menu when clicking outside
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (menuRef.current && 
                !menuRef.current.contains(event.target) &&
                menuButtonRef.current &&
                !menuButtonRef.current.contains(event.target)) {
                setMenuOpen(false);
            }
        };

        if (menuOpen) {
            document.addEventListener('mousedown', handleClickOutside);
        }

        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [menuOpen]);

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
        <div className={styles.pageContainer}>
            {/* Header for Menu Icon and Filter Icon */}
            <div className={styles.swipePageHeader}>
                <button 
                    ref={menuButtonRef}
                    className={styles.menuButton} 
                    onClick={handleMenuToggle}
                >
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

            {/* Menu Dropdown */}
            <AnimatePresence>
                {menuOpen && (
                    <motion.div
                        ref={menuRef}
                        className={styles.menuDropdown}
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        transition={{ duration: 0.2 }}
                    >
                        <button 
                            className={styles.menuItem}
                            onClick={handleBackToRecommendations}
                        >
                            <Target size={20} />
                            <span>Back to My Recommendations</span>
                        </button>
                        <button 
                            className={styles.menuItem}
                            onClick={handleQuestionnaireEdit}
                        >
                            <ClipboardList size={20} />
                            <span>Edit My Questionnaire</span>
                        </button>
                        <button 
                            className={styles.menuItem}
                            onClick={handleSignOut}
                        >
                            <LogOut size={20} />
                            <span>Sign Out</span>
                        </button>
                    </motion.div>
                )}
            </AnimatePresence>

            <div className={`${styles.pageContainer} ${detailsExpanded ? styles.detailsActive : ''}`}>
                {useApartmentsError && <div className={styles.errorContainer}>Error: {useApartmentsError.message || String(useApartmentsError)}</div>}
                
                <div className={styles.cardStackContainer}>
                    <AnimatePresence mode="popLayout">
                        {currentApartment && !detailsExpanded && (
                            <AnimatedApartmentCard
                                key={currentApartment.listing_id}
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
                <button className={styles.bottomBarButton} onClick={() => navigate('/neighborhoods')}>
                    <MapPin size={24} alt="Neighborhoods" style={{ width: '28px', height: '28px', stroke: '#371b34', strokeWidth: '1.5' }} />
                </button>
            </div>
        </div>
    );
};

export default ApartmentSwipePage;