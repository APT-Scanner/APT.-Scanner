"""
Attribute mapping between frontend English attributes and backend Hebrew attributes
"""

ATTRIBUTE_EN_TO_HE_MAPPING = {
    # Frontend English attribute -> Hebrew attribute in database
    # Based on Yad2 scraper PROPERTY_CHARACTERISTICS mapping
    'parking': 'חניה',
    'elevator': 'מעלית',
    'airconditioner': 'מיזוג',
    'balcony': 'מרפסת', 
    'shelter': 'ממ"ד',
    'bars': 'סורגים',
    'warehouse': 'מחסן',
    'accessibility': 'גישה לנכים',
    'renovated': 'משופצת', 
    'furniture': 'מרוהטת',
    'pets': 'חיות מחמד',
    'sunheatedboiler': 'דוד שמש',
    'forpartners': 'מתאים לשותפים',
    'forPartners': 'מתאים לשותפים', 
}

ATTRIBUTE_ID_MAPPING = {
    'parking': 1,
    'elevator': 2,
    'airconditioner': 3,
    'airConditioner': 3,
    'balcony': 4,
    'shelter': 5,
    'bars': 6,
    'warehouse': 7,
    'accessibility': 8,
    'renovated': 9,
    'furniture': 10,
    'pets': 11,
    'sunheatedboiler': 12,
    'forpartners': 13,
    'forPartners': 13,
}

def map_english_to_hebrew_attributes(english_attributes):
    """
    Map English attributes from frontend to Hebrew attributes for database query
    Only returns attributes that actually exist in the database
    """
    if not english_attributes:
        return []
    
    hebrew_attributes = []
    for attribute in english_attributes:
        attribute_lower = attribute.lower()
        
        # Check if attribute has variations
        if attribute_lower in ATTRIBUTE_EN_TO_HE_MAPPING:
            hebrew_attributes.append(ATTRIBUTE_EN_TO_HE_MAPPING[attribute_lower])
        # If no mapping found, skip this attribute (don't add non-existent attributes)
    
    return hebrew_attributes

def get_available_frontend_options():
    """
    Get the list of frontend options that have corresponding database attributes
    """
    return list(ATTRIBUTE_EN_TO_HE_MAPPING.keys())

def get_available_hebrew_attributes():
    """
    Get the list of available Hebrew attributes that match our English mapping
    """
    return list(ATTRIBUTE_EN_TO_HE_MAPPING.values())

def create_hebrew_to_english_mapping():
    """
    Create a reverse mapping from Hebrew attributes to English keys
    """
    return {hebrew: english for english, hebrew in ATTRIBUTE_EN_TO_HE_MAPPING.items()}

def map_hebrew_to_english_attributes(hebrew_attributes):
    """
    Map Hebrew attributes from scraper to English attributes for database storage
    """
    if not hebrew_attributes:
        return []
    
    hebrew_to_english = create_hebrew_to_english_mapping()
    english_attributes = []
    
    for attribute in hebrew_attributes:
        # Clean up the Hebrew text to match mapping
        cleaned_attribute = attribute.strip()
        if cleaned_attribute in hebrew_to_english:
            english_attributes.append(hebrew_to_english[cleaned_attribute])
    
    return english_attributes
