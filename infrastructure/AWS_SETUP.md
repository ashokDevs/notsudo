# AWS Setup Guide for ECS Fargate Sandbox

Complete step-by-step guide to set up ECR and ECS Fargate for running code validation.

## Prerequisites

1. Create an AWS account at https://aws.amazon.com/
2. Install AWS CLI: `brew install awscli`
3. Have Docker Desktop installed

---

## Step 1: Configure AWS CLI

```bash
# Configure with your credentials
aws configure

# You'll be prompted for:
# AWS Access Key ID: (from AWS Console → IAM → Users → Security credentials)
# AWS Secret Access Key: (same place)
# Default region: us-east-1
# Default output format: json
```

To get credentials:
1. Go to AWS Console → IAM → Users
2. Click "Create User" → Name it "notsudo-admin"
3. Attach policy: "AdministratorAccess" (for setup, we'll restrict later)
4. Go to Security Credentials → Create Access Key → CLI

---

## Step 2: Create ECR Repositories

```bash
# Set variables
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create repositories for sandbox images
aws ecr create-repository \
    --repository-name sandbox-python \
    --region $AWS_REGION

aws ecr create-repository \
    --repository-name sandbox-node \
    --region $AWS_REGION

echo "ECR Registry: $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
```

---

## Step 3: Build and Push Docker Images

```bash
cd backend/sandbox_dockerfiles

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin \
    $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build and push Python image
docker build -f python.Dockerfile -t sandbox-python:latest .
docker tag sandbox-python:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/sandbox-python:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/sandbox-python:latest

# Build and push Node.js image
docker build -f nodejs.Dockerfile -t sandbox-node:latest .
docker tag sandbox-node:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/sandbox-node:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/sandbox-node:latest

echo "✓ Images pushed to ECR"
```

---

## Step 4: Create S3 Bucket for Code Transfer

```bash
# Create bucket (name must be globally unique)
aws s3 mb s3://notsudo-sandbox-code-$AWS_ACCOUNT_ID --region $AWS_REGION

# Enable encryption
aws s3api put-bucket-encryption \
    --bucket notsudo-sandbox-code-$AWS_ACCOUNT_ID \
    --server-side-encryption-configuration '{
        "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
    }'

# Set lifecycle to auto-delete old files (cleanup after 1 day)
aws s3api put-bucket-lifecycle-configuration \
    --bucket notsudo-sandbox-code-$AWS_ACCOUNT_ID \
    --lifecycle-configuration '{
        "Rules": [{
            "ID": "DeleteOldCode",
            "Status": "Enabled",
            "Expiration": {"Days": 1},
            "Filter": {"Prefix": "jobs/"}
        }]
    }'
```

---

## Step 5: Create IAM Role for ECS Tasks

```bash
# Create trust policy file
cat > /tmp/ecs-trust-policy.json << 'EOF'
{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "ecs-tasks.amazonaws.com"},
        "Action": "sts:AssumeRole"
    }]
}
EOF

# Create the role
aws iam create-role \
    --role-name sandbox-task-role \
    --assume-role-policy-document file:///tmp/ecs-trust-policy.json

# Create policy for S3 and CloudWatch access
cat > /tmp/sandbox-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["s3:GetObject", "s3:ListBucket"],
            "Resource": [
                "arn:aws:s3:::notsudo-sandbox-code-$AWS_ACCOUNT_ID",
                "arn:aws:s3:::notsudo-sandbox-code-$AWS_ACCOUNT_ID/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
            "Resource": "arn:aws:logs:*:*:log-group:/ecs/sandbox:*"
        }
    ]
}
EOF

aws iam put-role-policy \
    --role-name sandbox-task-role \
    --policy-name sandbox-s3-logs \
    --policy-document file:///tmp/sandbox-policy.json

# Also attach the ECS task execution role policy
aws iam attach-role-policy \
    --role-name sandbox-task-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
```

---

## Step 6: Create ECS Cluster

```bash
# Create cluster
aws ecs create-cluster \
    --cluster-name sandbox-cluster \
    --capacity-providers FARGATE \
    --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1
```

---

## Step 7: Create CloudWatch Log Group

```bash
aws logs create-log-group \
    --log-group-name /ecs/sandbox \
    --region $AWS_REGION

# Set retention to 7 days to save costs
aws logs put-retention-policy \
    --log-group-name /ecs/sandbox \
    --retention-in-days 7
```

---

## Step 8: Get VPC and Subnet Info

```bash
# Get default VPC
VPC_ID=$(aws ec2 describe-vpcs \
    --filters "Name=isDefault,Values=true" \
    --query "Vpcs[0].VpcId" --output text)

# Get public subnets
SUBNET_IDS=$(aws ec2 describe-subnets \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query "Subnets[?MapPublicIpOnLaunch==\`true\`].SubnetId" \
    --output text | tr '\t' ',')

# Get or create security group
SG_ID=$(aws ec2 create-security-group \
    --group-name sandbox-sg \
    --description "Security group for sandbox tasks" \
    --vpc-id $VPC_ID \
    --query 'GroupId' --output text 2>/dev/null || \
    aws ec2 describe-security-groups \
        --filters "Name=group-name,Values=sandbox-sg" \
        --query "SecurityGroups[0].GroupId" --output text)

# Allow outbound internet access (for pip install)
aws ec2 authorize-security-group-egress \
    --group-id $SG_ID \
    --protocol all \
    --cidr 0.0.0.0/0 2>/dev/null || true

echo "VPC: $VPC_ID"
echo "Subnets: $SUBNET_IDS"
echo "Security Group: $SG_ID"
```

---

## Step 9: Create ECS Task Definition

```bash
# Get the role ARN
ROLE_ARN=$(aws iam get-role --role-name sandbox-task-role --query 'Role.Arn' --output text)

cat > /tmp/task-definition.json << EOF
{
    "family": "sandbox-task",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "256",
    "memory": "512",
    "executionRoleArn": "$ROLE_ARN",
    "taskRoleArn": "$ROLE_ARN",
    "containerDefinitions": [{
        "name": "sandbox",
        "image": "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/sandbox-python:latest",
        "essential": true,
        "logConfiguration": {
            "logDriver": "awslogs",
            "options": {
                "awslogs-group": "/ecs/sandbox",
                "awslogs-region": "$AWS_REGION",
                "awslogs-stream-prefix": "sandbox"
            }
        },
        "environment": [
            {"name": "AWS_REGION", "value": "$AWS_REGION"}
        ]
    }]
}
EOF

aws ecs register-task-definition --cli-input-json file:///tmp/task-definition.json
```

---

## Step 10: Create IAM User for Backend

```bash
# Create user for the backend app
aws iam create-user --user-name notsudo-backend

# Create policy for backend
cat > /tmp/backend-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["s3:PutObject", "s3:DeleteObject"],
            "Resource": "arn:aws:s3:::notsudo-sandbox-code-$AWS_ACCOUNT_ID/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ecs:RunTask",
                "ecs:DescribeTasks",
                "ecs:StopTask"
            ],
            "Resource": "*",
            "Condition": {
                "StringEquals": {"ecs:cluster": "arn:aws:ecs:$AWS_REGION:$AWS_ACCOUNT_ID:cluster/sandbox-cluster"}
            }
        },
        {
            "Effect": "Allow",
            "Action": ["iam:PassRole"],
            "Resource": "$ROLE_ARN"
        },
        {
            "Effect": "Allow",
            "Action": ["logs:GetLogEvents"],
            "Resource": "arn:aws:logs:$AWS_REGION:$AWS_ACCOUNT_ID:log-group:/ecs/sandbox:*"
        }
    ]
}
EOF

aws iam put-user-policy \
    --user-name notsudo-backend \
    --policy-name backend-sandbox-access \
    --policy-document file:///tmp/backend-policy.json

# Create access key
aws iam create-access-key --user-name notsudo-backend
# SAVE THE OUTPUT! You'll need these for Render
```

---

## Step 11: Set Environment Variables in Render

Add these to your Render backend service:

```
USE_AWS_SANDBOX=true
AWS_ACCESS_KEY_ID=<from step 10>
AWS_SECRET_ACCESS_KEY=<from step 10>
AWS_REGION=us-east-1
AWS_ECS_CLUSTER=sandbox-cluster
AWS_ECS_TASK_DEFINITION=sandbox-task
AWS_S3_BUCKET=notsudo-sandbox-code-<your-account-id>
AWS_ECR_REGISTRY=<your-account-id>.dkr.ecr.us-east-1.amazonaws.com
AWS_SUBNETS=<comma-separated subnet IDs from step 8>
AWS_SECURITY_GROUPS=<security group ID from step 8>
AWS_LOG_GROUP=/ecs/sandbox
```

---

## Quick Verification

```bash
# Test that everything is set up
aws ecs describe-clusters --clusters sandbox-cluster
aws ecr describe-repositories --repository-names sandbox-python
aws s3 ls s3://notsudo-sandbox-code-$AWS_ACCOUNT_ID/

echo "✓ AWS setup complete!"
```

---

## Cost Estimate

| Resource | Monthly Cost |
|----------|-------------|
| ECR Storage (500MB) | $0.05 |
| S3 (100MB) | $0.002 |
| CloudWatch Logs | $0.50 |
| Fargate (50 runs @ 2min) | $3.00 |
| **Total** | **~$4/month** |

---

## Cleanup (if needed)

```bash
# Delete everything (run in reverse order)
aws ecs delete-cluster --cluster sandbox-cluster
aws ecr delete-repository --repository-name sandbox-python --force
aws ecr delete-repository --repository-name sandbox-node --force
aws s3 rb s3://notsudo-sandbox-code-$AWS_ACCOUNT_ID --force
aws iam delete-user-policy --user-name notsudo-backend --policy-name backend-sandbox-access
aws iam delete-access-key --user-name notsudo-backend --access-key-id <key-id>
aws iam delete-user --user-name notsudo-backend
aws iam delete-role-policy --role-name sandbox-task-role --policy-name sandbox-s3-logs
aws iam detach-role-policy --role-name sandbox-task-role --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
aws iam delete-role --role-name sandbox-task-role
aws logs delete-log-group --log-group-name /ecs/sandbox
```
