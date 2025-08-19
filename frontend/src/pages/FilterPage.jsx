import React, { useState, useEffect, useRef } from 'react';
import styles from '../styles/FilterPage.module.css';
import { ArrowLeft } from 'lucide-react'; 
import { useNavigate } from 'react-router-dom';
import { useFilters } from '../hooks/useFilters';
import { fetchCities, fetchNeighborhoods } from '../services/neighborhoodsApi';
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
import RangeSlider from '../components/rangeSlider'; 


// All Yad2 features now available in database
const moreOptionsConfig = [
    { id: 'shelter', label: 'Shelter (ממ"ד)', icon: shelterIcon },
    { id: 'elevator', label: 'Elevator (מעלית)', icon: elevatorIcon },
    { id: 'parking', label: 'Parking (חניה)', icon: parkingIcon },
    { id: 'warehouse', label: 'Storage (מחסן)', icon: storageIcon },
    { id: 'airConditioner', label: 'A/C (מיזוג)', icon: acIcon },
    { id: 'balcony', label: 'Balcony (מרפסת)', icon: balconyIcon },
    { id: 'bars', label: 'Bars (סורגים)', icon: barsIcon },
    { id: 'accessibility', label: 'Accessible (גישה לנכים)', icon: accessibleIcon },
    { id: 'renovated', label: 'Renovated (משופץ)', icon: renovatedIcon },
    { id: 'forPartners', label: 'Roommates (לשותפים)', icon: roommatesIcon },
    { id: 'pets', label: 'Pet-friendly (חיות מחמד)', icon: petFriendlyIcon },
    { id: 'furniture', label: 'Furnished (מרוהט)', icon: furnishedIcon },
];

const MIN_PRICE = 500;
const MAX_PRICE = 15000;

const MIN_ROOMS = 1;
const MAX_ROOMS = 8;

const MIN_SIZE = 10;
const MAX_SIZE = 500;

const FilterPage = () => {
    const { filters, updateFilter, loading: filtersLoading } = useFilters();
    const [filterType, setFilterType] = useState(filters.type); 
    const [selectedCity, setSelectedCity] = useState(filters.city);
    const [selectedNeighborhood, setSelectedNeighborhood] = useState(filters.neighborhood);
    const [cities, setCities] = useState([]);
    const [neighborhoods, setNeighborhoods] = useState([]);
    const [isLoadingCities, setIsLoadingCities] = useState(false);
    const [isLoadingNeighborhoods, setIsLoadingNeighborhoods] = useState(false);
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
    const draggingHandleRef = useRef(null); // 'min' or 'max'

    // Refs for rooms slider interaction
    const draggingRoomsHandleRef = useRef(null); // For rooms slider: 'min' or 'max'

    // Refs for size slider interaction
    const draggingSizeHandleRef = useRef(null); 

    // Update local state when filters are loaded
    useEffect(() => {
        if (!filtersLoading) {
            setFilterType(filters.type);
            setSelectedCity(filters.city);
            setSelectedNeighborhood(filters.neighborhood);
            setPriceMin(filters.priceMin);
            setPriceMax(filters.priceMax);
            setRoomsMin(filters.roomsMin);
            setRoomsMax(filters.roomsMax);
            setSizeMin(filters.sizeMin);
            setSizeMax(filters.sizeMax);
            setSelectedOptions(filters.options || []);
        }
    }, [filters, filtersLoading]);

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

    const handleCityChange = (e) => {
        const newCity = e.target.value;
        setSelectedCity(newCity);
        setSelectedNeighborhood(''); // Reset neighborhood on city change
        setNeighborhoods([]); // Clear neighborhoods
    };

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

    // Fetch cities on component mount
    useEffect(() => {
        const loadCities = async () => {
            setIsLoadingCities(true);
            try {
                const citiesList = await fetchCities();
                setCities(citiesList);
            } catch (error) {
                console.error('Failed to fetch cities:', error);
                setCities([]);
            } finally {
                setIsLoadingCities(false);
            }
        };

        loadCities();
    }, []);

    // Fetch neighborhoods when city changes
    useEffect(() => {
        const loadNeighborhoods = async () => {
            if (!selectedCity) {
                setNeighborhoods([]);
                return;
            }

            setIsLoadingNeighborhoods(true);
            try {
                const neighborhoodsList = await fetchNeighborhoods(selectedCity);
                setNeighborhoods(neighborhoodsList);
            } catch (error) {
                console.error('Failed to fetch neighborhoods:', error);
                setNeighborhoods([]);
            } finally {
                setIsLoadingNeighborhoods(false);
            }
        };

        loadNeighborhoods();
    }, [selectedCity]);

    // Show loading while filters are being loaded
    if (filtersLoading) {
        return (
            <div className={styles.filterPage}>
                <div className={styles.header}>
                    <button onClick={handleBack} className={styles.backButton}>
                        <ArrowLeft size={24} />
                    </button>
                </div>
                <div style={{ 
                    display: 'flex', 
                    justifyContent: 'center', 
                    alignItems: 'center', 
                    height: '200px',
                    fontSize: '16px',
                    color: '#666'
                }}>
                    Loading filters...
                </div>
            </div>
        );
    }

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
                    onChange={handleCityChange}
                    disabled={isLoadingCities}
                >
                    <option value="">
                        {isLoadingCities ? 'Loading cities...' : 'Select a city...'}
                    </option>
                    {cities.map(city => <option key={city} value={city}>{city}</option>)}
                </select>
                <select 
                    className={styles.dropdown}
                    value={selectedNeighborhood}
                    onChange={(e) => setSelectedNeighborhood(e.target.value)}
                    disabled={!selectedCity || isLoadingNeighborhoods}
                >
                    <option value="">
                        {isLoadingNeighborhoods ? 'Loading neighborhoods...' : 'Select a neighborhood...'}
                    </option>
                    {selectedCity && neighborhoods.map(hood => <option key={hood} value={hood}>{hood}</option>)}
                </select>
            </div>

            <div className={styles.filterSection}>
                <h3 className={styles.sectionTitle}>-Price-</h3>
                <RangeSlider
                    min={MIN_PRICE}
                    max={MAX_PRICE}
                    step={100}
                    valueMin={priceMin}
                    valueMax={priceMax}
                    onChangeMin={setPriceMin}
                    onChangeMax={setPriceMax}
                    labels={[500, 5000, 10000, 15000]}
                />
            </div>
            <div className={styles.filterSection}>
                <h3 className={styles.sectionTitle}>-Rooms-</h3>
                <RangeSlider
                    min={MIN_ROOMS}
                    max={MAX_ROOMS}
                    step={1}
                    valueMin={roomsMin}
                    valueMax={roomsMax}
                    onChangeMin={setRoomsMin}
                    onChangeMax={setRoomsMax}
                    labels={[1, 2, 3, 4, 5, 6, 7, 8]}
                />
            </div>
            <div className={styles.filterSection}>
                <h3 className={styles.sectionTitle}>-Size in m²-</h3>
                <RangeSlider
                    min={MIN_SIZE}
                    max={MAX_SIZE}
                    step={10}
                    valueMin={sizeMin}
                    valueMax={sizeMax}
                    onChangeMin={setSizeMin}
                    onChangeMax={setSizeMax}
                    labels={[100, 200, 300, 400, 500]}
                />
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