"""
Tag mapping between frontend English tags and backend Hebrew tags
"""

TAG_MAPPING = {
    # Frontend English tag -> Hebrew tag in database
    # Based on Yad2 scraper PROPERTY_CHARACTERISTICS mapping
    'parking': 'חניה',
    'elevator': 'מעלית',
    'airconditioner': 'מיזוג',
    'airConditioner': 'מיזוג',
    'balcony': 'מרפסת', 
    'shelter': 'ממ"ד',
    'bars': 'סורגים',
    'warehouse': 'מחסן',
    'accessibility': 'גישה לנכים',
    'renovated': 'משופץ',  # General renovated
    'furniture': 'מרוהט',
    'pets': 'חיות מחמד',
    'forpartners': 'לשותפים',
    'forPartners': 'לשותפים', 
    'assetexclusive': 'נכס בלעדי',
    'assetExclusive': 'נכס בלעדי',
}

# Tags that have multiple variations
TAG_VARIATIONS = {
    'renovated': ['משופץ', 'בניין משופץ', 'משופצת אדריכלית'],
}

def map_english_to_hebrew_tags(english_tags):
    """
    Map English tags from frontend to Hebrew tags for database query
    Only returns tags that actually exist in the database
    """
    if not english_tags:
        return []
    
    hebrew_tags = []
    for tag in english_tags:
        tag_lower = tag.lower()
        
        # Check if tag has variations
        if tag_lower in TAG_VARIATIONS:
            hebrew_tags.extend(TAG_VARIATIONS[tag_lower])
        elif tag_lower in TAG_MAPPING:
            hebrew_tags.append(TAG_MAPPING[tag_lower])
        # If no mapping found, skip this tag (don't add non-existent tags)
    
    return hebrew_tags

def get_available_frontend_options():
    """
    Get the list of frontend options that have corresponding database tags
    """
    return list(TAG_MAPPING.keys())

def get_available_hebrew_tags():
    """
    Get the list of available Hebrew tags that match our English mapping
    """
    return list(TAG_MAPPING.values())
