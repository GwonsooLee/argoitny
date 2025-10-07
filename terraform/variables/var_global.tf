variable "assume_role_arn" {
  description = "The role to assume when accessing the AWS API."
  default     = ""
}

# Atlantis user
variable "atlantis_user" {
  description = "The username that will be triggering atlantis commands. This will be used to name the session when assuming a role. More information - https://github.com/runatlantis/atlantis#assume-role-session-names"
  default     = "atlantis_user"
}

# Account IDs
# Add all account ID to here 
variable "account_id" {
  default = {
    prod = "442863828268"
  }
}

# Remote State that will be used when creating other resources
# You can add any resource here, if you want to refer from others
variable "remote_state" {
  default = {
    databases = {
      prod = {
        xteapne2 = {
          region = "ap-northeast-2"
          bucket = "zte-prod-apnortheast2-tfstate"
          key    = "terraform/databases/zte-prod/zte_apnortheast2/terraform.tfstate"
        }
      }
    }

    # VPC
    vpc = {
      zteapne2 = {
        region = "ap-northeast-2"
        bucket = "zte-prod-apnortheast2-tfstate"
        key    = "terraform/vpc/zte_apnortheast2/terraform.tfstate"
      }
    }

    # AWS KMS
    kms = {
      prod = {
        apne2 = {
          region = "ap-northeast-2"
          bucket = "zte-prod-apnortheast2-tfstate"
          key    = "terraform/kms/zte-prod/prod_apnortheast2/terraform.tfstate"
        }
      }
    }
  }
}