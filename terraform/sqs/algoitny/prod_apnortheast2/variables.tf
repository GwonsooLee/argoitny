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

# SQS specific variables
variable "visibility_timeout" {
  description = "The visibility timeout for the queue in seconds"
  default     = 300
}

variable "message_retention_seconds" {
  description = "The number of seconds Amazon SQS retains a message"
  default     = 1209600 # 14 days
}

variable "max_message_size" {
  description = "The limit of how many bytes a message can contain before Amazon SQS rejects it"
  default     = 262144 # 256 KB
}

variable "delay_seconds" {
  description = "The time in seconds that the delivery of all messages in the queue will be delayed"
  default     = 0
}

variable "receive_wait_time_seconds" {
  description = "The time for which a ReceiveMessage call will wait for a message to arrive (long polling)"
  default     = 10
}

variable "max_receive_count" {
  description = "The number of times a message is delivered to the source queue before being moved to the dead-letter queue"
  default     = 5
}

variable "enable_content_based_deduplication" {
  description = "Enable content-based deduplication for FIFO queues"
  default     = false
}

variable "fifo_queue" {
  description = "Boolean designating a FIFO queue"
  default     = false
}

variable "tags" {
  description = "Additional tags for SQS queues"
  type        = map(string)
  default     = {}
}
