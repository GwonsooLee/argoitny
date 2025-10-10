# Celery Worker Deployment Guide

## Issue: Celery Worker Terminates Immediately in Production

### Root Cause
The Celery worker was configured to always use LocalStack (localhost:4566), even in production. The `ENVIRONMENT` variable was not set, causing the application to default to development mode.

### Changes Made

#### 1. **backend/config/celery.py**
- Added environment detection logic
- Production: Removes LocalStack environment variables, uses IAM roles
- Development: Configures LocalStack with test credentials

#### 2. **backend/systemd/celery-worker.service**
- Added `Environment="ENVIRONMENT=production"`
- Changed `Type=forking` to `Type=exec` (better process management)
- Added `--pool=threads` (required for async compatibility)
- Added `--prefetch-multiplier=1` (prevents duplicate task execution)
- Added `--queues=jobs,celery,ai,generation,execution,maintenance`
- Removed `--detach` (systemd manages the process directly)

#### 3. **backend/systemd/gunicorn.service** & **celery-beat.service**
- Added `Environment="ENVIRONMENT=production"` for consistency

---

## Deployment Steps

### Step 1: Commit and Push Changes
```bash
# On your local machine
cd /Users/gwonsoolee/algoitny
git add backend/config/celery.py
git add backend/systemd/*.service
git commit -m "Fix Celery production environment configuration

- Add ENVIRONMENT=production to systemd services
- Make celery.py environment-aware (production vs development)
- Fix Celery worker pool and queue configuration"
git push origin main
```

### Step 2: Deploy to Production Server
```bash
# SSH to production server
ssh algoitny@your-production-server

# Navigate to backend directory
cd /home/algoitny/apps/algoitny/backend

# Pull latest changes
git pull origin main

# Copy updated systemd service files
sudo cp systemd/celery-worker.service /etc/systemd/system/
sudo cp systemd/celery-beat.service /etc/systemd/system/
sudo cp systemd/gunicorn.service /etc/systemd/system/

# Reload systemd daemon
sudo systemctl daemon-reload

# Restart services
sudo systemctl restart celery-worker
sudo systemctl restart celery-beat
sudo systemctl restart gunicorn

# Check status
sudo systemctl status celery-worker
sudo systemctl status celery-beat
sudo systemctl status gunicorn
```

### Step 3: Verify Celery Worker
```bash
# Check worker logs
sudo journalctl -u celery-worker -f

# Or check log file
tail -f /var/log/celery/worker.log
```

**Expected Output (Success)**:
```
✅ Django settings loaded successfully
✅ CELERY_BROKER_URL: sqs://  # NO localhost!
✅ CELERY_RESULT_BACKEND: django-db
🚀 Production environment - using AWS SQS (no LocalStack)

-------------- celery@hostname v5.5.3
-- ******* ----
- ** ---------- [config]
- ** ---------- .> app:         algoitny:0x...
- ** ---------- .> transport:   sqs://  # ✅ No localhost!
- ** ---------- .> results:     django-db
- *** --- * --- .> concurrency: 4 (thread)
-- ******* ---- .> task events: ON
--- ***** -----
 --------------
[tasks]
  . api.tasks.delete_job_task
  . api.tasks.execute_code_task
  ...
```

**⚠️ FAILURE Signs**:
- `transport: sqs://localhost//` ❌ (contains localhost)
- `results:` (empty) ❌
- Process exits immediately

---

## Troubleshooting

### 1. Check Environment Variable
```bash
# On production server
sudo systemctl show celery-worker | grep Environment
```

Should include: `Environment=ENVIRONMENT=production`

### 2. Check SQS Queue
```bash
# Check if queue exists
aws sqs list-queues --region ap-northeast-2

# Should show: algoitny-jobs-prod
```

### 3. Check IAM Role (EC2 Instance)
```bash
# Verify instance has IAM role attached
aws sts get-caller-identity

# Check SQS permissions
aws sqs list-queues --region ap-northeast-2
```

### 4. Manual Test
```bash
# SSH to production
cd /home/algoitny/apps/algoitny/backend
source venv/bin/activate

# Test Django settings
ENVIRONMENT=production python -c "
import os
os.environ['ENVIRONMENT'] = 'production'
from django.conf import settings
import django
django.setup()
print(f'CELERY_BROKER_URL: {settings.CELERY_BROKER_URL}')
print(f'IS_PRODUCTION: {settings.IS_PRODUCTION}')
"
```

Should output:
```
CELERY_BROKER_URL: sqs://  # No localhost!
IS_PRODUCTION: True
```

---

## Key Configuration Files

### /etc/systemd/system/celery-worker.service
- **MUST** have `Environment="ENVIRONMENT=production"`
- **MUST** use `--pool=threads` for async support
- **MUST** use `--prefetch-multiplier=1` to prevent duplicates

### /home/algoitny/apps/algoitny/backend/.env
- Can optionally set `ENVIRONMENT=production`
- Systemd service overrides this value

### backend/config/settings.py (Line 26-30)
```python
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
if ENVIRONMENT == 'production':
    # Clean up LocalStack environment variables
    for env_var in ['AWS_ENDPOINT_URL', 'AWS_ENDPOINT_URL_SQS', ...]:
        if env_var in os.environ:
            del os.environ[env_var]
```

### backend/config/celery.py (Line 15-40)
```python
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
IS_PRODUCTION = ENVIRONMENT == 'production'

if IS_PRODUCTION:
    # Remove LocalStack variables
    for env_var in ['AWS_ENDPOINT_URL', 'AWS_ENDPOINT_URL_SQS', ...]:
        ...
```

---

## Rollback Plan

If deployment fails:

```bash
# Restore previous service files (if backed up)
sudo cp /etc/systemd/system/celery-worker.service.backup /etc/systemd/system/celery-worker.service
sudo systemctl daemon-reload
sudo systemctl restart celery-worker

# Or revert git commit
cd /home/algoitny/apps/algoitny/backend
git revert HEAD
sudo systemctl restart celery-worker
```

---

## Post-Deployment Checklist

- [ ] Celery worker is running without errors
- [ ] No "localhost" in CELERY_BROKER_URL
- [ ] Worker logs show: `🚀 Production environment - using AWS SQS`
- [ ] Tasks are being processed (check DynamoDB job status)
- [ ] No orphaned jobs accumulating
- [ ] Gunicorn is still running
- [ ] API endpoints are responsive

---

## Notes

- **ENVIRONMENT=production** is the key fix
- Production uses AWS SQS with IAM roles (no credentials)
- Development uses LocalStack with test credentials
- All systemd services now explicitly set `ENVIRONMENT=production`
- Changes are backward compatible with development environment
