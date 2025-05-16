import React, { useState, useEffect, useRef, useCallback } from 'react';
import styles from '../styles/FilterPage.module.css';
import { ArrowLeft } from 'lucide-react'; 
import { useNavigate } from 'react-router-dom';
import { useFilters } from '../hooks/useFilters';
import shelterIcon from '../assets/icons/image 12.png'; 
import elevatorIcon from '../assets/icons/image 11.png';
import parkingIcon from '../assets/icons/image 10.png';
import storageIcon from '../assets/icons/image 15.png';
import acIcon from '../assets/icons/image 14.png';
import balconyIcon from '../assets/icons/image 13.png';
import barsIcon from '../assets/icons/image 30.png';
import accessibleIcon from '../assets/icons/image 29.png';
import renovatedIcon from '../assets/icons/image 28.png';
import roommatesIcon from '../assets/icons/image 33.png';
import petFriendlyIcon from '../assets/icons/image 32.png';
import furnishedIcon from '../assets/icons/image 31.png';

const cities = ['תל אביב יפו'];
const neighborhoods = {
    'תל אביב יפו': ['פלנטין', 'נווה צדק', 'יהודה ושבע', 'צורן'],
};

const moreOptionsConfig = [
    { id: 'shelter', label: 'Shelter', icon: shelterIcon },
    { id: 'elevator', label: 'Elevator', icon: elevatorIcon },
    { id: 'parking', label: 'Parking', icon: parkingIcon },
    { id: 'storage', label: 'Storage', icon: storageIcon },
    { id: 'ac', label: 'A/C', icon: acIcon },
    { id: 'balcony', label: 'Balcony', icon: balconyIcon },
    { id: 'bars', label: 'Bars', icon: barsIcon },
    { id: 'accessible', label: 'Accessible', icon: accessibleIcon },
    { id: 'renovated', label: 'Renovated', icon: renovatedIcon },
    { id: 'roommates', label: 'Roommates', icon: roommatesIcon },
    { id: 'petFriendly', label: 'Pet-friendly', icon: petFriendlyIcon },
    { id: 'furnished', label: 'Furnished', icon: furnishedIcon },
];

const MIN_PRICE = 500;
const MAX_PRICE = 15000;

const MIN_ROOMS = 1;
const MAX_ROOMS = 8;

const MIN_SIZE = 10;
const MAX_SIZE = 500;

const FilterPage = () => {
    const { filters, updateFilter } = useFilters();
    const [filterType, setFilterType] = useState(filters.type); 
    const [selectedCity, setSelectedCity] = useState(filters.city);
    const [selectedNeighborhood, setSelectedNeighborhood] = useState(filters.neighborhood);
    const navigate = useNavigate();
    
    // Price filter state
    const [priceMin, setPriceMin] = useState(filters.priceMin);
    const [priceMax, setPriceMax] = useState(filters.priceMax);
    
    // Rooms filter state
    const [roomsMin, setRoomsMin] = useState(filters.roomsMin);
    const [roomsMax, setRoomsMax] = useState(filters.roomsMax);
    
    // Size filter state
    const [sizeMin, setSizeMin] = useState(filters.sizeMin);
    const [sizeMax, setSizeMax] = useState(filters.sizeMax);
    
    // More options state
    const [selectedOptions, setSelectedOptions] = useState(filters.options || []);

    // Refs for slider interaction
    const priceSliderRef = useRef(null);
    const draggingHandleRef = useRef(null); // 'min' or 'max'

    // Refs for rooms slider interaction
    const roomsSliderRef = useRef(null);
    const draggingRoomsHandleRef = useRef(null); // For rooms slider: 'min' or 'max'

    // Refs for size slider interaction
    const sizeSliderRef = useRef(null);
    const draggingSizeHandleRef = useRef(null); 

    const handleBack = () => {
        navigate(-1); 
    };

    const handleApplyFilters = () => {
        console.log("Apply filters with:", {
            filterType,
            selectedCity,
            selectedNeighborhood,
            priceRange: [priceMin, priceMax],
            roomsRange: [roomsMin, roomsMax],
            sizeRange: [sizeMin, sizeMax],
            selectedOptions
        });

        updateFilter({
            type: filterType,
            city: selectedCity,
            neighborhood: selectedNeighborhood,
            priceMin,
            priceMax,
            roomsMin,
            roomsMax,
            sizeMin,
            sizeMax,
            options: selectedOptions
        });
        
        navigate(-1); 
    };

    const toggleOption = (optionId) => {
        setSelectedOptions(prev => 
            prev.includes(optionId)
                ? prev.filter(id => id !== optionId)
                : [...prev, optionId]
        );
    };

    const handlePriceMouseDown = (handleType) => (event) => {
        // Prevent default behavior to stop page scrolling on mobile
        if (event.type === 'touchstart') {
            event.preventDefault();
        }
        
        draggingHandleRef.current = handleType;
        if (event.target instanceof HTMLElement) {
            event.target.classList.add(styles.active);
        }
    };

    const handleMouseUp = useCallback(() => {
        if (draggingHandleRef.current) {
            document.querySelectorAll(`.${styles.rangeHandle}.${styles.active}`).forEach(handle => {
                handle.classList.remove(styles.active);
            });
            draggingHandleRef.current = null;
        }
    }, []); 

    const handleMouseMove = useCallback((event) => {
        if (!draggingHandleRef.current || !priceSliderRef.current) return;

        // Prevent default behavior for touch events
        if (event.type === 'touchmove') {
            event.preventDefault();
        }

        const sliderRect = priceSliderRef.current.getBoundingClientRect();
        let offsetX = event.clientX - sliderRect.left;
        const sliderWidth = sliderRect.width;

        if (event.touches && event.touches.length > 0) {
            offsetX = event.touches[0].clientX - sliderRect.left;
        }

        let percentage = (offsetX / sliderWidth) * 100;
        percentage = Math.max(0, Math.min(100, percentage));

        let newValue = MIN_PRICE + (percentage / 100) * (MAX_PRICE - MIN_PRICE);
        // Snap to nearest 100 or any other step you prefer
        const step = 100;
        newValue = Math.round(newValue / step) * step;

        if (draggingHandleRef.current === 'min') {
            setPriceMin(prevMin => Math.max(MIN_PRICE, Math.min(newValue, priceMax - step)));
        } else if (draggingHandleRef.current === 'max') {
            setPriceMax(prevMax => Math.min(MAX_PRICE, Math.max(newValue, priceMin + step)));
        }
    }, [priceMin, priceMax, setPriceMin, setPriceMax]); 

    useEffect(() => {
        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('touchmove', handleMouseMove, { passive: false }); 
        document.addEventListener('mouseup', handleMouseUp);
        document.addEventListener('touchend', handleMouseUp);

        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('touchmove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
            document.removeEventListener('touchend', handleMouseUp);
        };
    }, [handleMouseMove, handleMouseUp]); 

    // Rooms Slider Handlers
    const handleRoomsMouseDown = (handleType) => (event) => {
        // Prevent default behavior to stop page scrolling on mobile
        if (event.type === 'touchstart') {
            event.preventDefault();
        }
        
        draggingRoomsHandleRef.current = handleType;
        if (event.target instanceof HTMLElement) {
            event.target.classList.add(styles.active);
        }
    };

    const handleRoomsMouseUp = useCallback(() => {
        if (draggingRoomsHandleRef.current) {
            document.querySelectorAll(`.${styles.rangeHandle}.${styles.active}`).forEach(handle => {
                handle.classList.remove(styles.active);
            });
            draggingRoomsHandleRef.current = null;
        }
    }, []);

    const handleRoomsMouseMove = useCallback((event) => {
        if (!draggingRoomsHandleRef.current || !roomsSliderRef.current) return;

        // Prevent default behavior for touch events
        if (event.type === 'touchmove') {
            event.preventDefault();
        }

        const sliderRect = roomsSliderRef.current.getBoundingClientRect();
        let offsetX = event.clientX - sliderRect.left;
        const sliderWidth = sliderRect.width;

        if (event.touches && event.touches.length > 0) {
            offsetX = event.touches[0].clientX - sliderRect.left;
        }

        let percentage = (offsetX / sliderWidth) * 100;
        percentage = Math.max(0, Math.min(100, percentage));

        const step = 1;
        let newValue = MIN_ROOMS + (percentage / 100) * (MAX_ROOMS - MIN_ROOMS);
        newValue = Math.round(newValue / step) * step;

        if (draggingRoomsHandleRef.current === 'min') {
            setRoomsMin(prevMin => Math.max(MIN_ROOMS, Math.min(newValue, roomsMax - step)));
        } else if (draggingRoomsHandleRef.current === 'max') {
            setRoomsMax(prevMax => Math.min(MAX_ROOMS, Math.max(newValue, roomsMin + step)));
        }
    }, [roomsMin, roomsMax, setRoomsMin, setRoomsMax]);

    useEffect(() => {
        document.addEventListener('mousemove', handleRoomsMouseMove);
        document.addEventListener('touchmove', handleRoomsMouseMove, { passive: false });
        document.addEventListener('mouseup', handleRoomsMouseUp);
        document.addEventListener('touchend', handleRoomsMouseUp);

        return () => {
            document.removeEventListener('mousemove', handleRoomsMouseMove);
            document.removeEventListener('touchmove', handleRoomsMouseMove);
            document.removeEventListener('mouseup', handleRoomsMouseUp);
            document.removeEventListener('touchend', handleRoomsMouseUp);
        };
    }, [handleRoomsMouseMove, handleRoomsMouseUp]);

    // Size Slider Handlers
    const handleSizeMouseDown = (handleType) => (event) => {
        // Prevent default behavior to stop page scrolling on mobile
        if (event.type === 'touchstart') {
            event.preventDefault();
        }
        
        draggingSizeHandleRef.current = handleType;
        if (event.target instanceof HTMLElement) {
            event.target.classList.add(styles.active);
        }
    };

    const handleSizeMouseUp = useCallback(() => {
        if (draggingSizeHandleRef.current) {
            document.querySelectorAll(`.${styles.rangeHandle}.${styles.active}`).forEach(handle => {
                handle.classList.remove(styles.active);
            });
            draggingSizeHandleRef.current = null;
        }
    }, []);

    const handleSizeMouseMove = useCallback((event) => {
        if (!draggingSizeHandleRef.current || !sizeSliderRef.current) return;

        // Prevent default behavior for touch events
        if (event.type === 'touchmove') {
            event.preventDefault();
        }

        const sliderRect = sizeSliderRef.current.getBoundingClientRect();
        let offsetX = event.clientX - sliderRect.left;
        const sliderWidth = sliderRect.width;

        if (event.touches && event.touches.length > 0) {
            offsetX = event.touches[0].clientX - sliderRect.left;
        }

        let percentage = (offsetX / sliderWidth) * 100;
        percentage = Math.max(0, Math.min(100, percentage));

        const step = 10; // Step for size slider
        let newValue = MIN_SIZE + (percentage / 100) * (MAX_SIZE - MIN_SIZE);
        newValue = Math.round(newValue / step) * step;

        if (draggingSizeHandleRef.current === 'min') {
            setSizeMin(prevMin => Math.max(MIN_SIZE, Math.min(newValue, sizeMax - step)));
        } else if (draggingSizeHandleRef.current === 'max') {
            setSizeMax(prevMax => Math.min(MAX_SIZE, Math.max(newValue, sizeMin + step)));
        }
    }, [sizeMin, sizeMax, setSizeMin, setSizeMax]);

    useEffect(() => {
        document.addEventListener('mousemove', handleSizeMouseMove);
        document.addEventListener('touchmove', handleSizeMouseMove, { passive: false });
        document.addEventListener('mouseup', handleSizeMouseUp);
        document.addEventListener('touchend', handleSizeMouseUp);

        return () => {
            document.removeEventListener('mousemove', handleSizeMouseMove);
            document.removeEventListener('touchmove', handleSizeMouseMove);
            document.removeEventListener('mouseup', handleSizeMouseUp);
            document.removeEventListener('touchend', handleSizeMouseUp);
        };
    }, [handleSizeMouseMove, handleSizeMouseUp]);

    useEffect(() => {
        // Function to prevent default touch behavior on sliders
        const preventDefaultForSliders = (event) => {
            if (
                draggingHandleRef.current || 
                draggingRoomsHandleRef.current || 
                draggingSizeHandleRef.current
            ) {
                event.preventDefault();
            }
        };

        // Add the event listener with capture to ensure it's triggered before scroll
        document.addEventListener('touchmove', preventDefaultForSliders, { passive: false });

        return () => {
            document.removeEventListener('touchmove', preventDefaultForSliders);
        };
    }, []);

    return (
        <div className={styles.filterPage}>
            <div className={styles.header}>
                <button onClick={handleBack} className={styles.backButton}>
                    <ArrowLeft size={24} />
                </button>
            </div>

            <div className={styles.typeToggle}>
                <button 
                    className={`${styles.toggleButton} ${filterType === 'rent' ? styles.active : ''}`}
                    onClick={() => setFilterType('rent')}
                >
                    Rent
                </button>
                <button 
                    className={`${styles.toggleButton} ${filterType === 'sale' ? styles.active : ''}`}
                    onClick={() => setFilterType('sale')}
                >
                    Sale
                </button>
            </div>

            <div className={styles.filterSection}>
                <h3 className={styles.sectionTitle}>-Location-</h3>
                <select 
                    className={styles.dropdown}
                    value={selectedCity} 
                    onChange={(e) => {
                        setSelectedCity(e.target.value);
                        setSelectedNeighborhood(''); // Reset neighborhood on city change
                    }}
                >
                    <option value="">Select a city...</option>
                    {cities.map(city => <option key={city} value={city}>{city}</option>)}
                </select>
                <select 
                    className={styles.dropdown}
                    value={selectedNeighborhood}
                    onChange={(e) => setSelectedNeighborhood(e.target.value)}
                    disabled={!selectedCity}
                >
                    <option value="">Select a neighborhood...</option>
                    {selectedCity && neighborhoods[selectedCity]?.map(hood => <option key={hood} value={hood}>{hood}</option>)}
                </select>
            </div>

            <div className={styles.filterSection}>
                <h3 className={styles.sectionTitle}>-Price-</h3>
                <div className={styles.rangeInputsContainer}>
                    <input 
                        type="number" 
                        className={styles.rangeInput} 
                        value={priceMin}
                        onChange={(e) => setPriceMin(Math.max(MIN_PRICE, Math.min(parseInt(e.target.value) || MIN_PRICE, priceMax -100)))}
                        placeholder="Min"
                        step="100"
                    />
                    <input 
                        type="number" 
                        className={styles.rangeInput} 
                        value={priceMax}
                        onChange={(e) => setPriceMax(Math.min(MAX_PRICE, Math.max(parseInt(e.target.value) || MAX_PRICE, priceMin + 100)))}
                        placeholder="Max"
                        step="100"
                    />
                </div>
                <div className={styles.rangeSlider} ref={priceSliderRef}>
                    <div 
                        className={styles.rangeTrack} 
                        style={{ 
                            left: `${((priceMin - MIN_PRICE) / (MAX_PRICE - MIN_PRICE)) * 100}%`, 
                            width: `${((priceMax - priceMin) / (MAX_PRICE - MIN_PRICE)) * 100}%` 
                        }}
                    ></div>
                    <div className={styles.rangeDot} style={{ left: '0%' }}></div>
                    <div className={styles.rangeDot} style={{ left: '25%' }}></div>
                    <div className={styles.rangeDot} style={{ left: '50%' }}></div>
                    <div className={styles.rangeDot} style={{ left: '75%' }}></div>
                    <div className={styles.rangeDot} style={{ left: '100%' }}></div>
                    
                    <div 
                        className={styles.rangeHandle} 
                        style={{ left: `${((priceMin - MIN_PRICE) / (MAX_PRICE - MIN_PRICE)) * 100}%` }}
                        onMouseDown={handlePriceMouseDown('min')}
                        onTouchStart={handlePriceMouseDown('min')} // For touch devices
                    ></div>
                    <div 
                        className={styles.rangeHandle} 
                        style={{ left: `${((priceMax - MIN_PRICE) / (MAX_PRICE - MIN_PRICE)) * 100}%` }}
                        onMouseDown={handlePriceMouseDown('max')}
                        onTouchStart={handlePriceMouseDown('max')} // For touch devices
                    ></div>
                </div>
                <div className={styles.rangeLabels}>
                    <span>500</span>
                    <span>5,000</span>
                    <span>10,000</span>
                    <span>15,000</span>
                </div>
            </div>

            <div className={styles.filterSection}>
                <h3 className={styles.sectionTitle}>-Rooms-</h3>
                <div className={styles.rangeInputsContainer}>
                    <input 
                        type="number" 
                        className={styles.rangeInput} 
                        value={roomsMin} 
                        onChange={(e) => setRoomsMin(Math.max(MIN_ROOMS, Math.min(parseInt(e.target.value) || MIN_ROOMS, roomsMax - 1)))}
                        placeholder="Min"
                        step="1"
                    />
                    <input 
                        type="number" 
                        className={styles.rangeInput} 
                        value={roomsMax}
                        onChange={(e) => setRoomsMax(Math.min(MAX_ROOMS, Math.max(parseInt(e.target.value) || MAX_ROOMS, roomsMin + 1)))}
                        placeholder="Max"
                        step="1"
                    />
                </div>
                <div className={styles.rangeSlider} ref={roomsSliderRef}>
                    <div 
                        className={styles.rangeTrack} 
                        style={{ 
                            left: `${((roomsMin - MIN_ROOMS) / (MAX_ROOMS - MIN_ROOMS)) * 100}%`, 
                            width: `${((roomsMax - roomsMin) / (MAX_ROOMS - MIN_ROOMS)) * 100}%` 
                        }}
                    ></div>
                    {[1, 2, 3, 4, 5, 6, 7, 8].map((num) => (
                        <div 
                            key={num} 
                            className={styles.rangeDot} 
                            style={{ left: `${((num - MIN_ROOMS) / (MAX_ROOMS - MIN_ROOMS)) * 100}%` }}
                        ></div>
                    ))}
                    
                    <div 
                        className={styles.rangeHandle} 
                        style={{ left: `${((roomsMin - MIN_ROOMS) / (MAX_ROOMS - MIN_ROOMS)) * 100}%` }}
                        onMouseDown={handleRoomsMouseDown('min')}
                        onTouchStart={handleRoomsMouseDown('min')}
                    ></div>
                    <div 
                        className={styles.rangeHandle} 
                        style={{ left: `${((roomsMax - MIN_ROOMS) / (MAX_ROOMS - MIN_ROOMS)) * 100}%` }}
                        onMouseDown={handleRoomsMouseDown('max')}
                        onTouchStart={handleRoomsMouseDown('max')}
                    ></div>
                </div>
                <div className={styles.rangeLabels}>
                    <span>1</span>
                    <span>2</span>
                    <span>3</span>
                    <span>4</span>
                    <span>5</span>
                    <span>6</span>
                    <span>7</span>
                    <span>8</span>
                </div>
            </div>

            <div className={styles.filterSection}>
                <h3 className={styles.sectionTitle}>-Size in m²-</h3>
                <div className={styles.rangeInputsContainer}>
                    <input 
                        type="number" 
                        className={styles.rangeInput} 
                        value={sizeMin} 
                        onChange={(e) => setSizeMin(Math.max(MIN_SIZE, Math.min(parseInt(e.target.value) || MIN_SIZE, sizeMax - 10)))}
                        placeholder="Min"
                        step="10"
                    />
                    <input 
                        type="number" 
                        className={styles.rangeInput} 
                        value={sizeMax}
                        onChange={(e) => setSizeMax(Math.min(MAX_SIZE, Math.max(parseInt(e.target.value) || MAX_SIZE, sizeMin + 10)))}
                        placeholder="Max"
                        step="10"
                    />
                </div>
                <div className={styles.rangeSlider} ref={sizeSliderRef}>
                    <div 
                        className={styles.rangeTrack} 
                        style={{ 
                            left: `${((sizeMin - MIN_SIZE) / (MAX_SIZE - MIN_SIZE)) * 100}%`, 
                            width: `${((sizeMax - sizeMin) / (MAX_SIZE - MIN_SIZE)) * 100}%` 
                        }}
                    ></div>
                    <div className={styles.rangeDot} style={{ left: '0%' }}></div>
                    <div className={styles.rangeDot} style={{ left: '18.37%' }}></div>
                    <div className={styles.rangeDot} style={{ left: '59.18%' }}></div>
                    <div className={styles.rangeDot} style={{ left: '100%' }}></div>
                    
                    <div 
                        className={styles.rangeHandle} 
                        style={{ left: `${((sizeMin - MIN_SIZE) / (MAX_SIZE - MIN_SIZE)) * 100}%` }}
                        onMouseDown={handleSizeMouseDown('min')}
                        onTouchStart={handleSizeMouseDown('min')}
                    ></div>
                    <div 
                        className={styles.rangeHandle} 
                        style={{ left: `${((sizeMax - MIN_SIZE) / (MAX_SIZE - MIN_SIZE)) * 100}%` }}
                        onMouseDown={handleSizeMouseDown('max')}
                        onTouchStart={handleSizeMouseDown('max')}
                    ></div>
                </div>
                <div className={`${styles.rangeLabels} ${styles.sizeSpecificLabels}`}>
                    <span style={{ position: 'absolute', left: '0%', transform: 'translateX(0%)' }}>10</span>
                    <span style={{ position: 'absolute', left: '18.37%', transform: 'translateX(-50%)' }}>100</span>
                    <span style={{ position: 'absolute', left: '59.18%', transform: 'translateX(-50%)' }}>300</span>
                    <span style={{ position: 'absolute', left: '100%', transform: 'translateX(-100%)' }}>500</span>
                </div>
            </div>

            <div className={styles.filterSection}>
                <h3 className={styles.sectionTitle}>-More options-</h3>
                <div className={styles.moreOptionsGrid}>
                    {moreOptionsConfig.map(option => (
                        <button 
                            key={option.id} 
                            className={`${styles.optionButton} ${selectedOptions.includes(option.id) ? styles.selected : ''}`}
                            onClick={() => toggleOption(option.id)}
                        >
                            <img src={option.icon} alt={option.label} className={styles.optionIcon} />
                            <span>{option.label}</span>
                        </button>
                    ))}
                </div>
            </div>
            
            <button className={styles.applyButton} onClick={handleApplyFilters}>
                Start Exploring
            </button>
        </div>
    );
};

export default FilterPage; 