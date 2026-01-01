"""
Supabase Service - Database and Authentication client for CloudAgent.

Provides:
- User authentication (sign up, sign in, sign out)
- Jobs persistence (CRUD operations)
- Issues tracking and statistics
"""

import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from supabase import create_client, Client
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SupabaseConfig:
    """Configuration for Supabase client."""
    url: str
    key: str
    
    @classmethod
    def from_env(cls) -> 'SupabaseConfig':
        """Load config from environment variables."""
        return cls(
            url=os.environ.get('SUPABASE_URL', ''),
            key=os.environ.get('SUPABASE_KEY', '')
        )
    
    def is_configured(self) -> bool:
        """Check if required config is present."""
        return bool(self.url and self.key)


class SupabaseService:
    """
    Supabase client wrapper for authentication and database operations.
    
    Usage:
        service = SupabaseService()
        if service.is_available():
            user = service.sign_in("email@example.com", "password")
    """
    
    def __init__(self, config: Optional[SupabaseConfig] = None):
        """Initialize Supabase client."""
        self.config = config or SupabaseConfig.from_env()
        self.client: Optional[Client] = None
        
        if self.config.is_configured():
            try:
                self.client = create_client(self.config.url, self.config.key)
                logger.info("supabase_initialized", url=self.config.url[:30] + "...")
            except Exception as e:
                logger.error("supabase_init_failed", error=str(e))
                self.client = None
    
    def is_available(self) -> bool:
        """Check if Supabase client is available."""
        return self.client is not None
    
    # =====================
    # Authentication Methods
    # =====================
    
    def sign_up(self, email: str, password: str) -> Dict[str, Any]:
        """
        Register a new user.
        
        Returns:
            Dict with 'user' and 'session' on success, 'error' on failure.
        """
        if not self.client:
            return {'error': 'Supabase not configured'}
        
        try:
            response = self.client.auth.sign_up({
                'email': email,
                'password': password
            })
            
            if response.user:
                logger.info("user_signed_up", user_id=str(response.user.id))
                return {
                    'user': {
                        'id': str(response.user.id),
                        'email': response.user.email,
                    },
                    'session': {
                        'access_token': response.session.access_token if response.session else None,
                    }
                }
            return {'error': 'Sign up failed'}
        except Exception as e:
            logger.error("sign_up_failed", error=str(e))
            return {'error': str(e)}
    
    def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """
        Sign in an existing user.
        
        Returns:
            Dict with 'user' and 'session' on success, 'error' on failure.
        """
        if not self.client:
            return {'error': 'Supabase not configured'}
        
        try:
            response = self.client.auth.sign_in_with_password({
                'email': email,
                'password': password
            })
            
            if response.user and response.session:
                logger.info("user_signed_in", user_id=str(response.user.id))
                return {
                    'user': {
                        'id': str(response.user.id),
                        'email': response.user.email,
                    },
                    'session': {
                        'access_token': response.session.access_token,
                        'refresh_token': response.session.refresh_token,
                        'expires_at': response.session.expires_at,
                    }
                }
            return {'error': 'Invalid credentials'}
        except Exception as e:
            logger.error("sign_in_failed", error=str(e))
            return {'error': str(e)}
    
    def sign_out(self) -> Dict[str, Any]:
        """Sign out the current user."""
        if not self.client:
            return {'error': 'Supabase not configured'}
        
        try:
            self.client.auth.sign_out()
            logger.info("user_signed_out")
            return {'success': True}
        except Exception as e:
            logger.error("sign_out_failed", error=str(e))
            return {'error': str(e)}
    
    def get_user(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user from access token."""
        if not self.client:
            return None
        
        try:
            response = self.client.auth.get_user(access_token)
            if response.user:
                return {
                    'id': str(response.user.id),
                    'email': response.user.email,
                }
            return None
        except Exception as e:
            logger.error("get_user_failed", error=str(e))
            return None
    
    # =====================
    # Jobs Methods
    # =====================
    
    def get_jobs(self, user_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get jobs from database.
        
        Args:
            user_id: Optional filter by user
            limit: Max number of jobs to return
            
        Returns:
            List of job dictionaries
        """
        if not self.client:
            return []
        
        try:
            query = self.client.table('jobs').select('*').order('created_at', desc=True).limit(limit)
            
            if user_id:
                query = query.eq('user_id', user_id)
            
            response = query.execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error("get_jobs_failed", error=str(e))
            return []
    
    def save_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save or update a job.
        
        Args:
            job: Job dictionary with 'id' field
            
        Returns:
            Saved job or error dict
        """
        if not self.client:
            return {'error': 'Supabase not configured'}
        
        try:
            job_id = job.get('id')
            
            # Map camelCase to snake_case for database
            db_job = {
                'id': job_id,
                'repo': job.get('repo'),
                'issue_number': job.get('issueNumber'),
                'issue_title': job.get('issueTitle'),
                'status': job.get('status'),
                'stage': job.get('stage'),
                'retry_count': job.get('retryCount', 0),
                'pr_url': job.get('prUrl'),
                'error': job.get('error'),
                'logs': job.get('logs', []),
                'validation_logs': job.get('validationLogs', []),
                'user_id': job.get('userId'),
                'updated_at': datetime.now().isoformat(),
            }
            
            # Use upsert for insert or update
            response = self.client.table('jobs').upsert(db_job).execute()
            
            if response.data:
                logger.info("job_saved", job_id=job_id)
                return response.data[0]
            return {'error': 'Failed to save job'}
        except Exception as e:
            logger.error("save_job_failed", error=str(e), job_id=job.get('id'))
            return {'error': str(e)}
    
    def get_job_by_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a single job by ID."""
        if not self.client:
            return None
        
        try:
            response = self.client.table('jobs').select('*').eq('id', job_id).single().execute()
            return response.data if response.data else None
        except Exception as e:
            logger.error("get_job_by_id_failed", error=str(e), job_id=job_id)
            return None
    
    # =====================
    # Issues Methods
    # =====================
    
    def get_issues_count(self, user_id: Optional[str] = None, repo: Optional[str] = None) -> int:
        """Get count of issues, optionally filtered by user or repo."""
        if not self.client:
            return 0
        
        try:
            query = self.client.table('issues').select('id', count='exact')
            
            if user_id:
                query = query.eq('user_id', user_id)
            if repo:
                query = query.eq('repo', repo)
            
            response = query.execute()
            return response.count if response.count else 0
        except Exception as e:
            logger.error("get_issues_count_failed", error=str(e))
            return 0
    
    def create_issue(self, user_id: str, repo: str, issue_number: int, title: str) -> Dict[str, Any]:
        """Create a new issue record."""
        if not self.client:
            return {'error': 'Supabase not configured'}
        
        try:
            response = self.client.table('issues').insert({
                'user_id': user_id,
                'repo': repo,
                'issue_number': issue_number,
                'title': title,
                'status': 'open',
            }).execute()
            
            if response.data:
                logger.info("issue_created", repo=repo, issue_number=issue_number)
                return response.data[0]
            return {'error': 'Failed to create issue'}
        except Exception as e:
            logger.error("create_issue_failed", error=str(e))
            return {'error': str(e)}
    
    def get_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics for jobs and issues.
        
        Returns:
            Dict with counts for jobs by status and total issues
        """
        if not self.client:
            return {'error': 'Supabase not configured'}
        
        try:
            jobs = self.get_jobs(user_id=user_id, limit=1000)
            
            stats = {
                'total_jobs': len(jobs),
                'completed_jobs': len([j for j in jobs if j.get('status') == 'completed']),
                'failed_jobs': len([j for j in jobs if j.get('status') == 'failed']),
                'processing_jobs': len([j for j in jobs if j.get('status') == 'processing']),
                'total_issues': self.get_issues_count(user_id=user_id),
            }
            
            return stats
        except Exception as e:
            logger.error("get_stats_failed", error=str(e))
            return {'error': str(e)}
