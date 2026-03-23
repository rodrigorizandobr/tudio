"""
Rate limiting configuration for the application.
Extracted to separate module to avoid circular imports.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.core.configs import settings

import os

# Initialize rate limiter
# Uses IP address as the key for rate limiting
# Enabled strict checks unless TESTING is True OR BYPASS_RATE_LIMIT is set
# This allows start.sh to run E2E tests (many logins) without blocking
bypass = os.getenv("BYPASS_RATE_LIMIT", "False").lower() in ("true", "1", "yes")

limiter = Limiter(
    key_func=get_remote_address,
    enabled=not settings.TESTING and not bypass
)

