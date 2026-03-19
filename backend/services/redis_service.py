import os
import redis
import json
from rq import Queue
from utils.logger import get_logger

logger = get_logger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
DEFAULT_JOB_TIMEOUT = '30m'
DEFAULT_JOB_CACHE_EXPIRE = 3_600

redis_client = redis.from_url(REDIS_URL)
default_queue = Queue("default", connection=redis_client)
priority_queue = Queue("high", connection=redis_client)


def acquire_lock(key: str, timeout: int = 10):
    try:
        return redis_client.set(key, "1", nx=True, ex=timeout)
    except Exception as e:
        logger.error("redis_acquire_lock_failed", key=key, error=str(e))
        return False


def release_lock(key: str):
    try:
        redis_client.delete(key)
        return True
    except Exception as e:
        logger.error("redis_release_lock_failed", key=key, error=str(e))
        return False


def set_cache(key: str, value: str, expire: int = None):
    try:
        redis_client.set(key, value, ex=expire)
        return True
    except Exception as e:
        logger.error("redis_set_cache_failed", key=key, error=str(e))
        return False


def get_cache(key: str):
    try:
        value = redis_client.get(key)
        return value.decode('utf-8') if value else None
    except Exception as e:
        logger.error("redis_get_cache_failed", key=key, error=str(e))
        return None


def delete_cache(key: str):
    try:
        redis_client.delete(key)
        return True
    except Exception as e:
        logger.error("redis_delete_cache_failed", key=key, error=str(e))
        return False


def set_job_cache(job_id: str, job_data: dict, expire: int = DEFAULT_JOB_CACHE_EXPIRE):
    try:
        cache_key = f"job:{job_id}"
        redis_client.set(cache_key, json.dumps(job_data), ex=expire)
        return True
    except Exception as e:
        logger.error("set_job_cache_failed", job_id=job_id, error=str(e))
        return False


def get_job_cache(job_id: str):
    try:
        cache_key = f"job:{job_id}"
        data = redis_client.get(cache_key)
        return json.loads(data) if data else None
    except Exception as e:
        logger.error("get_job_cache_failed", job_id=job_id, error=str(e))
        return None


def enqueue_job(func, *args, **kwargs):
    try:
        timeout = kwargs.pop('timeout', DEFAULT_JOB_TIMEOUT)
        job = default_queue.enqueue(func, *args, job_timeout=timeout, **kwargs)
        logger.info("job_enqueued", job_id=job.id, func=func.__name__)
        return job
    except Exception as e:
        logger.error("enqueue_job_failed", func=func.__name__, error=str(e))
        return None


def get_all_job_ids():
    try:
        keys = redis_client.keys("job:*")
        return [key.decode('utf-8').split(":", 1)[1] for key in keys]
    except Exception as e:
        logger.error("get_all_job_ids_failed", error=str(e))
        return []

