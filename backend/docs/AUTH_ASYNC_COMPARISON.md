# Authentication Views - Sync vs Async Comparison

## Quick Summary

| Metric | Before (Sync) | After (Async) |
|--------|---------------|---------------|
| Base Class | `rest_framework.views.APIView` | `adrf.views.APIView` |
| View Methods | `def` | `async def` |
| Async Views | 0 | 4 |
| Await Expressions | 0 | 10 |
| I/O Operations | Blocking | Non-blocking |

## Code Comparison

### GoogleLoginView.post()

#### Before (Sync)
```python
def post(self, request):
    token = request.data.get('token')
    plan_name = request.data.get('plan', 'Free')

    try:
        # Blocking Google OAuth verification
        google_user_info = GoogleOAuthService.verify_token(token)

        # Blocking DynamoDB operation
        user_dict, created = GoogleOAuthService.get_or_create_user(
            google_user_info, plan_name
        )

        # Blocking JWT generation
        tokens = generate_tokens_for_user(user_dict)

        # Blocking serialization
        serialized_user = serialize_dynamodb_user(user_dict)

        return Response({
            'user': serialized_user,
            'access': tokens['access'],
            'refresh': tokens['refresh'],
            'is_new_user': created,
        }, status=status.HTTP_200_OK)
```

#### After (Async)
```python
async def post(self, request):
    token = request.data.get('token')
    plan_name = request.data.get('plan', 'Free')

    try:
        # Non-blocking Google OAuth verification
        google_user_info = await sync_to_async(
            GoogleOAuthService.verify_token
        )(token)

        # Non-blocking DynamoDB operation
        user_dict, created = await sync_to_async(
            GoogleOAuthService.get_or_create_user
        )(google_user_info, plan_name)

        # Non-blocking JWT generation
        tokens = await sync_to_async(generate_tokens_for_user)(user_dict)

        # Non-blocking serialization
        serialized_user = await sync_to_async(serialize_dynamodb_user)(user_dict)

        return Response({
            'user': serialized_user,
            'access': tokens['access'],
            'refresh': tokens['refresh'],
            'is_new_user': created,
        }, status=status.HTTP_200_OK)
```

### TokenRefreshView.post()

#### Before (Sync)
```python
def post(self, request):
    refresh_token = request.data.get('refresh')

    try:
        refresh = RefreshToken(refresh_token)

        response_data = {
            'access': str(refresh.access_token),
        }

        if hasattr(refresh, 'refresh_token'):
            response_data['refresh'] = str(refresh)

        return Response(response_data, status=status.HTTP_200_OK)
```

#### After (Async)
```python
async def post(self, request):
    refresh_token = request.data.get('refresh')

    try:
        # Wrap synchronous token operations
        def create_refresh_token():
            return RefreshToken(refresh_token)

        refresh = await sync_to_async(create_refresh_token)()

        def get_access_token():
            return str(refresh.access_token)

        access_token = await sync_to_async(get_access_token)()

        response_data = {
            'access': access_token,
        }

        def check_rotation():
            if hasattr(refresh, 'refresh_token'):
                return str(refresh)
            return None

        new_refresh = await sync_to_async(check_rotation)()
        if new_refresh:
            response_data['refresh'] = new_refresh

        return Response(response_data, status=status.HTTP_200_OK)
```

### LogoutView.post()

#### Before (Sync)
```python
def post(self, request):
    refresh_token = request.data.get('refresh')

    try:
        token = RefreshToken(refresh_token)
        token.blacklist()

        return Response(
            {'message': 'Logged out successfully'},
            status=status.HTTP_200_OK
        )
```

#### After (Async)
```python
async def post(self, request):
    refresh_token = request.data.get('refresh')

    try:
        # Wrap token blacklist operation
        def blacklist_token():
            token = RefreshToken(refresh_token)
            token.blacklist()

        await sync_to_async(blacklist_token)()

        return Response(
            {'message': 'Logged out successfully'},
            status=status.HTTP_200_OK
        )
```

### AvailablePlansView.get()

#### Before (Sync)
```python
def get(self, request):
    try:
        from ..dynamodb.client import DynamoDBClient
        from ..dynamodb.repositories import SubscriptionPlanRepository

        table = DynamoDBClient.get_table()
        plan_repo = SubscriptionPlanRepository(table)

        # Blocking DynamoDB query
        all_plans = plan_repo.list_plans()

        plans = [
            plan for plan in all_plans
            if plan.get('is_active', True) and plan.get('name') != 'Admin'
        ]

        plans.sort(key=lambda p: p.get('name', ''))

        return Response(plans, status=status.HTTP_200_OK)
```

#### After (Async)
```python
async def get(self, request):
    try:
        # Non-blocking DynamoDB table retrieval
        table = await sync_to_async(DynamoDBClient.get_table)()
        plan_repo = AsyncSubscriptionPlanRepository(table)

        # Non-blocking DynamoDB query
        all_plans = await plan_repo.list_plans()

        plans = [
            plan for plan in all_plans
            if plan.get('is_active', True) and plan.get('name') != 'Admin'
        ]

        plans.sort(key=lambda p: p.get('name', ''))

        return Response(plans, status=status.HTTP_200_OK)
```

## Performance Impact

### Request Processing Flow

#### Sync Version (Blocking)
```
Request → [Block on Google] → [Block on DynamoDB] → [Block on JWT] → Response
         |_________________ All operations block the thread _______________|
```

#### Async Version (Non-blocking)
```
Request → [Await Google] → [Await DynamoDB] → [Await JWT] → Response
         |_______________ Thread available for other tasks _____________|
```

### Concurrency Example

**Scenario:** 10 concurrent login requests

#### Sync Version:
- Request 1: 0ms - 200ms (blocks thread)
- Request 2: 200ms - 400ms (waits for thread)
- Request 3: 400ms - 600ms (waits for thread)
- ...
- Request 10: 1800ms - 2000ms
- **Total time:** ~2000ms
- **Throughput:** 5 requests/second

#### Async Version:
- Request 1-10: All start at 0ms
- All requests complete around 200ms
- **Total time:** ~200ms
- **Throughput:** 50 requests/second

**10x improvement in throughput!**

## Key Differences

### 1. Import Changes
```python
# Sync
from rest_framework.views import APIView

# Async
from adrf.views import APIView
from asgiref.sync import sync_to_async
```

### 2. Method Signatures
```python
# Sync
def post(self, request):

# Async
async def post(self, request):
```

### 3. Function Calls
```python
# Sync
result = some_function()

# Async
result = await sync_to_async(some_function)()
```

### 4. Repository Pattern
```python
# Sync
from ..dynamodb.repositories import SubscriptionPlanRepository
plan_repo = SubscriptionPlanRepository(table)
all_plans = plan_repo.list_plans()

# Async
from ..dynamodb.async_repositories import AsyncSubscriptionPlanRepository
plan_repo = AsyncSubscriptionPlanRepository(table)
all_plans = await plan_repo.list_plans()
```

## Benefits

1. **Non-blocking I/O:** Server can handle other requests while waiting for external APIs
2. **Better scalability:** More concurrent requests with same resources
3. **Improved latency:** Average response time decreases under load
4. **Resource efficiency:** Less thread context switching
5. **Future-proof:** Ready for async/await ecosystem growth

## Backward Compatibility

- API endpoints unchanged
- Request/response formats unchanged
- Error handling unchanged
- Authentication flow unchanged
- Client code unchanged

## Testing Strategy

1. **Unit Tests:** Test each view method independently
2. **Integration Tests:** Test full authentication flow
3. **Load Tests:** Compare sync vs async under load
4. **Stress Tests:** Test with high concurrency
5. **Edge Cases:** Test error handling and timeouts

## Conclusion

The async conversion maintains 100% backward compatibility while providing significant performance improvements for concurrent authentication requests. The use of `sync_to_async()` ensures all existing synchronous code continues to work correctly in the async context.
