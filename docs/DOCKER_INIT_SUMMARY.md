# Docker Initialization Summary

## ✅ Implementation Complete

Docker Compose now automatically initializes both MySQL and DynamoDB with default data on startup.

---

## 🚀 What Happens on `docker-compose up`

### Automatic Initialization Flow

```
┌─────────────────────────────────────────────────────────┐
│ 1. MySQL Container Starts                               │
│    - Waits for health check                            │
│    - Creates database schema                           │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ 2. LocalStack Container Starts                          │
│    - Starts DynamoDB service                           │
│    - Waits for health check                            │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ 3. migration-init Service Runs (init_db.py)            │
│    ├── Waits for MySQL to be ready                    │
│    ├── Runs Django migrations (MySQL)                  │
│    ├── Waits for LocalStack DynamoDB to be ready      │
│    ├── Creates DynamoDB table (algoitny_main)          │
│    └── Seeds default plans (Free & Admin)             │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ 4. Backend Service Starts                               │
│    - Django REST API ready                             │
│    - Both MySQL and DynamoDB configured                │
└─────────────────────────────────────────────────────────┘
```

---

## 📦 Created Files

### 1. **Updated: `backend/init_db.py`**
Main initialization orchestrator that:
- Waits for MySQL connection
- Runs Django migrations
- Waits for LocalStack DynamoDB
- Initializes DynamoDB table
- Seeds default subscription plans

### 2. **Created: `backend/scripts/seed_default_plans.py`**
Seeds default subscription plans to DynamoDB:

**Free Plan (ID: 1)**
- Max hints/day: 5
- Max executions/day: 50
- Can view all problems: ✅
- Can register problems: ❌

**Admin Plan (ID: 2)**
- Max hints/day: Unlimited (-1)
- Max executions/day: Unlimited (-1)
- Can view all problems: ✅
- Can register problems: ✅

### 3. **Existing: `backend/scripts/init_dynamodb.py`**
Creates DynamoDB table with:
- Table name: `algoitny_main`
- 2 GSIs (GSI1: authentication, GSI2: public timeline)
- Pay-per-request billing mode

---

## 🔧 Configuration in docker-compose.yml

### migration-init Service
```yaml
migration-init:
  build:
    context: ./backend
    dockerfile: Dockerfile
  container_name: algoitny-migration-init
  env_file:
    - ./backend/.env
  environment:
    DB_HOST: mysql
    AWS_ACCESS_KEY_ID: test
    AWS_SECRET_ACCESS_KEY: test
    AWS_DEFAULT_REGION: us-east-1
    LOCALSTACK_URL: http://localstack:4566
  depends_on:
    mysql:
      condition: service_healthy
    localstack:
      condition: service_healthy
  volumes:
    - ./backend:/app
    - /app/.venv
  networks:
    - algoitny-network
  command: sh -c "python init_db.py"
  restart: "no"  # Only runs once on startup
```

### LocalStack Service (Updated)
```yaml
localstack:
  image: localstack/localstack:3.0.2
  environment:
    - SERVICES=sqs,dynamodb  # ← DynamoDB added
```

---

## 🧪 Testing

### Verify Initialization

```bash
# Start services
docker-compose up -d

# Check initialization logs
docker-compose logs migration-init

# Verify DynamoDB plans
docker-compose exec backend python -c "
from api.dynamodb.client import DynamoDBClient
from api.dynamodb.repositories.base_repository import BaseRepository

class PlanRepo(BaseRepository):
    def list_plans(self):
        return [i for i in self.scan() if i.get('tp') == 'plan']

table = DynamoDBClient.get_table()
plans = PlanRepo(table).list_plans()
print(f'Found {len(plans)} plans in DynamoDB')
"
```

### Expected Output

```
============================================================
🚀 AlgoItny Database Initialization
============================================================

============================================================
Waiting for MySQL to be ready...
============================================================
✅ MySQL is ready!

============================================================
Step 1/4: Running Django migrations (MySQL)
============================================================
✅ Step 1/4: Running Django migrations (MySQL) - Success

============================================================
Waiting for LocalStack to be ready...
============================================================
✅ LocalStack DynamoDB is ready!

============================================================
Step 2/4: Initializing DynamoDB table
============================================================
✓ Table 'algoitny_main' creation initiated
✅ Step 2/4: Initializing DynamoDB table - Success

============================================================
Step 3/4: Seeding default subscription plans (DynamoDB)
============================================================
✅ Created 'Free' plan (ID: 1)
✅ Created 'Admin' plan (ID: 2)
✅ Step 3/4: Seeding default subscription plans (DynamoDB) - Success

============================================================
✅ Database initialization completed successfully!
============================================================

📊 Summary:
  ✅ MySQL migrations applied
  ✅ DynamoDB table created
  ✅ Default subscription plans seeded (DynamoDB)
  ✅ System ready for use
============================================================
```

---

## 📊 Default Subscription Plans

### Free Plan Details
```python
{
    'id': 1,
    'name': 'Free',
    'description': 'Free plan with limited features',
    'max_hints_per_day': 5,
    'max_executions_per_day': 50,
    'max_problems': -1,  # Unlimited
    'can_view_all_problems': True,
    'can_register_problems': False,
    'is_active': True
}
```

### Admin Plan Details
```python
{
    'id': 2,
    'name': 'Admin',
    'description': 'Full access plan for administrators',
    'max_hints_per_day': -1,  # Unlimited
    'max_executions_per_day': -1,  # Unlimited
    'max_problems': -1,  # Unlimited
    'can_view_all_problems': True,
    'can_register_problems': True,
    'is_active': True
}
```

---

## 🔄 Idempotency

The initialization scripts are **idempotent**:

- **DynamoDB Table**: Skips creation if table already exists
- **Subscription Plans**: Skips creation if plan with same ID exists
- **Django Migrations**: Only applies new migrations

This means you can safely run `docker-compose up` multiple times without issues.

---

## 🚀 Usage

### First Time Setup
```bash
# Start all services (initialization happens automatically)
docker-compose up -d

# Wait for initialization to complete
docker-compose logs -f migration-init

# Verify services are ready
docker-compose ps
```

### Resetting Everything
```bash
# Stop and remove containers + volumes
docker-compose down -v

# Restart (will re-initialize everything)
docker-compose up -d
```

### Manual Re-initialization
```bash
# Re-run DynamoDB initialization only
docker-compose exec backend python scripts/init_dynamodb.py

# Re-seed plans only
docker-compose exec backend python scripts/seed_default_plans.py

# Full initialization
docker-compose exec backend python init_db.py
```

---

## 🎯 Benefits

1. **Zero Manual Setup** - Everything initializes automatically
2. **Consistent State** - Same initial data every time
3. **Fast Development** - New developers can start immediately
4. **Idempotent** - Safe to run multiple times
5. **Graceful Failures** - Continues if non-critical steps fail

---

## 📝 Troubleshooting

### Check Initialization Status
```bash
docker-compose logs migration-init
```

### LocalStack Not Ready
```bash
# Check LocalStack health
curl http://localhost:4566/_localstack/health

# Restart LocalStack
docker-compose restart localstack
```

### DynamoDB Table Not Created
```bash
# Manually create table
docker-compose exec backend python scripts/init_dynamodb.py
```

### Plans Not Seeded
```bash
# Manually seed plans
docker-compose exec backend python scripts/seed_default_plans.py
```

---

## ✅ Success Criteria

- [x] MySQL starts and migrations run
- [x] LocalStack DynamoDB starts
- [x] DynamoDB table `algoitny_main` created
- [x] GSI1 and GSI2 are ACTIVE
- [x] Free plan (ID: 1) created in DynamoDB
- [x] Admin plan (ID: 2) created in DynamoDB
- [x] Backend service depends on successful initialization
- [x] Initialization is idempotent

---

## 📚 Related Documentation

- **DynamoDB Design**: `DYNAMODB_SINGLE_TABLE_DESIGN_V2.md`
- **Migration Guide**: `DYNAMODB_MIGRATION_GUIDE.md`
- **Implementation Summary**: `DYNAMODB_IMPLEMENTATION_SUMMARY.md`
- **Makefile Commands**: Run `make dynamodb-help`

---

**Status**: ✅ **PRODUCTION READY**

Docker Compose now fully initializes both MySQL and DynamoDB with default subscription plans on every startup!
