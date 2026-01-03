import base64
import time
from github import Github
from github.GithubException import GithubException, UnknownObjectException
from utils.logger import get_logger

logger = get_logger(__name__)

class RateLimitExceeded(Exception):
    pass

def is_rate_limit_error(exception):
    if isinstance(exception, GithubException) and exception.status == 403:
        # Check headers if available
        if exception.headers:
            remaining = exception.headers.get('X-RateLimit-Remaining')
            if remaining is not None and int(remaining) == 0:
                return True
        # Also check message just in case
        if "rate limit" in str(exception.data.get('message', '')).lower():
            return True
    return False

class GitHubService:
    def __init__(self, token):
        if not token:
            raise ValueError("GitHub token is required")
        self.github = Github(token)
        logger.info("github_service_initialized")

        # Check rate limit on init
        self._log_rate_limit()

    def _log_rate_limit(self):
        try:
            rate_limit = self.github.get_rate_limit()
            core = rate_limit.core
            logger.info(
                "github_rate_limit",
                remaining=core.remaining,
                limit=core.limit,
                reset=core.reset.isoformat()
            )
        except Exception as e:
            logger.warning("failed_to_check_rate_limit", error=str(e))

    def _wait_for_rate_limit_reset(self, exception, max_wait_time=60):
        """
        Calculates wait time based on X-RateLimit-Reset header or defaults to 60 seconds.
        Returns the wait time if it's within max_wait_time, otherwise raises the exception.
        """
        wait_time = 60
        if isinstance(exception, GithubException) and exception.headers:
            reset_timestamp = exception.headers.get('X-RateLimit-Reset')
            if reset_timestamp:
                try:
                    reset_time = int(reset_timestamp)
                    current_time = int(time.time())
                    wait_time = max(1, reset_time - current_time)
                except (ValueError, TypeError):
                    pass

        if wait_time > max_wait_time:
            logger.error(
                "rate_limit_wait_too_long",
                wait_time=wait_time,
                max_wait_time=max_wait_time,
                reset_header=exception.headers.get('X-RateLimit-Reset') if isinstance(exception, GithubException) else None
            )
            raise exception

        logger.warning(
            "rate_limit_exceeded_waiting",
            wait_time_seconds=wait_time,
            reset_header=exception.headers.get('X-RateLimit-Reset') if isinstance(exception, GithubException) else None
        )
        return wait_time

    def _execute_with_retry(self, func, *args, **kwargs):
        max_retries = 3
        # Allow max wait time of 60 seconds per retry
        max_wait_time = 60

        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except GithubException as e:
                if is_rate_limit_error(e):
                    # This raises if wait time is too long
                    wait_time = self._wait_for_rate_limit_reset(e, max_wait_time=max_wait_time)
                    # Add a small buffer to be safe
                    wait_time += 1

                    if attempt < max_retries - 1:
                        logger.warning("rate_limited_sleeping", wait_time=wait_time, attempt=attempt+1)
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error("rate_limit_retries_exhausted")
                        raise
                raise
            except Exception:
                raise
    
    def verify_token_scopes(self):
        """
        Verify if the token has the required 'repo' scope for private repositories.
        """
        try:
            # Access user to trigger request and populate scopes
            user = self.github.get_user()
            # We access a property to ensure the request is made
            _ = user.login

            scopes = self.github.oauth_scopes
            logger.info("token_scopes_verified", scopes=scopes)

            # Scopes can be None if not OAuth/PAT or if not provided in headers
            if scopes is None:
                return {
                    'valid': True,
                    'scopes': [],
                    'has_repo_scope': False,
                    'warning': 'No scopes detected.'
                }

            has_repo_scope = 'repo' in scopes

            return {
                'valid': True,
                'scopes': scopes,
                'has_repo_scope': has_repo_scope,
                'warning': None if has_repo_scope else 'Missing "repo" scope. Private repositories will not be accessible.'
            }
        except GithubException as e:
            logger.error("token_verification_failed", error=str(e))
            return {
                'valid': False,
                'error': str(e)
            }
        except Exception as e:
            logger.error("token_verification_error", error=str(e))
            return {
                'valid': False,
                'error': str(e)
            }

    def get_available_repos(self):
        """
        Get all repositories accessible by the GitHub token.
        Returns a list of repository info dictionaries.
        Includes: owned repos, collaborator repos, and organization member repos.
        """
        logger.info("fetching_available_repos")
        
        def _fetch():
            repos = []
            seen = set()
            
            # Get repos with all affiliations: owner, collaborator, org member
            for repo in self.github.get_user().get_repos(affiliation='owner,collaborator,organization_member'):
                if repo.full_name not in seen:
                    seen.add(repo.full_name)
                    repos.append({
                        'full_name': repo.full_name,
                        'name': repo.name,
                        'owner': repo.owner.login,
                        'private': repo.private,
                        'default_branch': repo.default_branch,
                        'description': repo.description,
                        'url': repo.html_url,
                        'language': repo.language,
                        'updated_at': repo.updated_at.isoformat() if repo.updated_at else None,
                        'permissions': {
                            'admin': repo.permissions.admin if repo.permissions else False,
                            'push': repo.permissions.push if repo.permissions else False,
                            'pull': repo.permissions.pull if repo.permissions else False
                        }
                    })
            
            logger.info("repos_fetched", count=len(repos))
            self._log_rate_limit()
            return repos

        try:
            return self._execute_with_retry(_fetch)
        except GithubException as e:
            logger.error("fetch_repos_failed", error=str(e))
            raise ValueError(f"Failed to fetch repositories: {str(e)}")
    
    def get_repository(self, repo_full_name):
        if not repo_full_name:
            raise ValueError("Repository full name is required")
        
        logger.info("fetching_repository", repo=repo_full_name)
        
        def _get_repo():
            return self.github.get_repo(repo_full_name)

        try:
            repo = self._execute_with_retry(_get_repo)
            logger.info("repository_fetched", repo=repo_full_name, default_branch=repo.default_branch)
            return repo
        except UnknownObjectException as e:
            logger.error("repository_not_found", repo=repo_full_name, error=str(e))
            raise ValueError(
                f"Repository '{repo_full_name}' not found. "
                f"Check if the repository exists and your token has access to it. "
                f"Error: {str(e)}"
            )
        except GithubException as e:
            if e.status == 404:
                logger.error("repository_404", repo=repo_full_name)
                raise ValueError(
                    f"Repository '{repo_full_name}' not found (404). "
                    f"Possible causes: repository doesn't exist, token lacks access, or invalid repository name. "
                    f"Error: {str(e)}"
                )
            elif e.status == 401:
                logger.error("authentication_failed", status=401)
                raise ValueError(
                    f"Authentication failed (401). Check if your GitHub token is valid and has the required permissions. "
                    f"Error: {str(e)}"
                )
            elif e.status == 403:
                # If it was a rate limit error, it would have been handled by _execute_with_retry if it could be retried.
                # If we are here, either it wasn't a rate limit error, or retries were exhausted, or wait was too long.
                if is_rate_limit_error(e):
                     logger.error("rate_limit_exceeded_error", repo=repo_full_name, status=403)
                     raise ValueError("GitHub API rate limit exceeded. Please try again later.")

                logger.error("access_forbidden", repo=repo_full_name, status=403)
                raise ValueError(
                    f"Access forbidden (403). Your token may not have permission to access repository '{repo_full_name}'. "
                    f"Error: {str(e)}"
                )
            else:
                logger.error("github_api_error", status=e.status, error=str(e))
                raise ValueError(f"GitHub API error: {str(e)}")
    
    def get_file_content(self, repo, file_path, ref='main'):
        def _get_content():
            file_content = repo.get_contents(file_path, ref=ref)
            if file_content.encoding == 'base64':
                content = base64.b64decode(file_content.content).decode('utf-8')
            else:
                content = file_content.decoded_content.decode('utf-8')
            
            logger.debug("file_content_fetched", path=file_path, size=len(content))
            return content

        try:
            return self._execute_with_retry(_get_content)
        except UnknownObjectException:
            logger.debug("file_not_found", path=file_path)
            return None
        except GithubException as e:
            logger.warning("file_fetch_failed", path=file_path, error=str(e))
            return None
    
    def get_directory_structure(self, repo, path='', ref='main', max_depth=5, skip_patterns=None):
        if skip_patterns is None:
            skip_patterns = ['node_modules', 'vendor', '.git', 'dist', 'build', '__pycache__', '.idea', '.vscode']

        return self._get_directory_structure_recursive(repo, path, ref, max_depth, skip_patterns, 0)

    def _get_directory_structure_recursive(self, repo, path, ref, max_depth, skip_patterns, current_depth):
        contents = []

        if current_depth > max_depth:
            return contents

        try:
            # Recursion makes _execute_with_retry tricky if we wrap the whole method.
            # Instead, wrap the API call.
            def _get_items():
                return repo.get_contents(path, ref=ref)

            items = self._execute_with_retry(_get_items)

            for item in items:
                # Skip if matches pattern
                if any(pattern in item.path.split('/') for pattern in skip_patterns):
                    continue

                if item.type == 'dir':
                    contents.append({'path': item.path, 'type': 'directory'})
                    contents.extend(self._get_directory_structure_recursive(
                        repo, item.path, ref, max_depth, skip_patterns, current_depth + 1
                    ))
                else:
                    contents.append({'path': item.path, 'type': 'file', 'size': item.size})

            if len(contents) > 1000 and current_depth == 0:
                logger.warning("large_repository_detected", file_count=len(contents))

        except UnknownObjectException:
            pass
        except GithubException as e:
            logger.warning("directory_fetch_failed", path=path, error=str(e))

        return contents
    
    def get_relevant_files(self, repo, max_files=20):
        logger.info("fetching_relevant_files", repo=repo.full_name, max_files=max_files)
        
        structure = self.get_directory_structure(repo)
        
        files = [item for item in structure if item['type'] == 'file']
        
        priority_extensions = ['.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.go', '.rs']
        skip_patterns = ['node_modules', '.git', 'dist', 'build', '__pycache__']
        
        filtered_files = []
        for file_info in files:
            skip = False
            for pattern in skip_patterns:
                if pattern in file_info['path']:
                    skip = True
                    break
            if not skip:
                filtered_files.append(file_info)
        
        priority_files = [f for f in filtered_files if any(f['path'].endswith(ext) for ext in priority_extensions)]
        
        selected_files = priority_files[:max_files] if len(priority_files) > 0 else filtered_files[:max_files]
        
        logger.info(
            "files_selected",
            total_files=len(files),
            filtered_files=len(filtered_files),
            priority_files=len(priority_files),
            selected=len(selected_files)
        )
        
        files_with_content = []
        for file_info in selected_files:
            content = self.get_file_content(repo, file_info['path'])
            if content:
                files_with_content.append({
                    'path': file_info['path'],
                    'content': content
                })
        
        logger.info("files_loaded", count=len(files_with_content))
        self._log_rate_limit()
        return files_with_content
    
    def create_pull_request(self, repo, title, body, head_branch, base_branch='main'):
        logger.info(
            "creating_pull_request",
            repo=repo.full_name,
            head=head_branch,
            base=base_branch,
            title=title
        )
        
        try:
            def _create_pr():
                return repo.create_pull(
                    title=title,
                    body=body,
                    head=head_branch,
                    base=base_branch
                )

            pr = self._execute_with_retry(_create_pr)

            logger.info("pull_request_created", pr_number=pr.number, pr_url=pr.html_url)
            return {
                'success': True,
                'pr_url': pr.html_url,
                'pr_number': pr.number
            }
        except Exception as e:
            logger.error("pull_request_failed", error=str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_branch(self, repo, branch_name, source_branch='main'):
        logger.info("creating_branch", branch=branch_name, source=source_branch)
        
        try:
            def _create_ref():
                source = repo.get_branch(source_branch)
                return repo.create_git_ref(ref=f'refs/heads/{branch_name}', sha=source.commit.sha)

            self._execute_with_retry(_create_ref)
            logger.info("branch_created", branch=branch_name)
            return True
        except GithubException as e:
            logger.error("branch_creation_failed", branch=branch_name, error=str(e))
            return False
    
    def update_file(self, repo, file_path, content, message, branch):
        logger.info("updating_file", path=file_path, branch=branch)
        
        try:
            def _update():
                file = repo.get_contents(file_path, ref=branch)
                repo.update_file(
                    path=file_path,
                    message=message,
                    content=content,
                    sha=file.sha,
                    branch=branch
                )
                return True

            self._execute_with_retry(_update)
            logger.info("file_updated", path=file_path)
            return True
        except UnknownObjectException:
            logger.info("file_not_exists_creating", path=file_path)
            try:
                def _create():
                    repo.create_file(
                        path=file_path,
                        message=message,
                        content=content,
                        branch=branch
                    )

                self._execute_with_retry(_create)
                logger.info("file_created", path=file_path)
                return True
            except GithubException as e:
                logger.error("file_creation_failed", path=file_path, error=str(e))
                return False
        except GithubException as e:
            logger.error("file_update_failed", path=file_path, error=str(e))
            return False

    def get_webhook_status(self, repo_full_name, webhook_url):
        logger.info("checking_webhook_status", repo=repo_full_name, url=webhook_url)
        try:
            repo = self.get_repository(repo_full_name)
            hooks = repo.get_hooks()
            for hook in hooks:
                if hook.config.get('url') == webhook_url:
                    return {'id': hook.id, 'active': hook.active, 'events': hook.events}
            return None
        except Exception as e:
            logger.error("webhook_check_failed", error=str(e))
            # Don't raise here if it's just checking status - return None or propagate?
            # If repo doesn't exist, get_repository raises.
            # If permissions issue, get_hooks might fail.
            # We should probably propagate the error so the UI knows.
            raise

    def create_webhook(self, repo_full_name, webhook_url, secret):
        logger.info("creating_webhook", repo=repo_full_name, url=webhook_url)
        try:
            repo = self.get_repository(repo_full_name)

            # Check if exists
            try:
                existing = self.get_webhook_status(repo_full_name, webhook_url)
                if existing:
                    return existing
            except Exception:
                # Proceed to try creating if check fails? Or fail?
                # If we can't read hooks, we probably can't write them.
                pass

            config = {
                'url': webhook_url,
                'content_type': 'json',
                'secret': secret,
                'insecure_ssl': '0'
            }

            hook = repo.create_hook(
                name='web',
                config=config,
                events=['issues', 'issue_comment', 'pull_request'],
                active=True
            )
            logger.info("webhook_created", id=hook.id)
            return {'id': hook.id, 'active': hook.active, 'events': hook.events}
        except Exception as e:
            logger.error("webhook_creation_failed", error=str(e))
            raise

    def delete_webhook(self, repo_full_name, webhook_url):
        logger.info("deleting_webhook", repo=repo_full_name, url=webhook_url)
        try:
            repo = self.get_repository(repo_full_name)
            hooks = repo.get_hooks()
            for hook in hooks:
                if hook.config.get('url') == webhook_url:
                    hook.delete()
                    logger.info("webhook_deleted", id=hook.id)
                    return True
            return False
        except Exception as e:
            logger.error("webhook_deletion_failed", error=str(e))
            raise

    def get_issues(self, repo_full_name, state='open'):
        """Get issues for a repository."""
        logger.info("fetching_issues", repo=repo_full_name, state=state)
        try:
            repo = self.github.get_repo(repo_full_name)
            issues = []
            for issue in repo.get_issues(state=state):
                issues.append({
                    'number': issue.number,
                    'title': issue.title,
                    'body': issue.body,
                    'state': issue.state,
                    'html_url': issue.html_url,
                    'created_at': issue.created_at.isoformat(),
                    'updated_at': issue.updated_at.isoformat(),
                    'user': {
                        'login': issue.user.login,
                        'avatar_url': issue.user.avatar_url
                    },
                    'labels': [{'name': l.name, 'color': l.color} for l in issue.labels]
                })
            logger.info("issues_fetched", count=len(issues))
            return issues
        except Exception as e:
            logger.error("fetch_issues_failed", repo=repo_full_name, error=str(e))
            raise ValueError(f"Failed to fetch issues: {str(e)}")
