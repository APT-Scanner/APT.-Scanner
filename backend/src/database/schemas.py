"""Schemas for the API."""
from pydantic import BaseModel, Field, conint, ConfigDict, EmailStr
from typing import Optional, List, Any, Dict
from datetime import datetime
from decimal import Decimal 
from .models import PaceOfLife, ImportanceScale, YesNoPref


class UserBase(BaseModel):
    email: Optional[EmailStr] = Field(None, description="User's email address") 
    username: Optional[str] = Field(None, max_length=50) 
    
class UserCreate(UserBase):
    firebase_uid: str = Field(..., description="Firebase Unique User ID")
    email: EmailStr = Field(..., description="User's email address (required on creation)") 

class UserUpdate(UserBase):
    pass 

class UserInDBBase(UserBase):
    id: int = Field(..., description="Internal database User ID")
    firebase_uid: str = Field(..., description="Firebase Unique User ID")
    
    model_config = ConfigDict(from_attributes=True) 

class User(UserInDBBase): 
    pass

# Lookup table schemas
class PropertyConditionSchema(BaseModel):
    condition_id: int
    condition_name_he: Optional[str] = None
    condition_name_en: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class TagSchema(BaseModel):
    tag_id: int
    tag_name: str
    model_config = ConfigDict(from_attributes=True)

class ImageSchema(BaseModel):
    image_id: int
    listing_id: int
    image_url: str
    model_config = ConfigDict(from_attributes=True)

class NeighborhoodMetricsSchema(BaseModel):
    neighborhood_id: int
    avg_sale_price: Optional[Decimal] = None
    avg_rental_price: Optional[Decimal] = None
    social_economic_index: Optional[float] = None
    popular_political_party: Optional[str] = None
    school_rating: Optional[float] = None
    beach_distance_km: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class NeighborhoodMetadataSchema(BaseModel):
    neighborhood_id: int
    overview: Optional[str] = None
    external_city_id: Optional[int] = None
    external_area_id: Optional[int] = None
    external_top_area_id: Optional[int] = None
    
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class NeighborhoodSchema(BaseModel):
    id: int
    hebrew_name: str
    english_name: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    
    # Optional related data
    metrics: Optional[NeighborhoodMetricsSchema] = None
    meta_data: Optional[NeighborhoodMetadataSchema] = None
    
    model_config = ConfigDict(from_attributes=True)

class ListingMetadataSchema(BaseModel):
    listing_id: int
    neighborhood_id: Optional[int] = None
    category_id: Optional[int] = None
    subcategory_id: Optional[int] = None
    ad_type: Optional[str] = None
    property_condition_id: Optional[int] = None
    cover_image_url: Optional[str] = None
    video_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ListingSchema(BaseModel):
    listing_id: int
    yad2_url_token: str
    price: Optional[Decimal] = None
    property_type: Optional[str] = None
    rooms_count: Optional[Decimal] = None
    square_meter: Optional[int] = None
    street: Optional[str] = None
    house_number: Optional[str] = None
    floor: Optional[int] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    
    # Fields from ListingMetadata
    cover_image_url: Optional[str] = None
    is_active: Optional[bool] = True

    neighborhood: Optional[NeighborhoodSchema] = None
    property_condition: Optional[PropertyConditionSchema] = None
    images: List[ImageSchema] = []
    tags: List[TagSchema] = []

    model_config = ConfigDict(from_attributes=True)

class UserPreferencesSchema(BaseModel):
    user_id: int
    # Section 1: Lifestyle
    pace_of_life: Optional[PaceOfLife] = None
    commute_pref_pt: Optional[bool] = None
    commute_pref_walk: Optional[bool] = None
    commute_pref_bike: Optional[bool] = None
    commute_pref_car: Optional[bool] = None
    commute_pref_wfh: Optional[bool] = None

    # Section 2: Location preferences
    proximity_pref_shops: Optional[bool] = None
    proximity_pref_gym: Optional[bool] = None
    max_commute_time: Optional[int] = None

    # Section 3: Lifestyle-related needs
    dog_park_nearby: Optional[YesNoPref] = None
    learning_space_nearby: Optional[YesNoPref] = None

    # Section 4: Importance ratings
    proximity_beach_importance: Optional[ImportanceScale] = None
    safety_importance: Optional[ImportanceScale] = None
    green_spaces_importance: Optional[ImportanceScale] = None
    medical_center_importance: Optional[ImportanceScale] = None
    schools_importance: Optional[ImportanceScale] = None

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

class QuestionnaireAnswers(BaseModel):
    pace_of_life: Optional[PaceOfLife] = None
    commute_pref_pt: Optional[bool] = None
    commute_pref_walk: Optional[bool] = None
    commute_pref_bike: Optional[bool] = None
    commute_pref_car: Optional[bool] = None
    commute_pref_wfh: Optional[bool] = None
    proximity_pref_shops: Optional[bool] = None
    proximity_pref_gym: Optional[bool] = None
    max_commute_time: Optional[conint(ge=5, le=120)] = None
    dog_park_nearby: Optional[YesNoPref] = None
    learning_space_nearby: Optional[YesNoPref] = None
    proximity_beach_importance: Optional[ImportanceScale] = None
    safety_importance: Optional[ImportanceScale] = None
    green_spaces_importance: Optional[ImportanceScale] = None
    medical_center_importance: Optional[ImportanceScale] = None
    schools_importance: Optional[ImportanceScale] = None

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True
    )

class NeighborhoodFeaturesSchema(BaseModel):
    neighborhood_id: int
    hebrew_name: str
    
    # Individual feature scores (0-1 scale)
    cultural_level: Optional[float] = None
    religiosity_level: Optional[float] = None
    communality_level: Optional[float] = None
    kindergardens_level: Optional[float] = None
    maintenance_level: Optional[float] = None
    mobility_level: Optional[float] = None
    parks_level: Optional[float] = None
    peaceful_level: Optional[float] = None
    shopping_level: Optional[float] = None
    safety_level: Optional[float] = None
    nightlife_level: Optional[float] = None
    
    # Combined feature vector for ML calculations
    feature_vector: Optional[List[float]] = None
    
    # Metadata
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class UserPreferenceVectorSchema(BaseModel):
    user_id: str  # Firebase UID
    
    # Individual preference scores (0-1 scale, same order as NeighborhoodFeatures)
    cultural_level: float
    religiosity_level: float
    communality_level: float
    kindergardens_level: float
    maintenance_level: float
    mobility_level: float
    parks_level: float
    peaceful_level: float
    shopping_level: float
    safety_level: float
    nightlife_level: float
    
    # Combined preference vector for ML calculations  
    preference_vector: List[float]
    
    # Metadata
    questionnaire_version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class QuestionModel(BaseModel):
    id: str
    category: str
    text: str
    type: str
    options: Optional[List[Any]] = None
    config: Optional[dict[str,Any]] = None
    conditional: Optional[dict[str,Any]] = None
    display_type: Optional[str] = None
    placeholder: Optional[str] = None
    branches: Optional[Dict[str, List[str]]] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

class FavoriteSchema(BaseModel):
    id: int
    user_id: str
    listing_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# ViewHistory schemas
class ViewHistoryCreate(BaseModel):
    listing_id: int

class ViewHistorySchema(BaseModel):
    id: int
    user_id: str
    listing_id: int
    viewed_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# UserFilters schemas
class UserFiltersBase(BaseModel):
    type: Optional[str] = Field("rent", description="Type of listing (rent or sale)")
    city: Optional[str] = Field(None, description="City name")
    neighborhood: Optional[str] = Field(None, description="Neighborhood name")
    price_min: int = Field(500, description="Minimum price")
    price_max: int = Field(15000, description="Maximum price")
    rooms_min: float = Field(1, description="Minimum number of rooms")
    rooms_max: float = Field(8, description="Maximum number of rooms")
    size_min: int = Field(10, description="Minimum size in square meters")
    size_max: int = Field(500, description="Maximum size in square meters")
    options: Optional[str] = Field(None, description="Comma-separated list of filter options")

class UserFiltersCreate(UserFiltersBase):
    pass

class UserFiltersUpdate(UserFiltersBase):
    pass

class UserFiltersSchema(UserFiltersBase):
    user_id: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)