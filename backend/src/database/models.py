"""Database models for the application."""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, ForeignKey, Enum as SQLEnum,
    DECIMAL, TEXT, BIGINT, TIMESTAMP, Table,
    DateTime  
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from enum import Enum as PyEnum
from .postgresql_db import Base 


# Define the association table for the Many-to-Many relationship
# between listings and attributes using SQLAlchemy Core Table object
listing_attributes_association = Table(
    "listing_attributes",
    Base.metadata, 
    Column("listing_id", BIGINT, ForeignKey("listings.listing_id", ondelete="CASCADE"), primary_key=True),
    Column("attribute_id", Integer, ForeignKey("attributes.attribute_id", ondelete="CASCADE"), primary_key=True),
)

# --- Lookup Tables Models ---
class PropertyCondition(Base):
    __tablename__ = "property_conditions"

    condition_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    condition_name_he: Mapped[Optional[str]] = mapped_column(String(100))
    condition_name_en: Mapped[Optional[str]] = mapped_column(String(100))

    def __repr__(self):
        return f"<PropertyCondition(id={self.condition_id}, name_en='{self.condition_name_en}')>"

# --- Main Tables Models ---
class Neighborhood(Base):
    """Core neighborhood information - basic identification and geographic data."""
    __tablename__ = "neighborhoods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hebrew_name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    english_name: Mapped[Optional[str]] = mapped_column(String(150), unique=True)
    city: Mapped[Optional[str]] = mapped_column(String(100))
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # One-to-One relationships to related data tables
    metrics: Mapped[Optional["NeighborhoodMetrics"]] = relationship(back_populates="neighborhood", uselist=False)
    meta_data: Mapped[Optional["NeighborhoodMetadata"]] = relationship(back_populates="neighborhood", uselist=False)

    def __repr__(self):
        return f"<Neighborhood(id={self.id}, name='{self.hebrew_name}')>"


class NeighborhoodMetrics(Base):
    """Metrics data for neighborhoods."""
    __tablename__ = "neighborhood_metrics"

    neighborhood_id: Mapped[int] = mapped_column(Integer, ForeignKey("neighborhoods.id", ondelete="CASCADE"), primary_key=True)
    avg_sale_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(15, 2))
    avg_rental_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 2))
    social_economic_index: Mapped[Optional[float]] = mapped_column(Float)
    popular_political_party: Mapped[Optional[str]] = mapped_column(String(100))
    school_rating: Mapped[Optional[float]] = mapped_column(Float)
    beach_distance_km: Mapped[Optional[float]] = mapped_column(Float)
    
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # One-to-One relationship back to Neighborhood
    neighborhood: Mapped["Neighborhood"] = relationship(back_populates="metrics")

    def __repr__(self):
        return f"<NeighborhoodMetrics(id={self.neighborhood_id})>"


class NeighborhoodMetadata(Base):
    """Metadata and external system data for neighborhoods."""
    __tablename__ = "neighborhood_metadata"

    neighborhood_id: Mapped[int] = mapped_column(Integer, ForeignKey("neighborhoods.id", ondelete="CASCADE"), primary_key=True)
    overview: Mapped[Optional[str]] = mapped_column(TEXT)
    external_city_id: Mapped[Optional[int]] = mapped_column(Integer)
    external_area_id: Mapped[Optional[int]] = mapped_column(Integer)
    external_top_area_id: Mapped[Optional[int]] = mapped_column(Integer)
    
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # One-to-One relationship back to Neighborhood
    neighborhood: Mapped["Neighborhood"] = relationship(back_populates="meta_data")

    def __repr__(self):
        return f"<NeighborhoodMetadata(id={self.neighborhood_id})>"
    
class ListingMetadata(Base):
    __tablename__ = "listing_metadata"
    listing_id: Mapped[int] = mapped_column(Integer, ForeignKey("listings.listing_id", ondelete="CASCADE"), primary_key=True)
    neighborhood_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("neighborhoods.id", ondelete="CASCADE"))
    category_id: Mapped[Optional[int]] = mapped_column(Integer)
    subcategory_id: Mapped[Optional[int]] = mapped_column(Integer)
    ad_type: Mapped[Optional[str]] = mapped_column(String(20))
    property_condition_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("property_conditions.condition_id", ondelete="CASCADE"))
    cover_image_url: Mapped[Optional[str]] = mapped_column(TEXT)
    video_url: Mapped[Optional[str]] = mapped_column(TEXT)
    description: Mapped[Optional[str]] = mapped_column(TEXT)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    property_condition: Mapped[Optional["PropertyCondition"]] = relationship("PropertyCondition")
    neighborhood: Mapped[Optional["Neighborhood"]] = relationship("Neighborhood")


class Listing(Base):
    __tablename__ = "listings"

    listing_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    yad2_url_token: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)

    # Other fields
    price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 2))
    property_type: Mapped[Optional[str]] = mapped_column(String(50))
    rooms_count: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(3, 1))
    square_meter: Mapped[Optional[int]] = mapped_column(Integer)
    street: Mapped[Optional[str]] = mapped_column(String(150))
    house_number: Mapped[Optional[str]] = mapped_column(String(20)) # Varchar for '10א' etc.
    floor: Mapped[Optional[int]] = mapped_column(Integer)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()) 

    # One-to-Many relationship to Images
    images: Mapped[List["Image"]] = relationship(back_populates="listing", cascade="all, delete-orphan")

    # Many-to-Many relationship to Attributes
    attributes: Mapped[List["Attribute"]] = relationship(
        secondary=listing_attributes_association, back_populates="listings"
    )

    # One-to-One relationship to ListingMetadata
    listing_metadata: Mapped[Optional["ListingMetadata"]] = relationship(
        "ListingMetadata", 
        foreign_keys="ListingMetadata.listing_id",
        uselist=False
    )

    favorited_by = relationship("Favorite", back_populates="listing")

    # Add ViewHistory model to track when users viewed apartments
    view_history: Mapped[List["ViewHistory"]] = relationship(
        "ViewHistory", back_populates="listing"
    )

    @property
    def cover_image_url(self) -> Optional[str]:
        """Get cover image URL from metadata."""
        return self.listing_metadata.cover_image_url if self.listing_metadata else None

    @property
    def description(self) -> Optional[str]:
        """Get description from metadata."""
        return self.listing_metadata.description if self.listing_metadata else None

    @property 
    def is_active(self) -> bool:
        """Get active status from metadata."""
        return self.listing_metadata.is_active if self.listing_metadata else True

    @property
    def property_condition(self) -> Optional["PropertyCondition"]:
        """Get property condition from metadata."""
        return self.listing_metadata.property_condition if self.listing_metadata else None

    @property
    def neighborhood(self) -> Optional["Neighborhood"]:
        """Get neighborhood from metadata."""
        return self.listing_metadata.neighborhood if self.listing_metadata else None

    def __repr__(self):
        return f"<Listing(id={self.listing_id}, yad2_url_token='{self.yad2_url_token}')>"
    
class Image(Base):
    __tablename__ = "images"

    image_id: Mapped[int] = mapped_column(Integer, primary_key=True) # Serial handled by DB
    listing_id: Mapped[int] = mapped_column(Integer, ForeignKey("listings.listing_id", ondelete="CASCADE"), nullable=False)
    image_url: Mapped[str] = mapped_column(TEXT, nullable=False)

    # Many-to-One relationship back to Listing
    listing: Mapped["Listing"] = relationship(back_populates="images")

    def __repr__(self):
        return f"<Image(id={self.image_id}, listing_id={self.listing_id})>"

# --- Enums ---
class PaceOfLife(str, PyEnum):
    RELAXED = "relaxed"
    BALANCED = "balanced"
    ENERGETIC = "energetic"

class ParkingImportance(str, PyEnum):
    ESSENTIAL = "essential"
    PREFERABLE = "preferable"
    NOT_IMPORTANT = "not_important"

class ImportanceScale(str, PyEnum):
    NOT_IMPORTANT = "not_important"
    SOMEWHAT = "somewhat"
    VERY = "very"

class YesNoPref(str, PyEnum): 
    YES = "yes"
    NO = "no"
    NO_PREFERENCE = "no_preference"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    firebase_uid: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True, nullable=True)
    # Relationship to preferences
    preferences: Mapped[Optional["UserPreferences"]] = relationship(back_populates="owner")

class UserPreferences(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True, unique=True, nullable=False, index=True)

    # Section 1: Lifestyle
    pace_of_life: Mapped[Optional[PaceOfLife]] = mapped_column(SQLEnum(PaceOfLife), nullable=True)
    commute_pref_pt: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    commute_pref_walk: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    commute_pref_bike: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    commute_pref_car: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    commute_pref_wfh: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)

    # Section 2: Location preferences
    proximity_pref_shops: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    proximity_pref_gym: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    max_commute_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # in minutes

    # Section 3: Lifestyle-related needs
    dog_park_nearby: Mapped[Optional[YesNoPref]] = mapped_column(SQLEnum(YesNoPref), nullable=True)
    learning_space_nearby: Mapped[Optional[YesNoPref]] = mapped_column(SQLEnum(YesNoPref), nullable=True)

    # Section 4: Importance ratings
    proximity_beach_importance: Mapped[Optional[ImportanceScale]] = mapped_column(SQLEnum(ImportanceScale), nullable=True)
    safety_importance: Mapped[Optional[ImportanceScale]] = mapped_column(SQLEnum(ImportanceScale), nullable=True)
    green_spaces_importance: Mapped[Optional[ImportanceScale]] = mapped_column(SQLEnum(ImportanceScale), nullable=True)
    medical_center_importance: Mapped[Optional[ImportanceScale]] = mapped_column(SQLEnum(ImportanceScale), nullable=True)
    schools_importance: Mapped[Optional[ImportanceScale]] = mapped_column(SQLEnum(ImportanceScale), nullable=True)

    # Relationship back to User
    owner: Mapped["User"] = relationship(back_populates="preferences")


class Favorite(Base):
    __tablename__ = "favorites"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.firebase_uid"), nullable=False, index=True)
    listing_id: Mapped[int] = mapped_column(Integer, ForeignKey("listings.listing_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    listing: Mapped["Listing"] = relationship("Listing", back_populates="favorited_by")
    user: Mapped["User"] = relationship("User")

# Add ViewHistory model to track when users viewed apartments
class ViewHistory(Base):
    __tablename__ = "view_history"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.firebase_uid"), nullable=False, index=True)
    listing_id: Mapped[int] = mapped_column(Integer, ForeignKey("listings.listing_id"), nullable=False, index=True)
    viewed_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    listing: Mapped["Listing"] = relationship("Listing")
    user: Mapped["User"] = relationship("User")
    
    def __repr__(self):
        return f"<ViewHistory(user_id={self.user_id}, listing_id={self.listing_id}, viewed_at={self.viewed_at})>"


# Add UserFilters model to store user-specific filters
class UserFilters(Base):
    __tablename__ = "user_filters"
    
    # Using firebase_uid as primary key to directly link with frontend auth
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.firebase_uid"), primary_key=True, index=True)
    
    # Filter properties
    type: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="rent")
    city: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    neighborhood: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    property_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    price_min: Mapped[int] = mapped_column(Integer, nullable=False, default=500)
    price_max: Mapped[int] = mapped_column(Integer, nullable=False, default=15000)
    rooms_min: Mapped[float] = mapped_column(Float, nullable=False, default=1)
    rooms_max: Mapped[float] = mapped_column(Float, nullable=False, default=8)
    size_min: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    size_max: Mapped[int] = mapped_column(Integer, nullable=False, default=500)
    options: Mapped[Optional[str]] = mapped_column(String, nullable=True) # Comma-separated list of options
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), 
        server_default=func.now(),
        onupdate=func.now()
    )
    
    def __repr__(self):
        return f"<UserFilters(user_id={self.user_id}, type={self.type})>"

# Neighborhood Features Model for Recommendations
class NeighborhoodFeatures(Base):
    """Model for neighborhood feature vectors."""
    __tablename__ = "neighborhood_features"
    
    neighborhood_id: Mapped[int] = mapped_column(Integer, ForeignKey("neighborhoods.id", ondelete="CASCADE"), primary_key=True)
    
    # Individual feature scores (0-1 scale)
    cultural_level: Mapped[Optional[float]] = mapped_column(Float)
    religiosity_level: Mapped[Optional[float]] = mapped_column(Float)
    communality_level: Mapped[Optional[float]] = mapped_column(Float)
    kindergardens_level: Mapped[Optional[float]] = mapped_column(Float)
    maintenance_level: Mapped[Optional[float]] = mapped_column(Float)
    mobility_level: Mapped[Optional[float]] = mapped_column(Float)
    parks_level: Mapped[Optional[float]] = mapped_column(Float)
    peaceful_level: Mapped[Optional[float]] = mapped_column(Float)
    shopping_level: Mapped[Optional[float]] = mapped_column(Float)
    safety_level: Mapped[Optional[float]] = mapped_column(Float)
    nightlife_level: Mapped[Optional[float]] = mapped_column(Float)
    
    # Combined feature vector for ML calculations
    feature_vector: Mapped[Optional[List[float]]] = mapped_column(ARRAY(Float))
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())


class UserPreferenceVector(Base):
    """Stores cached user preference vectors for fast recommendation lookup."""
    __tablename__ = "user_preference_vectors"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)  # Firebase UID
    
    # Individual preference scores (0-1 scale, same order as NeighborhoodFeatures)
    cultural_level: Mapped[float] = mapped_column(Float, nullable=False)
    religiosity_level: Mapped[float] = mapped_column(Float, nullable=False)
    communality_level: Mapped[float] = mapped_column(Float, nullable=False)
    kindergardens_level: Mapped[float] = mapped_column(Float, nullable=False)
    maintenance_level: Mapped[float] = mapped_column(Float, nullable=False)
    mobility_level: Mapped[float] = mapped_column(Float, nullable=False)
    parks_level: Mapped[float] = mapped_column(Float, nullable=False)
    peaceful_level: Mapped[float] = mapped_column(Float, nullable=False)
    shopping_level: Mapped[float] = mapped_column(Float, nullable=False)
    safety_level: Mapped[float] = mapped_column(Float, nullable=False)
    nightlife_level: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Combined preference vector for ML calculations  
    preference_vector: Mapped[List[float]] = mapped_column(ARRAY(Float), nullable=False)
    
    # Metadata
    questionnaire_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<UserPreferenceVector(user_id='{self.user_id}', version={self.questionnaire_version})>"



class Attribute(Base):
    __tablename__ = "attributes"
    
    attribute_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attribute_name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Relationships
    listings: Mapped[List["Listing"]] = relationship(
        secondary=listing_attributes_association, back_populates="attributes"
    )

    def __repr__(self):
        return f"<Attribute(id={self.attribute_id}, name='{self.attribute_name}')>"
