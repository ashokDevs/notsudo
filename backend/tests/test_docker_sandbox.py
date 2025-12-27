"""
Integration tests for DockerSandboxService with REAL Docker.

These tests create actual containers in Docker Desktop!
Run with: DOCKER_HOST=unix://$HOME/.docker/run/docker.sock pytest tests/test_docker_sandbox.py -v -s

Requires:
- Docker Desktop running
- docker Python SDK installed (pip install docker)
"""
import pytest
import tempfile
import os
from pathlib import Path


# Skip all tests if Docker is not available
def docker_available():
    try:
        import docker
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


def ensure_image(client, image_name):
    """Pull an image if it doesn't exist locally."""
    try:
        client.images.get(image_name)
        print(f"  Image {image_name} already exists")
    except:
        print(f"  Pulling {image_name}...")
        client.images.pull(image_name)
        print(f"  ✓ Pulled {image_name}")


@pytest.fixture(scope="module")
def docker_client():
    """Get a Docker client and pull required images."""
    if not docker_available():
        pytest.skip("Docker not available")
    
    import docker
    client = docker.from_env()
    
    # Pull commonly used images
    print("\n--- Ensuring required Docker images ---")
    ensure_image(client, "alpine:latest")
    ensure_image(client, "python:3.11-slim")
    ensure_image(client, "node:20-slim")
    print("--- All images ready ---\n")
    
    return client


pytestmark = pytest.mark.skipif(
    not docker_available(),
    reason="Docker not available - start Docker Desktop to run these tests"
)


class TestDockerSandboxServiceReal:
    """Real Docker integration tests - creates actual containers!"""

    def test_is_available_with_real_docker(self, docker_client):
        """Verify Docker is actually running."""
        from services.docker_sandbox import DockerSandboxService
        
        service = DockerSandboxService()
        assert service.is_available() is True
        print("\n✓ Docker is available and responding!")

    def test_create_simple_container(self, docker_client):
        """Create a real container and verify it runs."""
        from services.docker_sandbox import DockerSandboxService
        
        service = DockerSandboxService()
        
        # Create a temp directory to mount
        with tempfile.TemporaryDirectory(prefix='docker-test-') as temp_dir:
            # Create a simple test file
            test_file = Path(temp_dir) / "hello.txt"
            test_file.write_text("Hello from test!")
            
            # Create container with alpine (small and fast)
            container = service.create_container(
                image='alpine:latest',
                repo_path=temp_dir,
                working_dir='/workspace'
            )
            
            try:
                print(f"\n✓ Created container: {container.short_id}")
                print(f"  Image: alpine:latest")
                print(f"  Mounted: {temp_dir} -> /workspace")
                
                # Verify container is running
                container.reload()
                assert container.status == 'running'
                print(f"  Status: {container.status}")
                
            finally:
                service.cleanup(container)
                print("✓ Container cleaned up")

    def test_exec_command_in_container(self, docker_client):
        """Execute real commands in a container."""
        from services.docker_sandbox import DockerSandboxService
        
        service = DockerSandboxService()
        
        with tempfile.TemporaryDirectory(prefix='docker-test-') as temp_dir:
            # Create a test Python file
            test_file = Path(temp_dir) / "test_script.py"
            test_file.write_text('print("Hello from inside Docker!")')
            
            container = service.create_container(
                image='python:3.11-slim',
                repo_path=temp_dir,
                working_dir='/workspace'
            )
            
            try:
                print(f"\n✓ Created Python container: {container.short_id}")
                
                # Run a simple echo command
                result = service.exec_command(container, "echo 'Testing exec!'")
                print(f"  Echo result: {result.stdout.strip()}")
                assert result.success
                assert 'Testing exec!' in result.stdout
                
                # List workspace contents
                result = service.exec_command(container, "ls -la /workspace")
                print(f"  Workspace contents:\n{result.stdout}")
                assert 'test_script.py' in result.stdout
                
                # Run the Python script
                result = service.exec_command(container, "python /workspace/test_script.py")
                print(f"  Python output: {result.stdout.strip()}")
                assert result.success
                assert 'Hello from inside Docker!' in result.stdout
                
            finally:
                service.cleanup(container)
                print("✓ Container cleaned up")

    def test_exec_command_failure(self, docker_client):
        """Test that failed commands return proper exit codes."""
        from services.docker_sandbox import DockerSandboxService
        
        service = DockerSandboxService()
        
        with tempfile.TemporaryDirectory(prefix='docker-test-') as temp_dir:
            container = service.create_container(
                image='alpine:latest',
                repo_path=temp_dir
            )
            
            try:
                print(f"\n✓ Created container: {container.short_id}")
                
                # Run a command that will fail
                result = service.exec_command(container, "exit 42")
                print(f"  Exit code: {result.exit_code}")
                assert result.exit_code == 42
                assert result.success is False
                
                # Try to run a non-existent command
                result = service.exec_command(container, "nonexistent_command_xyz")
                print(f"  Non-existent cmd exit code: {result.exit_code}")
                assert result.success is False
                
            finally:
                service.cleanup(container)
                print("✓ Container cleaned up")

    def test_python_dependency_install(self, docker_client):
        """Test installing Python dependencies in a container.
        
        Note: This test requires network access to download from PyPI.
        """
        from services.docker_sandbox import DockerSandboxService, SandboxConfig
        
        # Use config with network enabled for pip install
        config = SandboxConfig(network_disabled=False)
        service = DockerSandboxService(config=config)
        
        with tempfile.TemporaryDirectory(prefix='docker-test-') as temp_dir:
            # Create requirements.txt
            req_file = Path(temp_dir) / "requirements.txt"
            req_file.write_text("requests==2.31.0\n")
            
            container = service.create_container(
                image='python:3.11-slim',
                repo_path=temp_dir
            )
            
            try:
                print(f"\n✓ Created Python container: {container.short_id}")
                
                # Install dependencies
                print("  Installing requests...")
                result = service.exec_command(
                    container, 
                    "pip install -r /workspace/requirements.txt",
                    timeout=120
                )
                print(f"  Install output (truncated): {result.stdout[:200]}...")
                assert result.success, f"Install failed: {result.stderr}"
                
                # Verify it's installed
                result = service.exec_command(container, "python -c 'import requests; print(requests.__version__)'")
                print(f"  Requests version: {result.stdout.strip()}")
                assert '2.31.0' in result.stdout
                
            finally:
                service.cleanup(container)
                print("✓ Container cleaned up")

    def test_run_pytest_in_container(self, docker_client):
        """Actually run pytest inside a Docker container!
        
        Note: This test requires network access to download pytest from PyPI.
        """
        from services.docker_sandbox import DockerSandboxService, SandboxConfig
        
        # Use config with network enabled for pip install
        config = SandboxConfig(network_disabled=False)
        service = DockerSandboxService(config=config)
        
        with tempfile.TemporaryDirectory(prefix='docker-test-') as temp_dir:
            # Create a simple test file
            test_file = Path(temp_dir) / "test_example.py"
            test_file.write_text('''
def test_addition():
    assert 1 + 1 == 2

def test_string():
    assert "hello".upper() == "HELLO"

def test_list():
    items = [1, 2, 3]
    assert len(items) == 3
''')
            
            container = service.create_container(
                image='python:3.11-slim',
                repo_path=temp_dir
            )
            
            try:
                print(f"\n✓ Created Python container: {container.short_id}")
                
                # Install pytest
                print("  Installing pytest...")
                result = service.exec_command(container, "pip install pytest -q")
                assert result.success, f"Pytest install failed: {result.stderr}"
                
                # Run the tests!
                print("  Running pytest...")
                result = service.exec_command(container, "cd /workspace && pytest -v")
                print(f"\n  Pytest output:\n{result.stdout}")
                
                assert result.success
                assert '3 passed' in result.stdout
                
            finally:
                service.cleanup(container)
                print("✓ Container cleaned up")

    def test_nodejs_container(self, docker_client):
        """Test Node.js container with npm."""
        from services.docker_sandbox import DockerSandboxService
        
        service = DockerSandboxService()
        
        with tempfile.TemporaryDirectory(prefix='docker-test-') as temp_dir:
            # Create package.json
            package_json = Path(temp_dir) / "package.json"
            package_json.write_text('''{
  "name": "docker-test",
  "version": "1.0.0",
  "scripts": {
    "test": "node test.js"
  }
}
''')
            
            # Create test.js
            test_js = Path(temp_dir) / "test.js"
            test_js.write_text('console.log("Hello from Node.js in Docker!");')
            
            container = service.create_container(
                image='node:20-slim',
                repo_path=temp_dir
            )
            
            try:
                print(f"\n✓ Created Node.js container: {container.short_id}")
                
                # Check node version
                result = service.exec_command(container, "node --version")
                print(f"  Node version: {result.stdout.strip()}")
                
                # Run npm test
                result = service.exec_command(container, "cd /workspace && npm test")
                print(f"  npm test output: {result.stdout}")
                
                assert result.success
                assert 'Hello from Node.js in Docker!' in result.stdout
                
            finally:
                service.cleanup(container)
                print("✓ Container cleaned up")


class TestExecResultDataclass:
    """Tests for the ExecResult dataclass (no Docker needed)."""

    def test_success_property_true(self):
        """Should return True when exit_code is 0."""
        from services.docker_sandbox import ExecResult
        
        result = ExecResult(exit_code=0, stdout="output", stderr="")
        assert result.success is True

    def test_success_property_false(self):
        """Should return False when exit_code is non-zero."""
        from services.docker_sandbox import ExecResult
        
        result = ExecResult(exit_code=1, stdout="", stderr="error")
        assert result.success is False


class TestSandboxConfig:
    """Tests for SandboxConfig dataclass (no Docker needed)."""

    def test_default_config_values(self):
        """Should have sensible default config values."""
        from services.docker_sandbox import SandboxConfig
        
        config = SandboxConfig()
        
        assert config.memory_limit == "512m"
        assert config.cpu_period == 100000
        assert config.cpu_quota == 50000
        assert config.network_disabled is True
        assert config.timeout_seconds == 300

    def test_custom_config_values(self):
        """Should accept custom config values."""
        from services.docker_sandbox import SandboxConfig
        
        config = SandboxConfig(
            memory_limit="1g",
            cpu_quota=100000,
            network_disabled=False,
            timeout_seconds=600
        )
        
        assert config.memory_limit == "1g"
        assert config.cpu_quota == 100000
        assert config.network_disabled is False
        assert config.timeout_seconds == 600


class TestResolveImage:
    """Tests for image resolution logic."""

    @pytest.mark.skipif(not docker_available(), reason="Docker not available")
    def test_resolve_image_fallback_to_runtime(self):
        """Should use stack runtime when no Dockerfile."""
        from services.docker_sandbox import DockerSandboxService
        from services.stack_detector import StackConfig
        
        service = DockerSandboxService()
        
        stack_config = StackConfig(
            stack_type='python',
            runtime='python:3.11-slim',
            package_manager='pip',
            install_command='pip install -r requirements.txt',
            test_command='pytest',
            dockerfile_path=None  # No Dockerfile
        )
        
        result = service.resolve_image(stack_config, '/tmp/repo')
        assert result == 'python:3.11-slim'

    @pytest.mark.skipif(not docker_available(), reason="Docker not available")
    def test_resolve_image_with_dockerfile(self):
        """Should attempt to build from Dockerfile when available."""
        from services.docker_sandbox import DockerSandboxService
        from services.stack_detector import StackConfig
        
        service = DockerSandboxService()
        
        with tempfile.TemporaryDirectory(prefix='docker-test-') as temp_dir:
            # Create a simple Dockerfile
            dockerfile = Path(temp_dir) / "Dockerfile"
            dockerfile.write_text("""FROM alpine:latest
RUN echo "Hello from custom image"
""")
            
            stack_config = StackConfig(
                stack_type='python',
                runtime='python:3.11-slim',
                package_manager='pip',
                install_command='pip install -r requirements.txt',
                test_command='pytest',
                dockerfile_path='Dockerfile'
            )
            
            image_tag = service.resolve_image(stack_config, temp_dir)
            
            assert image_tag.startswith('sandbox-')
            print(f"\n✓ Built custom image: {image_tag}")
            
            # Cleanup the image
            service.cleanup_image(image_tag)
            print("✓ Cleaned up custom image")
