import React from 'react';
import styles from '../styles/ApartmentDetailSheet.module.css';
import { 
    Maximize2, 
    Layers3, 
    BedDouble, 
    MapPin, 
    DollarSign, 
    Home, 
    Briefcase, 
    Phone, 
    Mail, 
    User, 
    CheckCircle2, 
    Building, 
    Droplets,
    Map,
    Hash,
    Landmark
} from 'lucide-react'; 
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import customMarkerIconUrl from '../assets/marker-icon.png'; 

const customIcon = L.icon({
    iconUrl: customMarkerIconUrl,
    iconSize: [25, 41],      
    iconAnchor: [12, 41],       
    popupAnchor: [1, -34]    
});

const ApartmentDetailSheet = ({ apartment }) => {
    if (!apartment) {
        return null; 
    }

    const position = (apartment.latitude && apartment.longitude)
        ? [apartment.latitude, apartment.longitude]
        : [32.0853, 34.7818]; 

    const mapKey = `${apartment.listing_id}-${position.join(',')}`; 

    // Format date if available
    const formatDate = (dateString) => {
        if (!dateString) return 'Not specified';
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('en-US', { 
                year: 'numeric', 
                month: 'short', 
                day: 'numeric' 
            });
        } catch (e) {
            return dateString;
        }
    };

    // Helper to check if a feature exists in the apartment
    const hasFeature = (feature) => apartment[feature] === true || apartment[feature] === 'true' || apartment[feature] === 1;

    // Format price with commas
    const formatPrice = (price) => {
        if (!price) return 'Price not available';
        return Math.floor(price).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    };

    return (
            <div className={styles.content}>
                <div className={styles.section}>
                    <h3 className={styles.sectionTitle}>Description</h3>
                    <p className={styles.descriptionText}>{apartment.description}</p>
                    <a href={`https://www.yad2.co.il/realestate/item/${apartment.yad2_url_token}`} target="_blank" rel="noopener noreferrer">Go to Yad2 to see contact details</a>
                </div>
                <div className={styles.section}>
                    <h3 className={styles.sectionTitle}>General Information</h3>
                <h3 className={styles.address}>
                    <Landmark size={16} className={styles.headerIcon} />
                    {`City: ${apartment.neighborhood.city || ''}`}
                </h3>
                <h3 className={styles.address}>
                    <MapPin size={16} className={styles.headerIcon} />
                    {`Street: ${apartment.street || ''}`}
                </h3>
                <h3 className={styles.address}>
                    <Map size={16} className={styles.headerIcon} />
                    {`Neighborhood: ${apartment.neighborhood.hebrew_name || ''}`}
                </h3>
                <h3 className={styles.address}>
                    <Hash size={16} className={styles.headerIcon} />
                    {`House Number: ${apartment.house_number || ''}`}
                </h3>
                <h3 className={styles.address}>
                    <Layers3 size={16} className={styles.headerIcon} />
                    {`Floor: ${apartment.floor || ''}`}
                </h3>
                </div>

            <div className={styles.section}>
                <h3 className={styles.sectionTitle}>Key Specifications</h3>
                {apartment.property_type && (
                    <span className={styles.address}>
                        <Home size={18} className={styles.specIcon} />
                        {`Property Type: ${apartment.property_type}`}
                    </span>
                )}
                {apartment.square_meter && (
                    <span className={styles.address}>
                            <Maximize2 size={18} className={styles.specIcon} />
                        {`Square Meters: ${apartment.square_meter}`}
                        </span>
                    )}
                {apartment.rooms_count && (
                    <span className={styles.address}>
                        <BedDouble size={18} className={styles.specIcon} />
                        {`Rooms: ${parseInt(apartment.rooms_count)}`}
                            </span>
                    )}
                {apartment.property_condition && (
                    <span className={styles.address}>
                        <CheckCircle2 size={18} className={styles.specIcon} />
                        {`Property Condition: ${apartment.property_condition.condition_name_en}`}
                            </span>
                    )}
                </div>

            {(apartment.price || apartment.arnona || apartment.vaad_bayit || apartment.electricity || apartment.water) && (
                <div className={styles.section}>
                    <h3 className={styles.sectionTitle}>Financial Details</h3>
                    <div className={styles.sectionContent}>
                        {apartment.price && (
                            <div className={styles.detailItem}>
                                <DollarSign size={16} className={styles.detailIcon} />
                                <div>
                                    <span className={styles.detailLabel}>Price: </span>
                                    <span className={styles.detailValue}>₪{formatPrice(apartment.price)}{apartment.price_period ? `/${apartment.price_period}` : '/month'}</span>
                                </div>
                            </div>
                        )}
                        {apartment.arnona && (
                            <div className={styles.detailItem}>
                                <Briefcase size={16} className={styles.detailIcon} />
                                <div>
                                    <span className={styles.detailLabel}>Property Tax: </span>
                                    <span className={styles.detailValue}>₪{formatPrice(apartment.arnona)}</span>
                                </div>
                            </div>
                        )}
                        {apartment.vaad_bayit && (
                            <div className={styles.detailItem}>
                                <Building size={16} className={styles.detailIcon} />
                                <div>
                                    <span className={styles.detailLabel}>Building Maintenance: </span>
                                    <span className={styles.detailValue}>₪{formatPrice(apartment.vaad_bayit)}</span>
                                </div>
                            </div>
                        )}
                        {(apartment.electricity || apartment.water) && (
                            <div className={styles.detailItem}>
                                <Droplets size={16} className={styles.detailIcon} />
                                <div>
                                    <span className={styles.detailLabel}>Utilities: </span>
                                    <span className={styles.detailValue}>
                                        {apartment.electricity && apartment.water ? 'Water & electricity included' : 
                                         apartment.electricity ? 'Electricity included' : 
                                         apartment.water ? 'Water included' : 'Not included'}
                                    </span>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            <div className={styles.section}>
                <h3 className={styles.sectionTitle}>Amenities</h3>
                {apartment.attributes && apartment.attributes.length > 0 ? (
                    <div className={styles.tagList}>
                        {apartment.attributes.map((attribute) => (
                            <span key={attribute.attribute_id} className={styles.tag}>{attribute.attribute_name}</span>
                        ))}
                    </div>
                ) : (
                    <p className={styles.noAmenities}>No amenities information available</p>
                )}
            </div>

            {/* Contact information */}
            {(apartment.contact_name || apartment.contact_phone || apartment.contact_email) && (
                <div className={styles.section}>
                    <h3 className={styles.sectionTitle}>Contact Information</h3>
                    <div className={styles.sectionContent}>
                        {apartment.contact_name && (
                            <div className={styles.detailItem}>
                                <User size={16} className={styles.detailIcon} />
                                <div>
                                    <span className={styles.detailLabel}>Contact: </span>
                                    <span className={styles.detailValue}>{apartment.contact_name}</span>
                                </div>
                            </div>
                        )}
                        {apartment.contact_phone && (
                            <div className={styles.detailItem}>
                                <Phone size={16} className={styles.detailIcon} />
                                <div>
                                    <span className={styles.detailLabel}>Phone: </span>
                                    <span className={styles.detailValue}>{apartment.contact_phone}</span>
                                </div>
                            </div>
                        )}
                        {apartment.contact_email && (
                            <div className={styles.detailItem}>
                                <Mail size={16} className={styles.detailIcon} />
                                <div>
                                    <span className={styles.detailLabel}>Email: </span>
                                    <span className={styles.detailValue}>{apartment.contact_email}</span>
                                </div>
                            </div>
                        )}
                    </div>
                    </div>
                )}

            {/* Map section */}
                {apartment.latitude && apartment.longitude && (
                    <div className={styles.mapSection}>
                    <h3 className={styles.sectionTitle}>Location</h3>
                            <div className={styles.mapContainerWrapper}>
                            <MapContainer key={mapKey} center={position} zoom={15} scrollWheelZoom={false} className={styles.map}>
                                <TileLayer
                                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                                />
                            <Marker position={position} icon={customIcon}>
                                    <Popup>
                                    {apartment.street ? `${apartment.street}, ${apartment.city}` : apartment.address || 'Location'}
                                    </Popup>
                                </Marker>
                            </MapContainer>
                        </div>
                    </div>
                )}
            </div>
    );
};

export default ApartmentDetailSheet;