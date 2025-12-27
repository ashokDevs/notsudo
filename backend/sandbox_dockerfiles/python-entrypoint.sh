#!/bin/bash
# Python Sandbox Entrypoint for AWS ECS Fargate
# This script runs inside the container

set -e

echo "=== Python Sandbox Starting ==="
echo "Job ID: $JOB_ID"
echo "S3 Bucket: $S3_BUCKET"
echo "S3 Key: $S3_KEY"

# Step 1: Download code from S3
echo "=== Downloading code from S3 ==="
aws s3 cp "s3://$S3_BUCKET/$S3_KEY" /tmp/code.zip
unzip -o /tmp/code.zip -d /workspace
rm /tmp/code.zip

echo "=== Code contents ==="
ls -la /workspace

# Step 2: Install dependencies
echo "=== Installing dependencies ==="
echo "Running: $INSTALL_COMMAND"
cd /workspace

# Run install command (don't fail on install errors, let tests catch it)
eval "$INSTALL_COMMAND" 2>&1 || echo "WARNING: Install command had issues"

# Step 3: Run tests
echo "=== Running tests ==="
echo "Running: $TEST_COMMAND"
eval "$TEST_COMMAND" 2>&1
TEST_EXIT_CODE=$?

echo "=== Tests completed with exit code: $TEST_EXIT_CODE ==="

# Exit with test result
exit $TEST_EXIT_CODE
