from datetime import datetime, timedelta
from functools import wraps
import json

# Simple in-memory cache
_cache = {}

def cache_for_seconds(seconds=30):
    """Cache function result for specified seconds"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            cache_key = f"{func.__name__}:{json.dumps(args)}:{json.dumps(kwargs, sort_keys=True)}"
            
            # Check if cached and not expired
            if cache_key in _cache:
                cached_data, expiry = _cache[cache_key]
                if datetime.now() < expiry:
                    print(f"✓ Cache hit for {func.__name__}")
                    return cached_data
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            _cache[cache_key] = (result, datetime.now() + timedelta(seconds=seconds))
            
            # Clean old cache entries (simple cleanup)
            if len(_cache) > 1000:
                expired_keys = [k for k, (_, exp) in _cache.items() if datetime.now() >= exp]
                for k in expired_keys:
                    del _cache[k]
            
            print(f"✓ Cached result for {func.__name__}")
            return result
        return wrapper
    return decorator