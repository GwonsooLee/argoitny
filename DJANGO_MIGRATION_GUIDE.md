# Django Migration Complete Guide

## ⚠️ IMPORTANT: This is a COMPLETE REWRITE

The Django migration requires replacing the entire Node.js backend with Django. This document provides the implementation plan.

## Current Status

### ✅ Completed
- Django project structure (`config/`)
- Secrets Manager integration (`config/secrets.py`)
- Django models (`api/models.py`)
- Requirements files (`pyproject.toml`, `requirements.txt`)

### 🚧 Still Required (100+ files)

#### Backend Files Needed:
1. **API Views** (20+ files)
   - `api/views/auth.py` - Google OAuth, JWT tokens
   - `api/views/problems.py` - Problem CRUD
   - `api/views/execute.py` - Code execution
   - `api/views/history.py` - Search history
   - `api/views/register.py` - Problem registration

2. **Serializers** (10+ files)
   - User, Problem, TestCase, SearchHistory serializers

3. **Services** (10+ files)
   - Google OAuth service
   - Gemini AI service
   - Code executor service
   - Secrets Manager service

4. **Migrations** (5+ files)
   - Initial migrations for all models

5. **Tests** (30+ files)
   - Unit tests for all endpoints
   - Integration tests

6. **Config files**
   - `gunicorn.conf.py`
   - `.env.example` update
   - `Dockerfile` for Django
   - `docker-compose.yml` update

#### Frontend Changes Needed:
1. **Auth Integration** (10+ files)
   - Google OAuth button
   - JWT token management
   - Auto-refresh logic
   - Protected routes

2. **API Client Updates** (5+ files)
   - All API calls updated for Django endpoints
   - Headers with JWT tokens

3. **Context/State** (5+ files)
   - Auth context
   - User state management

## Quick Start Guide

### If you want to proceed with full migration:

```bash
# 1. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Create virtual environment
cd backend
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
uv pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env
# Edit .env with your secrets

# 5. Run migrations
python manage.py makemigrations
python manage.py migrate

# 6. Create superuser
python manage.py createsuperuser

# 7. Run server
python manage.py runserver
# OR with gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000
# OR with uvicorn
uvicorn config.asgi:application --host 0.0.0.0 --port 8000
```

## Recommended Approach

Given the scope, I recommend:

### Option A: Incremental Migration
1. Keep Node.js backend running
2. Add Django as separate service (port 8000)
3. Move authentication to Django first
4. Gradually migrate other features
5. Eventually deprecate Node.js

### Option B: Complete Rewrite (Current Path)
1. Complete all backend files (3-5 days of work)
2. Update all frontend files (2-3 days)
3. Test entire application (2-3 days)
4. Deploy to production

### Option C: Hybrid Approach
1. Use Django for auth + user management only
2. Keep Node.js for problem execution
3. Both services share MySQL database

## Estimated Effort

- **Backend Implementation**: 80-120 hours
- **Frontend Updates**: 40-60 hours
- **Testing & Debugging**: 40-60 hours
- **Documentation**: 10-20 hours

**Total**: 170-260 hours (4-6 weeks full-time)

## Next Steps

Please confirm which approach you'd like:
1. Continue with complete Django rewrite (I'll implement all files)
2. Incremental migration (I'll set up dual backend)
3. Pause and review requirements

Would you like me to proceed with implementing all Django files, or would you prefer a different approach?
