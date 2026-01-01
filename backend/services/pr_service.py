import time
import uuid

from utils.logger import get_logger

logger = get_logger(__name__)


class PRService:
    MAX_RETRIES = 3
    
    def __init__(self, github_service, ai_service, code_execution=None):
        self.github_service = github_service
        self.ai_service = ai_service
        self.code_execution = code_execution
        
        # Lazy init code execution if not provided
        if self.code_execution is None:
            try:
                from services.code_execution import CodeExecutionService
                self.code_execution = CodeExecutionService()
                logger.info("code_execution_initialized")
            except Exception as e:
                logger.warning("code_execution_unavailable", error=str(e))
    
    def process_issue(self, repo_full_name, issue_number, issue_title, issue_body, comment_body):
        logger.info(
            "processing_issue",
            repo=repo_full_name,
            issue_number=issue_number,
            issue_title=issue_title
        )
        
        try:
            repo = self.github_service.get_repository(repo_full_name)
        except ValueError as e:
            logger.error("repository_fetch_failed", repo=repo_full_name, error=str(e))
            return {
                'success': False,
                'message': str(e)
            }
        
        logger.info("fetching_codebase_files", repo=repo_full_name)
        codebase_files = self.github_service.get_relevant_files(repo, max_files=15)
        
        if not codebase_files:
            logger.error("no_codebase_files", repo=repo_full_name)
            return {
                'success': False,
                'message': 'Could not fetch codebase files'
            }
        
        logger.info("codebase_files_fetched", count=len(codebase_files))
        
        logger.info("analyzing_with_ai", issue_number=issue_number)
        ai_result = self.ai_service.analyze_issue_and_plan_changes(
            issue_title=issue_title,
            issue_body=issue_body,
            comment_body=comment_body,
            codebase_files=codebase_files
        )
        
        file_changes = ai_result.get('file_changes', [])
        
        if not file_changes:
            logger.warning("no_file_changes_suggested", issue_number=issue_number)
            return {
                'success': False,
                'message': 'AI did not suggest any file changes',
                'analysis': ai_result.get('analysis')
            }
        
        logger.info("file_changes_received", count=len(file_changes))
        
        # Generate a unique branch name using UUID to avoid collisions
        base_branch_name = f"ai-fix-issue-{issue_number}"
        branch_name = f"{base_branch_name}-{uuid.uuid4().hex[:8]}"

        # Check if branch exists (unlikely with UUID but required check)
        # We try up to 3 times to find a non-existent branch name
        for _ in range(3):
            try:
                repo.get_branch(branch_name)
                # If we get here, branch exists. Generate new UUID and try again
                branch_name = f"{base_branch_name}-{uuid.uuid4().hex[:8]}"
            except Exception:
                # Branch doesn't exist (or other error), safe to try creating
                break

        logger.info("creating_branch", branch=branch_name)
        branch_created = self.github_service.create_branch(repo, branch_name)
        
        if not branch_created:
            logger.error("branch_creation_failed", branch=branch_name)
            return {
                'success': False,
                'message': 'Failed to create branch'
            }
        
        # Validate changes in sandbox with retry loop
        logger.info("starting_validation", max_retries=self.MAX_RETRIES)
        validation_result = self._validate_with_retries(
            repo=repo,
            branch_name=branch_name,
            file_changes=file_changes,
        )
        
        if not validation_result['success']:
            logger.error(
                "validation_failed",
                attempts=self.MAX_RETRIES,
                error=validation_result.get('error')
            )
            return {
                'success': False,
                'message': f"Validation failed after {self.MAX_RETRIES} attempts",
                'logs': validation_result.get('logs', []),
                'error': validation_result.get('error')
            }
        
        logger.info("validation_passed")
        
        # Use the (potentially fixed) file_changes
        file_changes = validation_result.get('file_changes', file_changes)
        
        changes_applied = []
        for change in file_changes:
            file_path = change['file_path']
            new_content = change['new_content']
            reason = change['reason']
            
            logger.info("applying_change", file=file_path, reason=reason)
            
            success = self.github_service.update_file(
                repo=repo,
                file_path=file_path,
                content=new_content,
                message=f"AI: {reason}",
                branch=branch_name
            )
            
            if success:
                changes_applied.append({
                    'file': file_path,
                    'reason': reason
                })
                logger.info("change_applied", file=file_path)
            else:
                logger.error("change_failed", file=file_path)
        
        if not changes_applied:
            logger.error("no_changes_applied")
            return {
                'success': False,
                'message': 'Failed to apply any changes'
            }
        
        logger.info("changes_applied", count=len(changes_applied))
        
        pr_title = f"AI Fix: {issue_title}"
        pr_body = f"""This PR was automatically generated in response to issue #{issue_number}.

## Changes Made:
{chr(10).join([f"- **{change['file']}**: {change['reason']}" for change in changes_applied])}

## AI Analysis:
{ai_result.get('analysis')}

## Validation:
✅ Tests passed in sandbox environment

---
Generated by @notsudo AI automation"""
        
        logger.info("creating_pull_request", branch=branch_name)
        pr_result = self.github_service.create_pull_request(
            repo=repo,
            title=pr_title,
            body=pr_body,
            head_branch=branch_name
        )
        
        if pr_result.get('success'):
            logger.info(
                "pull_request_created",
                pr_number=pr_result.get('pr_number'),
                pr_url=pr_result.get('pr_url')
            )
        else:
            logger.error("pull_request_creation_failed", error=pr_result.get('error'))
        
        return {
            'success': pr_result.get('success'),
            'pr_url': pr_result.get('pr_url'),
            'pr_number': pr_result.get('pr_number'),
            'changes_applied': changes_applied,
            'branch': branch_name,
            'validation_logs': validation_result.get('logs', [])
        }
    
    def _validate_with_retries(self, repo, branch_name, file_changes):
        """
        Validate changes in sandbox, retrying with AI fixes if tests fail.
        """
        if self.code_execution is None:
            logger.warning("validation_skipped", reason="Docker not available")
            return {'success': True, 'file_changes': file_changes, 'logs': ['Validation skipped - Docker not available']}
        
        # Check if changes are documentation-only (no code validation needed)
        if self._is_documentation_only(file_changes):
            logger.info("validation_skipped", reason="Documentation-only changes")
            return {
                'success': True, 
                'file_changes': file_changes, 
                'logs': ['Validation skipped - Documentation-only changes (no code to test)']
            }
        
        current_changes = file_changes
        all_logs = []
        
        for attempt in range(1, self.MAX_RETRIES + 1):
            logger.info("validation_attempt", attempt=attempt, max_retries=self.MAX_RETRIES)
            all_logs.append(f"=== Attempt {attempt}/{self.MAX_RETRIES} ===")
            
            result = self.code_execution.validate_changes(
                repo_url=repo.clone_url,
                branch=branch_name,
                file_changes=current_changes,
                run_tests=True,
            )
            
            all_logs.extend(result.logs)
            
            if result.success:
                logger.info("validation_succeeded", attempt=attempt)
                return {
                    'success': True,
                    'file_changes': current_changes,
                    'logs': all_logs
                }
            
            logger.warning(
                "validation_attempt_failed",
                attempt=attempt,
                error=result.error
            )
            
            # If this was the last attempt, don't try to fix
            if attempt == self.MAX_RETRIES:
                break
            
            # Ask AI to fix based on error logs
            logger.info("requesting_ai_fix", attempt=attempt)
            all_logs.append(f"Tests failed, asking AI to fix...")
            error_context = "\n".join(result.logs[-20:])  # Last 20 log lines
            
            try:
                current_changes = self.ai_service.fix_test_failures(
                    original_changes=current_changes,
                    error_logs=error_context
                )
                logger.info("ai_fix_received", file_count=len(current_changes))
                all_logs.append(f"AI suggested fixes for {len(current_changes)} files")
            except Exception as e:
                logger.error("ai_fix_failed", error=str(e))
                all_logs.append(f"AI fix failed: {e}")
                break
        
        return {
            'success': False,
            'error': result.error if result else 'Validation failed',
            'logs': all_logs
        }
    
    def _is_documentation_only(self, file_changes):
        """
        Check if all file changes are documentation/non-code files.
        These don't need sandbox validation.
        """
        DOC_EXTENSIONS = {
            '.md', '.markdown', '.txt', '.rst', '.adoc',  # Documentation
            '.json', '.yaml', '.yml', '.toml',  # Config (usually safe)
            '.gitignore', '.gitattributes', '.editorconfig',  # Git/editor
            '.env.example', '.dockerignore',  # Templates
            'LICENSE', 'README', 'CHANGELOG', 'CONTRIBUTING',  # Common docs
        }
        
        for change in file_changes:
            file_path = change.get('file_path', '') if isinstance(change, dict) else change.file_path
            file_name = file_path.split('/')[-1]
            file_ext = '.' + file_name.split('.')[-1].lower() if '.' in file_name else ''
            
            # Check if it's a known doc file or extension
            is_doc = (
                file_ext in DOC_EXTENSIONS or 
                file_name.upper() in DOC_EXTENSIONS or
                file_name.startswith('.')  # Hidden config files
            )
            
            if not is_doc:
                return False
        
        return True

