import os
from flask_socketio import SocketIO
from utils.logger import get_logger

logger = get_logger(__name__)

# Load Redis URL from environment
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

_socketio = None

def get_socketio():
    global _socketio
    if _socketio is None:
        # Initialize SocketIO without an app - this will be used for emitting from background tasks
        # it uses the Redis message queue to communicate with the main SocketIO server
        # Explicitly set async_mode to avoid detection issues
        _socketio = SocketIO(message_queue=REDIS_URL, async_mode='gevent')
    return _socketio

def emit_job_update(job_id, entry):
    """
    Emit a structured log entry to the job's room.
    :param job_id: The ID of the job
    :param entry: The structured log entry dictionary
    """
    try:
        si = get_socketio()
        si.emit('job_log', {
            'jobId': job_id,
            'entry': entry
        }, room=job_id)
    except Exception as e:
        logger.error("socket_emit_failed", job_id=job_id, error=str(e))

def emit_job_status(job_id, status, stage=None):
    """
    Emit a status update for a job.
    """
    try:
        si = get_socketio()
        si.emit('job_status', {
            'jobId': job_id,
            'status': status,
            'stage': stage
        }, room=job_id)
    except Exception as e:
        logger.error("socket_emit_status_failed", job_id=job_id, error=str(e))

def emit_user_event(user_id, event_name, data):
    """
    Emit an event to a specific user's room.
    """
    try:
        si = get_socketio()
        si.emit(event_name, data, room=f"user_{user_id}")
    except Exception as e:
        logger.error("socket_emit_user_event_failed", user_id=user_id, event=event_name, error=str(e))

# For backward compatibility with db.py
class SocketProxy:
    def emit(self, *args, **kwargs):
        return get_socketio().emit(*args, **kwargs)

socketio = SocketProxy()
