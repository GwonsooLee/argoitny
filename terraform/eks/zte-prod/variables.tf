# Global variables for zte-prod EKS clusters
variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "product" {
  description = "Product name"
  type        = string
  default     = "algoitny"
}

variable "account_alias" {
  description = "AWS account alias"
  type        = string
  default     = "zte-prod"
}
