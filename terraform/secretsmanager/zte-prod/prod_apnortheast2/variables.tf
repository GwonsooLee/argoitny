variable "aws_region" {
  description = "The AWS region to deploy secrets into"
}

# Variables for Atlantis
variable "assume_role_arn" {
  description = "The role to assume when accessing the AWS API."
  default     = ""
}

variable "atlantis_user" {
  description = "The username that will be triggering atlantis commands."
  default     = "atlantis_user"
}
