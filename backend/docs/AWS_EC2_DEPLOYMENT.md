# AWS EC2 Django Backend Deployment Guide

Complete guide for deploying AlgoItny Django backend to AWS EC2 with production-grade configuration.

## Table of Contents
- [Prerequisites](#prerequisites)
- [AWS Account Setup](#aws-account-setup)
- [EC2 Instance Setup](#ec2-instance-setup)
- [Server Configuration](#server-configuration)
- [Application Deployment](#application-deployment)
- [Service Configuration](#service-configuration)
- [Nginx Setup](#nginx-setup)
- [SSL/TLS Configuration](#ssltls-configuration)
- [Database Setup](#database-setup)
- [Redis & Celery Setup](#redis--celery-setup)
- [Monitoring & Logging](#monitoring--logging)
- [Security Hardening](#security-hardening)
- [Backup Strategy](#backup-strategy)
- [CI/CD Automation](#cicd-automation)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Accounts & Tools
- AWS Account with billing enabled
- Domain name (api.testcase.run) with DNS access
- GitHub repository access
- SSH client installed locally
- Basic Linux command line knowledge

### Required AWS Services
- **EC2**: Application server
- **RDS**: MySQL/PostgreSQL database (optional, can use EC2-hosted)
- **ElastiCache**: Redis for Celery (optional, can use EC2-hosted)
- **Route 53**: DNS management (or use external DNS provider)
- **Certificate Manager**: SSL certificates (optional, can use Let's Encrypt)
- **S3**: Static files & backups
- **CloudWatch**: Monitoring & logging

### Cost Estimation (Monthly)
- **EC2 t3.medium**: ~$30-40 (24/7)
- **RDS db.t3.micro**: ~$15-20 (optional)
- **ElastiCache t3.micro**: ~$15 (optional)
- **Data Transfer**: ~$5-10
- **Route 53**: ~$1
- **S3 Storage**: ~$1-5
- **Total**: $50-90/month (with RDS/ElastiCache)
- **Budget Option**: $30-40/month (EC2-only with local DB/Redis)

---

## AWS Account Setup

### 1. Create IAM User for Deployment

```bash
# Access AWS Console → IAM → Users → Create User
# User name: algoitny-deploy
# Permissions: Attach existing policies directly
```

**Required Policies:**
- `AmazonEC2FullAccess`
- `AmazonRDSFullAccess` (if using RDS)
- `AmazonElastiCacheFullAccess` (if using ElastiCache)
- `AmazonS3FullAccess`
- `CloudWatchFullAccess`

**Security Best Practice:**
- Enable MFA (Multi-Factor Authentication)
- Create access keys for CLI/API access
- Download and securely store credentials

### 2. Configure AWS CLI (Local)

```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure credentials
aws configure
# AWS Access Key ID: [Your Access Key]
# AWS Secret Access Key: [Your Secret Key]
# Default region: us-east-1 (or your preferred region)
# Default output format: json
```

---

## EC2 Instance Setup

### 1. Launch EC2 Instance

**Step 1: Choose AMI**
- Navigate to EC2 Console → Launch Instance
- Name: `algoitny-backend-production`
- **AMI**: Ubuntu Server 22.04 LTS (64-bit x86)

**Step 2: Choose Instance Type**
- **Recommended**: `t3.medium` (2 vCPU, 4GB RAM)
  - Suitable for moderate traffic
  - Burst performance for peaks
- **Budget**: `t3.small` (2 vCPU, 2GB RAM)
  - For development/testing
- **High Traffic**: `t3.large` (2 vCPU, 8GB RAM)

**Step 3: Configure Key Pair**
```bash
# Create new key pair
# Name: algoitny-ec2-key
# Type: RSA
# Format: .pem

# Download and secure the key
chmod 400 algoitny-ec2-key.pem
```

**Step 4: Network Settings**
- VPC: Default or create custom VPC
- Auto-assign Public IP: Enable
- Firewall (Security Groups):
  - Create security group: `algoitny-backend-sg`

**Security Group Rules:**
```
Inbound Rules:
- SSH (22): Your IP (or 0.0.0.0/0 if dynamic IP, less secure)
- HTTP (80): 0.0.0.0/0
- HTTPS (443): 0.0.0.0/0
- Custom TCP (8000): 0.0.0.0/0 (for testing, remove in production)

Outbound Rules:
- All traffic: 0.0.0.0/0
```

**Step 5: Configure Storage**
- Root Volume: 30 GB gp3 (General Purpose SSD)
- Delete on Termination: Uncheck (for safety)

**Step 6: Advanced Details (Optional)**
- Enable detailed CloudWatch monitoring
- User data: Can add setup script later

### 2. Allocate Elastic IP

```bash
# In EC2 Console → Elastic IPs → Allocate Elastic IP address
# Associate with your instance

# Or via AWS CLI
aws ec2 allocate-address --domain vpc
aws ec2 associate-address --instance-id i-xxxxx --allocation-id eipalloc-xxxxx
```

**Why Elastic IP?**
- Static IP address that doesn't change on reboot
- Required for DNS configuration
- Free when associated with running instance

### 3. Configure DNS

**Route 53 (AWS DNS):**
```bash
# Create Hosted Zone for testcase.run
aws route53 create-hosted-zone --name testcase.run --caller-reference $(date +%s)

# Create A Record for api.testcase.run → Elastic IP
# Type: A
# Name: api.testcase.run
# Value: [Your Elastic IP]
# TTL: 300
```

**External DNS Provider:**
- Create A record: `api.testcase.run` → `[Elastic IP]`
- Wait for DNS propagation (5-30 minutes)

### 4. Connect to EC2

```bash
# SSH into instance
ssh -i algoitny-ec2-key.pem ubuntu@[ELASTIC_IP]

# Or using domain (after DNS propagation)
ssh -i algoitny-ec2-key.pem ubuntu@api.testcase.run
```

---

## Server Configuration

### 1. Initial System Setup

```bash
# Update package lists
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y build-essential git curl wget vim nano htop net-tools

# Set timezone
sudo timedatectl set-timezone UTC

# Create application user
sudo useradd -m -s /bin/bash algoitny
sudo usermod -aG sudo algoitny

# Set up sudo without password (for deployment automation)
echo "algoitny ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/algoitny
```

### 2. Install Python 3.11

```bash
# Add deadsnakes PPA for latest Python
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

# Install Python 3.11 and dependencies
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Set Python 3.11 as default
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
sudo update-alternatives --config python3

# Verify installation
python3 --version  # Should show Python 3.11.x

# Install pip for Python 3.11
curl -sS https://bootstrap.pypa.io/get-pip.py | sudo python3.11
```

### 3. Install MySQL

```bash
# Install MySQL Server
sudo apt install -y mysql-server mysql-client libmysqlclient-dev

# Secure MySQL installation
sudo mysql_secure_installation
# - Set root password
# - Remove anonymous users: Yes
# - Disallow root login remotely: Yes
# - Remove test database: Yes
# - Reload privilege tables: Yes

# Create database and user
sudo mysql -u root -p
```

```sql
-- In MySQL shell
CREATE DATABASE algoitny CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'algoitny'@'localhost' IDENTIFIED BY 'your_secure_password_here';
GRANT ALL PRIVILEGES ON algoitny.* TO 'algoitny'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

**MySQL Configuration for Django:**
```bash
# Edit MySQL config
sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf

# Add/modify these settings
[mysqld]
max_connections = 500
innodb_buffer_pool_size = 1G  # Adjust based on RAM
innodb_log_file_size = 256M
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

# Restart MySQL
sudo systemctl restart mysql
sudo systemctl enable mysql
```

### 4. Install Redis

```bash
# Install Redis
sudo apt install -y redis-server

# Configure Redis
sudo nano /etc/redis/redis.conf

# Modify these settings:
# supervised systemd
# maxmemory 256mb  # Adjust based on your needs
# maxmemory-policy allkeys-lru
# bind 127.0.0.1  # Ensure Redis only listens locally

# Restart Redis
sudo systemctl restart redis-server
sudo systemctl enable redis-server

# Test Redis
redis-cli ping  # Should return PONG
```

### 5. Install Nginx

```bash
# Install Nginx
sudo apt install -y nginx

# Start and enable Nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Allow through firewall
sudo ufw allow 'Nginx Full'

# Test (should see Nginx welcome page)
curl http://localhost
```

---

## Application Deployment

### 1. Clone Repository

```bash
# Switch to algoitny user
sudo su - algoitny

# Create application directory
mkdir -p /home/algoitny/apps
cd /home/algoitny/apps

# Clone repository
git clone https://github.com/YOUR_USERNAME/algoitny.git
cd algoitny/backend

# Set up Git credentials for future pulls
git config --global user.name "AlgoItny Deploy"
git config --global user.email "deploy@algoitny.com"
```

**For Private Repositories:**
```bash
# Generate SSH key on server
ssh-keygen -t ed25519 -C "deploy@api.testcase.run"

# Add public key to GitHub
cat ~/.ssh/id_ed25519.pub
# Copy and add to GitHub → Settings → Deploy Keys

# Test connection
ssh -T git@github.com
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel
```

### 3. Install Dependencies

```bash
# Install production requirements
pip install -r requirements-production.txt

# If requirements-production.txt doesn't exist, use requirements.txt
pip install -r requirements.txt

# Install additional production packages
pip install gunicorn psycopg2-binary redis
```

### 4. Environment Variables Setup

```bash
# Create .env file
nano /home/algoitny/apps/algoitny/backend/.env
```

**Production .env Template:**
```bash
# Django Settings
DEBUG=False
SECRET_KEY=your_super_secure_random_secret_key_here_generate_with_django
DJANGO_SETTINGS_MODULE=config.settings_production
ALLOWED_HOSTS=api.testcase.run,www.testcase.run,testcase.run

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_URL=redis://localhost:6379/0

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=django-db

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_OAUTH_REDIRECT_URI=https://api.testcase.run/auth/callback

# Gemini API
GEMINI_API_KEY=your_gemini_api_key

# Judge0 Configuration (if used)
USE_JUDGE0=false
JUDGE0_API_URL=https://judge0-ce.p.rapidapi.com
JUDGE0_API_KEY=your_judge0_api_key

# CORS Configuration
CORS_ALLOWED_ORIGINS=https://testcase.run,https://www.testcase.run

# AWS Configuration (for S3, if used)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_STORAGE_BUCKET_NAME=algoitny-static
AWS_S3_REGION_NAME=us-east-1

# Security Settings
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True

# Code Execution
CODE_EXECUTION_TIMEOUT=5
```

**Generate Django Secret Key:**
```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 5. Django Setup

```bash
# Activate virtual environment
source /home/algoitny/apps/algoitny/backend/venv/bin/activate

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
# Username: admin
# Email: admin@testcase.run
# Password: [secure password]

# Test Django
python manage.py check --deploy
```

---

## Service Configuration

### 1. Gunicorn Setup

**Create systemd service file:**
```bash
sudo nano /etc/systemd/system/gunicorn.service
```

**Gunicorn Service Configuration:**
```ini
[Unit]
Description=Gunicorn daemon for AlgoItny Django Application
After=network.target mysql.service redis.service

[Service]
Type=notify
User=algoitny
Group=www-data
WorkingDirectory=/home/algoitny/apps/algoitny/backend
Environment="PATH=/home/algoitny/apps/algoitny/backend/venv/bin"
EnvironmentFile=/home/algoitny/apps/algoitny/backend/.env

ExecStart=/home/algoitny/apps/algoitny/backend/venv/bin/gunicorn \
    --workers 4 \
    --worker-class sync \
    --worker-connections 1000 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --timeout 30 \
    --bind unix:/home/algoitny/apps/algoitny/backend/gunicorn.sock \
    --access-logfile /var/log/gunicorn/access.log \
    --error-logfile /var/log/gunicorn/error.log \
    --log-level info \
    config.wsgi:application

ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Create log directory:**
```bash
sudo mkdir -p /var/log/gunicorn
sudo chown algoitny:www-data /var/log/gunicorn
```

**Worker Calculation:**
- Formula: `(2 x CPU cores) + 1`
- t3.medium (2 vCPU): 4-5 workers
- Adjust based on memory and traffic

**Start Gunicorn:**
```bash
# Reload systemd
sudo systemctl daemon-reload

# Start Gunicorn
sudo systemctl start gunicorn

# Enable on boot
sudo systemctl enable gunicorn

# Check status
sudo systemctl status gunicorn

# View logs
sudo journalctl -u gunicorn -f
```

### 2. Celery Worker Setup

**Create systemd service file:**
```bash
sudo nano /etc/systemd/system/celery-worker.service
```

**Celery Worker Configuration:**
```ini
[Unit]
Description=Celery Worker for AlgoItny
After=network.target redis.service mysql.service

[Service]
Type=forking
User=algoitny
Group=www-data
WorkingDirectory=/home/algoitny/apps/algoitny/backend
Environment="PATH=/home/algoitny/apps/algoitny/backend/venv/bin"
EnvironmentFile=/home/algoitny/apps/algoitny/backend/.env

ExecStart=/home/algoitny/apps/algoitny/backend/venv/bin/celery -A config worker \
    --loglevel=info \
    --concurrency=4 \
    --max-tasks-per-child=1000 \
    --time-limit=1800 \
    --soft-time-limit=1500 \
    --logfile=/var/log/celery/worker.log \
    --pidfile=/var/run/celery/worker.pid

ExecReload=/bin/kill -s HUP $MAINPID
ExecStop=/bin/kill -s TERM $MAINPID

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Create necessary directories:**
```bash
sudo mkdir -p /var/log/celery /var/run/celery
sudo chown algoitny:www-data /var/log/celery /var/run/celery
```

**Start Celery Worker:**
```bash
sudo systemctl daemon-reload
sudo systemctl start celery-worker
sudo systemctl enable celery-worker
sudo systemctl status celery-worker
```

### 3. Celery Beat Setup (for Scheduled Tasks)

**Create systemd service file:**
```bash
sudo nano /etc/systemd/system/celery-beat.service
```

**Celery Beat Configuration:**
```ini
[Unit]
Description=Celery Beat Scheduler for AlgoItny
After=network.target redis.service

[Service]
Type=simple
User=algoitny
Group=www-data
WorkingDirectory=/home/algoitny/apps/algoitny/backend
Environment="PATH=/home/algoitny/apps/algoitny/backend/venv/bin"
EnvironmentFile=/home/algoitny/apps/algoitny/backend/.env

ExecStart=/home/algoitny/apps/algoitny/backend/venv/bin/celery -A config beat \
    --loglevel=info \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler \
    --logfile=/var/log/celery/beat.log \
    --pidfile=/var/run/celery/beat.pid

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Start Celery Beat:**
```bash
sudo systemctl daemon-reload
sudo systemctl start celery-beat
sudo systemctl enable celery-beat
sudo systemctl status celery-beat
```

---

## Nginx Setup

### 1. Create Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/testcase.run
```

**Nginx Configuration:**
```nginx
# Rate limiting zones
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/m;
limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=10r/m;

# Upstream Gunicorn
upstream django_backend {
    server unix:/home/algoitny/apps/algoitny/backend/gunicorn.sock fail_timeout=0;
}

# HTTP redirect to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name api.testcase.run testcase.run www.testcase.run;

    # Allow Let's Encrypt verification
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect all HTTP to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS Server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name api.testcase.run;

    # SSL Configuration (will be set up with certbot)
    ssl_certificate /etc/letsencrypt/live/api.testcase.run/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.testcase.run/privkey.pem;

    # SSL Security Settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # HSTS Header
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    # Security Headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # CORS Headers (if needed, or handle in Django)
    add_header Access-Control-Allow-Origin "https://testcase.run" always;
    add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
    add_header Access-Control-Allow-Headers "Authorization, Content-Type" always;
    add_header Access-Control-Allow-Credentials "true" always;

    # Max upload size
    client_max_body_size 10M;

    # Timeouts
    client_body_timeout 12;
    client_header_timeout 12;
    keepalive_timeout 15;
    send_timeout 10;

    # Gzip Compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss application/rss+xml font/truetype font/opentype application/vnd.ms-fontobject image/svg+xml;
    gzip_disable "msie6";

    # Access and Error Logs
    access_log /var/log/nginx/algoitny_access.log;
    error_log /var/log/nginx/algoitny_error.log warn;

    # Static files
    location /static/ {
        alias /home/algoitny/apps/algoitny/backend/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files (if you have user uploads)
    location /media/ {
        alias /home/algoitny/apps/algoitny/backend/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    # Django admin rate limiting
    location /admin/ {
        limit_req zone=auth_limit burst=5;

        proxy_pass http://django_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;

        # Increase timeout for admin operations
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # API rate limiting
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;

        proxy_pass http://django_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;

        # Buffering settings
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Auth endpoints with stricter rate limiting
    location ~ ^/(auth|token)/ {
        limit_req zone=auth_limit burst=3 nodelay;

        proxy_pass http://django_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    # All other Django routes
    location / {
        proxy_pass http://django_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
```

### 2. Enable Nginx Configuration

```bash
# Create symbolic link
sudo ln -s /etc/nginx/sites-available/testcase.run /etc/nginx/sites-enabled/

# Remove default configuration
sudo rm /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# If successful, restart Nginx
sudo systemctl restart nginx
```

---

## SSL/TLS Configuration

### Using Let's Encrypt (Free, Recommended)

**1. Install Certbot:**
```bash
sudo apt install -y certbot python3-certbot-nginx
```

**2. Obtain SSL Certificate:**
```bash
# Make sure DNS is pointing to your server
# Create webroot directory for verification
sudo mkdir -p /var/www/certbot

# Temporarily modify Nginx to allow verification
# (Already configured in the above Nginx config)

# Obtain certificate
sudo certbot --nginx -d api.testcase.run -d testcase.run -d www.testcase.run

# Follow prompts:
# - Enter email address
# - Agree to terms
# - Choose redirect HTTP to HTTPS (option 2)
```

**3. Auto-renewal:**
```bash
# Test renewal
sudo certbot renew --dry-run

# Certbot automatically sets up renewal cron job
# Check cron job
sudo systemctl status certbot.timer

# Manual renewal (if needed)
sudo certbot renew
```

### Using AWS Certificate Manager (ACM)

**For Load Balancer Setup:**
```bash
# 1. Request certificate in ACM (AWS Console)
# 2. Validate domain ownership (DNS or Email)
# 3. Attach certificate to Application Load Balancer
# 4. Configure ALB to forward to EC2 instance
```

---

## Database Setup

### Option 1: MySQL on EC2 (Already configured above)

**Backup Configuration:**
```bash
# Create backup script
sudo nano /home/algoitny/scripts/backup-mysql.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/home/algoitny/backups/mysql"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="algoitny"
DB_USER="algoitny"
DB_PASS="your_password"

mkdir -p $BACKUP_DIR

# Dump database
mysqldump -u $DB_USER -p$DB_PASS $DB_NAME | gzip > $BACKUP_DIR/backup_$DATE.sql.gz

# Keep only last 7 days
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: backup_$DATE.sql.gz"
```

```bash
# Make executable
chmod +x /home/algoitny/scripts/backup-mysql.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add: 0 2 * * * /home/algoitny/scripts/backup-mysql.sh
```

### Option 2: Amazon RDS MySQL

**1. Create RDS Instance:**
```bash
# Via AWS Console or CLI
aws rds create-db-instance \
    --db-instance-identifier algoitny-db \
    --db-instance-class db.t3.micro \
    --engine mysql \
    --engine-version 8.0 \
    --master-username admin \
    --master-user-password YourSecurePassword \
    --allocated-storage 20 \
    --storage-type gp2 \
    --vpc-security-group-ids sg-xxxxx \
    --db-subnet-group-name my-subnet-group \
    --backup-retention-period 7 \
    --preferred-backup-window "03:00-04:00" \
    --preferred-maintenance-window "mon:04:00-mon:05:00" \
    --publicly-accessible false
```

**2. Security Group Configuration:**
```bash
# Allow EC2 to access RDS
# Inbound Rule: MySQL/Aurora (3306) from EC2 security group
```

**3. Update Django Settings:**
```bash
# In .env file
DB_HOST=algoitny-db.xxxxx.us-east-1.rds.amazonaws.com
DB_PORT=3306
DB_NAME=algoitny
DB_USER=admin
DB_PASSWORD=YourSecurePassword
```

**Benefits of RDS:**
- Automated backups
- Multi-AZ deployment for high availability
- Automated patching
- Monitoring via CloudWatch
- Point-in-time recovery

---

## Redis & Celery Setup

### Option 1: Redis on EC2 (Already configured above)

**Redis Persistence:**
```bash
# Edit Redis config
sudo nano /etc/redis/redis.conf

# Enable RDB persistence
save 900 1      # Save if 1 key changed in 15 minutes
save 300 10     # Save if 10 keys changed in 5 minutes
save 60 10000   # Save if 10000 keys changed in 1 minute

# Enable AOF persistence (more durable)
appendonly yes
appendfsync everysec

# Restart Redis
sudo systemctl restart redis-server
```

### Option 2: Amazon ElastiCache Redis

**1. Create ElastiCache Cluster:**
```bash
aws elasticache create-cache-cluster \
    --cache-cluster-id algoitny-redis \
    --cache-node-type cache.t3.micro \
    --engine redis \
    --num-cache-nodes 1 \
    --cache-subnet-group-name my-subnet-group \
    --security-group-ids sg-xxxxx
```

**2. Update Django Settings:**
```bash
# In .env file
REDIS_HOST=algoitny-redis.xxxxx.cache.amazonaws.com
REDIS_PORT=6379
REDIS_URL=redis://algoitny-redis.xxxxx.cache.amazonaws.com:6379/0
```

### Celery Monitoring

**Install Flower (Celery monitoring tool):**
```bash
pip install flower

# Run Flower
celery -A config flower --port=5555

# Access at http://your-server:5555
```

**Flower as systemd service:**
```bash
sudo nano /etc/systemd/system/celery-flower.service
```

```ini
[Unit]
Description=Celery Flower
After=network.target

[Service]
Type=simple
User=algoitny
Group=www-data
WorkingDirectory=/home/algoitny/apps/algoitny/backend
Environment="PATH=/home/algoitny/apps/algoitny/backend/venv/bin"

ExecStart=/home/algoitny/apps/algoitny/backend/venv/bin/celery -A config flower --port=5555

Restart=always

[Install]
WantedBy=multi-user.target
```

---

## Monitoring & Logging

### 1. Application Logging

**Configure Django Logging:**
```python
# In settings_production.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/django/algoitny.log',
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/django/error.log',
            'maxBytes': 1024 * 1024 * 15,
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'error_file'],
            'level': 'INFO',
            'propagate': True,
        },
        'api': {
            'handlers': ['file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

```bash
# Create log directory
sudo mkdir -p /var/log/django
sudo chown algoitny:www-data /var/log/django
```

### 2. AWS CloudWatch

**Install CloudWatch Agent:**
```bash
# Download CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb

# Install
sudo dpkg -i amazon-cloudwatch-agent.deb

# Configure
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-config-wizard
```

**CloudWatch Configuration:**
```json
{
  "metrics": {
    "namespace": "AlgoItny/Backend",
    "metrics_collected": {
      "cpu": {
        "measurement": [{"name": "cpu_usage_idle"}],
        "metrics_collection_interval": 60
      },
      "disk": {
        "measurement": [{"name": "used_percent"}],
        "metrics_collection_interval": 60
      },
      "mem": {
        "measurement": [{"name": "mem_used_percent"}],
        "metrics_collection_interval": 60
      }
    }
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/nginx/algoitny_error.log",
            "log_group_name": "/algoitny/nginx/error",
            "log_stream_name": "{instance_id}"
          },
          {
            "file_path": "/var/log/gunicorn/error.log",
            "log_group_name": "/algoitny/gunicorn/error",
            "log_stream_name": "{instance_id}"
          },
          {
            "file_path": "/var/log/django/error.log",
            "log_group_name": "/algoitny/django/error",
            "log_stream_name": "{instance_id}"
          }
        ]
      }
    }
  }
}
```

### 3. System Monitoring Tools

**Install and configure monitoring:**
```bash
# Install htop for interactive process monitoring
sudo apt install -y htop

# Install netdata for real-time monitoring
bash <(curl -Ss https://my-netdata.io/kickstart.sh)

# Access Netdata dashboard at http://your-server:19999
```

---

## Security Hardening

### 1. Firewall Configuration (UFW)

```bash
# Enable UFW
sudo ufw enable

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow from specific IP (optional, for additional security)
# sudo ufw allow from YOUR_IP to any port 22

# Check status
sudo ufw status verbose
```

### 2. Fail2Ban (Protect against brute force)

```bash
# Install Fail2Ban
sudo apt install -y fail2ban

# Create local configuration
sudo nano /etc/fail2ban/jail.local
```

```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5
destemail = admin@testcase.run
sendername = Fail2Ban

[sshd]
enabled = true
port = 22
logpath = /var/log/auth.log

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/algoitny_error.log

[nginx-noscript]
enabled = true
port = http,https
filter = nginx-noscript
logpath = /var/log/nginx/algoitny_access.log
maxretry = 6

[nginx-badbots]
enabled = true
port = http,https
filter = nginx-badbots
logpath = /var/log/nginx/algoitny_access.log
maxretry = 2
```

```bash
# Start Fail2Ban
sudo systemctl start fail2ban
sudo systemctl enable fail2ban

# Check status
sudo fail2ban-client status
```

### 3. SSH Hardening

```bash
# Edit SSH config
sudo nano /etc/ssh/sshd_config
```

```bash
# Recommended SSH security settings
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
PermitEmptyPasswords no
X11Forwarding no
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
```

```bash
# Restart SSH
sudo systemctl restart sshd
```

### 4. System Updates

```bash
# Enable automatic security updates
sudo apt install -y unattended-upgrades

# Configure
sudo nano /etc/apt/apt.conf.d/50unattended-upgrades

# Enable
sudo dpkg-reconfigure -plow unattended-upgrades
```

### 5. Django Security Checklist

**In settings_production.py:**
```python
# Security settings
DEBUG = False
SECRET_KEY = env('SECRET_KEY')  # From environment variable
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

# HTTPS/SSL
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Other security headers
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# CSRF
CSRF_COOKIE_HTTPONLY = True
CSRF_USE_SESSIONS = True
CSRF_COOKIE_SAMESITE = 'Strict'

# Session security
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_AGE = 3600  # 1 hour
```

---

## Backup Strategy

### 1. Database Backup Script

**Already created above, enhance with S3:**
```bash
sudo nano /home/algoitny/scripts/backup-mysql-s3.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/home/algoitny/backups/mysql"
S3_BUCKET="s3://algoitny-backups/mysql"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="algoitny"
DB_USER="algoitny"
DB_PASS="your_password"
BACKUP_FILE="backup_$DATE.sql.gz"

mkdir -p $BACKUP_DIR

# Dump database
mysqldump -u $DB_USER -p$DB_PASS $DB_NAME | gzip > $BACKUP_DIR/$BACKUP_FILE

# Upload to S3
aws s3 cp $BACKUP_DIR/$BACKUP_FILE $S3_BUCKET/$BACKUP_FILE

# Keep only last 7 days locally
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete

# Keep only last 30 days in S3
aws s3 ls $S3_BUCKET/ | while read -r line; do
    createDate=$(echo $line | awk {'print $1" "$2'})
    createDate=$(date -d "$createDate" +%s)
    olderThan=$(date -d "30 days ago" +%s)
    if [[ $createDate -lt $olderThan ]]; then
        fileName=$(echo $line | awk {'print $4'})
        if [[ $fileName != "" ]]; then
            aws s3 rm $S3_BUCKET/$fileName
        fi
    fi
done

echo "Backup completed: $BACKUP_FILE"
```

### 2. Application Backup

```bash
sudo nano /home/algoitny/scripts/backup-app.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/home/algoitny/backups/app"
S3_BUCKET="s3://algoitny-backups/app"
DATE=$(date +%Y%m%d_%H%M%S)
APP_DIR="/home/algoitny/apps/algoitny"

mkdir -p $BACKUP_DIR

# Backup .env file and user uploads
tar -czf $BACKUP_DIR/app_backup_$DATE.tar.gz \
    $APP_DIR/backend/.env \
    $APP_DIR/backend/media/ \
    --exclude='*.pyc' \
    --exclude='__pycache__'

# Upload to S3
aws s3 cp $BACKUP_DIR/app_backup_$DATE.tar.gz $S3_BUCKET/

# Keep only last 7 days locally
find $BACKUP_DIR -name "app_backup_*.tar.gz" -mtime +7 -delete

echo "Application backup completed: app_backup_$DATE.tar.gz"
```

### 3. Automated Backup Schedule

```bash
# Edit crontab
crontab -e

# Add backup jobs
0 2 * * * /home/algoitny/scripts/backup-mysql-s3.sh
0 3 * * * /home/algoitny/scripts/backup-app.sh
```

---

## CI/CD Automation

### GitHub Actions Workflow

**Created in separate file (see deploy-ec2.yml)**

### Manual Deployment Script

**Created in separate file (see deploy.sh)**

---

## Troubleshooting

### Common Issues

#### 1. Gunicorn Won't Start

```bash
# Check logs
sudo journalctl -u gunicorn -n 50

# Common causes:
# - Permission issues: Check file ownership
sudo chown -R algoitny:www-data /home/algoitny/apps/algoitny

# - Python path issues: Verify virtual environment
/home/algoitny/apps/algoitny/backend/venv/bin/python --version

# - Socket file issues: Remove old socket
rm /home/algoitny/apps/algoitny/backend/gunicorn.sock

# Restart
sudo systemctl restart gunicorn
```

#### 2. Nginx 502 Bad Gateway

```bash
# Check if Gunicorn is running
sudo systemctl status gunicorn

# Check socket file exists and permissions
ls -la /home/algoitny/apps/algoitny/backend/gunicorn.sock

# Check Nginx error logs
sudo tail -f /var/log/nginx/algoitny_error.log

# Test Nginx config
sudo nginx -t

# Restart both services
sudo systemctl restart gunicorn nginx
```

#### 3. Database Connection Errors

```bash
# Test MySQL connection
mysql -u algoitny -p -h localhost

# Check MySQL is running
sudo systemctl status mysql

# Verify database exists
mysql -u algoitny -p -e "SHOW DATABASES;"

# Check Django database settings
cd /home/algoitny/apps/algoitny/backend
source venv/bin/activate
python manage.py dbshell
```

#### 4. Celery Tasks Not Running

```bash
# Check Celery worker status
sudo systemctl status celery-worker

# Check Redis is running
redis-cli ping

# Test Celery connection
cd /home/algoitny/apps/algoitny/backend
source venv/bin/activate
celery -A config inspect ping

# Check task queue
celery -A config inspect active

# View Celery logs
sudo journalctl -u celery-worker -f
```

#### 5. Static Files Not Loading

```bash
# Collect static files
cd /home/algoitny/apps/algoitny/backend
source venv/bin/activate
python manage.py collectstatic --noinput

# Check permissions
sudo chown -R algoitny:www-data /home/algoitny/apps/algoitny/backend/staticfiles

# Verify Nginx config
sudo nginx -t

# Check Nginx access logs
sudo tail -f /var/log/nginx/algoitny_access.log
```

#### 6. SSL Certificate Issues

```bash
# Renew certificate manually
sudo certbot renew

# Check certificate expiry
sudo certbot certificates

# Test SSL configuration
curl -I https://api.testcase.run

# Check Nginx SSL config
sudo nginx -t
```

### Performance Troubleshooting

#### High CPU Usage

```bash
# Check processes
htop

# Check Django queries (add django-debug-toolbar in dev)
# Enable query logging in production temporarily

# Check Celery worker load
celery -A config inspect stats
```

#### High Memory Usage

```bash
# Check memory
free -h

# Check largest processes
ps aux --sort=-%mem | head

# Reduce Gunicorn workers if needed
# Edit /etc/systemd/system/gunicorn.service
# Reduce --workers value
```

#### Slow Database Queries

```bash
# Enable MySQL slow query log
sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf

# Add:
# slow_query_log = 1
# slow_query_log_file = /var/log/mysql/slow-query.log
# long_query_time = 2

# Restart MySQL
sudo systemctl restart mysql

# Analyze slow queries
sudo mysqldumpslow /var/log/mysql/slow-query.log
```

### Logs Quick Reference

```bash
# Nginx
sudo tail -f /var/log/nginx/algoitny_error.log
sudo tail -f /var/log/nginx/algoitny_access.log

# Gunicorn
sudo journalctl -u gunicorn -f
sudo tail -f /var/log/gunicorn/error.log

# Celery
sudo journalctl -u celery-worker -f
sudo tail -f /var/log/celery/worker.log

# Django
sudo tail -f /var/log/django/error.log

# MySQL
sudo tail -f /var/log/mysql/error.log

# System
sudo journalctl -f
```

---

## Post-Deployment Checklist

- [ ] EC2 instance running with Elastic IP
- [ ] DNS configured and propagated
- [ ] SSL certificate installed and auto-renewal enabled
- [ ] Gunicorn service running and enabled
- [ ] Celery worker service running and enabled
- [ ] Celery beat service running (if needed)
- [ ] Nginx configured and running
- [ ] Database migrations completed
- [ ] Static files collected and accessible
- [ ] Admin panel accessible and functional
- [ ] API endpoints responding correctly
- [ ] CORS configured for frontend domain
- [ ] Authentication/JWT working
- [ ] Celery tasks executing successfully
- [ ] Firewall (UFW) enabled and configured
- [ ] Fail2Ban running
- [ ] CloudWatch monitoring configured
- [ ] Automated backups scheduled
- [ ] Django security settings verified (`python manage.py check --deploy`)
- [ ] All environment variables set correctly
- [ ] Log rotation configured
- [ ] Error monitoring set up (Sentry optional)

---

## Maintenance Tasks

### Daily
- Monitor CloudWatch metrics
- Check error logs for anomalies
- Verify backup completion

### Weekly
- Review application logs
- Check disk space usage
- Review Nginx access patterns
- Check SSL certificate expiry date

### Monthly
- Update system packages: `sudo apt update && sudo apt upgrade`
- Review and rotate logs
- Test backup restoration
- Review and optimize database
- Check for Django/package updates

### Quarterly
- Security audit
- Performance optimization review
- Cost optimization review
- Disaster recovery drill

---

## Additional Resources

### Documentation
- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [Gunicorn Documentation](https://docs.gunicorn.org/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [AWS EC2 Documentation](https://docs.aws.amazon.com/ec2/)

### Tools
- [SSL Labs Server Test](https://www.ssllabs.com/ssltest/)
- [Security Headers Check](https://securityheaders.com/)
- [GTmetrix Performance](https://gtmetrix.com/)

### Monitoring Services (Optional)
- [Sentry](https://sentry.io/) - Error tracking
- [New Relic](https://newrelic.com/) - Application performance monitoring
- [DataDog](https://www.datadoghq.com/) - Infrastructure monitoring
- [UptimeRobot](https://uptimerobot.com/) - Uptime monitoring

---

## Support

For issues or questions:
- Check troubleshooting section above
- Review application logs
- Check AWS service health dashboard
- Contact DevOps team

---

**Last Updated:** 2025-10-06
**Version:** 1.0
**Maintained by:** AlgoItny DevOps Team
