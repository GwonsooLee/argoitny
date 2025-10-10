# Claude Code Instructions

## IMPORTANT: Server Reload Policy

**⚠️ ALWAYS use Docker Compose to restart the server after code changes.**

### Server Restart Command

When code is modified and needs to be reloaded:

**IMPORTANT: Must be run from `/Users/gwonsoolee/algoitny` directory**

```bash
# From algoitny directory (/Users/gwonsoolee/algoitny)
docker-compose restart backend
```

### Check Logs After Restart

```bash
docker logs -f algoitny-backend
```

### DO NOT Use Local Development Server

- ❌ Do NOT use `python manage.py runserver`
- ❌ Do NOT run the server directly with LOCALSTACK_URL
- ✅ ALWAYS use `docker-compose restart backend`

This ensures:
- Consistent environment across development
- Proper container isolation
- Correct service dependencies
- Clean server state on each restart

## CRITICAL: Port 8000 Policy

**⚠️ NEVER kill processes on local port 8000**

- ❌ Do NOT run `lsof -ti:8000 | xargs kill`
- ❌ Do NOT kill processes running on port 8000
- ✅ Leave local port 8000 processes running

The user may have local development servers running on port 8000 that should NOT be terminated.

## CRITICAL: Async/Await Architecture

**⚠️ ALL services MUST support async/await**

### Async Requirements

- ✅ All view functions MUST be async (use `adrf.views.APIView`)
- ✅ All repository methods MUST be truly async (use `aioboto3`, NOT `sync_to_async` wrappers)
- ✅ All database operations MUST use `aioboto3` for async DynamoDB access
- ✅ All external API calls MUST use async HTTP clients (`httpx`, `aiohttp`)
- ❌ Do NOT use `sync_to_async` to wrap synchronous boto3 code
- ❌ Do NOT mix sync boto3 with async aioboto3

### Why Async is Required

- The application uses ASGI (Daphne) for async request handling
- Mixing sync and async code causes event loop conflicts
- `sync_to_async` creates threading overhead and potential deadlocks
- True async provides better performance and scalability
