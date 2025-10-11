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

  # Capacity settings for PROVISIONED mode
  read_capacity  = var.billing_mode == "PROVISIONED" ? var.read_capacity : null
  write_capacity = var.billing_mode == "PROVISIONED" ? var.write_capacity : null

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
    read_capacity   = var.billing_mode == "PROVISIONED" ? var.read_capacity : null
    write_capacity  = var.billing_mode == "PROVISIONED" ? var.write_capacity : null
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
    read_capacity   = var.billing_mode == "PROVISIONED" ? var.read_capacity : null
    write_capacity  = var.billing_mode == "PROVISIONED" ? var.write_capacity : null
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
    read_capacity   = var.billing_mode == "PROVISIONED" ? var.read_capacity : null
    write_capacity  = var.billing_mode == "PROVISIONED" ? var.write_capacity : null
  }

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

  # Capacity settings for PROVISIONED mode
  read_capacity  = var.billing_mode == "PROVISIONED" ? var.read_capacity : null
  write_capacity = var.billing_mode == "PROVISIONED" ? var.write_capacity : null

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
    read_capacity   = var.billing_mode == "PROVISIONED" ? var.read_capacity : null
    write_capacity  = var.billing_mode == "PROVISIONED" ? var.write_capacity : null
  }

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

# ============================================================================
# Auto-Scaling Configuration
# ============================================================================
# Auto-scaling for DynamoDB tables and GSIs to automatically adjust capacity
# based on utilization (target: 70%)

# ---------------------------------------------------------------------------
# Main Table Auto-Scaling
# ---------------------------------------------------------------------------

# Main Table - Read Capacity
resource "aws_appautoscaling_target" "main_table_read" {
  count              = var.enable_autoscaling && var.billing_mode == "PROVISIONED" ? 1 : 0
  max_capacity       = var.max_read_capacity
  min_capacity       = var.min_read_capacity
  resource_id        = "table/${aws_dynamodb_table.algoitny_main.name}"
  scalable_dimension = "dynamodb:table:ReadCapacityUnits"
  service_namespace  = "dynamodb"
}

resource "aws_appautoscaling_policy" "main_table_read_policy" {
  count              = var.enable_autoscaling && var.billing_mode == "PROVISIONED" ? 1 : 0
  name               = "${var.project_name}_main_read_scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.main_table_read[0].resource_id
  scalable_dimension = aws_appautoscaling_target.main_table_read[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.main_table_read[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBReadCapacityUtilization"
    }
    target_value = var.target_utilization
  }
}

# Main Table - Write Capacity
resource "aws_appautoscaling_target" "main_table_write" {
  count              = var.enable_autoscaling && var.billing_mode == "PROVISIONED" ? 1 : 0
  max_capacity       = var.max_write_capacity
  min_capacity       = var.min_write_capacity
  resource_id        = "table/${aws_dynamodb_table.algoitny_main.name}"
  scalable_dimension = "dynamodb:table:WriteCapacityUnits"
  service_namespace  = "dynamodb"
}

resource "aws_appautoscaling_policy" "main_table_write_policy" {
  count              = var.enable_autoscaling && var.billing_mode == "PROVISIONED" ? 1 : 0
  name               = "${var.project_name}_main_write_scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.main_table_write[0].resource_id
  scalable_dimension = aws_appautoscaling_target.main_table_write[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.main_table_write[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBWriteCapacityUtilization"
    }
    target_value = var.target_utilization
  }
}

# ---------------------------------------------------------------------------
# Main Table GSI1 Auto-Scaling
# ---------------------------------------------------------------------------

resource "aws_appautoscaling_target" "main_gsi1_read" {
  count              = var.enable_autoscaling && var.billing_mode == "PROVISIONED" ? 1 : 0
  max_capacity       = var.max_read_capacity
  min_capacity       = var.min_read_capacity
  resource_id        = "table/${aws_dynamodb_table.algoitny_main.name}/index/GSI1"
  scalable_dimension = "dynamodb:index:ReadCapacityUnits"
  service_namespace  = "dynamodb"
}

resource "aws_appautoscaling_policy" "main_gsi1_read_policy" {
  count              = var.enable_autoscaling && var.billing_mode == "PROVISIONED" ? 1 : 0
  name               = "${var.project_name}_main_gsi1_read_scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.main_gsi1_read[0].resource_id
  scalable_dimension = aws_appautoscaling_target.main_gsi1_read[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.main_gsi1_read[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBReadCapacityUtilization"
    }
    target_value = var.target_utilization
  }
}

resource "aws_appautoscaling_target" "main_gsi1_write" {
  count              = var.enable_autoscaling && var.billing_mode == "PROVISIONED" ? 1 : 0
  max_capacity       = var.max_write_capacity
  min_capacity       = var.min_write_capacity
  resource_id        = "table/${aws_dynamodb_table.algoitny_main.name}/index/GSI1"
  scalable_dimension = "dynamodb:index:WriteCapacityUnits"
  service_namespace  = "dynamodb"
}

resource "aws_appautoscaling_policy" "main_gsi1_write_policy" {
  count              = var.enable_autoscaling && var.billing_mode == "PROVISIONED" ? 1 : 0
  name               = "${var.project_name}_main_gsi1_write_scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.main_gsi1_write[0].resource_id
  scalable_dimension = aws_appautoscaling_target.main_gsi1_write[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.main_gsi1_write[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBWriteCapacityUtilization"
    }
    target_value = var.target_utilization
  }
}

# ---------------------------------------------------------------------------
# Main Table GSI2 Auto-Scaling
# ---------------------------------------------------------------------------

resource "aws_appautoscaling_target" "main_gsi2_read" {
  count              = var.enable_autoscaling && var.billing_mode == "PROVISIONED" ? 1 : 0
  max_capacity       = var.max_read_capacity
  min_capacity       = var.min_read_capacity
  resource_id        = "table/${aws_dynamodb_table.algoitny_main.name}/index/GSI2"
  scalable_dimension = "dynamodb:index:ReadCapacityUnits"
  service_namespace  = "dynamodb"
}

resource "aws_appautoscaling_policy" "main_gsi2_read_policy" {
  count              = var.enable_autoscaling && var.billing_mode == "PROVISIONED" ? 1 : 0
  name               = "${var.project_name}_main_gsi2_read_scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.main_gsi2_read[0].resource_id
  scalable_dimension = aws_appautoscaling_target.main_gsi2_read[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.main_gsi2_read[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBReadCapacityUtilization"
    }
    target_value = var.target_utilization
  }
}

resource "aws_appautoscaling_target" "main_gsi2_write" {
  count              = var.enable_autoscaling && var.billing_mode == "PROVISIONED" ? 1 : 0
  max_capacity       = var.max_write_capacity
  min_capacity       = var.min_write_capacity
  resource_id        = "table/${aws_dynamodb_table.algoitny_main.name}/index/GSI2"
  scalable_dimension = "dynamodb:index:WriteCapacityUnits"
  service_namespace  = "dynamodb"
}

resource "aws_appautoscaling_policy" "main_gsi2_write_policy" {
  count              = var.enable_autoscaling && var.billing_mode == "PROVISIONED" ? 1 : 0
  name               = "${var.project_name}_main_gsi2_write_scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.main_gsi2_write[0].resource_id
  scalable_dimension = aws_appautoscaling_target.main_gsi2_write[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.main_gsi2_write[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBWriteCapacityUtilization"
    }
    target_value = var.target_utilization
  }
}

# ---------------------------------------------------------------------------
# Main Table GSI3 Auto-Scaling
# ---------------------------------------------------------------------------

resource "aws_appautoscaling_target" "main_gsi3_read" {
  count              = var.enable_autoscaling && var.billing_mode == "PROVISIONED" ? 1 : 0
  max_capacity       = var.max_read_capacity
  min_capacity       = var.min_read_capacity
  resource_id        = "table/${aws_dynamodb_table.algoitny_main.name}/index/GSI3"
  scalable_dimension = "dynamodb:index:ReadCapacityUnits"
  service_namespace  = "dynamodb"
}

resource "aws_appautoscaling_policy" "main_gsi3_read_policy" {
  count              = var.enable_autoscaling && var.billing_mode == "PROVISIONED" ? 1 : 0
  name               = "${var.project_name}_main_gsi3_read_scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.main_gsi3_read[0].resource_id
  scalable_dimension = aws_appautoscaling_target.main_gsi3_read[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.main_gsi3_read[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBReadCapacityUtilization"
    }
    target_value = var.target_utilization
  }
}

resource "aws_appautoscaling_target" "main_gsi3_write" {
  count              = var.enable_autoscaling && var.billing_mode == "PROVISIONED" ? 1 : 0
  max_capacity       = var.max_write_capacity
  min_capacity       = var.min_write_capacity
  resource_id        = "table/${aws_dynamodb_table.algoitny_main.name}/index/GSI3"
  scalable_dimension = "dynamodb:index:WriteCapacityUnits"
  service_namespace  = "dynamodb"
}

resource "aws_appautoscaling_policy" "main_gsi3_write_policy" {
  count              = var.enable_autoscaling && var.billing_mode == "PROVISIONED" ? 1 : 0
  name               = "${var.project_name}_main_gsi3_write_scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.main_gsi3_write[0].resource_id
  scalable_dimension = aws_appautoscaling_target.main_gsi3_write[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.main_gsi3_write[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBWriteCapacityUtilization"
    }
    target_value = var.target_utilization
  }
}

# ---------------------------------------------------------------------------
# Django Table Auto-Scaling
# ---------------------------------------------------------------------------

# Django Table - Read Capacity
resource "aws_appautoscaling_target" "django_table_read" {
  count              = var.enable_autoscaling && var.billing_mode == "PROVISIONED" ? 1 : 0
  max_capacity       = var.max_read_capacity
  min_capacity       = var.min_read_capacity
  resource_id        = "table/${aws_dynamodb_table.algoitny_django.name}"
  scalable_dimension = "dynamodb:table:ReadCapacityUnits"
  service_namespace  = "dynamodb"
}

resource "aws_appautoscaling_policy" "django_table_read_policy" {
  count              = var.enable_autoscaling && var.billing_mode == "PROVISIONED" ? 1 : 0
  name               = "${var.project_name}_django_read_scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.django_table_read[0].resource_id
  scalable_dimension = aws_appautoscaling_target.django_table_read[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.django_table_read[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBReadCapacityUtilization"
    }
    target_value = var.target_utilization
  }
}

# Django Table - Write Capacity
resource "aws_appautoscaling_target" "django_table_write" {
  count              = var.enable_autoscaling && var.billing_mode == "PROVISIONED" ? 1 : 0
  max_capacity       = var.max_write_capacity
  min_capacity       = var.min_write_capacity
  resource_id        = "table/${aws_dynamodb_table.algoitny_django.name}"
  scalable_dimension = "dynamodb:table:WriteCapacityUnits"
  service_namespace  = "dynamodb"
}

resource "aws_appautoscaling_policy" "django_table_write_policy" {
  count              = var.enable_autoscaling && var.billing_mode == "PROVISIONED" ? 1 : 0
  name               = "${var.project_name}_django_write_scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.django_table_write[0].resource_id
  scalable_dimension = aws_appautoscaling_target.django_table_write[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.django_table_write[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBWriteCapacityUtilization"
    }
    target_value = var.target_utilization
  }
}

# ---------------------------------------------------------------------------
# Django Table TypeIndex GSI Auto-Scaling
# ---------------------------------------------------------------------------

resource "aws_appautoscaling_target" "django_typeindex_read" {
  count              = var.enable_autoscaling && var.billing_mode == "PROVISIONED" ? 1 : 0
  max_capacity       = var.max_read_capacity
  min_capacity       = var.min_read_capacity
  resource_id        = "table/${aws_dynamodb_table.algoitny_django.name}/index/TypeIndex"
  scalable_dimension = "dynamodb:index:ReadCapacityUnits"
  service_namespace  = "dynamodb"
}

resource "aws_appautoscaling_policy" "django_typeindex_read_policy" {
  count              = var.enable_autoscaling && var.billing_mode == "PROVISIONED" ? 1 : 0
  name               = "${var.project_name}_django_typeindex_read_scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.django_typeindex_read[0].resource_id
  scalable_dimension = aws_appautoscaling_target.django_typeindex_read[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.django_typeindex_read[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBReadCapacityUtilization"
    }
    target_value = var.target_utilization
  }
}

resource "aws_appautoscaling_target" "django_typeindex_write" {
  count              = var.enable_autoscaling && var.billing_mode == "PROVISIONED" ? 1 : 0
  max_capacity       = var.max_write_capacity
  min_capacity       = var.min_write_capacity
  resource_id        = "table/${aws_dynamodb_table.algoitny_django.name}/index/TypeIndex"
  scalable_dimension = "dynamodb:index:WriteCapacityUnits"
  service_namespace  = "dynamodb"
}

resource "aws_appautoscaling_policy" "django_typeindex_write_policy" {
  count              = var.enable_autoscaling && var.billing_mode == "PROVISIONED" ? 1 : 0
  name               = "${var.project_name}_django_typeindex_write_scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.django_typeindex_write[0].resource_id
  scalable_dimension = aws_appautoscaling_target.django_typeindex_write[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.django_typeindex_write[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBWriteCapacityUtilization"
    }
    target_value = var.target_utilization
  }
}
