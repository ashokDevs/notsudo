"""
AWS ECS Fargate Sandbox Service - Run code validation in isolated AWS containers.

This service:
1. Uploads code to S3
2. Starts an ECS Fargate task
3. Waits for completion (with timeout)
4. Fetches logs from CloudWatch
5. Returns results

The Fargate task automatically stops when the container exits.
"""
import json
import os
import time
import zipfile
import tempfile
import uuid
from dataclasses import dataclass, field
from typing import Optional
from io import BytesIO

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AWSConfig:
    """Configuration for AWS sandbox."""
    region: str = "us-east-1"
    ecs_cluster: str = "sandbox-cluster"
    task_definition: str = "sandbox-task"
    s3_bucket: str = "notsudo-sandbox-code"
    ecr_registry: str = ""
    subnets: list = field(default_factory=list)
    security_groups: list = field(default_factory=list)
    log_group: str = "/ecs/sandbox"
    task_timeout: int = 300  # 5 minutes
    
    @classmethod
    def from_env(cls) -> "AWSConfig":
        """Load config from environment variables."""
        return cls(
            region=os.environ.get("AWS_REGION", "us-east-1"),
            ecs_cluster=os.environ.get("AWS_ECS_CLUSTER", "sandbox-cluster"),
            task_definition=os.environ.get("AWS_ECS_TASK_DEFINITION", "sandbox-task"),
            s3_bucket=os.environ.get("AWS_S3_BUCKET", "notsudo-sandbox-code"),
            ecr_registry=os.environ.get("AWS_ECR_REGISTRY", ""),
            subnets=os.environ.get("AWS_SUBNETS", "").split(",") if os.environ.get("AWS_SUBNETS") else [],
            security_groups=os.environ.get("AWS_SECURITY_GROUPS", "").split(",") if os.environ.get("AWS_SECURITY_GROUPS") else [],
            log_group=os.environ.get("AWS_LOG_GROUP", "/ecs/sandbox"),
            task_timeout=int(os.environ.get("AWS_TASK_TIMEOUT", "300")),
        )


@dataclass
class FargateResult:
    """Result of a Fargate task execution."""
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    task_arn: Optional[str] = None
    duration_seconds: float = 0.0
    
    @property
    def logs(self) -> str:
        return self.stdout + self.stderr
    
    @property
    def estimated_cost_usd(self) -> float:
        """
        Estimate AWS cost for this task execution.
        
        Pricing (us-east-1, as of 2024):
        - Fargate vCPU: $0.04048 per vCPU-hour
        - Fargate Memory: $0.004445 per GB-hour
        - S3 PUT/GET: ~$0.000005 per request
        - CloudWatch Logs: $0.50 per GB ingested
        
        For our config (0.25 vCPU, 512MB):
        - vCPU cost: 0.25 * $0.04048/hr = $0.01012/hr = $0.0000028/sec
        - Memory cost: 0.5GB * $0.004445/hr = $0.0022/hr = $0.0000006/sec
        - Total Fargate: ~$0.0000034/sec
        """
        # Fargate compute cost per second (0.25 vCPU, 0.5GB)
        fargate_per_second = 0.0000034
        fargate_cost = self.duration_seconds * fargate_per_second
        
        # S3: 2 requests (upload + download) + negligible storage
        s3_cost = 0.00001
        
        # CloudWatch: ~1KB logs, negligible
        cloudwatch_cost = 0.000001
        
        total = fargate_cost + s3_cost + cloudwatch_cost
        return round(total, 6)


class AWSSandboxService:
    """
    Run code validation in AWS ECS Fargate containers.
    
    Usage:
        service = AWSSandboxService()
        result = service.run_validation(
            code_files=[{'path': 'main.py', 'content': 'print("hi")'}],
            stack_type='python',
            install_command='pip install -r requirements.txt',
            test_command='pytest',
        )
    """
    
    # Map stack types to ECR image names
    STACK_IMAGES = {
        'python': 'sandbox-python:latest',
        'nodejs': 'sandbox-node:latest',
    }
    
    def __init__(self, config: Optional[AWSConfig] = None):
        if not BOTO3_AVAILABLE:
            raise RuntimeError("boto3 not available. Install with: pip install boto3")
        
        self.config = config or AWSConfig.from_env()
        
        # Initialize AWS clients
        self.s3 = boto3.client('s3', region_name=self.config.region)
        self.ecs = boto3.client('ecs', region_name=self.config.region)
        self.logs = boto3.client('logs', region_name=self.config.region)
        
        logger.info(
            "aws_sandbox_initialized",
            region=self.config.region,
            cluster=self.config.ecs_cluster,
            bucket=self.config.s3_bucket,
        )
    
    def is_available(self) -> bool:
        """Check if AWS services are accessible."""
        try:
            self.s3.head_bucket(Bucket=self.config.s3_bucket)
            self.ecs.describe_clusters(clusters=[self.config.ecs_cluster])
            return True
        except Exception as e:
            logger.warning("aws_not_available", error=str(e))
            return False
    
    def run_validation(
        self,
        code_files: list[dict],
        stack_type: str,
        install_command: str,
        test_command: str,
    ) -> FargateResult:
        """
        Run code validation in an ECS Fargate container.
        
        Args:
            code_files: List of {'path': str, 'content': str} dicts
            stack_type: 'python' or 'nodejs'
            install_command: Command to install dependencies
            test_command: Command to run tests
            
        Returns:
            FargateResult with success status and logs
        """
        job_id = str(uuid.uuid4())[:8]
        s3_key = f"jobs/{job_id}/code.zip"
        start_time = time.time()
        
        logger.info(
            "starting_validation",
            job_id=job_id,
            stack_type=stack_type,
            file_count=len(code_files),
        )
        
        try:
            # Step 1: Upload code to S3
            self._upload_code_to_s3(code_files, s3_key)
            logger.info("code_uploaded", job_id=job_id, s3_key=s3_key)
            
            # Step 2: Start Fargate task
            task_arn = self._run_fargate_task(
                job_id=job_id,
                s3_key=s3_key,
                stack_type=stack_type,
                install_command=install_command,
                test_command=test_command,
            )
            logger.info("task_started", job_id=job_id, task_arn=task_arn)
            
            # Step 3: Wait for completion
            exit_code = self._wait_for_completion(task_arn)
            logger.info("task_completed", job_id=job_id, exit_code=exit_code)
            
            # Step 4: Fetch logs
            stdout, stderr = self._get_task_logs(task_arn)
            
            duration = time.time() - start_time
            
            result = FargateResult(
                success=exit_code == 0,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                task_arn=task_arn,
                duration_seconds=duration,
            )
            
            # Log cost estimate
            logger.info(
                "sandbox_cost_estimate",
                job_id=job_id,
                duration_seconds=round(duration, 2),
                estimated_cost_usd=result.estimated_cost_usd,
                success=result.success,
            )
            
            return result
            
        except Exception as e:
            logger.error("validation_failed", job_id=job_id, error=str(e))
            return FargateResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"AWS Sandbox error: {str(e)}",
            )
            
        finally:
            # Cleanup: delete code from S3
            self._cleanup_s3(s3_key)
    
    def _upload_code_to_s3(self, code_files: list[dict], s3_key: str) -> None:
        """Zip code files and upload to S3."""
        # Create zip in memory
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file in code_files:
                zf.writestr(file['path'], file['content'])
        
        zip_buffer.seek(0)
        
        self.s3.upload_fileobj(
            zip_buffer,
            self.config.s3_bucket,
            s3_key,
        )
    
    def _run_fargate_task(
        self,
        job_id: str,
        s3_key: str,
        stack_type: str,
        install_command: str,
        test_command: str,
    ) -> str:
        """Start an ECS Fargate task and return the task ARN."""
        
        # Get the image for this stack type
        image = self.STACK_IMAGES.get(stack_type, self.STACK_IMAGES['python'])
        if self.config.ecr_registry:
            image = f"{self.config.ecr_registry}/{image}"
        
        # Environment variables for the container
        env_vars = [
            {"name": "JOB_ID", "value": job_id},
            {"name": "S3_BUCKET", "value": self.config.s3_bucket},
            {"name": "S3_KEY", "value": s3_key},
            {"name": "INSTALL_COMMAND", "value": install_command},
            {"name": "TEST_COMMAND", "value": test_command},
        ]
        
        # Run the task
        response = self.ecs.run_task(
            cluster=self.config.ecs_cluster,
            taskDefinition=self.config.task_definition,
            launchType='FARGATE',
            networkConfiguration={
                'awsvpcConfiguration': {
                    'subnets': self.config.subnets,
                    'securityGroups': self.config.security_groups,
                    'assignPublicIp': 'ENABLED',
                }
            },
            overrides={
                'containerOverrides': [{
                    'name': 'sandbox',
                    'environment': env_vars,
                }]
            },
            count=1,
        )
        
        if not response['tasks']:
            failures = response.get('failures', [])
            raise RuntimeError(f"Failed to start task: {failures}")
        
        return response['tasks'][0]['taskArn']
    
    def _wait_for_completion(self, task_arn: str) -> int:
        """Wait for task to complete and return exit code."""
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            if elapsed > self.config.task_timeout:
                # Stop the task if it times out
                self._stop_task(task_arn, "Timeout")
                raise TimeoutError(f"Task timed out after {self.config.task_timeout}s")
            
            response = self.ecs.describe_tasks(
                cluster=self.config.ecs_cluster,
                tasks=[task_arn],
            )
            
            if not response['tasks']:
                raise RuntimeError("Task not found")
            
            task = response['tasks'][0]
            status = task['lastStatus']
            
            if status == 'STOPPED':
                # Get exit code from container
                containers = task.get('containers', [])
                if containers:
                    exit_code = containers[0].get('exitCode', -1)
                    return exit_code if exit_code is not None else -1
                return -1
            
            # Still running, wait and poll again
            time.sleep(5)
    
    def _stop_task(self, task_arn: str, reason: str) -> None:
        """Stop a running task."""
        try:
            self.ecs.stop_task(
                cluster=self.config.ecs_cluster,
                task=task_arn,
                reason=reason,
            )
            logger.info("task_stopped", task_arn=task_arn, reason=reason)
        except Exception as e:
            logger.warning("failed_to_stop_task", task_arn=task_arn, error=str(e))
    
    def _get_task_logs(self, task_arn: str) -> tuple[str, str]:
        """Fetch logs from CloudWatch for a completed task."""
        # Extract task ID from ARN: arn:aws:ecs:region:account:task/cluster/task-id
        task_id = task_arn.split('/')[-1]
        # ECS log stream format: {prefix}/{container-name}/{task-id}
        log_stream_name = f"sandbox/sandbox/{task_id}"
        
        try:
            response = self.logs.get_log_events(
                logGroupName=self.config.log_group,
                logStreamName=log_stream_name,
                startFromHead=True,
            )
            
            stdout_lines = []
            stderr_lines = []
            
            for event in response.get('events', []):
                message = event.get('message', '')
                # Simple heuristic: lines with ERROR or WARN go to stderr
                if 'ERROR' in message or 'FAIL' in message or 'WARN' in message:
                    stderr_lines.append(message)
                else:
                    stdout_lines.append(message)
            
            return '\n'.join(stdout_lines), '\n'.join(stderr_lines)
            
        except self.logs.exceptions.ResourceNotFoundException:
            logger.warning("log_stream_not_found", task_id=task_id, log_stream=log_stream_name)
            return "", "Log stream not found"
        except Exception as e:
            logger.warning("failed_to_get_logs", task_id=task_id, error=str(e))
            return "", f"Failed to get logs: {str(e)}"
    
    def _cleanup_s3(self, s3_key: str) -> None:
        """Delete code files from S3."""
        try:
            self.s3.delete_object(
                Bucket=self.config.s3_bucket,
                Key=s3_key,
            )
            logger.info("s3_cleanup_complete", s3_key=s3_key)
        except Exception as e:
            logger.warning("s3_cleanup_failed", s3_key=s3_key, error=str(e))
