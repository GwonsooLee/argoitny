"""
Django models for AlgoItny - All models migrated to DynamoDB

This file is kept for Django compatibility but contains no ORM models.
All data operations use DynamoDB repositories.

For authentication, see:
- api/authentication.py (DynamoDB-based authentication backend)
- api/dynamodb/repositories/user_repository.py
- api/dynamodb/repositories/subscription_plan_repository.py
"""

# ALL MODELS HAVE BEEN MIGRATED TO DYNAMODB:
# - User -> DynamoDB (UserRepository)
# - SubscriptionPlan -> DynamoDB (SubscriptionPlanRepository)
# - Problem -> DynamoDB (ProblemRepository)
# - TestCase -> DynamoDB (ProblemRepository)
# - SearchHistory -> DynamoDB (SearchHistoryRepository)
# - ScriptGenerationJob -> DynamoDB (ScriptGenerationJobRepository)
# - ProblemExtractionJob -> DynamoDB (ProblemExtractionJobRepository)
# - JobProgressHistory -> DynamoDB (JobProgressHistoryRepository)
# - UsageLog -> DynamoDB (UsageLogRepository)
