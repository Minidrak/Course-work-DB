import os
import redis
from datetime import timedelta

# Redis configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

# Create Redis client
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True  # This will automatically decode responses to strings
)

# Token configuration
TOKEN_EXPIRY = timedelta(hours=24)  # Token expires after 24 hours

def store_token(user_id, token):
    """Store user token in Redis with expiration"""
    key = f"user_token:{user_id}"
    redis_client.setex(key, TOKEN_EXPIRY, token)
    return token

def get_token(user_id):
    """Get user token from Redis"""
    key = f"user_token:{user_id}"
    return redis_client.get(key)

def delete_token(user_id):
    """Delete user token from Redis"""
    key = f"user_token:{user_id}"
    redis_client.delete(key)

def store_session_data(user_id, data):
    """Store session data in Redis"""
    key = f"session:{user_id}"
    redis_client.hmset(key, data)
    redis_client.expire(key, TOKEN_EXPIRY)
    return True

def get_session_data(user_id):
    """Get session data from Redis"""
    key = f"session:{user_id}"
    return redis_client.hgetall(key)

def delete_session_data(user_id):
    """Delete session data from Redis"""
    key = f"session:{user_id}"
    redis_client.delete(key) 