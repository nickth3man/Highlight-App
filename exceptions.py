"""
Custom exceptions for Highlight App
"""

class HighlightAppError(Exception):
    """Base exception for Highlight App"""
    pass

class APIError(HighlightAppError):
    """Base exception for API-related errors"""
    pass

class APIAuthenticationError(APIError):
    """Raised when API authentication fails"""
    pass

class RateLimitError(APIError):
    """Raised when API rate limit is exceeded"""
    pass

class APINotAvailableError(APIError):
    """Raised when a required API is not available"""
    pass

class SearchError(HighlightAppError):
    """Raised when search fails"""
    pass
