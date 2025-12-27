# Python Sandbox Dockerfile for AWS ECS Fargate
# Builds an image that:
# 1. Downloads code from S3
# 2. Installs dependencies
# 3. Runs tests
# 4. Exits with test result code

FROM python:3.11-slim

WORKDIR /workspace

# Install AWS CLI and common Python development tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    unzip \
    && curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install \
    && rm -rf awscliv2.zip aws \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install common Python test tools
RUN pip install --no-cache-dir \
    pytest \
    pytest-cov \
    black \
    flake8 \
    mypy

# Copy entrypoint script
COPY python-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Environment variables (overridden at runtime)
ENV JOB_ID=""
ENV S3_BUCKET=""
ENV S3_KEY=""
ENV INSTALL_COMMAND="pip install -r requirements.txt"
ENV TEST_COMMAND="pytest"

ENTRYPOINT ["/entrypoint.sh"]
