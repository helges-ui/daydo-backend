"""
Custom exception handler for DayDo exceptions.
"""
import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from .exceptions import DayDoException

logger = logging.getLogger(__name__)


def daydo_exception_handler(exc, context):
    """
    Custom exception handler for DayDo exceptions.
    
    Args:
        exc: The exception instance
        context: Dictionary containing context information about the exception
        
    Returns:
        Response: DRF Response object with standardized error format
    """
    if isinstance(exc, DayDoException):
        logger.warning(
            f"DayDo exception: {exc.error_code} - {exc.message}",
            extra={'error_code': exc.error_code, 'context': context}
        )
        return Response(
            {
                'error': exc.message,
                'error_code': exc.error_code
            },
            status=exc.status_code
        )
    
    # Let DRF handle other exceptions
    response = exception_handler(exc, context)
    if response is not None:
        logger.error(
            f"DRF exception: {exc.__class__.__name__} - {str(exc)}",
            extra={'exception_type': exc.__class__.__name__, 'context': context}
        )
        # Standardize error format
        if 'detail' in response.data:
            response.data = {
                'error': response.data['detail'],
                'error_code': exc.__class__.__name__
            }
    return response

