# DynamoDB Table for AlgoItny
# Based on Single Table Design V2
# Reference: backend/api/dynamodb/table_schema.py

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

  # GSI1 Attributes: User authentication by email/google_id
  attribute {
    name = "GSI1PK"
    type = "S"
  }

  attribute {
    name = "GSI1SK"
    type = "S"
  }

  # GSI2 Attributes: Public history timeline
  attribute {
    name = "GSI2PK"
    type = "S"
  }

  attribute {
    name = "GSI2SK"
    type = "S"
  }

  # GSI3 Attributes: Problem status index (completed/draft)
  attribute {
    name = "GSI3PK"
    type = "S"
  }

  attribute {
    name = "GSI3SK"
    type = "N"
  }

  # GSI1: User Authentication Index
  global_secondary_index {
    name            = "GSI1"
    hash_key        = "GSI1PK"
    range_key       = "GSI1SK"
    projection_type = "ALL"
  }

  # GSI2: Public History Timeline Index
  global_secondary_index {
    name            = "GSI2"
    hash_key        = "GSI2PK"
    range_key       = "GSI2SK"
    projection_type = "KEYS_ONLY"
  }

  # GSI3: Problem Status Index
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
  # Can be used for usage logs, sessions, etc.
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
