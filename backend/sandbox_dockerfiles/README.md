# Sandbox Dockerfiles for AWS ECS Fargate

Pre-built Docker images for running code validation in isolated containers.

## Images

| Image | Base | Purpose |
|-------|------|---------|
| `sandbox-python` | python:3.11-slim | Python projects |
| `sandbox-node` | node:20-slim | Node.js projects |

## How It Works

1. Backend uploads code to S3 as a zip file
2. ECS Fargate starts a container from these images
3. Entrypoint script downloads code from S3
4. Runs install + test commands
5. Container exits with test result code
6. Backend fetches logs from CloudWatch

## Building & Pushing to ECR

```bash
# Set your AWS account ID and region
export AWS_ACCOUNT_ID=123456789012
export AWS_REGION=us-east-1
export ECR_REGISTRY=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

# Create repositories (one-time)
aws ecr create-repository --repository-name sandbox-python --region $AWS_REGION
aws ecr create-repository --repository-name sandbox-node --region $AWS_REGION

# Build Python image
docker build -f python.Dockerfile -t sandbox-python:latest .
docker tag sandbox-python:latest $ECR_REGISTRY/sandbox-python:latest
docker push $ECR_REGISTRY/sandbox-python:latest

# Build Node.js image
docker build -f nodejs.Dockerfile -t sandbox-node:latest .
docker tag sandbox-node:latest $ECR_REGISTRY/sandbox-node:latest
docker push $ECR_REGISTRY/sandbox-node:latest
```

## Environment Variables (set at runtime)

| Variable | Description |
|----------|-------------|
| `JOB_ID` | Unique job identifier |
| `S3_BUCKET` | S3 bucket containing code |
| `S3_KEY` | S3 key for code.zip |
| `INSTALL_COMMAND` | Command to install deps |
| `TEST_COMMAND` | Command to run tests |

## Local Testing

```bash
# Build the image
docker build -f python.Dockerfile -t sandbox-python:latest .

# Test locally (mock S3 with local file)
docker run --rm \
  -e JOB_ID=test123 \
  -e S3_BUCKET=test \
  -e S3_KEY=test/code.zip \
  -e INSTALL_COMMAND="pip install pytest" \
  -e TEST_COMMAND="pytest --version" \
  sandbox-python:latest
```
