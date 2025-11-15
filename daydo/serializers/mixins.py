"""
Serializer mixins for common validation logic.
"""
from rest_framework import serializers


class CoordinateValidationMixin:
    """
    Mixin for latitude/longitude validation.
    
    Provides validate_latitude and validate_longitude methods
    that can be inherited by serializers that need coordinate validation.
    """
    
    def validate_latitude(self, value):
        """
        Validate latitude is between -90 and 90 degrees.
        
        Args:
            value: Latitude value to validate
            
        Returns:
            float: Validated latitude value
            
        Raises:
            ValidationError: If latitude is out of valid range
        """
        if value < -90 or value > 90:
            raise serializers.ValidationError(
                'Latitude must be between -90 and 90 degrees.'
            )
        return value
    
    def validate_longitude(self, value):
        """
        Validate longitude is between -180 and 180 degrees.
        
        Args:
            value: Longitude value to validate
            
        Returns:
            float: Validated longitude value
            
        Raises:
            ValidationError: If longitude is out of valid range
        """
        if value < -180 or value > 180:
            raise serializers.ValidationError(
                'Longitude must be between -180 and 180 degrees.'
            )
        return value

