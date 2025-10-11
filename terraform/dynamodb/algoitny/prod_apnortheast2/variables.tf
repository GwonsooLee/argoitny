variable "assume_role_arn" {
  description = "The role to assume when accessing the AWS API."
  default     = ""
}

variable "environment" {
  description = "Environment name (e.g. 'prod', 'dev', 'staging')"
  default     = "prod"
}

variable "project_name" {
  description = "Project name for resource naming"
  default     = "algoitny"
}

# Atlantis
variable "atlantis_user" {
  description = "The username that will be triggering atlantis commands. This will be used to name the session when assuming a role. More information - https://github.com/runatlantis/atlantis#assume-role-session-names"
  default     = "atlantis_user"
}

# DynamoDB specific variables
variable "billing_mode" {
  description = "DynamoDB billing mode (PROVISIONED or PAY_PER_REQUEST)"
  default     = "PAY_PER_REQUEST"
}

variable "read_capacity" {
  description = "Read capacity units for PROVISIONED billing mode"
  default     = 5
}

variable "write_capacity" {
  description = "Write capacity units for PROVISIONED billing mode"
  default     = 2
}

variable "enable_autoscaling" {
  description = "Enable auto-scaling for DynamoDB tables"
  default     = true
}

variable "min_read_capacity" {
  description = "Minimum read capacity for auto-scaling"
  default     = 3
}

variable "max_read_capacity" {
  description = "Maximum read capacity for auto-scaling"
  default     = 50
}

variable "min_write_capacity" {
  description = "Minimum write capacity for auto-scaling"
  default     = 1
}

variable "max_write_capacity" {
  description = "Maximum write capacity for auto-scaling"
  default     = 20
}

variable "target_utilization" {
  description = "Target utilization percentage for auto-scaling (recommended: 70)"
  default     = 70
}

variable "enable_point_in_time_recovery" {
  description = "Enable Point-in-Time Recovery"
  default     = true
}

variable "enable_deletion_protection" {
  description = "Enable deletion protection"
  default     = true
}

variable "tags" {
  description = "Additional tags for DynamoDB table"
  type        = map(string)
  default     = {}
}
