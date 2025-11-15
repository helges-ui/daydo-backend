"""
Custom exception classes for DayDo application.
"""
from rest_framework import status


class DayDoException(Exception):
    """Base exception for DayDo application"""
    default_message = "An error occurred"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "GENERIC_ERROR"
    
    def __init__(self, message=None, error_code=None):
        self.message = message or self.default_message
        self.error_code = error_code or self.error_code
        super().__init__(self.message)


class ChildProfileException(DayDoException):
    """Exception for child profile operations"""
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "CHILD_PROFILE_ERROR"


class UserAlreadyHasAccountException(ChildProfileException):
    """Exception raised when trying to create account for child that already has one"""
    default_message = "Child already has a login account"
    error_code = "USER_ALREADY_HAS_ACCOUNT"


class InvalidPermissionException(DayDoException):
    """Exception for invalid permission operations"""
    default_message = "Invalid permission"
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "INVALID_PERMISSION"


class LocationSharingException(DayDoException):
    """Exception for location sharing operations"""
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "LOCATION_SHARING_ERROR"


class LocationSharingNotActiveException(LocationSharingException):
    """Exception raised when location sharing is not active"""
    default_message = "Location sharing is not active for this user"
    error_code = "SHARING_NOT_ACTIVE"


class LocationSharingExpiredException(LocationSharingException):
    """Exception raised when location sharing session has expired"""
    default_message = "Location sharing session has expired"
    error_code = "SHARING_EXPIRED"

