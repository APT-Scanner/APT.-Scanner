import { forwardRef, useState, useEffect, useMemo } from 'react';
import { motion, useMotionValue, useTransform, animate } from 'framer-motion';
import { useDrag } from '@use-gesture/react';
import { ImageIcon, Maximize, ChevronLeft, ChevronRight, X } from 'lucide-react';
import PropTypes from 'prop-types';
import styles from '../styles/ApartmentSwipePage.module.css';

const AnimatedApartmentCard = forwardRef(({ apartment, onSwipeComplete, disableSwipe = false }, ref) => {
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
    const images = useMemo(() => {
        const availableImages = [];
        
        if (apartment.cover_image_url && apartment.cover_image_url.trim() !== '') {
            availableImages.push(apartment.cover_image_url);
        }
        
        if (apartment.images && Array.isArray(apartment.images)) {
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
                            className={styles.fullscreenNavButtonLeft}
                            onClick={prevImage}
                            aria-label="Previous image"
                        >
                            <ChevronLeft size={24} />
                        </button>
                        
                        <div className={styles.fullscreenCounter}>
                            {currentImageIndex + 1} / {images.length}
                        </div>
                        
                        <button 
                            className={styles.fullscreenNavButtonRight}
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

export default AnimatedApartmentCard;