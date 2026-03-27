import redis
from app.core.config import settings


# Shared client for connection pooling locally
redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
