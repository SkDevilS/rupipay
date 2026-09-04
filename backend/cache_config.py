from flask_caching import Cache
import redis

# Initialize cache
cache = Cache()

def init_cache(app):
    """Initialize Redis cache with Flask app"""
    cache.init_app(app, config={
        'CACHE_TYPE': 'redis',
        'CACHE_REDIS_HOST': 'localhost',
        'CACHE_REDIS_PORT': 6379,
        'CACHE_REDIS_DB': 0,
        'CACHE_DEFAULT_TIMEOUT': 300,  # 5 minutes default
        'CACHE_KEY_PREFIX': 'moneyone_',
        'CACHE_REDIS_URL': 'redis://localhost:6379/0'
    })
    
    print("✅ Redis cache initialized")
    return cache

# Direct Redis client for advanced operations
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True
)

def clear_user_cache(user_id):
    """Clear all cache for a specific user"""
    pattern = f"moneyone_*{user_id}*"
    keys = redis_client.keys(pattern)
    if keys:
        redis_client.delete(*keys)
        print(f"Cleared {len(keys)} cache keys for user {user_id}")
        return len(keys)
    return 0

def clear_all_cache():
    """Clear all MoneyOne cache"""
    pattern = "moneyone_*"
    keys = redis_client.keys(pattern)
    if keys:
        redis_client.delete(*keys)
        print(f"Cleared {len(keys)} cache keys")
        return len(keys)
    return 0

def get_cache_stats():
    """Get Redis cache statistics"""
    try:
        info = redis_client.info('stats')
        memory = redis_client.info('memory')
        
        hits = info.get('keyspace_hits', 0)
        misses = info.get('keyspace_misses', 0)
        total = hits + misses
        
        hit_rate = (hits / total * 100) if total > 0 else 0
        
        return {
            'hits': hits,
            'misses': misses,
            'hit_rate': round(hit_rate, 2),
            'memory_used': memory.get('used_memory_human', 'N/A'),
            'total_keys': len(redis_client.keys('moneyone_*'))
        }
    except Exception as e:
        print(f"Error getting cache stats: {e}")
        return None
