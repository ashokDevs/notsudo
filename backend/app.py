import os
import json
import hmac
import hashlib
from datetime import datetime
from pathlib import Path

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from services.ai_service import AIService
from services.github_service import GitHubService
from services.pr_service import PRService
from utils.logger import get_logger

logger = get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)
CORS(app)

jobs_file = "/tmp/jobs.json"


def load_config():
    return {
        'github_token': os.environ.get('GITHUB_TOKEN'),
        'openrouter_key': os.environ.get('OPENROUTER_API_KEY'),
        'webhook_secret': os.environ.get('WEBHOOK_SECRET', '')
    }

def load_jobs():
    if os.path.exists(jobs_file):
        with open(jobs_file, 'r') as f:
            return json.load(f)
    return []

def save_job(job):
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

def verify_github_signature(payload_body, signature_header, secret):
    if not signature_header or not secret:
        return False
    
    hash_algorithm, github_signature = signature_header.split('=')
    
    mac = hmac.new(secret.encode(), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = mac.hexdigest()
    
    return hmac.compare_digest(expected_signature, github_signature)

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
        'hasOpenrouterKey': bool(config.get('openrouter_key')),
        'hasWebhookSecret': bool(config.get('webhook_secret'))
    }), 200

@app.route('/api/webhook-url', methods=['GET'])
def get_webhook_url():
    base_url = os.environ.get('REPL_SLUG')
    if base_url:
        domain = f"{base_url}.{os.environ.get('REPL_OWNER', 'replit')}.repl.co"
        webhook_url = f"https://{domain}/api/webhook"
    else:
        webhook_url = "http://localhost:8000/api/webhook"
    
    return jsonify({'webhookUrl': webhook_url}), 200

@app.route('/api/webhook', methods=['POST'])
def handle_webhook():
    config = load_config()
    webhook_secret = config.get('webhook_secret')
    
    if webhook_secret:
        signature = request.headers.get('X-Hub-Signature-256')
        if not verify_github_signature(request.data, signature, webhook_secret):
            return jsonify({'error': 'Invalid signature'}), 403
    
    data = request.json
    
    if not data:
        logger.warning("webhook_no_data")
        return jsonify({'error': 'No data provided'}), 400
    
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
    
    if '@my-tool' not in comment_body:
        logger.debug("webhook_ignored", reason="my-tool not mentioned")
        return jsonify({'message': 'Ignored: @my-tool not mentioned'}), 200
    
    github_token = config.get('github_token')
    openrouter_key = config.get('openrouter_key')
    
    if not github_token or not openrouter_key:
        return jsonify({'error': 'Missing API credentials'}), 500
    
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
        'logs': ['Job started'],
        'validationLogs': []
    }
    save_job(job)
    
    try:
        github_service = GitHubService(github_token)
        ai_service = AIService(openrouter_key)
        pr_service = PRService(github_service, ai_service)
        
        job['stage'] = 'generating'
        job['logs'].append('AI analyzing issue...')
        save_job(job)
        
        result = pr_service.process_issue(
            repo_full_name=repo_full_name,
            issue_number=issue_number,
            issue_title=issue_title,
            issue_body=issue_body,
            comment_body=comment_body
        )
        
        job['status'] = 'completed' if result.get('success') else 'failed'
        job['prUrl'] = result.get('pr_url')
        job['error'] = result.get('message') if not result.get('success') else None
        job['validationLogs'] = result.get('validation_logs', [])
        job['stage'] = 'completed' if result.get('success') else 'failed'
        job['logs'].append(f"Result: {'PR created' if result.get('success') else result.get('message', 'Failed')}")
        save_job(job)
        
        return jsonify(result), 200
        
    except ValueError as e:
        job['status'] = 'failed'
        job['stage'] = 'error'
        job['error'] = str(e)
        job['logs'].append(f'Error: {str(e)}')
        save_job(job)
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        job['status'] = 'failed'
        job['stage'] = 'error'
        job['error'] = str(e)
        job['logs'].append(f'Error: {str(e)}')
        save_job(job)
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    jobs = load_jobs()
    return jsonify(jobs), 200


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


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify deployment status."""
    config = load_config()
    
    # Check required environment variables
    checks = {
        'github_token': bool(config.get('github_token')),
        'openrouter_key': bool(config.get('openrouter_key')),
    }
    
    all_healthy = all(checks.values())
    
    return jsonify({
        'status': 'healthy' if all_healthy else 'degraded',
        'timestamp': datetime.now().isoformat(),
        'checks': checks,
        'environment': os.environ.get('FLASK_ENV', 'production'),
        'version': '1.0.0'
    }), 200 if all_healthy else 503

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)

