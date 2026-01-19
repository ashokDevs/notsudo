import os
from datetime import datetime
from services.github_service import GitHubService
from services.ai_service import AIService, AVAILABLE_MODELS, DEFAULT_MODEL
from services.groq_service import GroqService
from services.pr_service import PRService
from services import db as database
from services.redis_service import set_job_cache
from utils.logger import get_logger

logger = get_logger(__name__)

def get_ai_service(config, user_model=None):
    if config.get('use_openrouter'):
        return AIService(api_key=config.get('openrouter_key'), model=user_model)
    else:
        return GroqService(api_key=config.get('groq_key'))

def save_job(job):
    """Save job to Redis cache (write-through) and then to database."""
    job_id = job.get('id')
    if job_id:
        # Step 1: Write to Redis cache first
        set_job_cache(job_id, job)
        
    # Step 2: Write to database
    if database.is_db_available():
        existing = database.get_job_by_id(job_id)
        if existing:
            database.update_job(job_id, job)
        else:
            database.insert_job(job)
        return
    # Fallback logs if DB is not available
    logger.info("job_saved_without_db", job_id=job.get('id'), status=job.get('status'))

def process_webhook_task(repo_full_name, issue_number, issue_title, issue_body, comment_body, is_pr, current_job_id, github_token, config):
    job = {
        'id': current_job_id,
        'repo': repo_full_name,
        'issueNumber': issue_number,
        'issueTitle': issue_title,
        'status': 'processing',
        'stage': 'generating',
        'retryCount': 0,
        'createdAt': datetime.now().isoformat(),
        'prUrl': None,
        'error': None,
        'logs': ['Job started via RQ'],
        'validationLogs': []
    }
    
    try:
        github_service = GitHubService(github_token)
        ai_service = get_ai_service(config)
        pr_service = PRService(github_service, ai_service)
        
        if is_pr:
            job['logs'].append('AI analyzing PR feedback...')
            save_job(job)
            result = pr_service.process_pr_comment(
                repo_full_name=repo_full_name,
                pr_number=issue_number,
                comment_body=comment_body,
                job_id=current_job_id
            )
        else:
            job['logs'].append('AI analyzing issue...')
            save_job(job)
            result = pr_service.process_issue(
                repo_full_name=repo_full_name,
                issue_number=issue_number,
                issue_title=issue_title,
                issue_body=issue_body,
                comment_body=comment_body,
                job_id=current_job_id
            )
        
        job['status'] = 'completed' if result.get('success') else 'failed'
        job['completedAt'] = datetime.now().isoformat()
        job['prUrl'] = result.get('pr_url')
        job['error'] = result.get('message') if not result.get('success') else None
        job['validationLogs'] = result.get('validation_logs', [])
        job['stage'] = 'completed' if result.get('success') else 'failed'
        job['logs'].append(f"Result: {'PR created' if result.get('success') else result.get('message', 'Failed')}")
        save_job(job)
        return result
        
    except Exception as e:
        logger.error("webhook_task_failed", error=str(e), job_id=current_job_id)
        job['status'] = 'failed'
        job['completedAt'] = datetime.now().isoformat()
        job['stage'] = 'error'
        job['error'] = str(e)
        job['logs'].append(f'Error: {str(e)}')
        save_job(job)
        return {'success': False, 'message': str(e)}

def process_manual_task(repo_full_name, prompt, user_id, current_job_id, github_token, config):
    job = {
        'id': current_job_id,
        'user_id': user_id,
        'repo': repo_full_name,
        'issueNumber': None,
        'issueTitle': f"Manual Task: {prompt[:50]}...",
        'status': 'processing',
        'stage': 'generating',
        'retryCount': 0,
        'createdAt': datetime.now().isoformat(),
        'prUrl': None,
        'error': None,
        'logs': ['Manual job started via RQ'],
        'validationLogs': []
    }
    save_job(job)
    
    try:
        github_service = GitHubService(github_token)
        ai_service = get_ai_service(config)
        pr_service = PRService(github_service, ai_service)
        
        result = pr_service.process_manual_task(
            repo_full_name=repo_full_name,
            prompt=prompt,
            user_id=user_id,
            job_id=current_job_id
        )
        
        job['status'] = 'completed' if result.get('success') else 'failed'
        job['completedAt'] = datetime.now().isoformat()
        job['prUrl'] = result.get('pr_url')
        job['error'] = result.get('message') if not result.get('success') else None
        job['validationLogs'] = result.get('validation_logs', [])
        job['stage'] = 'completed' if result.get('success') else 'failed'
        job['logs'].append(f"Result: {'PR created' if result.get('success') else result.get('message', 'Failed')}")
        save_job(job)
        return result
        
    except Exception as e:
        logger.error("manual_task_failed", error=str(e), job_id=current_job_id)
        job['status'] = 'failed'
        job['stage'] = 'error'
        job['error'] = str(e)
        job['logs'].append(f"Error: {str(e)}")
        save_job(job)
        return {'success': False, 'message': str(e)}

def dummy_task(x, y):
    """Simple task for testing purposes."""
    return x + y
