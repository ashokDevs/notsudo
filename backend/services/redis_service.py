import os
import redis
import json
from rq import Queue
from utils.logger import get_logger

logger = get_logger(__name__)

# Load Redis URL from environment
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Initialize Redis client
redis_client = redis.from_url(REDIS_URL)

# Initialize RQ Queues
# We use a default queue for general background jobs
default_queue = Queue("default", connection=redis_client)
# We can add more specialized queues if needed
priority_queue = Queue("high", connection=redis_client)

def set_cache(key: str, value: str, expire: int = None):
    """
    Set a value in Redis cache.
    :param key: Cache key
    :param value: Cache value (string)
    :param expire: Expiration time in seconds
    """
    try:
        redis_client.set(key, value, ex=expire)
        return True
    except Exception as e:
        logger.error("redis_set_cache_failed", key=key, error=str(e))
        return False

def get_cache(key: str):
    """
    Get a value from Redis cache.
    :param key: Cache key
    :return: Value or None
    """
    try:
        value = redis_client.get(key)
        return value.decode('utf-8') if value else None
    except Exception as e:
        logger.error("redis_get_cache_failed", key=key, error=str(e))
        return None

def delete_cache(key: str):
    """
    Delete a key from Redis cache.
    :param key: Cache key
    """
    try:
        redis_client.delete(key)
        return True
    except Exception as e:
        logger.error("redis_delete_cache_failed", key=key, error=str(e))
        return False

def set_job_cache(job_id: str, job_data: dict, expire: int = 3600):
    """
    Cache job data in Redis.
    """
    try:
        cache_key = f"job:{job_id}"
        redis_client.set(cache_key, json.dumps(job_data), ex=expire)
        return True
    except Exception as e:
        logger.error("set_job_cache_failed", job_id=job_id, error=str(e))
        return False

def get_job_cache(job_id: str):
    """
    Retrieve job data from Redis.
    """
    try:
        cache_key = f"job:{job_id}"
        data = redis_client.get(cache_key)
        return json.loads(data) if data else None
    except Exception as e:
        logger.error("get_job_cache_failed", job_id=job_id, error=str(e))
        return None

def enqueue_job(func, *args, **kwargs):
    """
    Enqueue a job in the default queue.
    """
    try:
        timeout = kwargs.pop('timeout', '30m') # Default timeout for PR processing is 30 mins
        job = default_queue.enqueue(func, *args, job_timeout=timeout, **kwargs)
        logger.info("job_enqueued", job_id=job.id, func=func.__name__)
        return job
    except Exception as e:
        logger.error("enqueue_job_failed", func=func.__name__, error=str(e))
        return None

def get_all_job_ids():
    """
    Get all job IDs stored in Redis by scanning for 'job:*' keys.
    """
    try:
        keys = redis_client.keys("job:*")
        return [key.decode('utf-8').split(":", 1)[1] for key in keys]
    except Exception as e:
        logger.error("get_all_job_ids_failed", error=str(e))
        return []

