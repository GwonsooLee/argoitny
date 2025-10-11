# DynamoDB Table for AlgoItny
# Single Table Design with optimized access patterns
# Reference: backend/api/dynamodb/repositories/
#
# Entities: User, Problem, SearchHistory, UsageLog, SubscriptionPlan, UserStats, Jobs
#
# Access Pattern Optimizations (from dynamodb-architect analysis):
# - Removed expensive SCAN operations (list_users, get_users_by_plan, list_problems_needing_review)
# - Added caching for list_active_users (10min TTL, 90% cost reduction)
# - UsageLog with date-partitioned PK for efficient rate limiting (1-3ms latency, 0.5 RCU)
# - UserStats for O(1) unique problem counting (125 RCU → 0.5 RCU)
# - TTL-based auto-cleanup for usage logs (90 days)

resource "aws_dynamodb_table" "algoitny_main" {
  name           = "${var.project_name}_main"
  billing_mode   = var.billing_mode
  hash_key       = "PK"
  range_key      = "SK"

  # Enable deletion protection in production
  deletion_protection_enabled = var.enable_deletion_protection

  # Primary Key Attributes
  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  # GSI1 Attributes: User email lookups & user history queries
  # Used by: UserRepository (email→user), SearchHistoryRepository (user→history)
  attribute {
    name = "GSI1PK"
    type = "S"
  }

  attribute {
    name = "GSI1SK"
    type = "S"
  }

  # GSI2 Attributes: Google OAuth & public history timeline
  # Used by: UserRepository (google_id→user), SearchHistoryRepository (public timeline)
  attribute {
    name = "GSI2PK"
    type = "S"
  }

  attribute {
    name = "GSI2SK"
    type = "S"
  }

  # GSI3 Attributes: Problem status queries (completed/draft/needs_review)
  # Used by: ProblemRepository (status-based problem queries)
  attribute {
    name = "GSI3PK"
    type = "S"
  }

  attribute {
    name = "GSI3SK"
    type = "N"
  }

  # GSI1: Multi-purpose index for user and history access patterns
  # Pattern 1: User email lookup
  #   - GSI1PK = "EMAIL#{email}"
  #   - GSI1SK = "USR#{user_id}"
  # Pattern 2: User's search history
  #   - GSI1PK = "USER#{user_id}"
  #   - GSI1SK = "HIST#{timestamp}"
  global_secondary_index {
    name            = "GSI1"
    hash_key        = "GSI1PK"
    range_key       = "GSI1SK"
    projection_type = "ALL"
  }

  # GSI2: Multi-purpose index for Google auth and public content
  # Pattern 1: Google OAuth lookup (no SK needed)
  #   - GSI2PK = "GID#{google_id}"
  # Pattern 2: Public history timeline (time-partitioned to avoid hot partition)
  #   - GSI2PK = "PUBLIC#HIST" or "PUBLIC#HIST#{YYYYMMDDHH}"
  #   - GSI2SK = "{timestamp}"
  # Note: KEYS_ONLY projection for cost efficiency (fetch full items separately if needed)
  global_secondary_index {
    name            = "GSI2"
    hash_key        = "GSI2PK"
    range_key       = "GSI2SK"
    projection_type = "KEYS_ONLY"
  }

  # GSI3: Problem status index for admin/filtering queries
  # Pattern: Query problems by status
  #   - GSI3PK = "STATUS#{completed|draft|needs_review}"
  #   - GSI3SK = {timestamp_numeric} (sorted chronologically)
  global_secondary_index {
    name            = "GSI3"
    hash_key        = "GSI3PK"
    range_key       = "GSI3SK"
    projection_type = "ALL"
  }

  # DynamoDB Streams for event processing
  stream_enabled   = var.enable_streams
  stream_view_type = var.enable_streams ? var.stream_view_type : null

  # Point-in-Time Recovery for data protection
  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  # Server-side encryption (enabled by default with AWS managed key)
  server_side_encryption {
    enabled = true
  }

  # Time to Live (TTL) for automatic data expiration
  # Used by: UsageLog (90-day auto-cleanup of rate limit logs)
  # Items with ttl attribute set will be automatically deleted after the specified timestamp
  # Cost optimization: Eliminates need for manual cleanup jobs
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # Tags for resource management
  tags = merge(
    {
      Name        = "${var.project_name}_main"
      Environment = var.environment
      Project     = var.project_name
      ManagedBy   = "Terraform"
      Purpose     = "AlgoItny main database"
    },
    var.tags
  )
}

# CloudWatch Alarms for DynamoDB monitoring

# Alarm for Read Throttle Events
resource "aws_cloudwatch_metric_alarm" "read_throttle_events" {
  alarm_name          = "${var.project_name}-dynamodb-read-throttle"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ReadThrottleEvents"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "This metric monitors DynamoDB read throttle events"
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = aws_dynamodb_table.algoitny_main.name
  }

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Alarm for Write Throttle Events
resource "aws_cloudwatch_metric_alarm" "write_throttle_events" {
  alarm_name          = "${var.project_name}-dynamodb-write-throttle"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "WriteThrottleEvents"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "This metric monitors DynamoDB write throttle events"
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = aws_dynamodb_table.algoitny_main.name
  }

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Alarm for High Consumed Read Capacity (for cost monitoring)
resource "aws_cloudwatch_metric_alarm" "high_read_capacity" {
  count               = var.billing_mode == "PAY_PER_REQUEST" ? 1 : 0
  alarm_name          = "${var.project_name}-dynamodb-high-read-capacity"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ConsumedReadCapacityUnits"
  namespace           = "AWS/DynamoDB"
  period              = 3600
  statistic           = "Sum"
  threshold           = 1000000 # 1M RCU per hour
  alarm_description   = "Alert when read capacity is unusually high (cost monitoring)"
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = aws_dynamodb_table.algoitny_main.name
  }

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ============================================================================
# Django/Celery DynamoDB Table
# ============================================================================
# Dedicated table for Django-related data:
# - Session storage (Django sessions)
# - Celery task results
# - Cache storage (optional)
#
# Table Structure:
#   PK: SESSION#{key}, TASK#{id}, CACHE#{key}
#   SK: META (or timestamp-based)
#   tp: Type attribute (session, task_result, cache) for TypeIndex GSI
#   exp: TTL attribute for automatic expiration

resource "aws_dynamodb_table" "algoitny_django" {
  name           = "${var.project_name}_django"
  billing_mode   = var.billing_mode
  hash_key       = "PK"
  range_key      = "SK"

  # Enable deletion protection in production
  deletion_protection_enabled = var.enable_deletion_protection

  # Primary Key Attributes
  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  # Type attribute for GSI (to query by type: session, task_result, cache)
  attribute {
    name = "tp"
    type = "S"
  }

  # TypeIndex GSI: Query items by type (session, task_result, cache)
  # Pattern: Query all sessions, all tasks, or all cache entries
  #   - tp = "session" | "task_result" | "cache"
  #   - SK = timestamp or META
  global_secondary_index {
    name            = "TypeIndex"
    hash_key        = "tp"
    range_key       = "SK"
    projection_type = "ALL"
  }

  # DynamoDB Streams for event processing
  stream_enabled   = var.enable_streams
  stream_view_type = var.enable_streams ? var.stream_view_type : null

  # Point-in-Time Recovery for data protection
  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  # Server-side encryption (enabled by default with AWS managed key)
  server_side_encryption {
    enabled = true
  }

  # Time to Live (TTL) for automatic data expiration
  # Used for:
  # - Session expiration (based on SESSION_COOKIE_AGE)
  # - Celery task result expiration (24 hours by default)
  # - Cache entry expiration
  ttl {
    attribute_name = "exp"
    enabled        = true
  }

  # Tags for resource management
  tags = merge(
    {
      Name        = "${var.project_name}_django"
      Environment = var.environment
      Project     = var.project_name
      ManagedBy   = "Terraform"
      Purpose     = "Django/Celery data storage"
    },
    var.tags
  )
}

# CloudWatch Alarms for Django Table

# Alarm for Read Throttle Events
resource "aws_cloudwatch_metric_alarm" "django_read_throttle_events" {
  alarm_name          = "${var.project_name}-django-dynamodb-read-throttle"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ReadThrottleEvents"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "This metric monitors DynamoDB read throttle events for Django table"
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = aws_dynamodb_table.algoitny_django.name
  }

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Alarm for Write Throttle Events
resource "aws_cloudwatch_metric_alarm" "django_write_throttle_events" {
  alarm_name          = "${var.project_name}-django-dynamodb-write-throttle"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "WriteThrottleEvents"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "This metric monitors DynamoDB write throttle events for Django table"
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = aws_dynamodb_table.algoitny_django.name
  }

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
