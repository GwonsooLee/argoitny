# Data source for the latest Amazon Linux 2023 AMI
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "root-device-type"
    values = ["ebs"]
  }
}

# Launch Template for API Server
resource "aws_launch_template" "api_server" {
  name_prefix   = "algoitny-api-${var.env_suffix}-"
  description   = "Launch template for AlgoItny API Server"
  image_id      = data.aws_ami.amazon_linux_2023.id
  instance_type = var.api_instance_type

  iam_instance_profile {
    arn = aws_iam_instance_profile.api_server.arn
  }

  vpc_security_group_ids = [aws_security_group.api_server.id]

  user_data = base64encode(templatefile("${path.module}/user_data_api.sh", {
    env_suffix          = var.env_suffix
    ecr_repository_url  = data.terraform_remote_state.ecr.outputs.algoitny_repository_url
    ecr_image_url       = "${data.terraform_remote_state.ecr.outputs.algoitny_repository_url}:${var.image_tag}"
    allowed_hosts       = var.allowed_hosts
    redis_host          = data.terraform_remote_state.databases.outputs.redis_primary_endpoint
    gunicorn_workers    = var.gunicorn_workers
  }))

  block_device_mappings {
    device_name = "/dev/xvda"

    ebs {
      volume_size           = var.api_volume_size
      volume_type           = "gp3"
      delete_on_termination = true
      encrypted             = true
    }
  }

  monitoring {
    enabled = true
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "enabled"
  }

  tag_specifications {
    resource_type = "instance"

    tags = {
      Name        = "algoitny-api-${var.env_suffix}"
      Environment = var.env_suffix
      Service     = "algoitny-api"
      ManagedBy   = "terraform"
    }
  }

  tag_specifications {
    resource_type = "volume"

    tags = {
      Name        = "algoitny-api-${var.env_suffix}-volume"
      Environment = var.env_suffix
      Service     = "algoitny-api"
      ManagedBy   = "terraform"
    }
  }

  tags = {
    Name        = "algoitny-api-lt-${var.env_suffix}"
    Environment = var.env_suffix
    Service     = "algoitny-api"
    ManagedBy   = "terraform"
  }
}

# Launch Template for Worker
resource "aws_launch_template" "worker" {
  name_prefix   = "algoitny-worker-${var.env_suffix}-"
  description   = "Launch template for AlgoItny Celery Worker"
  image_id      = data.aws_ami.amazon_linux_2023.id
  instance_type = var.worker_instance_type

  iam_instance_profile {
    arn = aws_iam_instance_profile.worker.arn
  }

  vpc_security_group_ids = [aws_security_group.worker.id]

  user_data = base64encode(templatefile("${path.module}/user_data_worker.sh", {
    env_suffix         = var.env_suffix
    ecr_repository_url = data.terraform_remote_state.ecr.outputs.algoitny_repository_url
    ecr_image_url      = "${data.terraform_remote_state.ecr.outputs.algoitny_repository_url}:${var.image_tag}"
    redis_host         = data.terraform_remote_state.databases.outputs.redis_primary_endpoint
  }))

  block_device_mappings {
    device_name = "/dev/xvda"

    ebs {
      volume_size           = var.worker_volume_size
      volume_type           = "gp3"
      delete_on_termination = true
      encrypted             = true
    }
  }

  monitoring {
    enabled = true
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "enabled"
  }

  tag_specifications {
    resource_type = "instance"

    tags = {
      Name        = "algoitny-worker-${var.env_suffix}"
      Environment = var.env_suffix
      Service     = "algoitny-worker"
      ManagedBy   = "terraform"
    }
  }

  tag_specifications {
    resource_type = "volume"

    tags = {
      Name        = "algoitny-worker-${var.env_suffix}-volume"
      Environment = var.env_suffix
      Service     = "algoitny-worker"
      ManagedBy   = "terraform"
    }
  }

  tags = {
    Name        = "algoitny-worker-lt-${var.env_suffix}"
    Environment = var.env_suffix
    Service     = "algoitny-worker"
    ManagedBy   = "terraform"
  }
}
