
import sys
import os
import logging

# Add backend to path so we can import services
sys.path.append(os.path.join(os.getcwd(), 'backend'))

try:
    from services.docker_sandbox import DockerSandboxService, DOCKER_AVAILABLE
    import docker
except ImportError as e:
    # If docker is not installed, it will raise ImportError (or ModuleNotFoundError)
    # But DOCKER_AVAILABLE might be False even if import succeeds if inside DockerSandboxService logic changes
    print(f"❌ Could not import DockerSandboxService or docker: {e}")
    print("Make sure you are running this from the project root.")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DockerVerification")

def verify_docker():
    print("🔍 Verifying Docker Configuration...\n")

    # 1. Check if docker python package is installed (checked by import)
    if not DOCKER_AVAILABLE:
        print("❌ Docker Python SDK is NOT installed.")
        print("   Run: pip install docker")
        return

    print("✅ Docker Python SDK is installed.")

    # 2. Check if DockerSandboxService can connect to Docker Daemon
    try:
        # Debug: Print env vars
        print(f"   DOCKER_HOST: {os.environ.get('DOCKER_HOST', 'Not Set')}")
        print(f"   DOCKER_CERT_PATH: {os.environ.get('DOCKER_CERT_PATH', 'Not Set')}")
        print(f"   DOCKER_TLS_VERIFY: {os.environ.get('DOCKER_TLS_VERIFY', 'Not Set')}")

        try:
            client = docker.from_env()
            client.ping()
            print("✅ Docker Daemon is running and accessible (via docker.from_env).")
            sandbox = DockerSandboxService()
        except Exception as e:
            print(f"❌ docker.from_env() failed: {e}")
            print(f"   Attempting explicit socket connection...")
            try:
                client = docker.DockerClient(base_url='unix://var/run/docker.sock')
                client.ping()
                print("✅ Docker Daemon is accessible via unix://var/run/docker.sock")
            except Exception as e2:
                print(f"❌ Explicit socket connection failed: {e2}")
                sandbox = None

        if sandbox or (client and client.ping()):
             # Get some info
            version = client.version()
            print(f"   Docker Version: {version.get('Version', 'Unknown')}")
            print(f"   Platform: {version.get('Platform', {}).get('Name', 'Unknown')}")
        else:
            print("❌ Docker Daemon is NOT accessible.")
    
    except Exception as e:
        print(f"❌ Error initializing DockerSandboxService: {e}")

    # 3. Check Environment Variables impacting CodeExecutionService
    print("\n🔍 Checking Environment Configuration for Code Execution:")
    
    use_aws = os.environ.get('USE_AWS_SANDBOX', 'false').lower() == 'true'
    dev_mode = os.environ.get('DEV_MODE', 'false').lower() == 'true'
    
    print(f"   USE_AWS_SANDBOX: {use_aws}")
    print(f"   DEV_MODE: {dev_mode}")
    
    if dev_mode:
        print("\nℹ️  DEV_MODE is enabled. CodeExecutionService will prioritize Local Docker.")
    elif use_aws:
        print("\nℹ️  USE_AWS_SANDBOX is enabled. CodeExecutionService will try AWS Fargate first.")
    else:
        print("\nℹ️  Default mode. CodeExecutionService will try Local Docker first, then fallback to local execution.")

if __name__ == "__main__":
    verify_docker()
