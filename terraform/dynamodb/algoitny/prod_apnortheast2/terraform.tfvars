# DynamoDB Configuration for AlgoItny Production

environment  = "prod"
project_name = "algoitny"

# Billing configuration
billing_mode = "PAY_PER_REQUEST" # On-demand billing for variable workloads

# Streams configuration
enable_streams     = true
stream_view_type   = "NEW_AND_OLD_IMAGES"

# Backup and recovery
enable_point_in_time_recovery = true

# Deletion protection (recommended for production)
enable_deletion_protection = true

# Additional tags
tags = {
  Team        = "Backend"
  Application = "AlgoItny"
  CostCenter  = "Engineering"
}
