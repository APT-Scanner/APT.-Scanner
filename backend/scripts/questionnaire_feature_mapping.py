#!/usr/bin/env python3
"""
Updated Questionnaire to Feature Vector Mapping System
Maps the reorganized questionnaire responses to neighborhood feature preferences.
"""

from typing import Dict, List, Optional, Tuple
import numpy as np

class QuestionnaireMapper:
    """Maps questionnaire responses to neighborhood feature preferences."""
    
    def __init__(self):
        # Current feature vector order (from create_neighborhood_features.py)
        self.feature_names = [
            'cultural_level',           # 0
            'religiosity_level',        # 1  
            'communality_level',        # 2
            'kindergardens_level',      # 3
            'maintenance_level',        # 4
            'mobility_level',           # 5
            'parks_level',              # 6
            'peaceful_level',           # 7
            'shopping_level',           # 8
            'safety_level'              # 9
        ]
        
        # Updated importance scale mapping for new question structure
        self.importance_scale = {
            'Very important': 0.9,
            'Somewhat important': 0.6,
            'Not important': 0.1,
            'Yes, I want to be in the center of the action': 0.9,
            'Close but not too close': 0.6,
            'As far as possible': 0.1,
            'No preference': 0.5,
            'Walking distance': 0.9,
            'Short drive or public transport ride': 0.6,
            'Very important - I want well-maintained buildings': 0.9,
            'Not important - I don\'t mind older/less maintained areas': 0.1,
            'Very important - I need a quiet area': 0.9,
            'Not important - I don\'t mind noise': 0.1,
            'Very important - I want an active, connected community': 0.9,
            'Not important - I prefer privacy': 0.2,
            'No': 0.1,
            'Yes': 0.9
        }
    
    def map_questionnaire_to_preferences(self, responses: Dict[str, any]) -> Dict[str, float]:
        """
        Convert questionnaire responses to feature preferences.
        
        Args:
            responses: Dictionary of question_id -> response
            
        Returns:
            Dictionary of feature_name -> importance_weight (0.1-0.9)
        """
        preferences = {feature: 0.5 for feature in self.feature_names}  # Default neutral
        
        # Map all question categories based on reorganized structure
        self._map_basic_questions(responses, preferences)
        self._map_dynamic_questions(responses, preferences)
        self._apply_persona_logic(responses, preferences)
        
        return preferences
    
    def _map_basic_questions(self, responses: Dict, preferences: Dict):
        """Map basic information questions."""
        
        # Religious community importance -> religiosity_level
        if 'religious_community_importance' in responses:
            importance = self.importance_scale.get(responses['religious_community_importance'], 0.5)
            preferences['religiosity_level'] = importance
        
        # Safety priority -> safety_level
        if 'safety_priority' in responses:
            importance = self.importance_scale.get(responses['safety_priority'], 0.5)
            preferences['safety_level'] = importance
        
        # Commute preference -> mobility_level (from nested questions)
        if 'commute_pref' in responses:
            commute_type = responses['commute_pref']
            if commute_type in ['Public transport', 'Walking']:
                preferences['mobility_level'] = 0.8
            elif commute_type in ['Bicycle / scooter']:
                preferences['mobility_level'] = 0.7
            elif commute_type == 'Private car':
                preferences['mobility_level'] = 0.4
    
    def _map_dynamic_questions(self, responses: Dict, preferences: Dict):
        """Map dynamic questionnaire questions."""
        
        # Children ages -> affects multiple features
        if 'children_ages' in responses:
            children_ages = responses['children_ages']
            if isinstance(children_ages, list):
                children_ages = children_ages[0] if children_ages else 'No children'
            
            if 'No children' not in children_ages:
                preferences['safety_level'] = max(preferences['safety_level'], 0.8)
                preferences['kindergardens_level'] = max(preferences['kindergardens_level'], 0.7)
                preferences['peaceful_level'] = max(preferences['peaceful_level'], 0.7)
        
        # Learning spaces -> cultural_level
        if 'learning_space_nearby' in responses:
            importance = self.importance_scale.get(responses['learning_space_nearby'], 0.5)
            preferences['cultural_level'] = max(preferences['cultural_level'], importance)
        
        # Shopping centers -> shopping_level
        if 'proximity_to_shopping_centers' in responses:
            importance = self.importance_scale.get(responses['proximity_to_shopping_centers'], 0.5)
            preferences['shopping_level'] = importance
        
        # Green spaces -> parks_level
        if 'proximity_to_green_spaces' in responses:
            importance = self.importance_scale.get(responses['proximity_to_green_spaces'], 0.5)
            preferences['parks_level'] = importance
        
        # Family activities -> communality_level
        if 'family_activities_nearby' in responses:
            importance = self.importance_scale.get(responses['family_activities_nearby'], 0.5)
            preferences['communality_level'] = max(preferences['communality_level'], importance)
        
        # Nightlife -> cultural_level and peaceful_level (inverse)
        if 'nightlife_proximity' in responses:
            response = responses['nightlife_proximity']
            if response == 'Yes, I want to be in the center of the action':
                preferences['cultural_level'] = max(preferences['cultural_level'], 0.9)
                preferences['peaceful_level'] = min(preferences['peaceful_level'], 0.3)
            elif response == 'Close but not too close':
                preferences['cultural_level'] = max(preferences['cultural_level'], 0.6)
                preferences['peaceful_level'] = 0.6
            elif response == 'As far as possible':
                preferences['cultural_level'] = min(preferences['cultural_level'], 0.2)
                preferences['peaceful_level'] = max(preferences['peaceful_level'], 0.9)
        
        # Community involvement -> communality_level
        if 'community_involvement_preference' in responses:
            importance = self.importance_scale.get(responses['community_involvement_preference'], 0.5)
            preferences['communality_level'] = max(preferences['communality_level'], importance)
        
        # Cultural activities -> cultural_level
        if 'cultural_activities_importance' in responses:
            importance = self.importance_scale.get(responses['cultural_activities_importance'], 0.5)
            preferences['cultural_level'] = max(preferences['cultural_level'], importance)
        
        # Neighborhood quality -> maintenance_level
        if 'neighborhood_quality_importance' in responses:
            importance = self.importance_scale.get(responses['neighborhood_quality_importance'], 0.5)
            preferences['maintenance_level'] = importance
        
        # Building condition -> maintenance_level (from nested question)
        if 'building_condition_preference' in responses:
            importance = self.importance_scale.get(responses['building_condition_preference'], 0.5)
            preferences['maintenance_level'] = max(preferences['maintenance_level'], importance)
        
        # Quiet hours -> peaceful_level
        if 'quiet_hours_importance' in responses:
            importance = self.importance_scale.get(responses['quiet_hours_importance'], 0.5)
            preferences['peaceful_level'] = max(preferences['peaceful_level'], importance)
        
        # Pet ownership -> parks_level
        if 'pet_ownership' in responses:
            if responses['pet_ownership'] == 'Yes':
                preferences['parks_level'] = max(preferences['parks_level'], 0.7)
    
    def _apply_persona_logic(self, responses: Dict, preferences: Dict):
        """Apply logic based on housing purpose (user persona)."""
        if 'housing_purpose' not in responses:
            return
        
        housing_purpose = responses['housing_purpose']
        if isinstance(housing_purpose, list):
            housing_purpose = housing_purpose[0] if housing_purpose else ''
        
        # Adjust preferences based on persona
        if 'Just me' in housing_purpose:
            # Single person - may prioritize convenience and cultural activities
            preferences['cultural_level'] = max(preferences['cultural_level'], 0.6)
            preferences['shopping_level'] = max(preferences['shopping_level'], 0.6)
            
        elif 'With a partner' in housing_purpose:
            # Couple - balanced preferences, slight emphasis on cultural and peaceful
            preferences['cultural_level'] = max(preferences['cultural_level'], 0.6)
            preferences['peaceful_level'] = max(preferences['peaceful_level'], 0.6)
            
        elif 'With family (and children)' in housing_purpose:
            # Family - prioritize safety, education, parks, peaceful environment
            preferences['safety_level'] = max(preferences['safety_level'], 0.8)
            preferences['kindergardens_level'] = max(preferences['kindergardens_level'], 0.7)
            preferences['parks_level'] = max(preferences['parks_level'], 0.7)
            preferences['peaceful_level'] = max(preferences['peaceful_level'], 0.7)
            preferences['communality_level'] = max(preferences['communality_level'], 0.6)
            
        elif 'With roommates' in housing_purpose:
            # Roommates - may prioritize nightlife, cultural activities, convenience
            preferences['cultural_level'] = max(preferences['cultural_level'], 0.7)
            preferences['shopping_level'] = max(preferences['shopping_level'], 0.6)
            preferences['mobility_level'] = max(preferences['mobility_level'], 0.7)
    
    def create_preference_vector(self, responses: Dict[str, any]) -> np.ndarray:
        """
        Create a preference vector from questionnaire responses.
        
        Args:
            responses: Dictionary of question_id -> response
            
        Returns:
            NumPy array of preferences matching feature vector order
        """
        preferences = self.map_questionnaire_to_preferences(responses)
        
        # Convert to array in correct order
        preference_vector = np.array([
            preferences[feature] for feature in self.feature_names
        ])
        
        return preference_vector
    
    def get_question_to_feature_mapping(self) -> Dict:
        """Get complete mapping of current questions to features."""
        return {
            'basic_questions_mapping': {
                'religious_community_importance': 'religiosity_level',
                'safety_priority': 'safety_level',
                'commute_pref': 'mobility_level'
            },
            'dynamic_questions_mapping': {
                'children_ages': 'kindergardens_level + safety_level + peaceful_level',
                'learning_space_nearby': 'cultural_level',
                'proximity_to_shopping_centers': 'shopping_level',
                'proximity_to_green_spaces': 'parks_level',
                'family_activities_nearby': 'communality_level',
                'nightlife_proximity': 'cultural_level + peaceful_level (inverse)',
                'community_involvement_preference': 'communality_level',
                'cultural_activities_importance': 'cultural_level',
                'neighborhood_quality_importance': 'maintenance_level',
                'building_condition_preference': 'maintenance_level',
                'quiet_hours_importance': 'peaceful_level',
                'pet_ownership': 'parks_level'
            },
            'persona_effects': {
                'Just me': 'cultural_level + shopping_level boost',
                'With a partner': 'cultural_level + peaceful_level boost',
                'With family (and children)': 'safety + kindergardens + parks + peaceful boost',
                'With roommates': 'cultural_level + shopping + mobility boost'
            },
            'missing_features_questions': [
                'proximity_to_gym -> fitness_facilities_level (MISSING FEATURE)',
                'medical_center_importance -> medical_facilities_level (MISSING FEATURE)', 
                'proximity_beach_importance -> beach_proximity_level (MISSING FEATURE)',
                'accessibility_needs -> accessibility_level (MISSING FEATURE)'
            ],
            'non_mappable_questions': [
                'housing_purpose (persona logic)',
                'points_of_interest (custom distance calculations)',
                'budget_range (price filtering)',
                'commute_time (filtering/scoring modifier)'
            ],
            'coverage_summary': {
                'total_features': 10,
                'features_with_questions': 10,
                'coverage_percentage': 100,
                'total_questions': 20,
                'mappable_questions': 12,
                'persona_questions': 1,
                'filter_questions': 3,
                'missing_feature_questions': 4
            }
        }

# Example usage and testing
def demo_updated_mapping():
    """Demonstrate the updated mapping system."""
    mapper = QuestionnaireMapper()
    
    # Example responses matching the new structure
    sample_responses = {
        # Basic questions
        'housing_purpose': ['With family (and children)'],
        'budget_range': 8000,
        'religious_community_importance': 'Not important',
        'safety_priority': 'Very important',
        'commute_pref': 'Public transport',
        
        # Dynamic questions
        'children_ages': ['School-age children (7-12 years)'],
        'learning_space_nearby': 'Not important',
        'proximity_to_shopping_centers': 'Very important',
        'proximity_to_green_spaces': 'Somewhat important',
        'family_activities_nearby': 'Very important',
        'nightlife_proximity': 'As far as possible',
        'community_involvement_preference': 'Very important - I want an active, connected community',
        'cultural_activities_importance': 'Somewhat important',
        'neighborhood_quality_importance': 'Very important',
        'quiet_hours_importance': 'Very important - I need a quiet area',
        'pet_ownership': 'No'
    }
    
    print("=== Updated Questionnaire to Feature Mapping Demo ===")
    print(f"Sample responses: {len(sample_responses)} questions answered")
    
    # Get preferences
    preferences = mapper.map_questionnaire_to_preferences(sample_responses)
    print("\nMapped preferences:")
    for feature, importance in preferences.items():
        print(f"  {feature}: {importance:.2f}")
    
    # Get preference vector
    pref_vector = mapper.create_preference_vector(sample_responses)
    print(f"\nPreference vector: {pref_vector}")
    
    # Show mapping summary
    mapping = mapper.get_question_to_feature_mapping()
    print(f"\n=== Coverage Summary ===")
    summary = mapping['coverage_summary']
    print(f"Total features: {summary['total_features']}")
    print(f"Features with questions: {summary['features_with_questions']}")
    print(f"Coverage: {summary['coverage_percentage']}%")
    print(f"Total questions: {summary['total_questions']}")
    print(f"Mappable to features: {summary['mappable_questions']}")
    print(f"Missing feature questions: {summary['missing_feature_questions']}")

if __name__ == "__main__":
    demo_updated_mapping()
