"""
Code Execution Service - Orchestrates the full code validation flow.

Flow:
1. Clone repo into temp directory
2. Apply file changes from AI
3. Detect stack & resolve Docker image
4. Create container (local Docker or AWS Fargate)
5. Install dependencies
6. Run tests
7. Return result with logs

Sandbox modes:
- AWS Fargate (production): USE_AWS_SANDBOX=true
- Local Docker (development): Docker available
- Local fallback: No Docker available
"""
import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from services.stack_detector import StackDetectorService, StackConfig
from services.docker_sandbox import DockerSandboxService, ExecResult, DOCKER_AVAILABLE

# Check if AWS sandbox is available
try:
    from services.aws_sandbox import AWSSandboxService, BOTO3_AVAILABLE
except ImportError:
    BOTO3_AVAILABLE = False
    AWSSandboxService = None

logger = logging.getLogger(__name__)

# Environment variable to enable AWS sandbox
USE_AWS_SANDBOX = os.environ.get('USE_AWS_SANDBOX', 'false').lower() == 'true'


@dataclass
class ExecutionResult:
    """Result of the full code validation flow."""
    success: bool
    stage: str  # 'clone', 'install', 'test', 'build'
    logs: list[str] = field(default_factory=list)
    error: Optional[str] = None
    exit_code: int = 0
    
    def add_log(self, message: str):
        self.logs.append(message)


@dataclass
class FileChange:
    """Represents a file change to apply."""
    file_path: str
    new_content: str
    reason: str


class CodeExecutionService:
    """Orchestrates the full code validation flow.
    
    Supports three modes:
    1. AWS Fargate (production) - Set USE_AWS_SANDBOX=true
    2. Local Docker (development) - Docker Desktop running
    3. Local fallback - No Docker, runs commands directly
    """
    
    def __init__(
        self,
        stack_detector: Optional[StackDetectorService] = None,
        docker_sandbox: Optional[DockerSandboxService] = None,
        aws_sandbox: Optional["AWSSandboxService"] = None,
    ):
        self.stack_detector = stack_detector or StackDetectorService()
        self.docker_sandbox = docker_sandbox
        self.aws_sandbox = aws_sandbox
        self.use_aws = False
        
        # Check which sandbox to use
        if USE_AWS_SANDBOX and BOTO3_AVAILABLE:
            # Production: Use AWS Fargate
            if self.aws_sandbox is None:
                try:
                    self.aws_sandbox = AWSSandboxService()
                    if self.aws_sandbox.is_available():
                        self.use_aws = True
                        logger.info("Using AWS Fargate sandbox")
                    else:
                        logger.warning("AWS sandbox configured but not available")
                except Exception as e:
                    logger.warning(f"AWS sandbox not available: {e}")
        
        # Fallback to local Docker
        if not self.use_aws and self.docker_sandbox is None and DOCKER_AVAILABLE:
            try:
                self.docker_sandbox = DockerSandboxService()
                logger.info("Using local Docker sandbox")
            except Exception as e:
                logger.warning(f"Docker sandbox not available: {e}")
    
    def validate_changes(
        self,
        repo_url: str,
        branch: str,
        file_changes: list[dict],
        run_tests: bool = True,
        run_build: bool = False,
    ) -> ExecutionResult:
        """
        Validate code changes in a Docker sandbox.
        
        Args:
            repo_url: Git URL to clone
            branch: Branch name containing the changes
            file_changes: List of file changes to apply
            run_tests: Whether to run tests
            run_build: Whether to run build command
            
        Returns:
            ExecutionResult with success status and logs
        """
        result = ExecutionResult(success=False, stage='init')
        temp_dir = None
        container = None
        built_image = None
        
        try:
            # Step 1: Clone repository
            result.stage = 'clone'
            temp_dir = tempfile.mkdtemp(prefix='sandbox-')
            result.add_log(f"Created temp directory: {temp_dir}")
            
            clone_result = self._clone_repo(repo_url, branch, temp_dir)
            if not clone_result.success:
                result.error = f"Clone failed: {clone_result.stderr}"
                return result
            result.add_log("Repository cloned successfully")
            
            # Step 2: Apply file changes
            result.stage = 'apply'
            changes = [FileChange(**c) if isinstance(c, dict) else c for c in file_changes]
            for change in changes:
                self._apply_change(temp_dir, change)
                result.add_log(f"Applied change to {change.file_path}")
            
            # Step 3: Detect stack
            result.stage = 'detect'
            file_paths = self._get_file_list(temp_dir)
            stack_config = self.stack_detector.detect_from_file_list(file_paths)
            
            if stack_config is None:
                result.error = "Could not detect project stack"
                return result
            result.add_log(f"Detected stack: {stack_config.stack_type}")
            
            # Step 4: Choose execution mode
            if self.use_aws and self.aws_sandbox:
                # Production: Use AWS Fargate
                result.add_log("Using AWS Fargate sandbox")
                return self._run_in_aws(
                    temp_dir, file_changes, stack_config, run_tests, run_build, result
                )
            elif self.docker_sandbox is not None and self.docker_sandbox.is_available():
                # Development: Use local Docker
                result.add_log("Using local Docker sandbox")
                # Continue to Docker container flow below
            else:
                # Fallback: Run locally
                result.add_log("Docker not available, running locally")
                return self._run_locally(temp_dir, stack_config, run_tests, run_build, result)
            
            # Step 5: Resolve image and create container
            result.stage = 'container'
            try:
                image = self.docker_sandbox.resolve_image(stack_config, temp_dir)
                if stack_config.dockerfile_path:
                    built_image = image  # Track for cleanup
                result.add_log(f"Using image: {image}")
            except Exception as e:
                # Fallback to stack image if project image fails
                image = stack_config.runtime
                result.add_log(f"Fallback to stack image: {image}")
            
            container = self.docker_sandbox.create_container(image, temp_dir)
            result.add_log(f"Created container: {container.short_id}")
            
            # Step 6: Install dependencies (with network enabled temporarily)
            result.stage = 'install'
            install_result = self._run_install(container, stack_config, result)
            if not install_result.success:
                result.error = f"Install failed: {install_result.stderr}"
                return result
            
            # Step 7: Run tests
            if run_tests:
                result.stage = 'test'
                test_result = self._run_tests(container, stack_config, result)
                if not test_result.success:
                    result.error = f"Tests failed with exit code {test_result.exit_code}"
                    result.exit_code = test_result.exit_code
                    return result
            
            # Step 8: Run build (optional)
            if run_build and stack_config.build_command:
                result.stage = 'build'
                build_result = self._run_build(container, stack_config, result)
                if not build_result.success:
                    result.error = f"Build failed: {build_result.stderr}"
                    return result
            
            result.success = True
            result.add_log("All validations passed!")
            return result
            
        except Exception as e:
            logger.exception("Validation error")
            result.error = str(e)
            return result
            
        finally:
            # Cleanup
            if container and self.docker_sandbox:
                self.docker_sandbox.cleanup(container)
            if built_image and self.docker_sandbox:
                self.docker_sandbox.cleanup_image(built_image)
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _clone_repo(self, repo_url: str, branch: str, dest: str) -> ExecResult:
        """Clone the repository."""
        try:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", branch, repo_url, dest],
                capture_output=True,
                text=True,
                timeout=120,
            )
            return ExecResult(
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
            )
        except subprocess.TimeoutExpired:
            return ExecResult(exit_code=-1, stdout="", stderr="Clone timed out")
        except Exception as e:
            return ExecResult(exit_code=-1, stdout="", stderr=str(e))
    
    def _apply_change(self, repo_path: str, change: FileChange) -> None:
        """Apply a file change to the cloned repo."""
        file_path = Path(repo_path) / change.file_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(change.new_content, encoding='utf-8')
    
    def _get_file_list(self, repo_path: str) -> list[str]:
        """Get list of all files in the repo (relative paths)."""
        files = []
        for root, dirs, filenames in os.walk(repo_path):
            # Skip .git directory
            dirs[:] = [d for d in dirs if d != '.git']
            for filename in filenames:
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, repo_path)
                files.append(rel_path)
        return files
    
    def _run_install(
        self, 
        container, 
        stack_config: StackConfig, 
        result: ExecutionResult
    ) -> ExecResult:
        """Run dependency installation in container."""
        result.add_log(f"Installing dependencies: {stack_config.install_command}")
        exec_result = self.docker_sandbox.exec_command(
            container, 
            stack_config.install_command,
            timeout=300,  # 5 minutes for install
        )
        result.add_log(f"Install output:\n{exec_result.stdout[:1000]}")
        if exec_result.stderr:
            result.add_log(f"Install stderr:\n{exec_result.stderr[:500]}")
        return exec_result
    
    def _run_tests(
        self, 
        container, 
        stack_config: StackConfig, 
        result: ExecutionResult
    ) -> ExecResult:
        """Run tests in container."""
        result.add_log(f"Running tests: {stack_config.test_command}")
        exec_result = self.docker_sandbox.exec_command(
            container,
            stack_config.test_command,
            timeout=300,  # 5 minutes for tests
        )
        result.add_log(f"Test output:\n{exec_result.stdout}")
        if exec_result.stderr:
            result.add_log(f"Test stderr:\n{exec_result.stderr}")
        return exec_result
    
    def _run_build(
        self, 
        container, 
        stack_config: StackConfig, 
        result: ExecutionResult
    ) -> ExecResult:
        """Run build command in container."""
        result.add_log(f"Running build: {stack_config.build_command}")
        exec_result = self.docker_sandbox.exec_command(
            container,
            stack_config.build_command,
            timeout=300,
        )
        result.add_log(f"Build output:\n{exec_result.stdout[:1000]}")
        return exec_result
    
    def _run_locally(
        self,
        repo_path: str,
        stack_config: StackConfig,
        run_tests: bool,
        run_build: bool,
        result: ExecutionResult,
    ) -> ExecutionResult:
        """Fallback: run validation locally without Docker."""
        try:
            # Install
            result.stage = 'install'
            result.add_log(f"Running install locally: {stack_config.install_command}")
            install = subprocess.run(
                stack_config.install_command,
                shell=True,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=300,
            )
            if install.returncode != 0:
                result.error = f"Install failed: {install.stderr}"
                return result
            
            # Test
            if run_tests:
                result.stage = 'test'
                result.add_log(f"Running tests locally: {stack_config.test_command}")
                test = subprocess.run(
                    stack_config.test_command,
                    shell=True,
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                result.add_log(f"Test output:\n{test.stdout}")
                if test.returncode != 0:
                    result.error = f"Tests failed: {test.stderr}"
                    result.exit_code = test.returncode
                    return result
            
            result.success = True
            return result
            
        except subprocess.TimeoutExpired:
            result.error = "Command timed out"
            return result
        except Exception as e:
            result.error = str(e)
            return result
    
    def _run_in_aws(
        self,
        repo_path: str,
        file_changes: list[dict],
        stack_config: StackConfig,
        run_tests: bool,
        run_build: bool,
        result: ExecutionResult,
    ) -> ExecutionResult:
        """Run validation in AWS ECS Fargate container."""
        result.stage = 'aws_fargate'
        
        try:
            # Prepare code files for upload
            code_files = []
            for root, dirs, files in os.walk(repo_path):
                dirs[:] = [d for d in dirs if d != '.git']
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, repo_path)
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        code_files.append({'path': rel_path, 'content': content})
                    except (UnicodeDecodeError, IOError):
                        # Skip binary files
                        pass
            
            result.add_log(f"Uploading {len(code_files)} files to AWS")
            
            # Determine test command
            test_command = stack_config.test_command if run_tests else "echo 'Skipping tests'"
            if run_build and stack_config.build_command:
                test_command = f"{test_command} && {stack_config.build_command}"
            
            # Run in Fargate
            fargate_result = self.aws_sandbox.run_validation(
                code_files=code_files,
                stack_type=stack_config.stack_type,
                install_command=stack_config.install_command,
                test_command=test_command,
            )
            
            # Map Fargate result to ExecutionResult
            result.add_log(f"AWS task completed in {fargate_result.duration_seconds:.1f}s")
            result.add_log(f"Exit code: {fargate_result.exit_code}")
            result.add_log(f"Output:\n{fargate_result.stdout}")
            
            if fargate_result.stderr:
                result.add_log(f"Errors:\n{fargate_result.stderr}")
            
            result.success = fargate_result.success
            result.exit_code = fargate_result.exit_code
            
            if not fargate_result.success:
                result.error = f"Tests failed with exit code {fargate_result.exit_code}"
            
            return result
            
        except TimeoutError as e:
            result.error = str(e)
            return result
        except Exception as e:
            result.error = f"AWS execution failed: {str(e)}"
            return result
