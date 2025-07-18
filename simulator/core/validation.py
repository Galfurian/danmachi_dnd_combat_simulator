"""
Input validation system for JSON data and user inputs.
"""
from typing import Any, Dict, List, Optional, Type, Union
from dataclasses import dataclass
from enum import Enum


class ValidationResult:
    def __init__(self, is_valid: bool = True, errors: List[str] = None):
        self.is_valid = is_valid
        self.errors = errors or []
    
    def add_error(self, error: str):
        self.is_valid = False
        self.errors.append(error)
    
    def merge(self, other: 'ValidationResult'):
        if not other.is_valid:
            self.is_valid = False
            self.errors.extend(other.errors)


@dataclass
class FieldValidator:
    """Defines validation rules for a field."""
    required: bool = False
    field_type: Optional[Type] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    allowed_values: Optional[List[Any]] = None
    pattern: Optional[str] = None


class DataValidator:
    """Validates data structures against defined schemas."""
    
    def __init__(self, schema: Dict[str, FieldValidator]):
        self.schema = schema
    
    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate data against the schema."""
        result = ValidationResult()
        
        # Check required fields
        for field_name, validator in self.schema.items():
            if validator.required and field_name not in data:
                result.add_error(f"Required field '{field_name}' is missing")
                continue
                
            if field_name not in data:
                continue
                
            field_value = data[field_name]
            field_result = self._validate_field(field_name, field_value, validator)
            result.merge(field_result)
        
        return result
    
    def _validate_field(self, field_name: str, value: Any, validator: FieldValidator) -> ValidationResult:
        """Validate a single field."""
        result = ValidationResult()
        
        # Type checking
        if validator.field_type and not isinstance(value, validator.field_type):
            result.add_error(f"Field '{field_name}' must be of type {validator.field_type.__name__}")
            return result
        
        # Numeric range checking
        if isinstance(value, (int, float)):
            if validator.min_value is not None and value < validator.min_value:
                result.add_error(f"Field '{field_name}' must be >= {validator.min_value}")
            if validator.max_value is not None and value > validator.max_value:
                result.add_error(f"Field '{field_name}' must be <= {validator.max_value}")
        
        # String length checking
        if isinstance(value, str):
            if validator.min_length is not None and len(value) < validator.min_length:
                result.add_error(f"Field '{field_name}' must be at least {validator.min_length} characters")
            if validator.max_length is not None and len(value) > validator.max_length:
                result.add_error(f"Field '{field_name}' must be at most {validator.max_length} characters")
        
        # Allowed values checking
        if validator.allowed_values and value not in validator.allowed_values:
            result.add_error(f"Field '{field_name}' must be one of: {validator.allowed_values}")
        
        return result


# Common validation schemas
CHARACTER_SCHEMA = DataValidator({
    "name": FieldValidator(required=True, field_type=str, min_length=1, max_length=50),
    "type": FieldValidator(required=True, field_type=str, allowed_values=["PLAYER", "ENEMY", "ALLY"]),
    "race": FieldValidator(required=True, field_type=str, min_length=1),
    "levels": FieldValidator(required=True, field_type=dict),
    "stats": FieldValidator(required=True, field_type=dict),
    "total_hands": FieldValidator(required=False, field_type=int, min_value=0, max_value=10),
    "number_of_attacks": FieldValidator(required=False, field_type=int, min_value=1, max_value=10),
})

STATS_SCHEMA = DataValidator({
    "strength": FieldValidator(required=True, field_type=int, min_value=1, max_value=30),
    "dexterity": FieldValidator(required=True, field_type=int, min_value=1, max_value=30),
    "constitution": FieldValidator(required=True, field_type=int, min_value=1, max_value=30),
    "intelligence": FieldValidator(required=True, field_type=int, min_value=1, max_value=30),
    "wisdom": FieldValidator(required=True, field_type=int, min_value=1, max_value=30),
    "charisma": FieldValidator(required=True, field_type=int, min_value=1, max_value=30),
})

WEAPON_SCHEMA = DataValidator({
    "name": FieldValidator(required=True, field_type=str, min_length=1, max_length=50),
    "description": FieldValidator(required=False, field_type=str),
    "hands_required": FieldValidator(required=False, field_type=int, min_value=0, max_value=5),
    "attacks": FieldValidator(required=True, field_type=list),
})


def validate_character_data(data: Dict[str, Any]) -> ValidationResult:
    """Validate character data."""
    result = CHARACTER_SCHEMA.validate(data)
    
    # Validate stats if present
    if "stats" in data and isinstance(data["stats"], dict):
        stats_result = STATS_SCHEMA.validate(data["stats"])
        result.merge(stats_result)
    
    return result


def validate_weapon_data(data: Dict[str, Any]) -> ValidationResult:
    """Validate weapon data."""
    return WEAPON_SCHEMA.validate(data)
