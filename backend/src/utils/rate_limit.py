"""
Rate limiting configuration.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Create limiter instance
limiter = Limiter(key_func=get_remote_address)

# Rate limit rules
RATE_LIMITS = {
    "default": "100/minute",
    "create": "20/minute",
    "delete": "10/minute",
    "health": "200/minute",
}
