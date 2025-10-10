# AWS Configuration
aws_region = "ap-northeast-2"
env_suffix = "prod"

# API Server Configuration
api_instance_type    = "t3.medium"
api_volume_size      = 30
api_min_size         = 2
api_max_size         = 10
api_desired_capacity = 2

# Worker Configuration
worker_instance_type    = "t3.large"
worker_volume_size      = 50
worker_min_size         = 1
worker_max_size         = 5
worker_desired_capacity = 2

# Application Configuration
image_tag        = "latest"
allowed_hosts    = "api.testcase.run,*.testcase.run"
gunicorn_workers = 4
