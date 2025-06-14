"""Schemas for the API."""
from pydantic import BaseModel, Field, conint, confloat, ConfigDict, EmailStr
from typing import Optional, List, Any, Dict
from datetime import datetime
from decimal import Decimal 
from .models import PaceOfLife, ParkingImportance, ImportanceScale, YesNoPref


class UserBase(BaseModel):
    email: Optional[EmailStr] = Field(None, description="User's email address") 
    username: Optional[str] = Field(None, max_length=100) 
    is_active: Optional[bool] = Field(True, description="Is the user account active?")
    

class UserCreate(UserBase):
    firebase_uid: str = Field(..., description="Firebase Unique User ID")
    email: EmailStr = Field(..., description="User's email address (required on creation)") 

class UserUpdate(UserBase):
    pass # No additional fields for update

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
    image_url: str
    model_config = ConfigDict(from_attributes=True)

class NeighborhoodSchema(BaseModel):
    yad2_hood_id: int
    hebrew_name: str
    english_name: Optional[str] = None
    avg_purchase_price: Optional[Decimal] = None
    avg_rent_price: Optional[Decimal] = None
    socioeconomic_index: Optional[float] = None
    avg_school_rating: Optional[float] = None
    general_overview: Optional[str] = None
    bars_count: Optional[int] = None
    restaurants_count: Optional[int] = None
    clubs_count: Optional[int] = None
    shopping_malls_count: Optional[int] = None
    unique_entertainment_count: Optional[int] = None
    primary_schools_count: Optional[int] = None
    elementary_schools_count: Optional[int] = None
    secondary_schools_count: Optional[int] = None
    high_schools_count: Optional[int] = None
    universities_count: Optional[int] = None
    closest_beach_distance_km: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: Optional[str] = None
    yad2_city_id: Optional[int] = None
    yad2_area_id: Optional[int] = None
    yad2_top_area_id: Optional[int] = None
    yad2_doc_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ListingSchema(BaseModel):
    order_id: int
    token: str
    subcategory_id: Optional[int] = None
    category_id: Optional[int] = None
    ad_type: Optional[str] = None
    price: Optional[Decimal] = None
    property_type: Optional[str] = None
    rooms_count: Optional[Decimal] = None
    square_meter: Optional[int] = None
    cover_image_url: Optional[str] = None
    video_url: Optional[str] = None
    city: Optional[str] = None
    area: Optional[str] = None
    neighborhood_text: Optional[str] = None
    street: Optional[str] = None
    house_number: Optional[str] = None
    floor: Optional[int] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool

    neighborhood: Optional[NeighborhoodSchema] = None
    property_condition: Optional[PropertyConditionSchema] = None
    images: List[ImageSchema] = []
    tags: List[TagSchema] = []

    model_config = ConfigDict(from_attributes=True)

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

class FavoriteCreateSchema(BaseModel):
    listing_id: int
    
class FavoriteSchema(BaseModel):
    id: int
    user_id: str
    listing_id: int
    created_at: datetime
    
    class Config:
        orm_mode = True

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
    type: Optional[str] = Field(None, description="Type of listing (rent or sale)")
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