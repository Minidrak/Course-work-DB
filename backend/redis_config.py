import os
import redis
import json
from datetime import timedelta

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

# Создаем Redis 
try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True, 
        socket_timeout=5,  
        socket_connect_timeout=5,  
        retry_on_timeout=True
    )
    # соединение
    redis_client.ping()
    print("Successfully connected to Redis")
except redis.ConnectionError as e:
    print(f"Failed to connect to Redis: {str(e)}")
    raise
except Exception as e:
    print(f"Unexpected error connecting to Redis: {str(e)}")
    raise

# Token on
TOKEN_EXPIRY = timedelta(hours=24)  
CACHE_EXPIRY = timedelta(minutes=30) 

def store_token(user_id, token):
    try:
        key = f"user_token:{user_id}"
        redis_client.setex(key, TOKEN_EXPIRY, token)
        return token
    except Exception as e:
        print(f"Error storing token: {str(e)}")
        raise

def get_token(user_id):
    try:
        key = f"user_token:{user_id}"
        return redis_client.get(key)
    except Exception as e:
        print(f"Error getting token: {str(e)}")
        return None

def delete_token(user_id):
    try:
        key = f"user_token:{user_id}"
        redis_client.delete(key)
    except Exception as e:
        print(f"Error deleting token: {str(e)}")
        raise

def store_session_data(user_id, data):
    try:
        key = f"session:{user_id}"
        redis_client.hmset(key, data)
        redis_client.expire(key, TOKEN_EXPIRY)
        return True
    except Exception as e:
        print(f"Error storing session data: {str(e)}")
        raise

def get_session_data(user_id):
    try:
        key = f"session:{user_id}"
        return redis_client.hgetall(key)
    except Exception as e:
        print(f"Error getting session data: {str(e)}")
        return None

def delete_session_data(user_id):
    try:
        key = f"session:{user_id}"
        redis_client.delete(key)
    except Exception as e:
        print(f"Error deleting session data: {str(e)}")
        raise

# кэш для артикулов
def cache_artworks(artworks):
    try:
        key = "artworks:all"
        redis_client.setex(key, CACHE_EXPIRY, json.dumps(artworks))
        return True
    except Exception as e:
        print(f"Error caching artworks: {str(e)}")
        raise

def get_cached_artworks():
    try:
        key = "artworks:all"
        data = redis_client.get(key)
        return json.loads(data) if data else None
    except json.JSONDecodeError as e:
        print(f"Error decoding cached artworks: {str(e)}")
        return None
    except Exception as e:
        print(f"Error getting cached artworks: {str(e)}")
        return None

def invalidate_artworks_cache():
    try:
        key = "artworks:all"
        redis_client.delete(key)
    except Exception as e:
        print(f"Error invalidating artworks cache: {str(e)}")
        raise

# кэш для отзывов
def cache_artwork_reviews(artwork_id, reviews):
    try:
        key = f"reviews:artwork:{artwork_id}"
        redis_client.setex(key, CACHE_EXPIRY, json.dumps(reviews))
        return True
    except Exception as e:
        print(f"Error caching artwork reviews: {str(e)}")
        raise

def get_cached_artwork_reviews(artwork_id):
    try:
        key = f"reviews:artwork:{artwork_id}"
        data = redis_client.get(key)
        return json.loads(data) if data else None
    except json.JSONDecodeError as e:
        print(f"Error decoding cached reviews: {str(e)}")
        return None
    except Exception as e:
        print(f"Error getting cached reviews: {str(e)}")
        return None

def invalidate_artwork_reviews_cache(artwork_id):
    try:
        key = f"reviews:artwork:{artwork_id}"
        redis_client.delete(key)
    except Exception as e:
        print(f"Error invalidating reviews cache: {str(e)}")
        raise

# PubSub для уведомлений
def publish_notification(channel, message):
    try:
        redis_client.publish(channel, json.dumps(message))
        return True
    except Exception as e:
        print(f"Error publishing notification: {str(e)}")
        raise

def get_pubsub():
    # получаем объект PubSub
    try:
        return redis_client.pubsub()
    except Exception as e:
        print(f"Error getting PubSub object: {str(e)}")
        raise 