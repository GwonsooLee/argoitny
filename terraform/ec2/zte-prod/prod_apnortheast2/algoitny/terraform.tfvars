# AWS Configuration
aws_region = "ap-northeast-2"
env_suffix = "prod"

# API Server Configuration (ARM-based t4g)
api_instance_type    = "t4g.medium"
api_volume_size      = 30
api_min_size         = 1
api_max_size         = 10
api_desired_capacity = 1

# Worker Configuration (ARM-based t4g)
worker_instance_type    = "t4g.large"
worker_volume_size      = 50
worker_min_size         = 1
worker_max_size         = 5
worker_desired_capacity = 1

# Application Configuration
image_tag        = "v0.0.15"
allowed_hosts    = "*"
gunicorn_workers = 4
