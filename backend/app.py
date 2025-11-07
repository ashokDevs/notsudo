from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import hmac
import hashlib
from datetime import datetime
from services.github_service import GitHubService
from services.ai_service import AIService
from services.pr_service import PRService

app = Flask(__name__)
CORS(app)

config_file = "/tmp/config.json"
jobs_file = "/tmp/jobs.json"

def load_config():
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    return {}

def save_config(config):
    with open(config_file, 'w') as f:
        json.dump(config, f)

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
    data = request.json
    github_token = data.get('githubToken')
    openai_key = data.get('openaiKey')
    webhook_secret = data.get('webhookSecret', '')
    
    config = {
        'github_token': github_token,
        'openai_key': openai_key,
        'webhook_secret': webhook_secret
    }
    save_config(config)
    
    return jsonify({'message': 'Configuration saved successfully'}), 200

@app.route('/api/config', methods=['GET'])
def get_configuration():
    config = load_config()
    return jsonify({
        'hasGithubToken': bool(config.get('github_token')),
        'hasOpenaiKey': bool(config.get('openai_key')),
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
        return jsonify({'error': 'No data provided'}), 400
    
    action = data.get('action')
    comment = data.get('comment', {})
    issue = data.get('issue', {})
    repository = data.get('repository', {})
    
    if action != 'created':
        return jsonify({'message': 'Ignored: not a comment creation'}), 200
    
    comment_body = comment.get('body', '')
    
    if '@my-tool' not in comment_body:
        return jsonify({'message': 'Ignored: @my-tool not mentioned'}), 200
    
    github_token = config.get('github_token')
    openai_key = config.get('openai_key')
    
    if not github_token or not openai_key:
        return jsonify({'error': 'Missing API credentials'}), 500
    
    repo_full_name = repository.get('full_name')
    issue_number = issue.get('number')
    issue_title = issue.get('title')
    issue_body = issue.get('body', '')
    
    job = {
        'id': f"{repo_full_name}-{issue_number}-{datetime.now().timestamp()}",
        'repo': repo_full_name,
        'issueNumber': issue_number,
        'issueTitle': issue_title,
        'status': 'processing',
        'createdAt': datetime.now().isoformat(),
        'prUrl': None,
        'error': None
    }
    save_job(job)
    
    try:
        github_service = GitHubService(github_token)
        ai_service = AIService(openai_key)
        pr_service = PRService(github_service, ai_service)
        
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
        save_job(job)
        
        return jsonify(result), 200
        
    except Exception as e:
        job['status'] = 'failed'
        job['error'] = str(e)
        save_job(job)
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    jobs = load_jobs()
    return jsonify(jobs), 200

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
