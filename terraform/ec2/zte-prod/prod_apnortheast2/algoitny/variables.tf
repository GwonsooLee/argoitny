# Global Variables
variable "aws_region" {
  description = "AWS Region"
  type        = string
  default     = "ap-northeast-2"
}

variable "env_suffix" {
  description = "Environment suffix"
  type        = string
  default     = "prod"
}

# API Server Variables
variable "api_instance_type" {
  description = "Instance type for API servers"
  type        = string
  default     = "t3.medium"
}

variable "api_volume_size" {
  description = "EBS volume size for API servers (GB)"
  type        = number
  default     = 30
}

variable "api_min_size" {
  description = "Minimum number of API server instances"
  type        = number
  default     = 2
}

variable "api_max_size" {
  description = "Maximum number of API server instances"
  type        = number
  default     = 10
}

variable "api_desired_capacity" {
  description = "Desired number of API server instances"
  type        = number
  default     = 2
}

# Worker Variables
variable "worker_instance_type" {
  description = "Instance type for Worker servers"
  type        = string
  default     = "t3.large"
}

variable "worker_volume_size" {
  description = "EBS volume size for Worker servers (GB)"
  type        = number
  default     = 50
}

variable "worker_min_size" {
  description = "Minimum number of Worker instances"
  type        = number
  default     = 1
}

variable "worker_max_size" {
  description = "Maximum number of Worker instances"
  type        = number
  default     = 5
}

variable "worker_desired_capacity" {
  description = "Desired number of Worker instances"
  type        = number
  default     = 2
}

# Application Variables
variable "image_tag" {
  description = "Docker image tag to deploy"
  type        = string
  default     = "latest"
}

variable "allowed_hosts" {
  description = "Allowed hosts for Django"
  type        = string
  default     = "*"
}

variable "gunicorn_workers" {
  description = "Number of Gunicorn workers"
  type        = number
  default     = 4
}
