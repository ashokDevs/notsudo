"""
Tests for CodeExecutionService.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

from services.code_execution import CodeExecutionService, ExecutionResult, FileChange


class TestFileChange:
    def test_file_change_from_dict(self):
        """FileChange should work with dict input."""
        change = FileChange(
            file_path='src/main.py',
            new_content='print("hello")',
            reason='Add greeting'
        )
        assert change.file_path == 'src/main.py'


class TestExecutionResult:
    def test_add_log(self):
        """Should accumulate logs."""
        result = ExecutionResult(success=False, stage='init')
        result.add_log("Step 1")
        result.add_log("Step 2")
        
        assert len(result.logs) == 2
        assert "Step 1" in result.logs


class TestCodeExecutionService:
    def setup_method(self):
        self.service = CodeExecutionService()

    def test_init_with_custom_services(self):
        """Should accept custom stack detector and sandbox."""
        mock_detector = Mock()
        mock_sandbox = Mock()
        
        service = CodeExecutionService(
            stack_detector=mock_detector,
            docker_sandbox=mock_sandbox
        )
        
        assert service.stack_detector is mock_detector
        assert service.docker_sandbox is mock_sandbox

    def test_get_file_list(self, tmp_path):
        """Should list all files in repo."""
        # Create test structure
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print('hi')")
        (tmp_path / "requirements.txt").write_text("pytest")
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("git config")
        
        files = self.service._get_file_list(str(tmp_path))
        
        assert "src/main.py" in files
        assert "requirements.txt" in files
        # .git should be excluded
        assert ".git/config" not in files

    def test_apply_change_creates_file(self, tmp_path):
        """Should create file with content."""
        change = FileChange(
            file_path='new_file.py',
            new_content='print("created")',
            reason='test'
        )
        
        self.service._apply_change(str(tmp_path), change)
        
        assert (tmp_path / "new_file.py").exists()
        assert (tmp_path / "new_file.py").read_text() == 'print("created")'

    def test_apply_change_creates_directories(self, tmp_path):
        """Should create parent directories."""
        change = FileChange(
            file_path='deep/nested/dir/file.py',
            new_content='content',
            reason='test'
        )
        
        self.service._apply_change(str(tmp_path), change)
        
        assert (tmp_path / "deep" / "nested" / "dir" / "file.py").exists()

    @patch('services.code_execution.subprocess.run')
    def test_clone_repo_success(self, mock_run):
        """Should return success on successful clone."""
        mock_run.return_value = Mock(returncode=0, stdout='', stderr='')
        
        result = self.service._clone_repo(
            'https://github.com/test/repo.git',
            'main',
            '/tmp/test'
        )
        
        assert result.success
        assert result.exit_code == 0

    @patch('services.code_execution.subprocess.run')
    def test_clone_repo_failure(self, mock_run):
        """Should return failure on clone error."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout='',
            stderr='fatal: repository not found'
        )
        
        result = self.service._clone_repo(
            'https://github.com/test/nonexistent.git',
            'main',
            '/tmp/test'
        )
        
        assert not result.success
        assert 'repository not found' in result.stderr


class TestValidateChangesFlow:
    """Tests for the full validate_changes flow with mocked sandbox."""

    def test_validate_changes_full_flow_success(self, tmp_path):
        """Test successful validation with mocked Docker sandbox."""
        from services.code_execution import CodeExecutionService, FileChange
        from services.stack_detector import StackConfig
        
        # Create mock stack detector
        mock_detector = Mock()
        mock_config = StackConfig(
            stack_type='python',
            runtime='python:3.11-slim',
            package_manager='pip',
            install_command='pip install -r requirements.txt',
            test_command='pytest'
        )
        mock_detector.detect_from_file_list.return_value = mock_config
        
        # Create mock sandbox
        mock_sandbox = Mock()
        mock_sandbox.is_available.return_value = True
        mock_sandbox.resolve_image.return_value = 'python:3.11-slim'
        
        mock_container = Mock()
        mock_container.short_id = 'abc123'
        mock_sandbox.create_container.return_value = mock_container
        
        # Mock successful exec results
        mock_sandbox.exec_command.return_value = Mock(
            exit_code=0,
            success=True,
            stdout='All tests passed',
            stderr=''
        )
        
        service = CodeExecutionService(
            stack_detector=mock_detector,
            docker_sandbox=mock_sandbox
        )
        
        # Mock clone to succeed
        with patch.object(service, '_clone_repo') as mock_clone:
            mock_clone.return_value = Mock(success=True, exit_code=0, stderr='')
            
            with patch('services.code_execution.tempfile.mkdtemp') as mock_temp:
                mock_temp.return_value = str(tmp_path)
                
                with patch('services.code_execution.shutil.rmtree'):
                    result = service.validate_changes(
                        repo_url='https://github.com/test/repo.git',
                        branch='main',
                        file_changes=[{
                            'file_path': 'test.py',
                            'new_content': 'print("hello")',
                            'reason': 'test'
                        }],
                        run_tests=True
                    )
        
        assert result.success is True
        assert "All validations passed" in result.logs[-1]
        mock_sandbox.cleanup.assert_called_once()

    def test_validate_changes_docker_unavailable_falls_back_to_local(self, tmp_path):
        """Should fall back to local execution when Docker unavailable."""
        from services.code_execution import CodeExecutionService
        from services.stack_detector import StackConfig
        
        mock_detector = Mock()
        mock_config = StackConfig(
            stack_type='python',
            runtime='python:3.11-slim',
            package_manager='pip',
            install_command='pip install -r requirements.txt',
            test_command='pytest'
        )
        mock_detector.detect_from_file_list.return_value = mock_config
        
        # Sandbox is None (not available)
        service = CodeExecutionService(stack_detector=mock_detector)
        service.docker_sandbox = None
        
        with patch.object(service, '_clone_repo') as mock_clone:
            mock_clone.return_value = Mock(success=True, exit_code=0, stderr='')
            
            with patch('services.code_execution.tempfile.mkdtemp') as mock_temp:
                mock_temp.return_value = str(tmp_path)
                
                with patch('services.code_execution.subprocess.run') as mock_run:
                    mock_run.return_value = Mock(returncode=0, stdout='OK', stderr='')
                    
                    with patch('services.code_execution.shutil.rmtree'):
                        result = service.validate_changes(
                            repo_url='https://github.com/test/repo.git',
                            branch='main',
                            file_changes=[{
                                'file_path': 'test.py',
                                'new_content': 'code',
                                'reason': 'test'
                            }],
                            run_tests=True
                        )
        
        assert result.success is True
        assert any('Docker not available' in log for log in result.logs)

    def test_validate_changes_install_failure(self, tmp_path):
        """Should return failure when install fails."""
        from services.code_execution import CodeExecutionService
        from services.stack_detector import StackConfig
        
        mock_detector = Mock()
        mock_config = StackConfig(
            stack_type='nodejs',
            runtime='node:20-slim',
            package_manager='npm',
            install_command='npm install',
            test_command='npm test'
        )
        mock_detector.detect_from_file_list.return_value = mock_config
        
        mock_sandbox = Mock()
        mock_sandbox.is_available.return_value = True
        mock_sandbox.resolve_image.return_value = 'node:20-slim'
        
        mock_container = Mock()
        mock_container.short_id = 'abc123'
        mock_sandbox.create_container.return_value = mock_container
        
        # Install fails
        mock_sandbox.exec_command.return_value = Mock(
            exit_code=1,
            success=False,
            stdout='',
            stderr='npm ERR! Could not resolve dependency'
        )
        
        service = CodeExecutionService(
            stack_detector=mock_detector,
            docker_sandbox=mock_sandbox
        )
        
        with patch.object(service, '_clone_repo') as mock_clone:
            mock_clone.return_value = Mock(success=True, exit_code=0, stderr='')
            
            with patch('services.code_execution.tempfile.mkdtemp') as mock_temp:
                mock_temp.return_value = str(tmp_path)
                
                with patch('services.code_execution.shutil.rmtree'):
                    result = service.validate_changes(
                        repo_url='https://github.com/test/repo.git',
                        branch='main',
                        file_changes=[],
                        run_tests=True
                    )
        
        assert result.success is False
        assert result.stage == 'install'
        assert 'Install failed' in result.error

    def test_validate_changes_test_failure(self, tmp_path):
        """Should return failure with exit code when tests fail."""
        from services.code_execution import CodeExecutionService
        from services.stack_detector import StackConfig
        
        mock_detector = Mock()
        mock_config = StackConfig(
            stack_type='python',
            runtime='python:3.11-slim',
            package_manager='pip',
            install_command='pip install -r requirements.txt',
            test_command='pytest'
        )
        mock_detector.detect_from_file_list.return_value = mock_config
        
        mock_sandbox = Mock()
        mock_sandbox.is_available.return_value = True
        mock_sandbox.resolve_image.return_value = 'python:3.11-slim'
        
        mock_container = Mock()
        mock_container.short_id = 'abc123'
        mock_sandbox.create_container.return_value = mock_container
        
        # Install succeeds, tests fail
        def exec_side_effect(container, cmd, **kwargs):
            if 'install' in cmd:
                return Mock(exit_code=0, success=True, stdout='OK', stderr='')
            else:  # test command
                return Mock(exit_code=2, success=False, stdout='FAILED test_foo', stderr='')
        
        mock_sandbox.exec_command.side_effect = exec_side_effect
        
        service = CodeExecutionService(
            stack_detector=mock_detector,
            docker_sandbox=mock_sandbox
        )
        
        with patch.object(service, '_clone_repo') as mock_clone:
            mock_clone.return_value = Mock(success=True, exit_code=0, stderr='')
            
            with patch('services.code_execution.tempfile.mkdtemp') as mock_temp:
                mock_temp.return_value = str(tmp_path)
                
                with patch('services.code_execution.shutil.rmtree'):
                    result = service.validate_changes(
                        repo_url='https://github.com/test/repo.git',
                        branch='main',
                        file_changes=[],
                        run_tests=True
                    )
        
        assert result.success is False
        assert result.stage == 'test'
        assert result.exit_code == 2

    def test_validate_changes_stack_detection_failure(self, tmp_path):
        """Should return failure when stack cannot be detected."""
        from services.code_execution import CodeExecutionService
        
        mock_detector = Mock()
        mock_detector.detect_from_file_list.return_value = None  # Can't detect
        
        service = CodeExecutionService(stack_detector=mock_detector)
        
        with patch.object(service, '_clone_repo') as mock_clone:
            mock_clone.return_value = Mock(success=True, exit_code=0, stderr='')
            
            with patch('services.code_execution.tempfile.mkdtemp') as mock_temp:
                mock_temp.return_value = str(tmp_path)
                
                with patch('services.code_execution.shutil.rmtree'):
                    result = service.validate_changes(
                        repo_url='https://github.com/test/repo.git',
                        branch='main',
                        file_changes=[],
                        run_tests=True
                    )
        
        assert result.success is False
        assert 'Could not detect project stack' in result.error

    def test_validate_changes_image_build_fallback(self, tmp_path):
        """Should fall back to stack image when project image build fails."""
        from services.code_execution import CodeExecutionService
        from services.stack_detector import StackConfig
        
        mock_detector = Mock()
        mock_config = StackConfig(
            stack_type='python',
            runtime='python:3.11-slim',
            package_manager='pip',
            install_command='pip install -r requirements.txt',
            test_command='pytest',
            dockerfile_path='Dockerfile'  # Has Dockerfile
        )
        mock_detector.detect_from_file_list.return_value = mock_config
        
        mock_sandbox = Mock()
        mock_sandbox.is_available.return_value = True
        # Image build fails
        mock_sandbox.resolve_image.side_effect = Exception("Build failed")
        
        mock_container = Mock()
        mock_container.short_id = 'abc123'
        mock_sandbox.create_container.return_value = mock_container
        mock_sandbox.exec_command.return_value = Mock(
            exit_code=0, success=True, stdout='OK', stderr=''
        )
        
        service = CodeExecutionService(
            stack_detector=mock_detector,
            docker_sandbox=mock_sandbox
        )
        
        with patch.object(service, '_clone_repo') as mock_clone:
            mock_clone.return_value = Mock(success=True, exit_code=0, stderr='')
            
            with patch('services.code_execution.tempfile.mkdtemp') as mock_temp:
                mock_temp.return_value = str(tmp_path)
                
                with patch('services.code_execution.shutil.rmtree'):
                    result = service.validate_changes(
                        repo_url='https://github.com/test/repo.git',
                        branch='main',
                        file_changes=[],
                        run_tests=True
                    )
        
        # Should have fallen back to stack image
        assert any('Fallback to stack image' in log for log in result.logs)
        # Container should have been created with fallback image
        mock_sandbox.create_container.assert_called()


class TestRunLocally:
    """Tests for local execution fallback."""

    def test_run_locally_success(self, tmp_path):
        """Should run install and tests locally."""
        from services.code_execution import CodeExecutionService, ExecutionResult
        from services.stack_detector import StackConfig
        
        service = CodeExecutionService()
        
        config = StackConfig(
            stack_type='python',
            runtime='python:3.11-slim',
            package_manager='pip',
            install_command='pip install -r requirements.txt',
            test_command='pytest'
        )
        
        result = ExecutionResult(success=False, stage='local')
        
        with patch('services.code_execution.subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='OK', stderr='')
            
            final = service._run_locally(
                str(tmp_path), config, run_tests=True, run_build=False, result=result
            )
        
        assert final.success is True

    def test_run_locally_install_failure(self, tmp_path):
        """Should return failure when local install fails."""
        from services.code_execution import CodeExecutionService, ExecutionResult
        from services.stack_detector import StackConfig
        
        service = CodeExecutionService()
        
        config = StackConfig(
            stack_type='nodejs',
            runtime='node:20-slim',
            package_manager='npm',
            install_command='npm install',
            test_command='npm test'
        )
        
        result = ExecutionResult(success=False, stage='local')
        
        with patch('services.code_execution.subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout='', stderr='npm ERR!')
            
            final = service._run_locally(
                str(tmp_path), config, run_tests=True, run_build=False, result=result
            )
        
        assert final.success is False
        assert 'Install failed' in final.error

    def test_run_locally_timeout(self, tmp_path):
        """Should handle timeout in local execution."""
        from services.code_execution import CodeExecutionService, ExecutionResult
        from services.stack_detector import StackConfig
        import subprocess
        
        service = CodeExecutionService()
        
        config = StackConfig(
            stack_type='python',
            runtime='python:3.11-slim',
            package_manager='pip',
            install_command='pip install -r requirements.txt',
            test_command='pytest'
        )
        
        result = ExecutionResult(success=False, stage='local')
        
        with patch('services.code_execution.subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd='test', timeout=300)
            
            final = service._run_locally(
                str(tmp_path), config, run_tests=True, run_build=False, result=result
            )
        
        assert final.success is False
        assert 'timed out' in final.error
