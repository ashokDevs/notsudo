# Node.js Sandbox Dockerfile for AWS ECS Fargate
# Builds an image that:
# 1. Downloads code from S3
# 2. Installs dependencies
# 3. Runs tests
# 4. Exits with test result code

FROM node:20-slim

WORKDIR /workspace

# Install AWS CLI and utilities (platform-aware)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    unzip \
    ca-certificates \
    && ARCH=$(dpkg --print-architecture) \
    && if [ "$ARCH" = "amd64" ]; then \
         curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"; \
       else \
         curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"; \
       fi \
    && unzip awscliv2.zip \
    && ./aws/install \
    && rm -rf awscliv2.zip aws \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install pnpm (yarn already included in node:20-slim)
RUN npm install -g pnpm

# Copy entrypoint script
COPY node-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Environment variables (overridden at runtime)
ENV JOB_ID=""
ENV S3_BUCKET=""
ENV S3_KEY=""
ENV INSTALL_COMMAND="npm install"
ENV TEST_COMMAND="npm test"

ENTRYPOINT ["/entrypoint.sh"]
