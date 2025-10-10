#!/bin/bash
set -e

# Setup logging
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
echo "Starting user data script at $(date)"

# Update system packages
echo "Updating system packages..."
yum update -y

# Install Docker
echo "Installing Docker..."
yum install -y docker
systemctl start docker
systemctl enable docker

# Add ec2-user to docker group
usermod -a -G docker ec2-user

# Install Docker Compose
echo "Installing Docker Compose..."
DOCKER_COMPOSE_VERSION="2.24.5"
curl -L "https://github.com/docker/compose/releases/download/v$${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

# Install AWS CLI v2
echo "Installing AWS CLI..."
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip -q awscliv2.zip
./aws/install
rm -rf awscliv2.zip aws

# Install CloudWatch Agent
echo "Installing CloudWatch Agent..."
yum install -y amazon-cloudwatch-agent

# Configure CloudWatch Agent
cat > /opt/aws/amazon-cloudwatch-agent/etc/config.json <<'EOF'
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/user-data.log",
            "log_group_name": "/aws/ec2/algoitny-api-${env_suffix}",
            "log_stream_name": "{instance_id}/user-data.log"
          },
          {
            "file_path": "/var/log/docker.log",
            "log_group_name": "/aws/ec2/algoitny-api-${env_suffix}",
            "log_stream_name": "{instance_id}/docker.log"
          }
        ]
      }
    }
  }
}
EOF

# Start CloudWatch Agent
systemctl enable amazon-cloudwatch-agent
systemctl start amazon-cloudwatch-agent

# Get AWS region
TOKEN=$(curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
AWS_REGION=$(curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/region)
INSTANCE_ID=$(curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)

echo "AWS Region: $AWS_REGION"
echo "Instance ID: $INSTANCE_ID"

# Fetch secrets from Secrets Manager
echo "Fetching secrets from Secrets Manager..."
SECRET_JSON=$(aws secretsmanager get-secret-value \
    --secret-id algoitny-secrets \
    --region $AWS_REGION \
    --query SecretString \
    --output text)

# Parse secrets
export SECRET_KEY=$(echo $SECRET_JSON | jq -r '.SECRET_KEY')
export GOOGLE_CLIENT_ID=$(echo $SECRET_JSON | jq -r '.GOOGLE_CLIENT_ID')
export GOOGLE_CLIENT_SECRET=$(echo $SECRET_JSON | jq -r '.GOOGLE_CLIENT_SECRET')
export GEMINI_API_KEY=$(echo $SECRET_JSON | jq -r '.GEMINI_API_KEY')
export OPENAI_API_KEY=$(echo $SECRET_JSON | jq -r '.OPENAI_API_KEY')
export ANTHROPIC_API_KEY=$(echo $SECRET_JSON | jq -r '.ANTHROPIC_API_KEY // ""')

# Get DynamoDB and ElastiCache endpoints from Tags or Parameter Store
DYNAMODB_TABLE="algoitny_main"
REDIS_HOST="${redis_host}"

# Login to ECR
echo "Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin ${ecr_repository_url}

# Pull Docker image
echo "Pulling Docker image..."
docker pull ${ecr_image_url}

# Create application directory
mkdir -p /app/logs
mkdir -p /app/tmp

# Run Docker container
echo "Starting API server container..."
docker run -d \
  --name algoitny-api \
  --restart unless-stopped \
  -p 8000:8000 \
  -v /app/logs:/app/logs \
  -v /app/tmp:/app/tmp \
  -e DEBUG=False \
  -e SECRET_KEY="$SECRET_KEY" \
  -e ALLOWED_HOSTS="${allowed_hosts}" \
  -e GOOGLE_CLIENT_ID="$GOOGLE_CLIENT_ID" \
  -e GOOGLE_CLIENT_SECRET="$GOOGLE_CLIENT_SECRET" \
  -e GEMINI_API_KEY="$GEMINI_API_KEY" \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  -e AWS_REGION="$AWS_REGION" \
  -e AWS_DEFAULT_REGION="$AWS_REGION" \
  -e USE_SECRETS_MANAGER=true \
  -e AWS_SECRET_NAME=algoitny-secrets \
  -e DYNAMODB_TABLE="$DYNAMODB_TABLE" \
  -e REDIS_HOST="$REDIS_HOST" \
  -e REDIS_PORT=6379 \
  -e GUNICORN_WORKERS="${gunicorn_workers}" \
  -e GUNICORN_LOG_LEVEL="info" \
  -e SERVICE_TYPE="api" \
  ${ecr_image_url}

# Configure Docker logs to CloudWatch
echo "Configuring Docker logs..."
docker logs -f algoitny-api >> /var/log/docker.log 2>&1 &

# Health check
echo "Waiting for application to start..."
sleep 30

for i in {1..30}; do
  if curl -f http://localhost:8000/api/health/ > /dev/null 2>&1; then
    echo "Application is healthy!"
    break
  fi
  echo "Waiting for application... ($i/30)"
  sleep 10
done

echo "User data script completed at $(date)"
