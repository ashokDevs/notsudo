from gevent import monkey
monkey.patch_all()
import os
import json
import hmac
import hashlib
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, join_room, leave_room
from dotenv import load_dotenv

from services.groq_service import GroqService
from services.ai_service import AIService, AVAILABLE_MODELS, DEFAULT_MODEL
from services.github_service import GitHubService
from services.pr_service import PRService
from services import db as database
from services.redis_service import set_cache, get_cache, delete_cache, enqueue_job, set_job_cache, get_job_cache, get_all_job_ids
import tasks
from utils.logger import get_logger
import requests as py_requests

logger = get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)
CORS(app)

# Initialize SocketIO with Redis message queue for background task communication
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
socketio = SocketIO(app, cors_allowed_origins="*", message_queue=REDIS_URL)

@socketio.on('join_job')
def handle_join_job(data):
    job_id = data.get('jobId')
    if job_id:
        join_room(job_id)
        logger.info("socket_client_joined_job", job_id=job_id, sid=request.sid)

@socketio.on('leave_job')
def handle_leave_job(data):
    job_id = data.get('jobId')
    if job_id:
        leave_room(job_id)
        logger.info("socket_client_left_job", job_id=job_id, sid=request.sid)

@socketio.on('join_user')
def handle_join_user(data):
    user_id = data.get('userId')
    if user_id:
        join_room(f"user_{user_id}")
        logger.info("socket_client_joined_user", user_id=user_id, sid=request.sid)

@socketio.on('leave_user')
def handle_leave_user(data):
    user_id = data.get('userId')
    if user_id:
        leave_room(f"user_{user_id}")
        logger.info("socket_client_left_user", user_id=user_id, sid=request.sid)

jobs_file = "/tmp/jobs.json"

# Global executor for thread management
# Limit max_workers to avoid resource exhaustion
executor = ThreadPoolExecutor(max_workers=10)

def load_config():
    return {
        'github_token': os.environ.get('GITHUB_TOKEN'),
        'groq_key': os.environ.get('GROQ_API_KEY'),
        'openrouter_key': os.environ.get('OPENROUTER_API_KEY'),
        'use_openrouter': os.environ.get('USE_OPENROUTER', 'false').lower() == 'true',
        'webhook_secret': os.environ.get('WEBHOOK_SECRET', '')
    }


def get_ai_service(config, user_model=None):
    """
    Factory function to get the appropriate AI service.
    
    In development (USE_OPENROUTER=false): Uses GroqService
    In production (USE_OPENROUTER=true): Uses AIService (OpenRouter)
    
    Args:
        config: Application config dict
        user_model: Optional user-selected model for OpenRouter
    """
    if config.get('use_openrouter'):
        api_key = config.get('openrouter_key')
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not configured")
        return AIService(api_key=api_key, model=user_model)
    else:
        api_key = config.get('groq_key')
        if not api_key:
            raise ValueError("GROQ_API_KEY not configured")
        return GroqService(api_key=api_key)

def load_jobs(user_id=None):
    """Load jobs from database or fall back to JSON file, merging with Redis cache."""
    base_jobs = []
    if database.is_db_available():
        base_jobs = database.get_jobs(user_id=user_id)
    elif os.path.exists(jobs_file):
        # Fallback to JSON file
        try:
            with open(jobs_file, 'r') as f:
                base_jobs = json.load(f)
        except Exception:
            base_jobs = []
        
        # Simple local filtering if DB not available
        if user_id:
            base_jobs = [j for j in base_jobs if (j.get('userId') == user_id or j.get('user_id') == user_id)]
    
    # Track which job IDs we already have
    existing_job_ids = {job.get('id') for job in base_jobs if job.get('id')}
    
    # Merge with Redis cache for the most up-to-date status
    for i, job in enumerate(base_jobs):
        job_id = job.get('id')
        if job_id:
            cached_job = get_job_cache(job_id)
            if cached_job:
                # Update with cached data while preserving non-cached fields if any
                base_jobs[i] = {**job, **cached_job}

    # Add jobs from Redis that aren't in base_jobs (e.g. newly created or not yet persisted)
    redis_job_ids = get_all_job_ids()
    for job_id in redis_job_ids:
        if job_id not in existing_job_ids:
            cached_job = get_job_cache(job_id)
            if cached_job:
                # Filter by user_id if requested
                if user_id:
                    cached_user_id = cached_job.get('userId') or cached_job.get('user_id')
                    # If job has a user_id and it doesn't match, skip it.
                    # If it doesn't have a user_id, we might want to show it anyway (system jobs/webhooks)
                    # but for now, let's be strict if they are in the user's dashboard.
                    if cached_user_id and cached_user_id != user_id:
                        continue
                        
                base_jobs.insert(0, cached_job)
                
    return base_jobs

def save_job(job):
    """Save job to Redis cache (write-through) and then to database or JSON file."""
    job_id = job.get('id')
    if job_id:
        # Step 1: Write to Redis cache first
        set_job_cache(job_id, job)
        
    # Step 2: Write to persistent storage
    if database.is_db_available():
        existing = database.get_job_by_id(job_id)
        if existing:
            database.update_job(job_id, job)
        else:
            database.insert_job(job)
        return
    
    # Fallback to JSON file
    jobs = load_jobs()
    existing_index = None
    for i, existing_job in enumerate(jobs):
        if existing_job.get('id') == job.get('id'):
            existing_index = i
            break
    
    if existing_index is not None:
        jobs[existing_index] = job
    else:
        jobs.insert(0, job)
    
    jobs = jobs[:100]
    with open(jobs_file, 'w') as f:
        json.dump(jobs, f)

def is_job_in_progress(repo_full_name, issue_number):
    """Check if there is already a job in progress for this issue."""
    jobs = load_jobs()
    for job in jobs:
        if (job.get('repo') == repo_full_name and
            job.get('issueNumber') == issue_number and
            job.get('status') in ['processing', 'generating', 'analyzing']):
            return True
    return False

def is_rate_limited(repo_full_name, issue_number, window_seconds=60):
    """Check if a job was created for this issue recently."""
    jobs = load_jobs()
    now = datetime.now()
    for job in jobs:
        if (job.get('repo') == repo_full_name and
            job.get('issueNumber') == issue_number):

            created_at_str = job.get('createdAt')
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str)
                    time_diff = (now - created_at).total_seconds()
                    if time_diff < window_seconds:
                        return True
                except ValueError:
                    continue
    return False


def create_job_atomically(repo_full_name, issue_number, job_data):
    """
    Create a job atomically, preventing race conditions from concurrent webhooks.
    
    Uses atomic database operation when available, falls back to in-memory checks
    for JSON storage.
    
    Returns:
        The created job dict if successful, None if a duplicate exists
    """
    if database.is_db_available():
        # Use atomic database operation
        result = database.atomic_create_job_if_not_exists(
            repo_full_name=repo_full_name,
            issue_number=issue_number,
            job_data=job_data
        )
        if result is None:
            logger.warning("job_duplicate_prevented_atomic", repo=repo_full_name, issue=issue_number)
        return result
    else:
        # Fallback: use in-memory checks (not fully atomic, but best effort)
        if is_job_in_progress(repo_full_name, issue_number):
            logger.warning("job_duplicate_prevented", repo=repo_full_name, issue=issue_number)
            return None
        if is_rate_limited(repo_full_name, issue_number):
            logger.warning("job_rate_limited", repo=repo_full_name, issue=issue_number)
            return None
        save_job(job_data)
        return job_data



def verify_github_signature(payload_body, signature_header, secret):
    if not signature_header or not secret:
        return False
    
    hash_algorithm, github_signature = signature_header.split('=')
    
    mac = hmac.new(secret.encode(), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = mac.hexdigest()
    
    return hmac.compare_digest(expected_signature, github_signature)

def get_current_webhook_url():
    base_url = os.environ.get('REPL_SLUG')
    if base_url:
        domain = f"{base_url}.{os.environ.get('REPL_OWNER', 'replit')}.repl.co"
        webhook_url = f"https://{domain}/api/webhook"
    else:
        webhook_url = "http://localhost:8000/api/webhook"
    return webhook_url

@app.route('/api/config', methods=['POST'])
def save_configuration():
    return jsonify({
        'error': 'Configuration is managed with environment variables. Update your .env file instead of using this endpoint.'
    }), 400

@app.route('/api/config', methods=['GET'])
def get_configuration():
    config = load_config()
    return jsonify({
        'hasGithubToken': bool(config.get('github_token')),
        'hasGroqKey': bool(config.get('groq_key')),
        'hasOpenRouterKey': bool(config.get('openrouter_key')),
        'useOpenRouter': config.get('use_openrouter', False),
        'hasWebhookSecret': bool(config.get('webhook_secret'))
    }), 200

@app.route('/api/models', methods=['GET'])
def get_available_models():
    """Get list of available AI models."""
    return jsonify({
        'models': list(AVAILABLE_MODELS.values()),
        'default': DEFAULT_MODEL
    }), 200

@app.route('/api/user/ai-settings', methods=['GET'])
def get_user_ai_settings():
    """Get user's AI settings (selected model and custom rules)."""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    
    settings = database.get_user_ai_settings(user_id)
    if settings is None:
        return jsonify({
            'selectedModel': DEFAULT_MODEL,
            'customRules': ''
        }), 200
    
    return jsonify(settings), 200

@app.route('/api/user/ai-settings', methods=['PUT'])
def update_user_ai_settings():
    """Update user's AI settings."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    
    selected_model = data.get('selectedModel')
    custom_rules = data.get('customRules')
    
    result = database.update_user_ai_settings(
        user_id=user_id,
        selected_model=selected_model,
        custom_rules=custom_rules
    )
    
    if result is None:
        return jsonify({'error': 'Failed to update settings'}), 500
    
    return jsonify(result), 200

@app.route('/api/user/delete', methods=['DELETE'])
def delete_user():
    """Delete user and all associated data."""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    
    success = database.delete_user_data(user_id)
    if success:
        return jsonify({'message': 'User and all data deleted successfully'}), 200
    else:
        return jsonify({'error': 'Failed to delete user or user not found'}), 404

@app.route('/api/webhook-url', methods=['GET'])
def get_webhook_url():
    return jsonify({'webhookUrl': get_current_webhook_url()}), 200

@app.route('/api/auth/<path:path>', methods=['GET', 'POST'])
def proxy_auth(path):
    """
    Proxy Better Auth and Dodo webhooks from Flask (8000) to Next.js (3000).
    Highly transparent proxy to ensure signatures aren't broken.
    """
    url = f"http://localhost:3000/api/auth/{path}"
    
    # Filter out problematic headers
    excluded = ['host', 'content-length', 'connection', 'content-type']
    headers = {key: value for (key, value) in request.headers if key.lower() not in excluded}
    
    # Add forwarding headers
    headers['X-Forwarded-Host'] = request.host
    headers['X-Forwarded-Proto'] = request.scheme
    headers['X-Forwarded-For'] = request.remote_addr
    # Re-add content-type specifically
    if request.content_type:
        headers['Content-Type'] = request.content_type

    # Enhanced logging for webhook debugging
    webhook_headers = {k: v for k, v in request.headers if 'webhook' in k.lower() or 'signature' in k.lower() or 'dodo' in k.lower()}
    logger.info("proxy_auth_attempt", 
                path=path, 
                method=request.method, 
                webhook_headers=webhook_headers,
                all_headers_passed=list(headers.keys()))
    
    try:
        data = request.get_data()
        if request.method == 'GET':
            resp = py_requests.get(url, params=request.args, headers=headers, timeout=10)
        else:
            resp = py_requests.post(url, data=data, headers=headers, timeout=10)
        
        # Enhanced logging for errors
        if resp.status_code >= 400:
            logger.error("proxy_auth_result", 
                        status=resp.status_code, 
                        path=path,
                        response_body=resp.text[:500] if resp.text else None)
        else:
            logger.info("proxy_auth_result", status=resp.status_code, path=path)
        
        # Filter response headers
        resp_excluded = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        resp_headers = [(name, value) for (name, value) in resp.headers.items()
                        if name.lower() not in resp_excluded]
        
        return (resp.content, resp.status_code, resp_headers)
    except Exception as e:
        logger.error("proxy_auth_error", error=str(e), path=path)
        return jsonify({'error': 'Proxy failed'}), 502

@app.route('/api/repos/webhook', methods=['POST'])
def manage_webhook():
    """Enable or disable webhook for a repository."""
    config = load_config()
    github_token = config.get('github_token')

    if not github_token:
        return jsonify({'error': 'GitHub token not configured'}), 500

    data = request.get_json()
    repo_full_name = data.get('repo')
    action = data.get('action') # 'enable' or 'disable'
    
    if not repo_full_name or action not in ['enable', 'disable']:
        return jsonify({'error': 'Invalid request parameters'}), 400

    try:
        github_service = GitHubService(github_token)
        webhook_url = get_current_webhook_url()

        if action == 'enable':
            secret = config.get('webhook_secret', '')
            if not secret:
                 return jsonify({'error': 'Webhook secret not configured in env'}), 500

            result = github_service.create_webhook(repo_full_name, webhook_url, secret)
            return jsonify({'success': True, 'webhook': result}), 200
        else:
            result = github_service.delete_webhook(repo_full_name, webhook_url)
            return jsonify({'success': result}), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error("manage_webhook_failed", error=str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/api/repos/webhook/bulk', methods=['POST'])
def manage_webhook_bulk():
    """Enable or disable webhooks for multiple repositories."""
    config = load_config()
    github_token = config.get('github_token')

    if not github_token:
        return jsonify({'error': 'GitHub token not configured'}), 500

    data = request.get_json()
    repos = data.get('repos', [])
    action = data.get('action') # 'enable' or 'disable'

    if not repos or action not in ['enable', 'disable']:
        return jsonify({'error': 'Invalid request parameters'}), 400

    try:
        github_service = GitHubService(github_token)
        webhook_url = get_current_webhook_url()
        secret = config.get('webhook_secret', '')

        if action == 'enable' and not secret:
             return jsonify({'error': 'Webhook secret not configured in env'}), 500

        results = {}

        def process_repo(repo_name):
            try:
                if action == 'enable':
                    github_service.create_webhook(repo_name, webhook_url, secret)
                    return repo_name, True
                else:
                    github_service.delete_webhook(repo_name, webhook_url)
                    return repo_name, True
            except Exception as e:
                logger.error("bulk_webhook_failed_single", repo=repo_name, action=action, error=str(e))
                return repo_name, False

        # Use global executor
        futures = {executor.submit(process_repo, repo): repo for repo in repos}
        for future in futures:
            repo_name, success = future.result()
            results[repo_name] = success

        return jsonify({'results': results}), 200

    except Exception as e:
        logger.error("manage_webhook_bulk_failed", error=str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/api/repos/check-webhooks', methods=['POST'])
def check_webhooks():
    """Check webhook status for a list of repositories."""
    config = load_config()
    github_token = config.get('github_token')

    if not github_token:
        return jsonify({'error': 'GitHub token not configured'}), 500

    data = request.get_json()
    repos = data.get('repos', [])

    if not repos:
        return jsonify({'statuses': {}}), 200

    try:
        github_service = GitHubService(github_token)
        webhook_url = get_current_webhook_url()

        results = {}

        # Helper function for threading
        def check_repo(repo_name):
            try:
                status = github_service.get_webhook_status(repo_name, webhook_url)
                return repo_name, bool(status)
            except Exception as e:
                logger.warning("check_webhook_failed_single", repo=repo_name, error=str(e))
                return repo_name, False

        # Use global executor
        futures = {executor.submit(check_repo, repo): repo for repo in repos}
        for future in futures:
            repo_name, status = future.result()
            results[repo_name] = status

        return jsonify({'statuses': results}), 200

    except Exception as e:
        logger.error("check_webhooks_failed", error=str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/api/webhook', methods=['POST'])
def handle_webhook():
    config = load_config()
    webhook_secret = config.get('webhook_secret')
    
    # Read raw data once - it can only be read once from the stream
    raw_data = request.data
    
    if webhook_secret:
        signature = request.headers.get('X-Hub-Signature-256')
        if not verify_github_signature(raw_data, signature, webhook_secret):
            return jsonify({'error': 'Invalid signature'}), 403
    
    # Parse JSON from the raw data we already read
    try:
        data = json.loads(raw_data) if raw_data else None
    except (json.JSONDecodeError, TypeError):
        data = None
    
    if not data:
        logger.warning("webhook_no_data", content_type=request.content_type, body_length=len(raw_data) if raw_data else 0)
        return jsonify({'error': 'No data provided or invalid JSON'}), 400
    
    action = data.get('action')
    comment = data.get('comment', {})
    issue = data.get('issue', {})
    repository = data.get('repository', {})
    
    logger.info(
        "webhook_received",
        action=action,
        repo=repository.get('full_name'),
        issue_number=issue.get('number')
    )
    
    if action != 'created':
        return jsonify({'message': 'Ignored: not a comment creation'}), 200
    
    comment_body = comment.get('body', '')
    comment_id = comment.get('id')  # GitHub's unique comment ID
    
    if '@notsudo' not in comment_body:
        logger.debug("webhook_ignored", reason="notsudo not mentioned")
        return jsonify({'message': 'Ignored: @notsudo not mentioned'}), 200
    
    github_token = config.get('github_token')
    
    if not github_token:
        return jsonify({'error': 'Missing GitHub token'}), 500
    
    # Validate AI service availability
    try:
        _ = get_ai_service(config)
    except ValueError as e:
        return jsonify({'error': str(e)}), 500
    
    repo_full_name = repository.get('full_name')
    issue_number = issue.get('number')
    issue_title = issue.get('title')
    issue_body = issue.get('body', '')
    
    if not repo_full_name:
        return jsonify({
            'error': 'Repository full_name is missing from webhook payload',
            'repository_data': repository
        }), 400
    
    if not issue_number:
        return jsonify({
            'error': 'Issue number is missing from webhook payload',
            'issue_data': issue
        }), 400
    
    # Use comment_id for deduplication - same comment will have same ID across webhook retries
    job_id = f"{repo_full_name}-{issue_number}-{comment_id}" if comment_id else f"{repo_full_name}-{issue_number}-{datetime.now().timestamp()}"
    
    # Build job data
    job = {
        'id': job_id,
        'repo': repo_full_name,
        'issueNumber': issue_number,
        'issueTitle': issue_title,
        'status': 'processing',
        'stage': 'analyzing',
        'retryCount': 0,
        'createdAt': datetime.now().isoformat(),
        'prUrl': None,
        'error': None,
        'logs': ['Job started'],
        'validationLogs': []
    }
    
    # Atomically check for duplicates and create job
    created_job = create_job_atomically(repo_full_name, issue_number, job)
    if created_job is None:
        return jsonify({'message': 'Job already in progress or rate limited for this issue'}), 429
    
    # Enqueue the job in Redis Queue
    is_pr = 'pull_request' in issue or bool(issue.get('pull_request'))
    
    enqueue_job(
        tasks.process_webhook_task,
        repo_full_name=repo_full_name,
        issue_number=issue_number,
        issue_title=issue_title,
        issue_body=issue_body,
        comment_body=comment_body,
        is_pr=is_pr,
        job_id=job_id,
        github_token=github_token,
        config=config
    )
    
    return jsonify({
        'success': True,
        'message': 'Job enqueued successfully',
        'job_id': job_id
    }), 202

@app.route('/api/test-issue', methods=['POST'])
def test_issue():
    """
    Test endpoint that processes an issue directly without needing a webhook.
    Accepts raw issue data and runs through the same pipeline as the webhook.
    
    Expected JSON payload:
    {
        "repo": "owner/repo-name",
        "issue_number": 123,
        "issue_title": "Issue title",
        "issue_body": "Issue description",
        "comment_body": "@notsudo please fix this"
    }
    """
    config = load_config()
    github_token = config.get('github_token')
    
    if not github_token:
        return jsonify({'error': 'Missing GitHub token'}), 500
    
    # Validate AI service availability
    try:
        _ = get_ai_service(config)
    except ValueError as e:
        return jsonify({'error': str(e)}), 500
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    
    repo_full_name = data.get('repo')
    issue_number = data.get('issue_number')
    issue_title = data.get('issue_title', f'Test Issue #{issue_number}')
    issue_body = data.get('issue_body', '')
    comment_body = data.get('comment_body', '@notsudo')
    
    if not repo_full_name:
        return jsonify({'error': 'Missing required field: repo'}), 400
    
    if not issue_number:
        return jsonify({'error': 'Missing required field: issue_number'}), 400
    
    logger.info(
        "test_issue_received",
        repo=repo_full_name,
        issue_number=issue_number,
        issue_title=issue_title
    )
    
    job = {
        'id': f"{repo_full_name}-{issue_number}-{datetime.now().timestamp()}",
        'repo': repo_full_name,
        'issueNumber': issue_number,
        'issueTitle': issue_title,
        'status': 'processing',
        'stage': 'analyzing',
        'retryCount': 0,
        'createdAt': datetime.now().isoformat(),
        'prUrl': None,
        'error': None,
        'logs': ['Test job started (via /api/test-issue)'],
        'validationLogs': []
    }
    save_job(job)
    
    # Enqueue the job in Redis Queue
    is_pr = data.get('is_pr', False)
    
    enqueue_job(
        tasks.process_webhook_task,
        repo_full_name=repo_full_name,
        issue_number=issue_number,
        issue_title=issue_title,
        issue_body=issue_body,
        comment_body=comment_body,
        is_pr=is_pr,
        current_job_id=job['id'],
        github_token=github_token,
        config=config
    )
    
    return jsonify({
        'success': True,
        'message': 'Test job enqueued successfully',
        'job_id': job['id']
    }), 202


@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    user_id = request.args.get('user_id')
    jobs = load_jobs(user_id=user_id)
    return jsonify(jobs), 200


@app.route('/api/jobs', methods=['POST'])
def create_manual_job():
    """
    Create a manual PR generation job from a prompt.
    """
    config = load_config()
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
        
    repo_full_name = data.get('repo')
    prompt = data.get('prompt')
    user_id = data.get('user_id')
    
    if not repo_full_name or not prompt:
        return jsonify({'error': 'repo and prompt are required'}), 400
        
    github_token = config.get('github_token')
    if not github_token:
        return jsonify({'error': 'GitHub token not configured'}), 500
        
    # Generate a job ID
    job_id = f"manual-{repo_full_name.replace('/', '-')}-{int(datetime.now().timestamp())}"
    
    # Build job data
    job = {
        'id': job_id,
        'user_id': user_id,
        'repo': repo_full_name,
        'issueNumber': None,
        'issueTitle': f"Manual Task: {prompt[:50]}...",
        'status': 'processing',
        'stage': 'analyzing',
        'retryCount': 0,
        'createdAt': datetime.now().isoformat(),
        'prUrl': None,
        'error': None,
        'logs': ['Manual job started'],
        'validationLogs': []
    }
    
    # Save initial job state
    save_job(job)
    
    # Enqueue the job in Redis Queue
    enqueue_job(
        tasks.process_manual_task,
        repo_full_name=repo_full_name,
        prompt=prompt,
        user_id=user_id,
        current_job_id=job_id,
        github_token=github_token,
        config=config
    )
    
    return jsonify({
        'success': True,
        'message': 'Manual job enqueued successfully',
        'job_id': job_id
    }), 202


@app.route('/api/repos', methods=['GET'])
def get_repos():
    """Get all repositories accessible by the GitHub token."""
    config = load_config()
    github_token = config.get('github_token')
    
    if not github_token:
        return jsonify({'error': 'GitHub token not configured'}), 500
    
    # Try to get from cache
    cache_key = f"repos_{hashlib.md5(github_token.encode()).hexdigest()}"
    cached_repos = get_cache(cache_key)
    if cached_repos:
        return jsonify(json.loads(cached_repos)), 200

    try:
        github_service = GitHubService(github_token)
        repos = github_service.get_available_repos()
        response_data = {'repos': repos, 'count': len(repos)}
        
        # Cache for 10 minutes
        set_cache(cache_key, json.dumps(response_data), expire=600)
        
        return jsonify(response_data), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error("get_repos_failed", error=str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/api/repos/<path:repo_full_name>/issues', methods=['GET'])
def get_repo_issues(repo_full_name):
    """Get issues for a specific repository."""
    config = load_config()
    github_token = config.get('github_token')

    if not github_token:
        return jsonify({'error': 'GitHub token not configured'}), 500

    try:
        github_service = GitHubService(github_token)
        issues = github_service.get_issues(repo_full_name)
        return jsonify({'issues': issues, 'count': len(issues)}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error("get_repo_issues_failed", error=str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/api/jobs/<job_id>/logs', methods=['GET'])
def get_job_logs(job_id):
    """Get detailed logs for a specific job."""
    jobs = load_jobs()
    for job in jobs:
        if job.get('id') == job_id:
            return jsonify({
                'id': job_id,
                'logs': job.get('logs', []),
                'validationLogs': job.get('validationLogs', []),
                'retryCount': job.get('retryCount', 0),
                'stage': job.get('stage', 'unknown')
            }), 200
    return jsonify({'error': 'Job not found'}), 404


@app.route('/api/jobs/<job_id>/feed', methods=['GET'])
def get_job_feed(job_id):
    """Get structured logs (feed) for a specific job."""
    logs = database.get_job_logs(job_id)
    return jsonify({
        'jobId': job_id,
        'entries': logs
    }), 200


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify deployment status."""
    config = load_config()
    
    # Check required environment variables
    checks = {
        'github_token': bool(config.get('github_token')),
        'groq_key': bool(config.get('groq_key')),
    }
    
    # Verify GitHub scopes if token exists
    github_scopes = None
    if checks['github_token']:
        try:
            github_service = GitHubService(config.get('github_token'))
            scope_info = github_service.verify_token_scopes()
            github_scopes = scope_info
            if not scope_info.get('valid'):
                checks['github_api'] = False
            elif not scope_info.get('has_repo_scope'):
                # We don't mark it as unhealthy, but we report it
                pass
        except Exception as e:
            checks['github_api'] = False
            logger.error("health_check_github_failed", error=str(e))

    all_healthy = all(checks.values())
    
    response = {
        'status': 'healthy' if all_healthy else 'degraded',
        'timestamp': datetime.now().isoformat(),
        'checks': checks,
        'environment': os.environ.get('FLASK_ENV', 'production'),
        'version': '1.0.0'
    }

    if github_scopes:
        response['github_scopes'] = github_scopes

    return jsonify(response), 200 if all_healthy else 503


@app.route('/api/test-sandbox', methods=['POST'])
def test_sandbox():
    """
    Test endpoint that runs a simple task in AWS sandbox without AI.
    Useful for testing the full AWS ECS Fargate flow.
    
    Expected JSON payload (all optional):
    {
        "code": "print('Hello World')",  # Python code to run (defaults to simple test)
        "stack": "python"  # or "nodejs"
    }
    """
    # Check if AWS sandbox is enabled
    if not os.environ.get('USE_AWS_SANDBOX'):
        return jsonify({
            'error': 'AWS sandbox not enabled. Set USE_AWS_SANDBOX=true in .env'
        }), 400
    
    data = request.get_json() or {}
    stack = data.get('stack', 'python')
    
    # Default test code based on stack
    if stack == 'python':
        default_code = '''
# Simple test script
import os
print("=" * 50)
print("SANDBOX TEST STARTED")
print("=" * 50)

# Test 1: Print environment
print("\\n[TEST 1] Environment info:")
print(f"  Python version: {os.sys.version}")
print(f"  Working directory: {os.getcwd()}")

# Test 2: Read a file
print("\\n[TEST 2] Creating and reading a test file:")
with open("test_file.txt", "w") as f:
    f.write("Hello from AWS Sandbox!")
with open("test_file.txt", "r") as f:
    content = f.read()
print(f"  File content: {content}")

# Test 3: Simple assertion
print("\\n[TEST 3] Running assertions:")
assert 1 + 1 == 2, "Math is broken!"
print("  ✓ 1 + 1 = 2")
assert "hello".upper() == "HELLO", "String ops broken!"
print("  ✓ String operations work")

print("\\n" + "=" * 50)
print("ALL TESTS PASSED!")
print("=" * 50)
'''
    else:  # nodejs
        default_code = '''
console.log("=" .repeat(50));
console.log("SANDBOX TEST STARTED");
console.log("=".repeat(50));

// Test 1: Environment
console.log("\\n[TEST 1] Environment info:");
console.log("  Node version:", process.version);
console.log("  Working directory:", process.cwd());

// Test 2: File operations
const fs = require("fs");
console.log("\\n[TEST 2] Creating and reading a test file:");
fs.writeFileSync("test_file.txt", "Hello from AWS Sandbox!");
const content = fs.readFileSync("test_file.txt", "utf8");
console.log("  File content:", content);

// Test 3: Assertions
console.log("\\n[TEST 3] Running assertions:");
console.assert(1 + 1 === 2, "Math is broken!");
console.log("  ✓ 1 + 1 = 2");

console.log("\\n" + "=".repeat(50));
console.log("ALL TESTS PASSED!");
console.log("=".repeat(50));
'''
    
    code = data.get('code', default_code)
    
    # Prepare code files
    if stack == 'python':
        code_files = [
            {'path': 'main.py', 'content': code},
            {'path': 'requirements.txt', 'content': '# No dependencies needed for test'},
        ]
        install_cmd = 'pip install -r requirements.txt 2>/dev/null || true'
        test_cmd = 'python main.py'
    else:
        code_files = [
            {'path': 'index.js', 'content': code},
            {'path': 'package.json', 'content': '{"name": "sandbox-test", "version": "1.0.0"}'},
        ]
        install_cmd = 'npm install 2>/dev/null || true'
        test_cmd = 'node index.js'
    
    logger.info(
        "test_sandbox_started",
        stack=stack,
        file_count=len(code_files),
    )
    
    try:
        from services.aws_sandbox import AWSSandboxService
        
        sandbox = AWSSandboxService()
        
        # Check if sandbox is accessible
        if not sandbox.is_available():
            return jsonify({
                'error': 'AWS sandbox not accessible. Check your AWS credentials and configuration.',
                'config': {
                    'region': sandbox.config.region,
                    'cluster': sandbox.config.ecs_cluster,
                    'bucket': sandbox.config.s3_bucket,
                }
            }), 500
        
        # Run the validation
        result = sandbox.run_validation(
            code_files=code_files,
            stack_type=stack,
            install_command=install_cmd,
            test_command=test_cmd,
        )
        
        return jsonify({
            'success': result.success,
            'exit_code': result.exit_code,
            'duration_seconds': round(result.duration_seconds, 2),
            'estimated_cost_usd': result.estimated_cost_usd,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'task_arn': result.task_arn,
        }), 200 if result.success else 500
        
    except Exception as e:
        logger.error("test_sandbox_failed", error=str(e))
        return jsonify({
            'error': str(e),
            'type': type(e).__name__,
        }), 500

# =====================
# Authentication Routes
# =====================
# NOTE: Authentication is now handled by Better Auth on the frontend.
# These routes are kept for backward compatibility but will redirect.

@app.route('/api/auth/signup', methods=['POST'])
def auth_signup():
    """Auth now handled by Better Auth on frontend."""
    return jsonify({
        'error': 'Please use the frontend authentication. Visit /login to sign up with GitHub.'
    }), 410


@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    """Auth now handled by Better Auth on frontend."""
    return jsonify({
        'error': 'Please use the frontend authentication. Visit /login to sign in with GitHub.'
    }), 410


@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    """Auth now handled by Better Auth on frontend."""
    return jsonify({'message': 'Use frontend /api/auth/signout for logout'}), 410


@app.route('/api/auth/user', methods=['GET'])
def auth_user():
    """Auth now handled by Better Auth on frontend."""
    return jsonify({
        'error': 'Please use the frontend /api/auth/session to get user info.'
    }), 410


# =====================
# GitHub App Routes
# =====================

@app.route('/api/github-app/status', methods=['GET'])
def github_app_status():
    """Check if GitHub App is configured and get installation URL."""
    from services.github_app import get_github_app_service
    
    try:
        app_service = get_github_app_service()
        
        if not app_service.is_configured():
            return jsonify({
                'configured': False,
                'message': 'GitHub App is not configured. Set GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY in your environment.'
            }), 200
        
        # Try to get app info
        try:
            app_info = app_service.get_app_info()
            install_url = app_service.get_installation_url()
            return jsonify({
                'configured': True,
                'app_name': app_info.get('name'),
                'app_slug': app_info.get('slug'),
                'install_url': install_url,
                'html_url': app_info.get('html_url')
            }), 200
        except Exception as e:
            logger.error("github_app_info_failed", error=str(e))
            return jsonify({
                'configured': True,
                'error': str(e)
            }), 200
            
    except Exception as e:
        logger.error("github_app_status_failed", error=str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/api/github-app/installations', methods=['GET'])
def get_github_app_installations():
    """Get all installations of the GitHub App."""
    from services.github_app import get_github_app_service
    
    try:
        app_service = get_github_app_service()
        
        if not app_service.is_configured():
            return jsonify({'error': 'GitHub App not configured'}), 400
        
        installations = app_service.list_installations()
        
        return jsonify({
            'installations': [{
                'id': inst.get('id'),
                'account': inst.get('account', {}).get('login'),
                'account_type': inst.get('account', {}).get('type'),
                'repository_selection': inst.get('repository_selection'),
                'html_url': inst.get('html_url'),
                'suspended_at': inst.get('suspended_at')
            } for inst in installations],
            'count': len(installations)
        }), 200
        
    except Exception as e:
        logger.error("get_installations_failed", error=str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/api/github-app/installations/<int:installation_id>/repos', methods=['GET'])
def get_installation_repos(installation_id):
    """Get repositories for a specific installation."""
    from services.github_app import get_github_app_service
    
    try:
        app_service = get_github_app_service()
        
        if not app_service.is_configured():
            return jsonify({'error': 'GitHub App not configured'}), 400
        
        repos = app_service.get_installation_repos(installation_id)
        
        return jsonify({
            'repos': [{
                'id': str(repo.get('id')),
                'name': repo.get('name'),
                'full_name': repo.get('full_name'),
                'private': repo.get('private', False),
                'html_url': repo.get('html_url'),
                'description': repo.get('description'),
                'language': repo.get('language'),
                'default_branch': repo.get('default_branch', 'main')
            } for repo in repos],
            'count': len(repos)
        }), 200
        
    except Exception as e:
        logger.error("get_installation_repos_failed", error=str(e), installation_id=installation_id)
        return jsonify({'error': str(e)}), 500


@app.route('/api/github-app/webhook', methods=['POST'])
def handle_github_app_webhook():
    """
    Handle webhooks from GitHub App.
    This receives installation events and issue comment events.
    """
    from services.github_app import get_github_app_service
    
    raw_data = request.data
    signature = request.headers.get('X-Hub-Signature-256')
    event_type = request.headers.get('X-GitHub-Event')
    
    app_service = get_github_app_service()
    
    # Verify signature if webhook secret is configured
    if app_service.webhook_secret:
        if not app_service.verify_webhook_signature(raw_data, signature):
            logger.warning("github_app_webhook_invalid_signature")
            return jsonify({'error': 'Invalid signature'}), 403
    
    try:
        data = json.loads(raw_data) if raw_data else None
    except (json.JSONDecodeError, TypeError):
        return jsonify({'error': 'Invalid JSON'}), 400
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    action = data.get('action')
    
    logger.info(
        "github_app_webhook_received",
        event_type=event_type,
        action=action
    )
    
    # Handle installation events
    if event_type == 'installation':
        return handle_installation_event(data, action)
    
    # Handle installation_repositories events (when repos are added/removed)
    if event_type == 'installation_repositories':
        return handle_installation_repos_event(data, action)
    
    # Handle issue_comment events (same as before, but from app)
    if event_type == 'issue_comment':
        return handle_issue_comment_from_app(data, action)
    
    # Ignore other events
    return jsonify({'message': f'Event {event_type} ignored'}), 200


def handle_installation_event(data, action):
    """Handle GitHub App installation/uninstallation events."""
    installation = data.get('installation', {})
    
    installation_id = str(installation.get('id'))
    account = installation.get('account', {})
    
    logger.info(
        "installation_event",
        action=action,
        installation_id=installation_id,
        account=account.get('login')
    )
    
    if action in ['created', 'new_permissions_accepted']:
        # Store installation in database
        if database.is_db_available():
            from services.models import GitHubAppInstallation
            from services.db import get_db_session
            
            with get_db_session() as session:
                existing = session.query(GitHubAppInstallation).filter_by(id=installation_id).first()
                
                if existing:
                    existing.repository_selection = installation.get('repository_selection', 'all')
                    existing.suspended_at = None
                    existing.updated_at = datetime.now()
                else:
                    new_installation = GitHubAppInstallation(
                        id=installation_id,
                        account_login=account.get('login'),
                        account_type=account.get('type', 'User'),
                        account_id=account.get('id'),
                        target_type=installation.get('target_type'),
                        repository_selection=installation.get('repository_selection', 'all'),
                        access_tokens_url=installation.get('access_tokens_url'),
                        repositories_url=installation.get('repositories_url'),
                        html_url=installation.get('html_url'),
                        app_id=installation.get('app_id')
                    )
                    session.add(new_installation)
                
                session.commit()
        
        return jsonify({'message': 'Installation recorded'}), 200
    
    elif action == 'deleted':
        # Remove installation from database
        if database.is_db_available():
            from services.models import GitHubAppInstallation
            from services.db import get_db_session
            
            with get_db_session() as session:
                session.query(GitHubAppInstallation).filter_by(id=installation_id).delete()
                session.commit()
        
        return jsonify({'message': 'Installation removed'}), 200
    
    elif action == 'suspended':
        if database.is_db_available():
            from services.models import GitHubAppInstallation
            from services.db import get_db_session
            
            with get_db_session() as session:
                existing = session.query(GitHubAppInstallation).filter_by(id=installation_id).first()
                if existing:
                    existing.suspended_at = datetime.now()
                    session.commit()
        
        return jsonify({'message': 'Installation suspended'}), 200
    
    return jsonify({'message': f'Installation action {action} handled'}), 200


def handle_installation_repos_event(data, action):
    """Handle when repositories are added/removed from an installation."""
    installation = data.get('installation', {})
    installation_id = str(installation.get('id'))
    
    repos_added = data.get('repositories_added', [])
    repos_removed = data.get('repositories_removed', [])
    
    logger.info(
        "installation_repos_event",
        action=action,
        installation_id=installation_id,
        repos_added=len(repos_added),
        repos_removed=len(repos_removed)
    )
    
    # For now, just log it - repos are fetched dynamically when needed
    return jsonify({
        'message': 'Repository changes recorded',
        'added': len(repos_added),
        'removed': len(repos_removed)
    }), 200


def handle_issue_comment_from_app(data, action):
    """Handle issue comments from GitHub App webhook."""
    if action != 'created':
        return jsonify({'message': 'Ignored: not a comment creation'}), 200
    
    comment = data.get('comment', {})
    issue = data.get('issue', {})
    repository = data.get('repository', {})
    installation = data.get('installation', {})
    
    comment_body = comment.get('body', '')
    
    if '@notsudo' not in comment_body:
        return jsonify({'message': 'Ignored: @notsudo not mentioned'}), 200
    
    repo_full_name = repository.get('full_name')
    issue_number = issue.get('number')
    issue_title = issue.get('title')
    issue_body = issue.get('body', '')
    installation_id = installation.get('id')
    
    if not repo_full_name or not issue_number:
        return jsonify({'error': 'Missing repo or issue info'}), 400
    
    # Get installation access token first (before creating job)
    from services.github_app import get_github_app_service
    
    try:
        app_service = get_github_app_service()
        token_data = app_service.get_installation_access_token(installation_id)
        github_token = token_data['token']
    except Exception as e:
        logger.error("failed_to_get_installation_token", error=str(e))
        return jsonify({'error': 'Failed to get installation token'}), 500
    
    groq_key = load_config().get('groq_key')
    
    if not groq_key:
        return jsonify({'error': 'GROQ API key not configured'}), 500
    
    # Build job data
    job = {
        'id': f"{repo_full_name}-{issue_number}-{datetime.now().timestamp()}",
        'repo': repo_full_name,
        'issueNumber': issue_number,
        'issueTitle': issue_title,
        'status': 'processing',
        'stage': 'analyzing',
        'retryCount': 0,
        'createdAt': datetime.now().isoformat(),
        'prUrl': None,
        'error': None,
        'logs': ['Job started via GitHub App webhook'],
        'validationLogs': []
    }
    
    # Atomically check for duplicates and create job
    created_job = create_job_atomically(repo_full_name, issue_number, job)
    if created_job is None:
        return jsonify({'message': 'Job already in progress or rate limited'}), 429
    
    # Enqueue the job in Redis Queue
    enqueue_job(
        tasks.process_webhook_task,
        repo_full_name=repo_full_name,
        issue_number=issue_number,
        issue_title=issue_title,
        issue_body=issue_body,
        comment_body=comment_body,
        is_pr='pull_request' in issue or bool(issue.get('pull_request')),
        current_job_id=job['id'],
        github_token=github_token,
        config=load_config()
    )
    
    return jsonify({
        'success': True,
        'message': 'Job enqueued successfully',
        'job_id': job['id']
    }), 202


# =====================
# Stats Route
# =====================

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get job and issue statistics."""
    if not database.is_db_available():
        # Return stats from JSON file fallback
        jobs = load_jobs()
        return jsonify({
            'total_jobs': len(jobs),
            'completed_jobs': len([j for j in jobs if j.get('status') == 'completed']),
            'failed_jobs': len([j for j in jobs if j.get('status') == 'failed']),
            'processing_jobs': len([j for j in jobs if j.get('status') == 'processing']),
            'total_issues': 0,
            'total_repos': 0
        }), 200
    
    # Get stats from database
    stats = database.get_stats()
    
    if 'error' in stats:
        return jsonify(stats), 500
    
    return jsonify(stats), 200


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8000, debug=True)
