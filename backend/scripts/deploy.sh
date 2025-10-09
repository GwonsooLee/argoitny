#!/bin/bash
#
# AlgoItny Deployment Script
# This script handles application deployment and updates
#
# Usage: bash deploy.sh [--initial]
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_DIR="/home/algoitny/apps/algoitny"
BACKEND_DIR="$APP_DIR/backend"
VENV_DIR="$BACKEND_DIR/venv"
BRANCH="main"
INITIAL_DEPLOY=false

# Parse arguments
if [[ "$1" == "--initial" ]]; then
    INITIAL_DEPLOY=true
fi

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Error handler
error_exit() {
    log_error "$1"
    exit 1
}

# Check if running as algoitny user
if [ "$USER" != "algoitny" ]; then
    error_exit "Please run this script as 'algoitny' user: sudo su - algoitny"
fi

log_info "=========================================="
log_info "AlgoItny Deployment Script"
log_info "=========================================="
log_info "Mode: $([ "$INITIAL_DEPLOY" = true ] && echo "Initial Deployment" || echo "Update Deployment")"
log_info ""

# Initial deployment setup
if [ "$INITIAL_DEPLOY" = true ]; then
    log_step "Performing initial deployment..."

    # Check if directory exists
    if [ -d "$APP_DIR" ]; then
        log_warn "Application directory already exists. Skipping clone."
    else
        log_step "Cloning repository..."
        read -p "Enter repository URL: " repo_url
        git clone "$repo_url" "$APP_DIR" || error_exit "Failed to clone repository"
    fi

    cd "$BACKEND_DIR"

    # Create virtual environment
    log_step "Creating Python virtual environment..."
    python3.11 -m venv "$VENV_DIR" || error_exit "Failed to create virtual environment"

    # Activate virtual environment
    source "$VENV_DIR/bin/activate"

    # Upgrade pip
    log_step "Upgrading pip..."
    pip install --upgrade pip setuptools wheel

    # Install dependencies
    log_step "Installing Python dependencies..."
    if [ -f "requirements-production.txt" ]; then
        pip install -r requirements-production.txt || error_exit "Failed to install production requirements"
    else
        pip install -r requirements.txt || error_exit "Failed to install requirements"
    fi

    # Create .env file
    if [ ! -f ".env" ]; then
        log_step "Creating .env file..."
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_warn "Please edit .env file with your production settings"
            read -p "Press enter to continue after editing .env file..."
        else
            error_exit ".env.example not found. Please create .env file manually."
        fi
    fi

    # Collect static files
    log_step "Collecting static files..."
    python manage.py collectstatic --noinput || error_exit "Failed to collect static files"

    # Run migrations
    log_step "Running database migrations..."
    python manage.py migrate || error_exit "Failed to run migrations"

    # Create superuser
    log_step "Creating superuser..."
    read -p "Do you want to create a superuser? (y/n): " create_superuser
    if [ "$create_superuser" = "y" ]; then
        python manage.py createsuperuser
    fi

    log_info "Initial deployment setup complete!"
    log_info "Next steps:"
    log_info "  1. Configure systemd services (Gunicorn, Celery)"
    log_info "  2. Configure Nginx"
    log_info "  3. Set up SSL certificate"
    log_info "  4. Start all services"
    exit 0
fi

# Update deployment
log_step "Starting update deployment..."

cd "$BACKEND_DIR" || error_exit "Backend directory not found"

# Activate virtual environment
source "$VENV_DIR/bin/activate" || error_exit "Failed to activate virtual environment"

# Stash any local changes
log_step "Stashing local changes..."
git stash

# Pull latest code
log_step "Pulling latest code from $BRANCH branch..."
git fetch origin
git checkout "$BRANCH"
git pull origin "$BRANCH" || error_exit "Failed to pull latest code"

# Update dependencies
log_step "Updating Python dependencies..."
if [ -f "requirements-production.txt" ]; then
    pip install -r requirements-production.txt --upgrade
else
    pip install -r requirements.txt --upgrade
fi

# Collect static files
log_step "Collecting static files..."
python manage.py collectstatic --noinput || error_exit "Failed to collect static files"

# Run migrations
log_step "Running database migrations..."
python manage.py migrate || error_exit "Failed to run migrations"

# Run Django checks
log_step "Running Django deployment checks..."
python manage.py check --deploy || log_warn "Deployment checks found some issues"

# Restart services
log_step "Restarting services..."

# Restart Gunicorn
log_info "Restarting Gunicorn..."
sudo systemctl restart gunicorn || log_warn "Failed to restart Gunicorn"

# Restart Celery worker
log_info "Restarting Celery worker..."
sudo systemctl restart celery-worker || log_warn "Failed to restart Celery worker"

# Restart Celery beat (if exists)
if systemctl list-unit-files | grep -q celery-beat.service; then
    log_info "Restarting Celery beat..."
    sudo systemctl restart celery-beat || log_warn "Failed to restart Celery beat"
fi

# Reload Nginx
log_info "Reloading Nginx..."
sudo systemctl reload nginx || log_warn "Failed to reload Nginx"

# Wait for services to start
sleep 3

# Check service status
log_step "Checking service status..."

check_service() {
    local service=$1
    if sudo systemctl is-active --quiet "$service"; then
        log_info "$service: ${GREEN}RUNNING${NC}"
        return 0
    else
        log_error "$service: ${RED}FAILED${NC}"
        sudo journalctl -u "$service" -n 20 --no-pager
        return 1
    fi
}

SERVICES_OK=true

check_service "gunicorn" || SERVICES_OK=false
check_service "celery-worker" || SERVICES_OK=false
check_service "nginx" || SERVICES_OK=false

if systemctl list-unit-files | grep -q celery-beat.service; then
    check_service "celery-beat" || SERVICES_OK=false
fi

# Test application
log_step "Testing application..."

# Test health endpoint (if you have one)
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ 2>/dev/null || echo "000")
if [ "$RESPONSE" = "200" ] || [ "$RESPONSE" = "301" ] || [ "$RESPONSE" = "302" ]; then
    log_info "Application is responding (HTTP $RESPONSE)"
else
    log_warn "Application test returned HTTP $RESPONSE"
fi

# Clean up
log_step "Cleaning up..."

# Remove Python cache
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# Remove old log files (older than 30 days)
find /var/log/gunicorn -name "*.log*" -mtime +30 -delete 2>/dev/null || true
find /var/log/celery -name "*.log*" -mtime +30 -delete 2>/dev/null || true

log_info "=========================================="
if [ "$SERVICES_OK" = true ]; then
    log_info "${GREEN}Deployment completed successfully!${NC}"
else
    log_warn "${YELLOW}Deployment completed with some warnings${NC}"
    log_warn "Please check the service logs above"
fi
log_info "=========================================="
log_info ""
log_info "Deployment summary:"
log_info "  - Branch: $BRANCH"
log_info "  - Commit: $(git rev-parse --short HEAD)"
log_info "  - Time: $(date '+%Y-%m-%d %H:%M:%S')"
log_info ""
log_info "Useful commands:"
log_info "  - Check logs: logs-gunicorn, logs-celery, logs-nginx, logs-django"
log_info "  - Restart services: restart-app"
log_info "  - Check status: status-app"
log_info ""

# Send deployment notification (optional)
if command -v curl &> /dev/null && [ -n "$SLACK_WEBHOOK_URL" ]; then
    log_info "Sending deployment notification..."
    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"AlgoItny deployed successfully\nBranch: $BRANCH\nCommit: $(git rev-parse --short HEAD)\nTime: $(date '+%Y-%m-%d %H:%M:%S')\"}" \
        "$SLACK_WEBHOOK_URL" 2>/dev/null || true
fi

# Create deployment log
DEPLOY_LOG_DIR="/home/algoitny/logs/deployments"
mkdir -p "$DEPLOY_LOG_DIR"
echo "$(date '+%Y-%m-%d %H:%M:%S') - Branch: $BRANCH - Commit: $(git rev-parse --short HEAD) - Status: Success" >> "$DEPLOY_LOG_DIR/deployment.log"

exit 0
