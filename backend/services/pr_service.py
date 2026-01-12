import time
import uuid

from utils.logger import get_logger

logger = get_logger(__name__)


class PRService:
    MAX_RETRIES = 10
    
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
            
            # 1. Add processing comment
            self.github_service.add_issue_comment(
                repo, 
                issue_number, 
                "🤖 **@notsudo is working on this issue...**\n\nAnalyzing codebase and generating changes. This may take a few minutes."
            )
            
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
            self.github_service.add_issue_comment(repo, issue_number, "❌ **Failed to process issue**\n\nCould not fetch codebase files. Please check repository permissions.")
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
            codebase_files=codebase_files,
            repo_url=repo.clone_url,
            code_execution_service=self.code_execution
        )
        
        file_changes = ai_result.get('file_changes', [])
        
        if not file_changes:
            logger.warning("no_file_changes_suggested", issue_number=issue_number)
            self.github_service.add_issue_comment(
                repo, 
                issue_number, 
                f"ℹ️ **Analysis Complete**\n\nI analyzed the issue but couldn't determine any necessary code changes.\n\n**Analysis:**\n{ai_result.get('analysis')}"
            )
            return {
                'success': False,
                'message': 'AI did not suggest any file changes',
                'analysis': ai_result.get('analysis')
            }
        
        logger.info("file_changes_received", count=len(file_changes))
        
        # Generate a descriptive branch name using AI
        branch_name = self.ai_service.generate_branch_name(
            issue_number=issue_number,
            issue_title=issue_title,
            issue_body=issue_body
        )

        # Check if branch exists and handle collisions
        for _ in range(3):
            try:
                repo.get_branch(branch_name)
                # If exists, append a small random string to make it unique
                branch_name = f"{branch_name}-{uuid.uuid4().hex[:4]}"
            except Exception:
                # Branch doesn't exist, safe to use
                break

        logger.info("creating_branch", branch=branch_name)
        branch_result = self.github_service.create_branch(repo, branch_name)
        
        if not branch_result.get('success'):
            logger.error("branch_creation_failed", branch=branch_name, error=branch_result.get('error'))
            self.github_service.add_issue_comment(repo, issue_number, "❌ **Failed to create branch**\n\nI encountered an error while trying to create a new branch.")
            return {
                'success': False,
                'message': 'Failed to create branch'
            }
        
        # If branch already existed (another process is handling this issue), abort gracefully
        if branch_result.get('already_exists'):
            logger.info("branch_already_exists_abort", branch=branch_name)
            return {
                'success': False,
                'message': 'Branch already exists - another process is handling this issue'
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
            
            # Cleanup branch on failure
            self.github_service.delete_branch(repo, branch_name)
            
            self.github_service.add_issue_comment(
                repo, 
                issue_number, 
                f"❌ **Validation Failed**\n\nI attempted to fix the issue but the changes failed validation (tests/linting).\n\n**Error:**\n{validation_result.get('error')}"
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
            # Cleanup branch
            self.github_service.delete_branch(repo, branch_name)
            self.github_service.add_issue_comment(repo, issue_number, "❌ **Failed to apply changes**\n\nI generated a plan but failed to apply the file changes to the repository.")
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
            self.github_service.add_issue_comment(
                repo, 
                issue_number, 
                f"✅ **PR Created!**\n\nI've created a pull request to address this issue:\n→ [PR #{pr_result.get('pr_number')}: {pr_title}]({pr_result.get('pr_url')})\n\nPlease review the changes and merge if they look good."
            )
        else:
            logger.error("pull_request_creation_failed", error=pr_result.get('error'))
            # Cleanup branch? Maybe keep it if changes were valid but PR creation failed (e.g. rate limit)
            self.github_service.add_issue_comment(repo, issue_number, f"⚠️ **PR Creation Failed**\n\nThe changes were validated and the branch `{branch_name}` was created, but I failed to create the Pull Request object.\nError: {pr_result.get('error')}")
        
        return {
            'success': pr_result.get('success'),
            'pr_url': pr_result.get('pr_url'),
            'pr_number': pr_result.get('pr_number'),
            'changes_applied': changes_applied,
            'branch': branch_name,
            'validation_logs': validation_result.get('logs', [])
        }
    
    def process_pr_comment(self, repo_full_name, pr_number, comment_body):
        logger.info(
            "processing_pr_comment",
            repo=repo_full_name,
            pr_number=pr_number
        )
        
        try:
            repo = self.github_service.get_repository(repo_full_name)
            pr = repo.get_pull(pr_number)
            branch_name = pr.head.ref
            
            # 1. Add processing comment
            self.github_service.add_issue_comment(
                repo, 
                pr_number, 
                "🤖 **Processing feedback...**\n\nI'm analyzing your comments and updating the PR. This might take a few minutes."
            )
            
            # Fetch files changed in PR to give context
            pr_files = list(pr.get_files())
            codebase_files = []
            
            logger.info("fetching_pr_files", count=len(pr_files), branch=branch_name)
            
            for file in pr_files:
                # Skip deleted files
                if file.status == "removed":
                    continue
                    
                try:
                    content = self.github_service.get_file_content(repo, file.filename, ref=branch_name)
                    if content:
                        codebase_files.append({
                            'path': file.filename,
                            'content': content
                        })
                except Exception as e:
                    logger.warning("failed_to_fetch_file", file=file.filename, error=str(e))
            
            # If we don't have enough context, maybe fetch some top-level files too?
            if not codebase_files:
                logger.warning("no_pr_files_fetched", pr_number=pr_number)
                codebase_files = self.github_service.get_relevant_files(repo, max_files=10)

        except Exception as e:
            logger.error("pr_context_fetch_failed", error=str(e))
            return {
                'success': False,
                'message': f"Failed to fetch PR context: {str(e)}"
            }
            
        # Analyze with AI
        logger.info("analyzing_pr_comment_with_ai")
        try:
            ai_result = self.ai_service.analyze_pr_comment(
                pr_title=pr.title,
                pr_body=pr.body,
                comment_body=comment_body,
                codebase_files=codebase_files
            )
        except Exception as e:
            logger.error("ai_analysis_failed", error=str(e))
            self.github_service.add_issue_comment(repo, pr_number, f"❌ **AI Analysis Failed**\n\n{str(e)}")
            return {'success': False, 'message': str(e)}
        
        file_changes = ai_result.get('file_changes', [])
        
        if not file_changes:
            logger.info("no_changes_needed_for_pr")
            self.github_service.add_issue_comment(
                repo,
                pr_number,
                f"ℹ️ **Analysis Complete**\n\nI analyzed your comment but didn't find any code changes to apply.\n\n**Analysis:**\n{ai_result.get('analysis')}"
            )
            return {
                'success': True, 
                'message': 'No changes needed',
                'analysis': ai_result.get('analysis')
            }

        # Validate changes
        logger.info("validating_pr_changes", branch=branch_name)
        validation_result = self._validate_with_retries(
            repo=repo,
            branch_name=branch_name,
            file_changes=file_changes
        )
        
        if not validation_result['success']:
            logger.error("pr_validation_failed", error=validation_result.get('error'))
            self.github_service.add_issue_comment(
                repo,
                pr_number,
                f"❌ **Validation Failed**\n\nI tried to apply changes but they failed validation (tests/linting).\n\n**Error:**\n{validation_result.get('error')}"
            )
            return {
                'success': False,
                'message': 'Validation failed',
                'logs': validation_result.get('logs', [])
            }
            
        # Apply valid changes to the branch
        final_changes = validation_result.get('file_changes', file_changes)
        changes_applied = []
        
        for change in final_changes:
            file_path = change['file_path']
            new_content = change['new_content']
            reason = change['reason']
            
            success = self.github_service.update_file(
                repo=repo,
                file_path=file_path,
                content=new_content,
                message=f"AI Fix: {reason}",
                branch=branch_name
            )
            
            if success:
                changes_applied.append({'file': file_path, 'reason': reason})
        
        if changes_applied:
            self.github_service.add_issue_comment(
                repo,
                pr_number,
                f"✅ **Changes Applied!**\n\nI've updated the branch `{branch_name}` based on your feedback.\n\n**Changes:**\n" + 
                "\n".join([f"- {c['file']}: {c['reason']}" for c in changes_applied])
            )
            return {
                'success': True,
                'changes_applied': changes_applied,
                'branch': branch_name
            }
        else:
             return {
                'success': False,
                'message': 'Failed to apply changes to GitHub'
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
        session = None
        
        try:
            for attempt in range(1, self.MAX_RETRIES + 1):
                logger.info("validation_attempt", attempt=attempt, max_retries=self.MAX_RETRIES)
                all_logs.append(f"=== Attempt {attempt}/{self.MAX_RETRIES} ===")
                
                result = self.code_execution.validate_changes(
                    repo_url=repo.clone_url,
                    branch=branch_name,
                    file_changes=current_changes,
                    run_tests=True,
                    run_build=True,
                    session=session,
                    keep_alive=True  # Keep container alive for retries or subsequent cleanup
                )
                
                # Update session for next iteration
                if result.session:
                    session = result.session
                    
                all_logs.extend(result.logs)
                
                if result.success:
                    logger.info("validation_succeeded", attempt=attempt)
                    # Use formatted file changes if available (from project formatters)
                    final_changes = current_changes
                    if result.formatted_file_changes:
                        logger.info("using_formatted_changes", count=len(result.formatted_file_changes))
                        final_changes = result.formatted_file_changes
                    return {
                        'success': True,
                        'file_changes': final_changes,
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
                error_context = "\n".join(result.logs[-50:])  # Last 50 log lines for better root cause analysis
                
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
            
        finally:
            # Always cleanup the session (stop container) when validation loop finishes
            if session:
                logger.info("cleaning_up_validation_session", session_id=session.id)
                self.code_execution.cleanup_session(session)
    
    def _is_documentation_only(self, file_changes):
        """
        Check if all file changes are documentation/non-code files.
        These don't need sandbox validation.
        
        Note: Config files that affect builds (tsconfig, eslint, Dockerfile) 
        REQUIRE validation even though they're not 'code'.
        """
        # Files that are pure documentation (never need validation)
        DOC_EXTENSIONS = {
            '.md', '.markdown', '.txt', '.rst', '.adoc',  # Documentation
            '.gitignore', '.gitattributes', '.editorconfig',  # Git/editor config
            '.env.example',  # Templates (not actual env)
        }
        
        # File names that are pure documentation
        DOC_FILES = {
            'LICENSE', 'README', 'CHANGELOG', 'CONTRIBUTING',
            'AUTHORS', 'CODEOWNERS', 'SECURITY', 'CODE_OF_CONDUCT'
        }
        
        # Config files that NEED validation (affect build/test)
        VALIDATION_REQUIRED_PATTERNS = {
            'tsconfig', 'jsconfig',  # TypeScript/JavaScript config
            'eslint', 'prettier', 'biome',  # Linter/formatter config
            'webpack', 'vite', 'rollup', 'esbuild',  # Bundler config  
            'jest', 'vitest', 'pytest', 'karma',  # Test config
            'babel', 'postcss', 'tailwind',  # Compiler/CSS config
            'package.json', 'package-lock.json', 'pnpm-lock.yaml', 'yarn.lock',  # Package files
            'requirements.txt', 'setup.py', 'pyproject.toml', 'poetry.lock',  # Python deps
            'go.mod', 'go.sum', 'cargo.toml', 'gemfile',  # Other langs
        }
        
        for change in file_changes:
            file_path = change.get('file_path', '') if isinstance(change, dict) else change.file_path
            file_path_lower = file_path.lower()
            file_name = file_path.split('/')[-1]
            file_name_lower = file_name.lower()
            file_ext = '.' + file_name.split('.')[-1].lower() if '.' in file_name else ''
            
            # GitHub workflows, Dockerfiles, Makefiles always need validation
            if '.github/' in file_path or file_name_lower in ('dockerfile', 'makefile', 'docker-compose.yml', 'docker-compose.yaml'):
                logger.debug("requires_validation", file=file_path, reason="workflow_or_docker")
                return False
            
            # Config files that affect builds need validation
            for pattern in VALIDATION_REQUIRED_PATTERNS:
                if pattern in file_name_lower:
                    logger.debug("requires_validation", file=file_path, reason=f"matches_pattern_{pattern}")
                    return False
            
            # Check if it's a known pure doc file or extension
            is_doc = (
                file_ext in DOC_EXTENSIONS or 
                file_name.upper() in DOC_FILES
            )
            
            if not is_doc:
                return False
        
        return True

