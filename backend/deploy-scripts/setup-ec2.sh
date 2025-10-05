#!/bin/bash
#
# AlgoItny EC2 Initial Setup Script
# This script automates the initial setup of an EC2 instance for Django deployment
#
# Usage: sudo bash setup-ec2.sh
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root (use sudo)"
    exit 1
fi

log_info "Starting AlgoItny EC2 setup..."

# Update system
log_info "Updating system packages..."
apt update && apt upgrade -y

# Install essential packages
log_info "Installing essential packages..."
apt install -y \
    build-essential \
    git \
    curl \
    wget \
    vim \
    nano \
    htop \
    net-tools \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    unzip

# Set timezone to UTC
log_info "Setting timezone to UTC..."
timedatectl set-timezone UTC

# Create application user
log_info "Creating application user 'algoitny'..."
if id "algoitny" &>/dev/null; then
    log_warn "User 'algoitny' already exists"
else
    useradd -m -s /bin/bash algoitny
    usermod -aG sudo algoitny
    echo "algoitny ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/algoitny
    log_info "User 'algoitny' created successfully"
fi

# Install Python 3.11
log_info "Installing Python 3.11..."
add-apt-repository ppa:deadsnakes/ppa -y
apt update
apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Set Python 3.11 as default
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
update-alternatives --set python3 /usr/bin/python3.11

log_info "Python version: $(python3 --version)"

# Install pip for Python 3.11
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11

# Install MySQL
log_info "Installing MySQL Server..."
apt install -y mysql-server mysql-client libmysqlclient-dev

# Start and enable MySQL
systemctl start mysql
systemctl enable mysql

log_info "MySQL installed successfully"

# Prompt for MySQL configuration
read -p "Do you want to configure MySQL database now? (y/n): " configure_mysql
if [ "$configure_mysql" = "y" ]; then
    log_info "Configuring MySQL..."
    read -p "Enter MySQL root password: " -s mysql_root_password
    echo
    read -p "Enter database name [algoitny]: " db_name
    db_name=${db_name:-algoitny}
    read -p "Enter database user [algoitny]: " db_user
    db_user=${db_user:-algoitny}
    read -p "Enter database password: " -s db_password
    echo

    # Create database and user
    mysql -u root -p"$mysql_root_password" <<EOF
CREATE DATABASE IF NOT EXISTS $db_name CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '$db_user'@'localhost' IDENTIFIED BY '$db_password';
GRANT ALL PRIVILEGES ON $db_name.* TO '$db_user'@'localhost';
FLUSH PRIVILEGES;
EOF

    log_info "MySQL database '$db_name' created successfully"
fi

# Configure MySQL for production
log_info "Configuring MySQL for production..."
cat >> /etc/mysql/mysql.conf.d/mysqld.cnf <<EOF

# AlgoItny Production Settings
max_connections = 500
innodb_buffer_pool_size = 1G
innodb_log_file_size = 256M
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
EOF

systemctl restart mysql

# Install Redis
log_info "Installing Redis..."
apt install -y redis-server

# Configure Redis
log_info "Configuring Redis..."
sed -i 's/supervised no/supervised systemd/' /etc/redis/redis.conf
sed -i 's/# maxmemory <bytes>/maxmemory 256mb/' /etc/redis/redis.conf
sed -i 's/# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/' /etc/redis/redis.conf

# Ensure Redis only listens on localhost
sed -i 's/bind .*/bind 127.0.0.1/' /etc/redis/redis.conf

systemctl restart redis-server
systemctl enable redis-server

log_info "Redis installed and configured"

# Test Redis
if redis-cli ping | grep -q PONG; then
    log_info "Redis is working correctly"
else
    log_warn "Redis test failed"
fi

# Install Nginx
log_info "Installing Nginx..."
apt install -y nginx

systemctl start nginx
systemctl enable nginx

log_info "Nginx installed successfully"

# Install Certbot for SSL
log_info "Installing Certbot..."
apt install -y certbot python3-certbot-nginx

# Create webroot for certbot
mkdir -p /var/www/certbot

log_info "Certbot installed successfully"

# Install UFW Firewall
log_info "Configuring UFW firewall..."
apt install -y ufw

# Configure UFW rules
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS

log_info "UFW firewall configured"

# Install Fail2Ban
log_info "Installing Fail2Ban..."
apt install -y fail2ban

# Create basic Fail2Ban configuration
cat > /etc/fail2ban/jail.local <<EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = 22
logpath = /var/log/auth.log

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/*error.log

[nginx-noscript]
enabled = true
port = http,https
filter = nginx-noscript
logpath = /var/log/nginx/*access.log
maxretry = 6
EOF

systemctl start fail2ban
systemctl enable fail2ban

log_info "Fail2Ban installed and configured"

# Enable automatic security updates
log_info "Enabling automatic security updates..."
apt install -y unattended-upgrades
dpkg-reconfigure -plow unattended-upgrades

# Create directory structure
log_info "Creating directory structure..."
sudo -u algoitny mkdir -p /home/algoitny/apps
sudo -u algoitny mkdir -p /home/algoitny/backups/mysql
sudo -u algoitny mkdir -p /home/algoitny/backups/app
sudo -u algoitny mkdir -p /home/algoitny/scripts
sudo -u algoitny mkdir -p /home/algoitny/logs

# Create log directories
mkdir -p /var/log/gunicorn
mkdir -p /var/log/celery
mkdir -p /var/log/django

chown algoitny:www-data /var/log/gunicorn
chown algoitny:www-data /var/log/celery
chown algoitny:www-data /var/log/django

# Install AWS CLI
log_info "Installing AWS CLI..."
if ! command -v aws &> /dev/null; then
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip awscliv2.zip
    ./aws/install
    rm -rf aws awscliv2.zip
    log_info "AWS CLI installed successfully"
else
    log_info "AWS CLI already installed"
fi

# Install monitoring tools
log_info "Installing monitoring tools..."
apt install -y htop iotop nethogs

# Optimize system settings
log_info "Optimizing system settings..."

# Increase file descriptors
cat >> /etc/security/limits.conf <<EOF

# AlgoItny optimization
* soft nofile 65536
* hard nofile 65536
EOF

# Optimize network settings
cat >> /etc/sysctl.conf <<EOF

# AlgoItny network optimization
net.core.somaxconn = 1024
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.ip_local_port_range = 10000 65000
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 30
EOF

sysctl -p

# SSH Hardening
log_info "Hardening SSH configuration..."
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/#PermitEmptyPasswords no/PermitEmptyPasswords no/' /etc/ssh/sshd_config

# Add these settings if they don't exist
grep -q "^MaxAuthTries" /etc/ssh/sshd_config || echo "MaxAuthTries 3" >> /etc/ssh/sshd_config
grep -q "^ClientAliveInterval" /etc/ssh/sshd_config || echo "ClientAliveInterval 300" >> /etc/ssh/sshd_config
grep -q "^ClientAliveCountMax" /etc/ssh/sshd_config || echo "ClientAliveCountMax 2" >> /etc/ssh/sshd_config

systemctl restart sshd

log_info "SSH hardened successfully"

# Create helpful aliases
log_info "Creating helpful aliases..."
sudo -u algoitny cat >> /home/algoitny/.bashrc <<'EOF'

# AlgoItny aliases
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'
alias app='cd /home/algoitny/apps/algoitny/backend'
alias venv='source /home/algoitny/apps/algoitny/backend/venv/bin/activate'
alias logs-gunicorn='sudo journalctl -u gunicorn -f'
alias logs-celery='sudo journalctl -u celery-worker -f'
alias logs-nginx='sudo tail -f /var/log/nginx/algoitny_error.log'
alias logs-django='sudo tail -f /var/log/django/error.log'
alias restart-app='sudo systemctl restart gunicorn celery-worker celery-beat nginx'
alias status-app='sudo systemctl status gunicorn celery-worker celery-beat nginx'

# Activate virtual environment on login
if [ -f /home/algoitny/apps/algoitny/backend/venv/bin/activate ]; then
    cd /home/algoitny/apps/algoitny/backend
    source venv/bin/activate
fi
EOF

# Clean up
log_info "Cleaning up..."
apt autoremove -y
apt autoclean -y

# Print summary
log_info "=========================================="
log_info "EC2 Setup Complete!"
log_info "=========================================="
log_info ""
log_info "Installed components:"
log_info "  - Python 3.11"
log_info "  - MySQL Server"
log_info "  - Redis"
log_info "  - Nginx"
log_info "  - Certbot (Let's Encrypt)"
log_info "  - UFW Firewall"
log_info "  - Fail2Ban"
log_info "  - AWS CLI"
log_info ""
log_info "Next steps:"
log_info "  1. Switch to algoitny user: sudo su - algoitny"
log_info "  2. Clone your repository: git clone <repo_url> /home/algoitny/apps/algoitny"
log_info "  3. Run deployment script: bash /home/algoitny/apps/algoitny/backend/deploy-scripts/deploy.sh"
log_info "  4. Configure SSL: sudo certbot --nginx -d api.testcase.run"
log_info ""
log_info "System will now reboot to apply all changes..."

# Ask for reboot
read -p "Reboot now? (y/n): " reboot_now
if [ "$reboot_now" = "y" ]; then
    log_info "Rebooting system..."
    reboot
else
    log_warn "Please reboot manually to apply all changes"
fi
