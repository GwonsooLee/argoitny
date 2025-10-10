#!/bin/bash
set -e

# Setup logging
exec > >(tee /var/log/user-data.log) 2>&1
echo "Starting user data script at $(date)"

# Update system packages
echo "Updating system packages..."
yum update -y

# Install Docker and required tools
echo "Installing Docker and required tools..."
yum install -y docker jq unzip
systemctl start docker
systemctl enable docker

# Add ec2-user to docker group
usermod -a -G docker ec2-user

# Install AWS CLI v2 (ARM64 version)
echo "Installing AWS CLI for ARM64..."
curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"
unzip -q awscliv2.zip
./aws/install
rm -rf awscliv2.zip aws

# Get AWS region and instance metadata
TOKEN=$(curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
AWS_REGION=$(curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/region)
INSTANCE_ID=$(curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)

echo "AWS Region: $AWS_REGION"
echo "Instance ID: $INSTANCE_ID"
echo "Architecture: ARM64 (aarch64)"

# Get DynamoDB endpoint
DYNAMODB_TABLE="algoitny_main"

# Login to ECR
echo "Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin ${ecr_repository_url}

# Pull Docker image (ARM64 compatible)
echo "Pulling Docker image for ARM64..."
docker pull ${ecr_image_url}

# Create application directory
mkdir -p /var/log/algoitny
mkdir -p /app/tmp
mkdir -p /app/config

# Set proper permissions for log directory
chmod 777 /var/log/algoitny

# Create config.yaml for Django
cat > /app/config/config.yaml <<'CONFIGEOF'
# AlgoItny Production Configuration
django:
  debug: false
  allowed_hosts:
    - "api.testcase.run"
    - "*.testcase.run"
  timezone: "UTC"
  language_code: "en-us"

cache:
  enable_redis: false
  key_prefix: "algoitny"
  default_timeout: 300
  ttl:
    problem_list: 300
    problem_detail: 600
    user_stats: 180
    search_history: 120
    test_cases: 900
    short: 60
    medium: 300
    long: 1800

celery:
  result_backend: "django-db"
  task_time_limit: 1800
  task_soft_time_limit: 1680
  task_acks_late: false
  task_reject_on_worker_lost: true
  worker_prefetch_multiplier: 1
  worker_max_tasks_per_child: 1000
  broker_connection_retry: true
  broker_connection_retry_on_startup: true
  broker_connection_max_retries: 10
  broker_pool_limit: 10
  result_expires: 86400
  result_compression: "gzip"
  task_queue_max_priority: 10
  task_default_priority: 5

google_oauth:
  redirect_uri: "https://api.testcase.run/auth/callback"

cors:
  allowed_origins:
    - "https://testcase.run"
    - "https://www.testcase.run"
  allow_credentials: true

security:
  csrf_trusted_origins:
    - "https://api.testcase.run"
    - "https://testcase.run"
  secure_ssl_redirect: false
  secure_hsts_seconds: 0
  secure_content_type_nosniff: true
  secure_browser_xss_filter: true
  x_frame_options: "DENY"
  data_upload_max_number_fields: 10000

application:
  code_execution_timeout: 5
  admin_url: "admin/"
  admin_emails:
    - "gwonsoo.lee@gmail.com"

jwt:
  access_token_lifetime: 60
  refresh_token_lifetime: 43200
  rotate_refresh_tokens: true
  blacklist_after_rotation: false
  update_last_login: true

rest_framework:
  page_size: 20
  default_permission: "AllowAny"
  throttling:
    anon_rate: "2000/hour"
    user_rate: "5000/hour"

session:
  cookie_age: 3600
  save_every_request: false
  cookie_secure: false
  cookie_httponly: true
  cookie_samesite: "Lax"

email:
  backend: "django.core.mail.backends.console.EmailBackend"
  smtp:
    host: "localhost"
    port: 25
    use_tls: false
  default_from: "noreply@testcase.run"
  server_email: "root@testcase.run"

monitoring:
  environment: "production"
  sentry_traces_sample_rate: 0.1
  sentry_send_pii: false

logging:
  level: "INFO"
  log_to_file: true
  log_dir: "/app/logs"
  app_log_file: "algoitny.log"
  error_log_file: "error.log"
  max_bytes: 15728640
  backup_count: 10

static_files:
  storage: "django.contrib.staticfiles.storage.StaticFilesStorage"
  media_storage: "django.core.files.storage.FileSystemStorage"

aws:
  use_s3: false
  testcase_bucket: "algoitny-testcases-zteapne2"
  s3:
    region: "ap-northeast-2"
    cache_control: "max-age=86400"

middleware:
  use_whitenoise: false
  enable_debug_toolbar: false

testing:
  use_sqlite: false
  celery_eager: false

api_keys:
  judge0:
    enabled: false
    url: "https://judge0-ce.p.rapidapi.com"
CONFIGEOF

chmod 644 /app/config/config.yaml

# Create environment file for Docker
cat > /etc/algoitny-api.env <<EOF
DEBUG=False
ALLOWED_HOSTS=${allowed_hosts},localhost,127.0.0.1
AWS_REGION=$AWS_REGION
AWS_DEFAULT_REGION=$AWS_REGION
USE_SECRETS_MANAGER=true
AWS_SECRET_NAME=algoitny/prod/apnortheast2
DYNAMODB_TABLE=$DYNAMODB_TABLE
GUNICORN_WORKERS=${gunicorn_workers}
GUNICORN_LOG_LEVEL=info
SERVICE_TYPE=api
ENVIRONMENT=production
EOF

chmod 600 /etc/algoitny-api.env

# Create systemd service file
cat > /etc/systemd/system/algoitny-api.service <<'EOF'
[Unit]
Description=AlgoItny API Server
After=docker.service
Requires=docker.service

[Service]
Type=simple
Restart=always
RestartSec=10
TimeoutStartSec=300
User=root
EnvironmentFile=/etc/algoitny-api.env
ExecStartPre=-/usr/bin/docker stop algoitny-api
ExecStartPre=-/usr/bin/docker rm algoitny-api
ExecStart=/usr/bin/docker run --rm \
  --name algoitny-api \
  -p 8000:8000 \
  -v /var/log/algoitny:/app/logs \
  -v /app/tmp:/app/tmp \
  -v /app/config/config.yaml:/app/config/config.yaml:ro \
  --env-file /etc/algoitny-api.env \
  ${ecr_image_url}
ExecStop=/usr/bin/docker stop algoitny-api

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and start service
echo "Starting AlgoItny API service..."
systemctl daemon-reload
systemctl enable algoitny-api.service
systemctl start algoitny-api.service

# Wait for service to be ready
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

# Check service status
systemctl status algoitny-api.service --no-pager

echo "User data script completed at $(date)"
