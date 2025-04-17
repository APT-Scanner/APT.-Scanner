import React, { useEffect } from 'react';
import styles from '../styles/ApartmentDetailSheet.module.css';
import { X, Maximize2, Layers3, BedDouble, MapPin } from 'lucide-react'; 
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import customMarkerIconUrl from '../assets/marker-icon.png'; 

const customIcon = L.icon({
    iconUrl: customMarkerIconUrl,
    iconSize: [25, 41],      
    iconAnchor: [12, 41],       
    popupAnchor: [1, -34]    
});

const ApartmentDetailSheet = ({ apartment, isOpen, onClose }) => {
    if (!apartment) {
        return null; // אל תרנדר כלום אם אין דירה
    }

    // מונע גלילה של הדף שמאחורי החלון כשהוא פתוח
    useEffect(() => {
        if (isOpen) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = 'unset';
        }
        // Cleanup effect
        return () => {
            document.body.style.overflow = 'unset';
        };
    }, [isOpen]);


    // קביעת מיקום ברירת מחדל למקרה שאין קואורדינטות
    const position = (apartment.latitude && apartment.longitude)
        ? [apartment.latitude, apartment.longitude]
        : [32.0853, 34.7818]; // ברירת מחדל לתל אביב אם אין נתונים

    const mapKey = `${apartment.id}-${position.join(',')}`; // מפתח ייחודי למפה כדי לאלץ רינדור מחדש

    return (
        <>
            {/* רקע חצי שקוף מאחור */}
            <div
                className={`${styles.backdrop} ${isOpen ? styles.backdropOpen : ''}`}
                onClick={onClose} // סגירה בלחיצה על הרקע
            />

            {/* החלון עצמו */}
            <div className={`${styles.sheetContainer} ${isOpen ? styles.sheetOpen : ''}`}>
                {/* ידית אופציונלית למעלה */}
                <div className={styles.handle}></div>

                {/* כפתור סגירה */}
                <button onClick={onClose} className={styles.closeButton} aria-label="Close details">
                    <X size={24} />
                </button>

                {/* תוכן החלון */}
                <div className={styles.content}>
                    {/* אפשר להוסיף את התמונה גם כאן אם רוצים */}
                    {/* <img src={apartment.cover_image_url || apartment.image} alt={apartment.address} className={styles.headerImage} /> */}

                    <h2 className={styles.address}>{apartment.address}</h2>
                    <p className={styles.price}>{apartment.price?.toLocaleString()} ₪ per month</p>

                    {/* פרטים טכניים עם אייקונים */}
                    <div className={styles.specs}>
                        {apartment.size && (
                            <span className={styles.specItem}>
                                <Maximize2 size={18} className={styles.specIcon} />
                                {apartment.size} מ"ר
                            </span>
                        )}
                        {apartment.floors && (
                             <span className={styles.specItem}>
                                <Layers3 size={18} className={styles.specIcon} />
                                {apartment.floors} {apartment.floors > 1 ? 'קומות' : 'קומה'}
                             </span>
                        )}
                        {apartment.rooms && (
                             <span className={styles.specItem}>
                                <BedDouble size={18} className={styles.specIcon} />
                                {apartment.rooms} חדרים
                             </span>
                        )}
                    </div>

                    {/* תיאור הדירה */}
                    {apartment.description && (
                        <div className={styles.descriptionSection}>
                            <h3>תיאור הנכס</h3>
                            <p className={styles.descriptionText}>{apartment.description}</p>
                        </div>
                    )}

                    {/* מפה */}
                    {apartment.latitude && apartment.longitude && (
                        <div className={styles.mapSection}>
                             <h3>מיקום הנכס</h3>
                             {/* חשוב: MapContainer צריך מידות מוגדרות כדי להופיע */}
                             <div className={styles.mapContainerWrapper}>
                                <MapContainer key={mapKey} center={position} zoom={15} scrollWheelZoom={false} className={styles.map}>
                                    <TileLayer
                                        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                                        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                                    />
                                    <Marker position={position}>
                                        <Popup>
                                            {apartment.address}
                                        </Popup>
                                    </Marker>
                                </MapContainer>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </>
    );
};

export default ApartmentDetailSheet;