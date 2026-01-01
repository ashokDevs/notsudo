import base64

from github import Github
from github.GithubException import GithubException, UnknownObjectException
from utils.logger import get_logger

logger = get_logger(__name__)


class GitHubService:
    def __init__(self, token):
        if not token:
            raise ValueError("GitHub token is required")
        self.github = Github(token)
        logger.info("github_service_initialized")
    
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
        
        try:
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
            return repos
        except GithubException as e:
            logger.error("fetch_repos_failed", error=str(e))
            raise ValueError(f"Failed to fetch repositories: {str(e)}")
    
    def get_repository(self, repo_full_name):
        if not repo_full_name:
            raise ValueError("Repository full name is required")
        
        logger.info("fetching_repository", repo=repo_full_name)
        
        try:
            repo = self.github.get_repo(repo_full_name)
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
                logger.error("access_forbidden", repo=repo_full_name, status=403)
                raise ValueError(
                    f"Access forbidden (403). Your token may not have permission to access repository '{repo_full_name}'. "
                    f"Error: {str(e)}"
                )
            else:
                logger.error("github_api_error", status=e.status, error=str(e))
                raise ValueError(f"GitHub API error: {str(e)}")
    
    def get_file_content(self, repo, file_path, ref='main'):
        try:
            file_content = repo.get_contents(file_path, ref=ref)
            if file_content.encoding == 'base64':
                content = base64.b64decode(file_content.content).decode('utf-8')
            else:
                content = file_content.decoded_content.decode('utf-8')
            
            logger.debug("file_content_fetched", path=file_path, size=len(content))
            return content
        except UnknownObjectException:
            logger.debug("file_not_found", path=file_path)
            return None
        except GithubException as e:
            logger.warning("file_fetch_failed", path=file_path, error=str(e))
            return None
    
    def get_directory_structure(self, repo, path='', ref='main'):
        contents = []
        try:
            items = repo.get_contents(path, ref=ref)
            for item in items:
                if item.type == 'dir':
                    contents.append({'path': item.path, 'type': 'directory'})
                    contents.extend(self.get_directory_structure(repo, item.path, ref))
                else:
                    contents.append({'path': item.path, 'type': 'file', 'size': item.size})
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
            pr = repo.create_pull(
                title=title,
                body=body,
                head=head_branch,
                base=base_branch
            )
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
            source = repo.get_branch(source_branch)
            repo.create_git_ref(ref=f'refs/heads/{branch_name}', sha=source.commit.sha)
            logger.info("branch_created", branch=branch_name, sha=source.commit.sha[:8])
            return True
        except GithubException as e:
            logger.error("branch_creation_failed", branch=branch_name, error=str(e))
            return False
    
    def update_file(self, repo, file_path, content, message, branch):
        logger.info("updating_file", path=file_path, branch=branch)
        
        try:
            file = repo.get_contents(file_path, ref=branch)
            repo.update_file(
                path=file_path,
                message=message,
                content=content,
                sha=file.sha,
                branch=branch
            )
            logger.info("file_updated", path=file_path)
            return True
        except UnknownObjectException:
            logger.info("file_not_exists_creating", path=file_path)
            try:
                repo.create_file(
                    path=file_path,
                    message=message,
                    content=content,
                    branch=branch
                )
                logger.info("file_created", path=file_path)
                return True
            except GithubException as e:
                logger.error("file_creation_failed", path=file_path, error=str(e))
                return False
        except GithubException as e:
            logger.error("file_update_failed", path=file_path, error=str(e))
            return False
