import os
import json
import hmac
import hashlib
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from services.groq_service import GroqService
from services.github_service import GitHubService
from services.pr_service import PRService
from services import db as database
from utils.logger import get_logger

logger = get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)
CORS(app)

jobs_file = "/tmp/jobs.json"

# Global executor for thread management
# Limit max_workers to avoid resource exhaustion
executor = ThreadPoolExecutor(max_workers=10)

def load_config():
    return {
        'github_token': os.environ.get('GITHUB_TOKEN'),
        'groq_key': os.environ.get('GROQ_API_KEY'),
        'webhook_secret': os.environ.get('WEBHOOK_SECRET', '')
    }

def load_jobs():
    """Load jobs from database or fall back to JSON file."""
    if database.is_db_available():
        return database.get_jobs()
    
    # Fallback to JSON file
    if os.path.exists(jobs_file):
        with open(jobs_file, 'r') as f:
            return json.load(f)
    return []

def save_job(job):
    """Save job to database or fall back to JSON file."""
    if database.is_db_available():
        existing = database.get_job_by_id(job.get('id'))
        if existing:
            database.update_job(job.get('id'), job)
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
        'hasWebhookSecret': bool(config.get('webhook_secret'))
    }), 200

@app.route('/api/webhook-url', methods=['GET'])
def get_webhook_url():
    return jsonify({'webhookUrl': get_current_webhook_url()}), 200

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
    
    if '@notsudo' not in comment_body:
        logger.debug("webhook_ignored", reason="notsudo not mentioned")
        return jsonify({'message': 'Ignored: @notsudo not mentioned'}), 200
    
    github_token = config.get('github_token')
    groq_key = config.get('groq_key')
    
    if not github_token or not groq_key:
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
    
    # Check for duplicates and rate limiting
    if is_job_in_progress(repo_full_name, issue_number):
        logger.warning("job_duplicate_prevented", repo=repo_full_name, issue=issue_number)
        return jsonify({'message': 'Job already in progress for this issue'}), 429

    if is_rate_limited(repo_full_name, issue_number):
        logger.warning("job_rate_limited", repo=repo_full_name, issue=issue_number)
        return jsonify({'message': 'Rate limit exceeded for this issue. Please wait.'}), 429

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
        ai_service = GroqService(api_key=groq_key)
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
        job['completedAt'] = datetime.now().isoformat()
        job['prUrl'] = result.get('pr_url')
        job['error'] = result.get('message') if not result.get('success') else None
        job['validationLogs'] = result.get('validation_logs', [])
        job['stage'] = 'completed' if result.get('success') else 'failed'
        job['logs'].append(f"Result: {'PR created' if result.get('success') else result.get('message', 'Failed')}")
        save_job(job)
        
        return jsonify(result), 200
        
    except ValueError as e:
        job['status'] = 'failed'
        job['completedAt'] = datetime.now().isoformat()
        job['stage'] = 'error'
        job['error'] = str(e)
        job['logs'].append(f'Error: {str(e)}')
        save_job(job)
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        job['status'] = 'failed'
        job['completedAt'] = datetime.now().isoformat()
        job['stage'] = 'error'
        job['error'] = str(e)
        job['logs'].append(f'Error: {str(e)}')
        save_job(job)
        return jsonify({'error': str(e)}), 500

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
    groq_key = config.get('groq_key')
    
    if not github_token or not groq_key:
        return jsonify({'error': 'Missing API credentials'}), 500
    
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
    
    try:
        github_service = GitHubService(github_token)
        ai_service = GroqService(api_key=groq_key)
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
        job['completedAt'] = datetime.now().isoformat()
        job['prUrl'] = result.get('pr_url')
        job['error'] = result.get('message') if not result.get('success') else None
        job['validationLogs'] = result.get('validation_logs', [])
        job['stage'] = 'completed' if result.get('success') else 'failed'
        job['logs'].append(f"Result: {'PR created' if result.get('success') else result.get('message', 'Failed')}")
        save_job(job)
        
        return jsonify(result), 200
        
    except ValueError as e:
        job['status'] = 'failed'
        job['completedAt'] = datetime.now().isoformat()
        job['stage'] = 'error'
        job['error'] = str(e)
        job['logs'].append(f'Error: {str(e)}')
        save_job(job)
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        job['status'] = 'failed'
        job['completedAt'] = datetime.now().isoformat()
        job['stage'] = 'error'
        job['error'] = str(e)
        job['logs'].append(f'Error: {str(e)}')
        save_job(job)
        return jsonify({'error': str(e)}), 500


@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    jobs = load_jobs()
    return jsonify(jobs), 200


@app.route('/api/repos', methods=['GET'])
def get_repos():
    """Get all repositories accessible by the GitHub token."""
    config = load_config()
    github_token = config.get('github_token')
    
    if not github_token:
        return jsonify({'error': 'GitHub token not configured'}), 500
    
    try:
        github_service = GitHubService(github_token)
        repos = github_service.get_available_repos()
        return jsonify({'repos': repos, 'count': len(repos)}), 200
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
    app.run(host='0.0.0.0', port=8000, debug=True)
