"""
Django signals for cache invalidation - DISABLED

All models have been migrated to DynamoDB.
Django signals don't work with DynamoDB operations.

Cache invalidation should be done manually in repository methods or views.

TODO: Implement cache invalidation in DynamoDB repositories
"""

# All signal handlers have been removed due to DynamoDB migration
# Cache invalidation needs to be implemented at the repository layer
