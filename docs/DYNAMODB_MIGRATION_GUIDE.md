# DynamoDB Migration Guide

## Overview

This guide walks you through migrating from MySQL to DynamoDB using LocalStack for local development.

## Architecture

### Design Document
See `DYNAMODB_SINGLE_TABLE_DESIGN_V2.md` for complete design details including:
- Single-table design with 2 GSIs
- Short field names for cost optimization
- Access patterns and query examples
- Cost analysis

### Implementation Structure

```
backend/
├── api/dynamodb/
│   ├── client.py                    # DynamoDB client (LocalStack/AWS)
│   ├── table_schema.py              # Table creation schema
│   └── repositories/
│       ├── base_repository.py       # Base CRUD operations
│       ├── user_repository.py       # User entity
│       ├── problem_repository.py    # Problem & TestCase entities
│       ├── search_history_repository.py  # SearchHistory entity
│       └── usage_log_repository.py  # UsageLog (rate limiting hot path)
└── scripts/
    ├── init_dynamodb.py             # Initialize DynamoDB table
    ├── migrate_to_dynamodb.py       # Migrate data from MySQL
    └── verify_migration.py          # Verify migration success
```

## Prerequisites

1. **Docker Compose** - Services are running
2. **LocalStack** - DynamoDB service enabled in docker-compose.yml
3. **boto3** - Already added to requirements.txt

## Quick Start

### 1. Initialize DynamoDB Table

```bash
make dynamodb-init
```

This creates the `algoitny_main` table with 2 GSIs in LocalStack.

### 2. Test Migration (Dry Run)

```bash
make dynamodb-migrate-dry-run
```

Shows what will be migrated without actually migrating.

### 3. Run Migration

```bash
make dynamodb-migrate
```

Migrates all data from MySQL to DynamoDB:
- Users
- Problems & TestCases
- SearchHistory
- UsageLogs

### 4. Verify Migration

```bash
make dynamodb-verify
```

Compares MySQL and DynamoDB data counts.

## Detailed Commands

### Initialization

```bash
# Initialize DynamoDB table (LocalStack)
make dynamodb-init

# Or manually:
docker-compose exec backend python scripts/init_dynamodb.py
```

### Migration Options

```bash
# Migrate all entities
make dynamodb-migrate

# Migrate specific entities
make dynamodb-migrate-users      # Users only
make dynamodb-migrate-problems   # Problems + TestCases
make dynamodb-migrate-history    # SearchHistory only

# Dry run (no actual migration)
make dynamodb-migrate-dry-run

# Custom batch size
docker-compose exec backend python scripts/migrate_to_dynamodb.py --entity all --batch-size 50
```

### Verification

```bash
# Verify migration
make dynamodb-verify

# Or manually:
docker-compose exec backend python scripts/verify_migration.py
```

## Environment Configuration

### LocalStack (Development)

Already configured in `docker-compose.yml`:

```yaml
localstack:
  environment:
    - SERVICES=sqs,dynamodb
    - LOCALSTACK_URL=http://localstack:4566
```

All services automatically connect to LocalStack when `LOCALSTACK_URL` is set.

### AWS (Production)

Remove or unset `LOCALSTACK_URL` environment variable. Configure AWS credentials:

```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

## Repository Usage

### Example: User Repository

```python
from api.dynamodb.client import DynamoDBClient
from api.dynamodb.repositories import UserRepository

# Initialize
table = DynamoDBClient.get_table()
user_repo = UserRepository(table)

# Create user
user = user_repo.create_user({
    'user_id': 12345,
    'email': 'user@example.com',
    'name': 'John Doe',
    'subscription_plan_id': 1,
    'is_active': True,
    'is_staff': False
})

# Get user by email (GSI1 query)
user = user_repo.get_user_by_email('user@example.com')

# Update user
user_repo.update_user(12345, {'name': 'Jane Doe'})
```

### Example: Rate Limiting (Hot Path)

```python
from api.dynamodb.repositories import UsageLogRepository

usage_repo = UsageLogRepository(table)

# Check rate limit (called on EVERY request)
allowed, count, reset_time = usage_repo.check_rate_limit(
    user_id=12345,
    action='hint',
    limit=5
)

if not allowed:
    raise RateLimitExceeded(f"Limit exceeded. Resets at {reset_time}")

# Log usage
usage_repo.log_usage(
    user_id=12345,
    action='hint',
    problem_id=100,
    metadata={'history_id': 5000}
)
```

## Performance Characteristics

| Operation | Latency | Cost (per 1000 ops) |
|-----------|---------|---------------------|
| Rate limit check | 1-3ms | $0.0005 (0.5 RCU) |
| User login (GSI1) | 3-5ms | $0.0005 (0.5 RCU) |
| Problem lookup | 1-3ms | $0.0005 (0.5 RCU) |
| Public history (GSI2) | 10-20ms | $0.001 (1-2 RCU) |
| Create user | 5-10ms | $0.00125 (1.25 WCU) |

## Cost Optimization

### Short Field Names
Reduces storage costs by ~40%:
- `email` → `em`
- `name` → `nm`
- `is_active` → `act`

### Strategic GSIs
Only 2 GSIs for critical hot paths:
1. **GSI1**: User authentication (5K req/min)
2. **GSI2**: Public history timeline (800 req/min)

### TTL Auto-Expiry
UsageLog entries auto-delete after 90 days, reducing storage costs by 70%.

## Troubleshooting

### Table Already Exists

```bash
# Delete and recreate
docker-compose exec backend python -c "
from api.dynamodb.client import DynamoDBClient
from api.dynamodb.table_schema import delete_table
client = DynamoDBClient.get_client()
delete_table(client)
"

make dynamodb-init
```

### Migration Fails

Check logs:
```bash
docker-compose logs backend
```

Re-run specific entity:
```bash
make dynamodb-migrate-users
```

### LocalStack Not Running

```bash
# Check status
docker-compose ps localstack

# Restart
docker-compose restart localstack

# Check health
curl http://localhost:4566/_localstack/health
```

## Migration Checklist

- [ ] Review design document: `DYNAMODB_SINGLE_TABLE_DESIGN_V2.md`
- [ ] LocalStack running with DynamoDB enabled
- [ ] Run `make dynamodb-init` to create table
- [ ] Run `make dynamodb-migrate-dry-run` to test
- [ ] Run `make dynamodb-migrate` to migrate all data
- [ ] Run `make dynamodb-verify` to verify counts
- [ ] Test repository operations manually
- [ ] Update Django views to use repositories (future work)
- [ ] Deploy to production AWS (when ready)

## Next Steps

1. **Local Testing** - Test all repository operations
2. **Integration** - Update Django views to use repositories
3. **Dual Write** - Write to both MySQL and DynamoDB during transition
4. **Production Deploy** - Deploy DynamoDB table to AWS
5. **Cut Over** - Switch all reads to DynamoDB
6. **MySQL Deprecation** - Remove MySQL after validation period

## References

- Design: `DYNAMODB_SINGLE_TABLE_DESIGN_V2.md`
- Help: `make dynamodb-help`
- LocalStack Docs: https://docs.localstack.cloud/user-guide/aws/dynamodb/
- Boto3 DynamoDB: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/dynamodb.html
