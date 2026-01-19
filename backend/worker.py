from gevent import monkey
monkey.patch_all()
import os
from rq import Worker, Queue
from redis import from_url
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

listen = ['default', 'high']

conn = from_url(REDIS_URL)

if __name__ == '__main__':
    print("Starting RQ worker...")
    worker = Worker(listen, connection=conn)
    worker.work()
