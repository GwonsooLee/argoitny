# Auto Scaling Group for API Server
resource "aws_autoscaling_group" "api_server" {
  name                = "algoitny-api-asg-${var.env_suffix}"
  vpc_zone_identifier = data.terraform_remote_state.vpc.outputs.private_subnets
  target_group_arns   = [data.terraform_remote_state.services.outputs.external_target_group_arn]
  health_check_type   = "ELB"
  health_check_grace_period = 300

  min_size         = var.api_min_size
  max_size         = var.api_max_size
  desired_capacity = var.api_desired_capacity

  launch_template {
    id      = aws_launch_template.api_server.id
    version = "$Latest"
  }

  enabled_metrics = [
    "GroupDesiredCapacity",
    "GroupInServiceInstances",
    "GroupMaxSize",
    "GroupMinSize",
    "GroupPendingInstances",
    "GroupStandbyInstances",
    "GroupTerminatingInstances",
    "GroupTotalInstances"
  ]

  instance_refresh {
    strategy = "Rolling"
    preferences {
      min_healthy_percentage = 50
      instance_warmup        = 300
    }
  }

  tag {
    key                 = "Name"
    value               = "algoitny-api-${var.env_suffix}"
    propagate_at_launch = true
  }

  tag {
    key                 = "Environment"
    value               = var.env_suffix
    propagate_at_launch = true
  }

  tag {
    key                 = "Service"
    value               = "algoitny-api"
    propagate_at_launch = true
  }

  tag {
    key                 = "ManagedBy"
    value               = "terraform"
    propagate_at_launch = true
  }

  lifecycle {
    create_before_destroy = true
    ignore_changes        = [desired_capacity]
  }
}

# Auto Scaling Policy - Target Tracking for CPU
resource "aws_autoscaling_policy" "api_cpu_policy" {
  name                   = "algoitny-api-cpu-policy-${var.env_suffix}"
  policy_type            = "TargetTrackingScaling"
  autoscaling_group_name = aws_autoscaling_group.api_server.name

  target_tracking_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ASGAverageCPUUtilization"
    }
    target_value = 70.0
  }
}

# Auto Scaling Policy - Target Tracking for Request Count
resource "aws_autoscaling_policy" "api_request_count_policy" {
  name                   = "algoitny-api-request-count-policy-${var.env_suffix}"
  policy_type            = "TargetTrackingScaling"
  autoscaling_group_name = aws_autoscaling_group.api_server.name

  target_tracking_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ALBRequestCountPerTarget"
      resource_label         = "${data.terraform_remote_state.services.outputs.external_lb_arn_suffix}/${data.terraform_remote_state.services.outputs.external_target_group_arn_suffix}"
    }
    target_value = 1000.0
  }
}

# Auto Scaling Group for Worker
resource "aws_autoscaling_group" "worker" {
  name                = "algoitny-worker-asg-${var.env_suffix}"
  vpc_zone_identifier = data.terraform_remote_state.vpc.outputs.private_subnets
  health_check_type   = "EC2"
  health_check_grace_period = 300

  min_size         = var.worker_min_size
  max_size         = var.worker_max_size
  desired_capacity = var.worker_desired_capacity

  launch_template {
    id      = aws_launch_template.worker.id
    version = "$Latest"
  }

  enabled_metrics = [
    "GroupDesiredCapacity",
    "GroupInServiceInstances",
    "GroupMaxSize",
    "GroupMinSize",
    "GroupPendingInstances",
    "GroupStandbyInstances",
    "GroupTerminatingInstances",
    "GroupTotalInstances"
  ]

  instance_refresh {
    strategy = "Rolling"
    preferences {
      min_healthy_percentage = 50
      instance_warmup        = 300
    }
  }

  tag {
    key                 = "Name"
    value               = "algoitny-worker-${var.env_suffix}"
    propagate_at_launch = true
  }

  tag {
    key                 = "Environment"
    value               = var.env_suffix
    propagate_at_launch = true
  }

  tag {
    key                 = "Service"
    value               = "algoitny-worker"
    propagate_at_launch = true
  }

  tag {
    key                 = "ManagedBy"
    value               = "terraform"
    propagate_at_launch = true
  }

  lifecycle {
    create_before_destroy = true
    ignore_changes        = [desired_capacity]
  }
}

# Auto Scaling Policy for Worker - Target Tracking for CPU
resource "aws_autoscaling_policy" "worker_cpu_policy" {
  name                   = "algoitny-worker-cpu-policy-${var.env_suffix}"
  policy_type            = "TargetTrackingScaling"
  autoscaling_group_name = aws_autoscaling_group.worker.name

  target_tracking_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ASGAverageCPUUtilization"
    }
    target_value = 70.0
  }
}

# CloudWatch Alarms for API ASG
resource "aws_cloudwatch_metric_alarm" "api_high_cpu" {
  alarm_name          = "algoitny-api-high-cpu-${var.env_suffix}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors API server CPU utilization"
  alarm_actions       = []

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.api_server.name
  }
}

# CloudWatch Alarms for Worker ASG
resource "aws_cloudwatch_metric_alarm" "worker_high_cpu" {
  alarm_name          = "algoitny-worker-high-cpu-${var.env_suffix}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors Worker CPU utilization"
  alarm_actions       = []

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.worker.name
  }
}
