"""
Database Module - SQLAlchemy ORM queries for CloudAgent.

Single file for all database operations.
Uses SQLAlchemy models defined in models.py.
"""

import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import sessionmaker, Session

from services.models import Base, User, Repository, Job, Issue, JobLog, Subscription, CodebaseMemory
from utils.logger import get_logger

logger = get_logger(__name__)

# Database engine and session factory
_engine = None
_SessionFactory = None


def get_engine():
    """Get or create database engine."""
    global _engine
    if _engine is None:
        database_url = os.environ.get('DATABASE_URL', '')
        if not database_url:
            logger.warning("DATABASE_URL not set")
            return None
        _engine = create_engine(database_url, pool_pre_ping=True)
    return _engine


def get_session_factory():
    """Get or create session factory."""
    global _SessionFactory
    if _SessionFactory is None:
        engine = get_engine()
        if engine:
            _SessionFactory = sessionmaker(bind=engine)
    return _SessionFactory


@contextmanager
def get_db_session():
    """Context manager for database sessions."""
    factory = get_session_factory()
    if factory is None:
        yield None
        return
    
    session = factory()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error("db_session_error", error=str(e))
        raise
    finally:
        session.close()


def init_db():
    """Initialize database tables."""
    engine = get_engine()
    if engine:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized")
    else:
        logger.error("Failed to initialize database: No engine")


def is_db_available() -> bool:
    """Check if database is available."""
    try:
        with get_db_session() as session:
            if session is None:
                return False
            session.execute(text("SELECT 1"))
            return True
    except Exception:
        return False


# ======================
# Jobs CRUD
# ======================

def get_jobs(user_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Get jobs from database."""
    try:
        with get_db_session() as session:
            if session is None:
                return []
            
            query = session.query(Job).order_by(Job.created_at.desc())
            
            if user_id:
                query = query.filter(Job.user_id == user_id)
            
            jobs = query.limit(limit).all()
            return [job_to_dict(job) for job in jobs]
    except Exception as e:
        logger.error("get_jobs_failed", error=str(e))
        return []


def insert_job(job_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Insert a new job."""
    try:
        with get_db_session() as session:
            if session is None:
                return None
            
            job = Job(
                id=job_data.get('id'),
                user_id=job_data.get('userId') or job_data.get('user_id'),
                repository_id=job_data.get('repositoryId') or job_data.get('repository_id'),
                issue_number=job_data.get('issueNumber') or job_data.get('issue_number'),
                issue_title=job_data.get('issueTitle') or job_data.get('issue_title'),
                status=job_data.get('status', 'processing'),
                stage=job_data.get('stage', 'analyzing'),
                retry_count=job_data.get('retryCount') or job_data.get('retry_count', 0),
                pr_url=job_data.get('prUrl') or job_data.get('pr_url'),
                error=job_data.get('error'),
                logs=job_data.get('logs', []),
                validation_logs=job_data.get('validationLogs') or job_data.get('validation_logs', []),
            )
            session.add(job)
            session.flush()
            
            result = job_to_dict(job)
            
            # Emit socket event to user room
            from services.socket_service import socketio
            user_id = result.get('userId') or result.get('user_id')
            if user_id:
                socketio.emit('job_created', result, room=f"user_{user_id}")
            
            logger.info("job_inserted", job_id=job.id)
            return result
    except Exception as e:
        logger.error("insert_job_failed", error=str(e))
        return None


def update_job(job_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update an existing job."""
    try:
        with get_db_session() as session:
            if session is None:
                return None
            
            job = session.query(Job).filter(Job.id == job_id).first()
            if not job:
                return None
            
            # Map camelCase to snake_case
            field_map = {
                'status': 'status',
                'stage': 'stage',
                'retryCount': 'retry_count',
                'prUrl': 'pr_url',
                'error': 'error',
                'logs': 'logs',
                'validationLogs': 'validation_logs',
            }
            
            for key, value in updates.items():
                attr = field_map.get(key, key)
                if hasattr(job, attr):
                    setattr(job, attr, value)
            
            job.updated_at = datetime.utcnow()
            session.flush()
            
            result = job_to_dict(job)
            
            # Emit socket event for status/stage updates
            from services.socket_service import emit_job_status, socketio
            emit_job_status(job_id, result.get('status'), result.get('stage'))
            
            # Also notify user room about job update
            user_id = result.get('userId') or result.get('user_id')
            if user_id:
                socketio.emit('job_updated', result, room=f"user_{user_id}")
            
            logger.info("job_updated", job_id=job_id)
            return result
    except Exception as e:
        logger.error("update_job_failed", error=str(e), job_id=job_id)
        return None


def get_job_by_id(job_id: str) -> Optional[Dict[str, Any]]:
    """Get a single job by ID."""
    try:
        with get_db_session() as session:
            if session is None:
                return None
            job = session.query(Job).filter(Job.id == job_id).first()
            return job_to_dict(job) if job else None
    except Exception as e:
        logger.error("get_job_by_id_failed", error=str(e))
        return None


def atomic_create_job_if_not_exists(
    repo_full_name: str,
    issue_number: int,
    job_data: Dict[str, Any],
    window_seconds: int = 60
) -> Optional[Dict[str, Any]]:
    """
    Atomically create a job if no in-progress job exists for this issue.
    
    Uses a single database transaction to check and insert, preventing race conditions
    when multiple webhook handlers receive the same event simultaneously.
    
    Args:
        repo_full_name: Full name of the repository (owner/repo)
        issue_number: Issue number being processed
        job_data: Job data to insert if no duplicate exists
        window_seconds: Time window to check for recent jobs
        
    Returns:
        The created job dict if successful, None if a duplicate was found
    """
    try:
        with get_db_session() as session:
            if session is None:
                logger.warning("atomic_create_job: database not available")
                return None
            
            from datetime import timedelta
            from sqlalchemy import and_, or_
            
            now = datetime.utcnow()
            window_start = now - timedelta(seconds=window_seconds)
            # Stale job timeout - jobs processing for more than 10 minutes are considered stale
            stale_timeout = now - timedelta(minutes=10)
            
            # Check for any in-progress or recently created jobs for this issue
            # The job ID format is: "{repo_full_name}-{issue_number}-{timestamp}"
            job_id_prefix = f"{repo_full_name}-{issue_number}-"
            
            # Only block if:
            # 1. Job is in progress AND was created within the last 10 minutes (not stale)
            # 2. OR job was created within the rate limit window (regardless of status)
            existing = session.query(Job).filter(
                and_(
                    Job.id.like(f"{job_id_prefix}%"),
                    or_(
                        # In-progress jobs that aren't stale
                        and_(
                            Job.status.in_(['processing', 'generating', 'analyzing']),
                            Job.created_at >= stale_timeout
                        ),
                        # Rate limiting: any job created in the last minute
                        Job.created_at >= window_start
                    )
                )
            ).first()
            
            if existing:
                logger.warning(
                    "atomic_create_job_duplicate_prevented",
                    existing_job_id=existing.id,
                    existing_status=existing.status,
                    repo=repo_full_name,
                    issue=issue_number
                )
                return None
            
            # No duplicate found, create the job
            job = Job(
                id=job_data.get('id'),
                user_id=job_data.get('userId') or job_data.get('user_id'),
                repository_id=job_data.get('repositoryId') or job_data.get('repository_id'),
                issue_number=job_data.get('issueNumber') or job_data.get('issue_number'),
                issue_title=job_data.get('issueTitle') or job_data.get('issue_title'),
                status=job_data.get('status', 'processing'),
                stage=job_data.get('stage', 'analyzing'),
                retry_count=job_data.get('retryCount') or job_data.get('retry_count', 0),
                pr_url=job_data.get('prUrl') or job_data.get('pr_url'),
                error=job_data.get('error'),
                logs=job_data.get('logs', []),
                validation_logs=job_data.get('validationLogs') or job_data.get('validation_logs', []),
            )
            session.add(job)
            session.flush()
            
            logger.info("atomic_job_created", job_id=job.id)
            return job_to_dict(job)
            
    except Exception as e:
        logger.error("atomic_create_job_failed", error=str(e))
        return None


def job_to_dict(job: Job) -> Dict[str, Any]:
    """Convert Job model to dictionary."""
    return {
        'id': job.id,
        'userId': str(job.user_id) if job.user_id else None,
        'repositoryId': job.repository_id,
        'issueNumber': job.issue_number,
        'issueTitle': job.issue_title,
        'status': job.status,
        'stage': job.stage,
        'retryCount': job.retry_count,
        'prUrl': job.pr_url,
        'error': job.error,
        'logs': job.logs or [],
        'validationLogs': job.validation_logs or [],
        'createdAt': job.created_at.isoformat() if job.created_at else None,
        'updatedAt': job.updated_at.isoformat() if job.updated_at else None,
    }


# ======================
# Job Logs CRUD
# ======================

def insert_job_log(log_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Insert a new job log entry."""
    try:
        with get_db_session() as session:
            if session is None:
                return None
            
            import uuid
            log_id = str(uuid.uuid4())
            
            log = JobLog(
                id=log_id,
                job_id=log_data.get('jobId') or log_data.get('job_id'),
                role=log_data.get('role'),
                type=log_data.get('type'),
                content=log_data.get('content'),
                metadata_=log_data.get('metadata', {}),
                created_at=datetime.utcnow()
            )
            session.add(log)
            session.flush()
            
            result = job_log_to_dict(log)
            
            # Emit socket event for real-time updates
            from services.socket_service import emit_job_update
            emit_job_update(log.job_id, result)
            
            return result
    except Exception as e:
        logger.error("insert_job_log_failed", error=str(e))
        return None


def get_job_logs(job_id: str) -> List[Dict[str, Any]]:
    """Get logs for a specific job."""
    try:
        with get_db_session() as session:
            if session is None:
                return []
            
            logs = session.query(JobLog).filter(
                JobLog.job_id == job_id
            ).order_by(JobLog.created_at.asc()).all()
            
            return [job_log_to_dict(log) for log in logs]
    except Exception as e:
        logger.error("get_job_logs_failed", error=str(e))
        return []


def job_log_to_dict(log: JobLog) -> Dict[str, Any]:
    """Convert JobLog model to dictionary."""
    return {
        'id': log.id,
        'jobId': log.job_id,
        'role': log.role,
        'type': log.type,
        'content': log.content,
        'metadata': log.metadata_,
        'createdAt': log.created_at.isoformat() if log.created_at else None,
    }


# ======================
# Repositories CRUD
# ======================

def get_repositories(user_id: str) -> List[Dict[str, Any]]:
    """Get repositories for a user."""
    try:
        with get_db_session() as session:
            if session is None:
                return []
            repos = session.query(Repository).filter(
                Repository.user_id == user_id
            ).order_by(Repository.created_at.desc()).all()
            return [repo_to_dict(repo) for repo in repos]
    except Exception as e:
        logger.error("get_repositories_failed", error=str(e))
        return []


def insert_repository(repo_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Insert or update a repository."""
    try:
        with get_db_session() as session:
            if session is None:
                return None
            
            repo_id = str(repo_data.get('id'))
            existing = session.query(Repository).filter(Repository.id == repo_id).first()
            
            if existing:
                # Update existing
                existing.name = repo_data.get('name', existing.name)
                existing.description = repo_data.get('description', existing.description)
                existing.is_private = repo_data.get('isPrivate') or repo_data.get('is_private', existing.is_private)
                existing.default_branch = repo_data.get('defaultBranch') or repo_data.get('default_branch', existing.default_branch)
                existing.language = repo_data.get('language', existing.language)
                existing.updated_at = datetime.utcnow()
                repo = existing
            else:
                # Insert new
                repo = Repository(
                    id=repo_id,
                    user_id=repo_data.get('userId') or repo_data.get('user_id'),
                    name=repo_data.get('name'),
                    full_name=repo_data.get('fullName') or repo_data.get('full_name'),
                    description=repo_data.get('description'),
                    is_private=repo_data.get('isPrivate') or repo_data.get('is_private', False),
                    html_url=repo_data.get('htmlUrl') or repo_data.get('html_url'),
                    default_branch=repo_data.get('defaultBranch') or repo_data.get('default_branch', 'main'),
                    language=repo_data.get('language'),
                )
                session.add(repo)
            
            session.flush()
            logger.info("repository_saved", repo_id=repo_id)
            return repo_to_dict(repo)
    except Exception as e:
        logger.error("insert_repository_failed", error=str(e))
        return None


def repo_to_dict(repo: Repository) -> Dict[str, Any]:
    """Convert Repository model to dictionary."""
    return {
        'id': repo.id,
        'userId': str(repo.user_id) if repo.user_id else None,
        'name': repo.name,
        'fullName': repo.full_name,
        'description': repo.description,
        'isPrivate': repo.is_private,
        'htmlUrl': repo.html_url,
        'defaultBranch': repo.default_branch,
        'language': repo.language,
        'createdAt': repo.created_at.isoformat() if repo.created_at else None,
    }


# ======================
# Issues CRUD
# ======================

def get_issues(user_id: Optional[str] = None, repository_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Get issues from database."""
    try:
        with get_db_session() as session:
            if session is None:
                return []
            
            query = session.query(Issue).order_by(Issue.created_at.desc())
            
            if user_id:
                query = query.filter(Issue.user_id == user_id)
            if repository_id:
                query = query.filter(Issue.repository_id == repository_id)
            
            issues = query.limit(limit).all()
            return [issue_to_dict(issue) for issue in issues]
    except Exception as e:
        logger.error("get_issues_failed", error=str(e))
        return []


def insert_issue(issue_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Insert a new issue."""
    try:
        with get_db_session() as session:
            if session is None:
                return None
            
            issue = Issue(
                github_id=issue_data.get('githubId') or issue_data.get('github_id'),
                user_id=issue_data.get('userId') or issue_data.get('user_id'),
                repository_id=issue_data.get('repositoryId') or issue_data.get('repository_id'),
                number=issue_data.get('number'),
                title=issue_data.get('title'),
                body=issue_data.get('body'),
                state=issue_data.get('state', 'open'),
                html_url=issue_data.get('htmlUrl') or issue_data.get('html_url'),
            )
            session.add(issue)
            session.flush()
            logger.info("issue_inserted", github_id=issue.github_id)
            return issue_to_dict(issue)
    except Exception as e:
        logger.error("insert_issue_failed", error=str(e))
        return None


def get_issues_count(user_id: Optional[str] = None, repository_id: Optional[str] = None) -> int:
    """Get count of issues."""
    try:
        with get_db_session() as session:
            if session is None:
                return 0
            
            query = session.query(func.count(Issue.id))
            
            if user_id:
                query = query.filter(Issue.user_id == user_id)
            if repository_id:
                query = query.filter(Issue.repository_id == repository_id)
            
            return query.scalar() or 0
    except Exception as e:
        logger.error("get_issues_count_failed", error=str(e))
        return 0


def issue_to_dict(issue: Issue) -> Dict[str, Any]:
    """Convert Issue model to dictionary."""
    return {
        'id': issue.id,
        'githubId': issue.github_id,
        'userId': str(issue.user_id) if issue.user_id else None,
        'repositoryId': issue.repository_id,
        'number': issue.number,
        'title': issue.title,
        'body': issue.body,
        'state': issue.state,
        'htmlUrl': issue.html_url,
        'processedAt': issue.processed_at.isoformat() if issue.processed_at else None,
        'createdAt': issue.created_at.isoformat() if issue.created_at else None,
    }


# ======================
# Stats
# ======================

def get_stats(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Get aggregated statistics."""
    try:
        with get_db_session() as session:
            if session is None:
                return {'error': 'Database not available'}
            
            # Jobs stats
            jobs_query = session.query(Job)
            if user_id:
                jobs_query = jobs_query.filter(Job.user_id == user_id)
            
            total_jobs = jobs_query.count()
            completed_jobs = jobs_query.filter(Job.status == 'completed').count()
            failed_jobs = jobs_query.filter(Job.status == 'failed').count()
            processing_jobs = jobs_query.filter(Job.status == 'processing').count()
            
            # Issues and repos count
            issues_count = get_issues_count(user_id=user_id)
            
            repos_query = session.query(func.count(Repository.id))
            if user_id:
                repos_query = repos_query.filter(Repository.user_id == user_id)
            repos_count = repos_query.scalar() or 0
            
            return {
                'total_jobs': total_jobs,
                'completed_jobs': completed_jobs,
                'failed_jobs': failed_jobs,
                'processing_jobs': processing_jobs,
                'total_issues': issues_count,
                'total_repos': repos_count,
            }
    except Exception as e:
        logger.error("get_stats_failed", error=str(e))
        return {'error': str(e)}


# ======================
# User AI Settings
# ======================

def get_user_ai_settings(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user's AI settings (selected model and custom rules)."""
    try:
        with get_db_session() as session:
            if session is None:
                return None
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            return {
                'selectedModel': user.selectedModel,
                'customRules': user.customRules,
            }
    except Exception as e:
        logger.error("get_user_ai_settings_failed", error=str(e), user_id=user_id)
        return None


def update_user_ai_settings(user_id: str, selected_model: Optional[str] = None, custom_rules: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Update user's AI settings."""
    try:
        with get_db_session() as session:
            if session is None:
                return None
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            
            if selected_model is not None:
                user.selectedModel = selected_model
            if custom_rules is not None:
                user.customRules = custom_rules
            
            session.flush()
            logger.info("user_ai_settings_updated", user_id=user_id)
            return {
                'selectedModel': user.selectedModel,
                'customRules': user.customRules,
            }
    except Exception as e:
        logger.error("update_user_ai_settings_failed", error=str(e), user_id=user_id)
        return None
        
# ======================
# Subscriptions CRUD
# ======================

def insert_subscription(sub_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Insert or update a subscription."""
    try:
        with get_db_session() as session:
            if session is None:
                return None
            
            sub_id = sub_data.get('id')
            existing = session.query(Subscription).filter(Subscription.id == sub_id).first()
            
            if existing:
                # Update
                for key, value in sub_data.items():
                    if hasattr(existing, key) and key != 'id':
                        setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
                sub = existing
            else:
                # Insert
                sub = Subscription(
                    id=sub_id,
                    user_id=sub_data.get('user_id'),
                    plan=sub_data.get('plan'),
                    status=sub_data.get('status'),
                    quantity=sub_data.get('quantity', 1),
                    next_billing_date=sub_data.get('next_billing_date')
                )
                session.add(sub)
            
            session.flush()
            logger.info("subscription_saved", sub_id=sub_id, status=sub.status)
            return subscription_to_dict(sub)
    except Exception as e:
        logger.error("insert_subscription_failed", error=str(e))
        return None

def get_user_subscription(user_id: str) -> Optional[Dict[str, Any]]:
    """Get active subscription for a user."""
    try:
        with get_db_session() as session:
            if session is None:
                return None
            sub = session.query(Subscription).filter(
                Subscription.user_id == user_id
            ).order_by(Subscription.created_at.desc()).first()
            return subscription_to_dict(sub) if sub else None
    except Exception as e:
        logger.error("get_user_subscription_failed", error=str(e), user_id=user_id)
        return None

def subscription_to_dict(sub: Subscription) -> Dict[str, Any]:
    """Convert Subscription model to dictionary."""
    return {
        'id': sub.id,
        'userId': sub.user_id,
        'plan': sub.plan,
        'status': sub.status,
        'quantity': sub.quantity,
        'nextBillingDate': sub.next_billing_date.isoformat() if sub.next_billing_date else None,
        'createdAt': sub.created_at.isoformat() if sub.created_at else None,
        'updatedAt': sub.updated_at.isoformat() if sub.updated_at else None,
    }

def delete_user_data(user_id: str) -> bool:
    """
    Delete a user and all related data (subscriptions, jobs, logs, repositories, etc.).
    Uses cascaded deletes where configured, manual delete for others.
    """
    try:
        with get_db_session() as session:
            if session is None:
                return False
                
            # 1. Delete Issues associated with this user
            session.query(Issue).filter(Issue.user_id == user_id).delete()
            
            # 2. Delete Jobs associated with this user (JobLogs will be deleted by cascade)
            session.query(Job).filter(Job.user_id == user_id).delete()
            
            # 3. Delete the User (Cascades: Session, Account, Repository, Subscription, GitHubAppInstallation)
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                session.delete(user)
                session.commit()
                logger.info("user_deleted", user_id=user_id)
                return True
            else:
                logger.warning("user_not_found_for_deletion", user_id=user_id)
                return False
    except Exception as e:
        logger.error("delete_user_data_failed", error=str(e), user_id=user_id)
        return False


# ======================
# Codebase Memory CRUD
# ======================

def get_codebase_memory(repository_id: str) -> Optional[Dict[str, Any]]:
    """Get memory for a repository."""
    try:
        with get_db_session() as session:
            if session is None:
                return None
            memory = session.query(CodebaseMemory).filter(
                CodebaseMemory.repository_id == repository_id
            ).first()
            return codebase_memory_to_dict(memory) if memory else None
    except Exception as e:
        logger.error("get_codebase_memory_failed", error=str(e), repository_id=repository_id)
        return None


def insert_or_update_codebase_memory(repository_id: str, memory_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Insert or update codebase memory."""
    try:
        with get_db_session() as session:
            if session is None:
                return None

            import uuid

            existing = session.query(CodebaseMemory).filter(
                CodebaseMemory.repository_id == repository_id
            ).first()

            if existing:
                # Update existing
                existing.memory = memory_data
                existing.updated_at = datetime.utcnow()
                memory = existing
            else:
                # Insert new
                memory_id = str(uuid.uuid4())
                memory = CodebaseMemory(
                    id=memory_id,
                    repository_id=repository_id,
                    memory=memory_data
                )
                session.add(memory)

            session.flush()
            logger.info("codebase_memory_saved", repository_id=repository_id)
            return codebase_memory_to_dict(memory)
    except Exception as e:
        logger.error("insert_or_update_codebase_memory_failed", error=str(e))
        return None


def codebase_memory_to_dict(memory: CodebaseMemory) -> Dict[str, Any]:
    """Convert CodebaseMemory model to dictionary."""
    return {
        'id': memory.id,
        'repositoryId': memory.repository_id,
        'memory': memory.memory,
        'createdAt': memory.created_at.isoformat() if memory.created_at else None,
        'updatedAt': memory.updated_at.isoformat() if memory.updated_at else None,
    }
