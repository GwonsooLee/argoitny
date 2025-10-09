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

variable "enable_streams" {
  description = "Enable DynamoDB Streams"
  default     = true
}

variable "stream_view_type" {
  description = "Stream view type (NEW_IMAGE, OLD_IMAGE, NEW_AND_OLD_IMAGES, KEYS_ONLY)"
  default     = "NEW_AND_OLD_IMAGES"
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
