# AWS EC2 Deployment Checklist

Complete this checklist before and after deploying to production.

## Pre-Deployment Checklist

### 1. Code Preparation
- [ ] All code is committed and pushed to GitHub
- [ ] `.env.example` is up to date
- [ ] No sensitive data in code or version control
- [ ] Code passes all tests locally
- [ ] `requirements-production.txt` includes all dependencies

### 2. Environment Variables
- [ ] Generated new `SECRET_KEY` for production
- [ ] Set `DEBUG=False`
- [ ] Configured `ALLOWED_HOSTS` with actual domain
- [ ] Set strong database password
- [ ] Configured `CORS_ALLOWED_ORIGINS` with frontend domain
- [ ] Set `CSRF_TRUSTED_ORIGINS`
- [ ] All API keys are set (Google OAuth, Gemini, etc.)
- [ ] Email configuration is set up
- [ ] AWS credentials configured (if using S3/RDS)

### 3. AWS Setup
- [ ] EC2 instance launched and running
- [ ] Security group configured (ports 22, 80, 443)
- [ ] Elastic IP allocated and associated
- [ ] SSH key pair downloaded and secured (chmod 400)
- [ ] DNS A record configured (api.testcase.run)
- [ ] RDS instance created (optional)
- [ ] ElastiCache Redis created (optional)
- [ ] S3 bucket created for backups

### 4. Server Configuration
- [ ] Ran `setup-ec2.sh` script
- [ ] MySQL installed and configured
- [ ] Redis installed and running
- [ ] Nginx installed
- [ ] Python 3.11 installed
- [ ] UFW firewall enabled and configured
- [ ] Fail2Ban installed and running
- [ ] SSH hardened (no root login, key-based auth)

### 5. Application Setup
- [ ] Repository cloned to `/home/algoitny/apps/algoitny`
- [ ] Virtual environment created
- [ ] Dependencies installed from `requirements-production.txt`
- [ ] `.env` file created with production values
- [ ] Static files collected (`python manage.py collectstatic`)
- [ ] Database migrations run (`python manage.py migrate`)
- [ ] Superuser created

### 6. Service Configuration
- [ ] Gunicorn service file copied and enabled
- [ ] Celery worker service file copied and enabled
- [ ] Celery beat service file copied and enabled
- [ ] Nginx configuration copied and tested
- [ ] All services started and running
- [ ] Services set to auto-start on boot

### 7. SSL/HTTPS
- [ ] Certbot installed
- [ ] SSL certificate obtained (`sudo certbot --nginx`)
- [ ] Auto-renewal tested (`sudo certbot renew --dry-run`)
- [ ] HTTPS redirect working
- [ ] SSL Labs test passed (A rating or higher)

### 8. Testing
- [ ] Can access site via HTTPS
- [ ] Admin panel accessible and functional
- [ ] API endpoints responding correctly
- [ ] Authentication/login working
- [ ] Database connections working
- [ ] Redis/Celery tasks executing
- [ ] Static files loading correctly
- [ ] CORS working from frontend
- [ ] Error pages (404, 500) displaying correctly

## Post-Deployment Checklist

### 1. Service Verification
- [ ] Gunicorn service active: `sudo systemctl status gunicorn`
- [ ] Celery worker active: `sudo systemctl status celery-worker`
- [ ] Celery beat active: `sudo systemctl status celery-beat`
- [ ] Nginx active: `sudo systemctl status nginx`
- [ ] MySQL active: `sudo systemctl status mysql`
- [ ] Redis active: `sudo systemctl status redis`

### 2. Security Verification
- [ ] `python manage.py check --deploy` passes all checks
- [ ] UFW firewall active: `sudo ufw status`
- [ ] Fail2Ban active: `sudo systemctl status fail2ban`
- [ ] SSH only accepts key-based authentication
- [ ] No DEBUG mode in production
- [ ] Security headers present (check browser DevTools)
- [ ] HSTS header enabled
- [ ] No sensitive data exposed in error messages

### 3. Monitoring Setup
- [ ] CloudWatch agent installed and configured
- [ ] Log files rotating correctly
- [ ] Error logs being written to `/var/log/django/error.log`
- [ ] Nginx logs accessible
- [ ] Sentry configured (if using)
- [ ] Email notifications for errors working

### 4. Backup Configuration
- [ ] Database backup script created
- [ ] Backup cron job scheduled
- [ ] Backups uploading to S3
- [ ] Tested database restore from backup

### 5. Performance Optimization
- [ ] Gunicorn worker count appropriate for CPU
- [ ] Database connection pooling enabled
- [ ] Redis caching working
- [ ] Static files compressed (gzip)
- [ ] Database queries optimized
- [ ] No N+1 query issues

### 6. CI/CD Setup
- [ ] GitHub Actions workflow configured
- [ ] GitHub Secrets added:
  - [ ] `EC2_SSH_PRIVATE_KEY`
  - [ ] `EC2_HOST`
  - [ ] `EC2_USER`
  - [ ] `AWS_ACCESS_KEY_ID`
  - [ ] `AWS_SECRET_ACCESS_KEY`
- [ ] Test deployment workflow
- [ ] Auto-deployment on push to main working

### 7. Documentation
- [ ] Deployment guide reviewed
- [ ] Team notified of deployment
- [ ] Runbook for common issues created
- [ ] Access credentials shared securely

## Production Maintenance Checklist

### Daily
- [ ] Check error logs
- [ ] Monitor disk space
- [ ] Verify backups completed
- [ ] Check application uptime

### Weekly
- [ ] Review application logs
- [ ] Check server resource usage (CPU, RAM, disk)
- [ ] Review security logs
- [ ] Test backup restoration

### Monthly
- [ ] Update system packages: `sudo apt update && sudo apt upgrade`
- [ ] Review and rotate logs
- [ ] Check SSL certificate expiry
- [ ] Review database performance
- [ ] Check for Django/package updates
- [ ] Review AWS costs

### Quarterly
- [ ] Security audit
- [ ] Performance optimization review
- [ ] Disaster recovery drill
- [ ] Review and update documentation

## Emergency Procedures

### If Site is Down
1. Check service status: `status-app`
2. Check error logs: `logs-django`, `logs-gunicorn`, `logs-nginx`
3. Restart services: `restart-app`
4. Check database connection
5. Check Redis connection
6. Review recent deployments

### Rollback Procedure
1. SSH into server
2. `cd /home/algoitny/apps/algoitny`
3. `git log` to see recent commits
4. `git checkout [previous-commit-hash]`
5. `cd backend && source venv/bin/activate`
6. `python manage.py migrate`
7. `sudo systemctl restart gunicorn celery-worker`

### Database Recovery
1. Stop application: `sudo systemctl stop gunicorn celery-worker`
2. Restore from backup
3. Run migrations: `python manage.py migrate`
4. Restart application: `sudo systemctl start gunicorn celery-worker`

## Useful Commands Reference

```bash
# Service management
sudo systemctl status gunicorn celery-worker celery-beat nginx
sudo systemctl restart gunicorn celery-worker celery-beat nginx
sudo systemctl stop gunicorn celery-worker celery-beat

# Log monitoring
sudo journalctl -u gunicorn -f
sudo journalctl -u celery-worker -f
sudo tail -f /var/log/nginx/algoitny_error.log
sudo tail -f /var/log/django/error.log

# Django management
cd /home/algoitny/apps/algoitny/backend
source venv/bin/activate
python manage.py shell
python manage.py dbshell
python manage.py check --deploy

# Database
mysql -u algoitny -p algoitny
mysqldump -u algoitny -p algoitny > backup.sql

# Nginx
sudo nginx -t
sudo systemctl reload nginx

# SSL certificate
sudo certbot renew
sudo certbot certificates

# System monitoring
htop
df -h
free -h
systemctl list-units --failed
```

## Support Contacts

- **DevOps Lead**: [email@domain.com]
- **Backend Team**: [email@domain.com]
- **AWS Support**: [Support Plan Details]
- **On-Call Rotation**: [Link to Schedule]

---

**Last Updated**: 2025-10-06
**Deployment Version**: 1.0
