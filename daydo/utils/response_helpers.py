"""
Response helper utilities for standardizing API responses.
"""
from rest_framework import status
from rest_framework.response import Response


class ResponseHelper:
    """Helper class for creating standardized API responses"""
    
    @staticmethod
    def error_response(message, status_code=status.HTTP_400_BAD_REQUEST, errors=None):
        """
        Create standardized error response.
        
        Args:
            message: Error message string
            status_code: HTTP status code (default: 400 Bad Request)
            errors: Optional dict of field-specific errors
            
        Returns:
            Response: DRF Response object with error format
        """
        response = {'error': message}
        if errors:
            response['errors'] = errors
        return Response(response, status=status_code)
    
    @staticmethod
    def success_response(data, message=None, status_code=status.HTTP_200_OK):
        """
        Create standardized success response.
        
        Args:
            data: Response data
            message: Optional success message
            status_code: HTTP status code (default: 200 OK)
            
        Returns:
            Response: DRF Response object with success format
        """
        response = {'data': data}
        if message:
            response['message'] = message
        return Response(response, status=status_code)
    
    @staticmethod
    def not_found_response(resource_name="Resource"):
        """
        Create standardized 404 Not Found response.
        
        Args:
            resource_name: Name of the resource that was not found
            
        Returns:
            Response: DRF Response with 404 status
        """
        return Response(
            {'error': f'{resource_name} not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    @staticmethod
    def forbidden_response(message="You do not have permission for this action"):
        """
        Create standardized 403 Forbidden response.
        
        Args:
            message: Forbidden message (default: generic permission message)
            
        Returns:
            Response: DRF Response with 403 status
        """
        return Response(
            {'error': message},
            status=status.HTTP_403_FORBIDDEN
        )
    
    @staticmethod
    def service_unavailable_response(message="Service is currently unavailable"):
        """
        Create standardized 503 Service Unavailable response.
        
        Args:
            message: Service unavailable message
            
        Returns:
            Response: DRF Response with 503 status
        """
        return Response(
            {'error': message},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    @staticmethod
    def bad_request_response(message="Invalid request", errors=None):
        """
        Create standardized 400 Bad Request response.
        
        Args:
            message: Bad request message
            errors: Optional dict of field-specific errors
            
        Returns:
            Response: DRF Response with 400 status
        """
        return ResponseHelper.error_response(
            message,
            status_code=status.HTTP_400_BAD_REQUEST,
            errors=errors
        )

