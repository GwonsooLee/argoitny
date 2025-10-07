# Configuration & Secrets Quick Start

This is a quick guide to get started with AlgoItny configuration and secrets management.

**📖 Complete Documentation:**
- **Secrets (passwords, API keys)**: [SECRETS_MANAGEMENT.md](SECRETS_MANAGEMENT.md)
- **Configuration (app settings)**: [CONFIGURATION_MANAGEMENT.md](CONFIGURATION_MANAGEMENT.md)

## 🚀 Quick Setup

### For Local Development

1. **Set required SECRETS as environment variables:**
   ```bash
   # Generate a new secret key
   export SECRET_KEY="$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')"

   # Database password
   export DB_PASSWORD="your-local-db-password"

   # Gemini API key for AI features
   export GEMINI_API_KEY="your-gemini-api-key"

   # Google OAuth credentials
   export GOOGLE_CLIENT_ID="your-google-client-id"
   export GOOGLE_CLIENT_SECRET="your-google-client-secret"
   ```

2. **[Optional] Copy and customize configuration:**
   ```bash
   cp config/config.example.yaml config/config.yaml
   # Edit config/config.yaml with your settings (database host, Redis, etc.)
   ```

3. **Run the application:**
   ```bash
   python manage.py runserver
   ```

### For Docker/Docker Compose

1. **Create `.env` file:**
   ```bash
   SECRET_KEY=your-secret-key
   DB_PASSWORD=your-db-password
   GEMINI_API_KEY=your-gemini-api-key
   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   ```

2. **Optional: Create `config/config.yaml`** or use defaults

3. **Run with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

### For Kubernetes

1. **Create ConfigMap from config file:**
   ```bash
   kubectl create configmap algoitny-backend-config \
     --from-file=config.yaml=config/config.yaml
   ```

2. **Create Secret for sensitive data:**
   ```bash
   kubectl create secret generic algoitny-backend-secrets \
     --from-literal=SECRET_KEY='your-secret-key' \
     --from-literal=DB_PASSWORD='your-db-password' \
     --from-literal=GEMINI_API_KEY='your-gemini-key'
   ```

3. **Deploy:**
   ```bash
   kubectl apply -f k8s/configmap.yaml
   ```

## 📋 Priority System

### Secrets (Sensitive Data)
```
AWS Secrets Manager (highest priority)
         ↓
Environment Variables
         ↓
Legacy secrets.py (deprecated)
         ↓
Default Values (lowest priority)
```

### Configuration (Non-Sensitive)
```
Environment Variables (highest priority)
         ↓
Configuration File (config.yaml)
         ↓
Default Values (lowest priority)
```

## 🔐 Security Best Practices

### SECRETS (Use SecretsManager)

✅ **Store in AWS Secrets Manager (Production):**
- SECRET_KEY
- DB_PASSWORD
- GEMINI_API_KEY
- GOOGLE_CLIENT_ID
- GOOGLE_CLIENT_SECRET
- REDIS_PASSWORD
- EMAIL_HOST_USER
- EMAIL_HOST_PASSWORD
- All other passwords/API keys

✅ **Store in Environment Variables (Development):**
- Same as above, for local development

❌ **NEVER store in files or version control:**
- No passwords in config.yaml
- No API keys in config files
- No secrets in Git

### CONFIGURATION (Use ConfigLoader)

✅ **Store in Config File (config.yaml):**
- Application settings (debug, allowed hosts)
- Database connection info (host, port, name, user) - NOT password
- Cache settings (host, port) - NOT password
- Celery settings
- Email configuration (host, port) - NOT credentials

✅ **Can commit to Git:**
- `config/config.example.yaml` (template without secrets)

❌ **Never commit to Git:**
- `config/config.yaml` (your local/production config)
- `config/secrets.py` (legacy, deprecated)

## 📚 Key Configuration Sections

### Django Settings
```yaml
django:
  debug: false
  allowed_hosts:
    - api.example.com
```

### Database
```yaml
database:
  host: mysql-service
  port: 3306
  name: algoitny
  user: algoitny
  # password: Set via DB_PASSWORD env var
```

### Cache (Redis)
```yaml
cache:
  enable_redis: true
  redis:
    host: redis-service
    port: 6379
```

### Celery
```yaml
celery:
  broker_url: "redis://redis-service:6379/0"
  worker_concurrency: 4
```

## 🧪 Testing Configuration

```bash
# Install dependencies
pip install pyyaml

# Run config tests
pytest tests/test_config.py -v

# Test config loading in Django shell
python manage.py shell

>>> from api.utils.config import ConfigLoader
>>> config = ConfigLoader.load()
>>> config.get('django.debug')
False
```

## 🐛 Troubleshooting

### "Configuration file not found"
- Check `CONFIG_FILE` environment variable
- Verify file exists at expected location
- Check file permissions

### "Secret key not set"
- Ensure `SECRET_KEY` environment variable is set
- Or set in `config/secrets.py` (legacy)
- Generate new key: `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`

### Values not updating
- Restart application after config changes
- For Kubernetes: `kubectl rollout restart deployment algoitny-backend`
- ConfigMaps don't auto-reload, pods must be restarted

### Type errors
```python
# Use typed getters
port = config.get_int('database.port')  # ✅ Returns int
debug = config.get_bool('django.debug')  # ✅ Returns bool

# Instead of
port = config.get('database.port')  # ❌ Might return string
```

## 📖 Full Documentation

### Secrets (Passwords, API Keys)
**[SECRETS_MANAGEMENT.md](SECRETS_MANAGEMENT.md)** - Complete guide including:
- AWS Secrets Manager setup
- IAM permissions
- Secret rotation
- Security best practices
- Troubleshooting

### Configuration (Application Settings)
**[CONFIGURATION_MANAGEMENT.md](CONFIGURATION_MANAGEMENT.md)** - Complete guide including:
- Detailed API reference
- Kubernetes ConfigMap examples
- Migration guide
- Best practices

## 🆘 Getting Help

1. Review [CONFIGURATION_MANAGEMENT.md](CONFIGURATION_MANAGEMENT.md)
2. Check test examples in `tests/test_config.py`
3. Examine `config/config.example.yaml` for all options
4. Review Kubernetes examples in `k8s/configmap.yaml`

---

**Need more details?** → [Full Documentation](CONFIGURATION_MANAGEMENT.md)
