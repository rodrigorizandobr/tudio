#!/usr/bin/env python3
"""
Script to manually cleanup expired image search cache.
Usage: PYTHONPATH=. python scripts/cleanup_image_cache.py
"""

import sys
sys.path.insert(0, '.')

from backend.services.cache_service import search_cache
from backend.core.logger import log

if __name__ == "__main__":
    print("Starting manual cache cleanup...")
    log.info("Starting manual cache cleanup...")
    
    deleted = search_cache.cleanup_expired()
    
    print(f"✓ Removed {deleted} expired cache entries")
    log.info(f"Manual cache cleanup completed: {deleted} entries removed")
