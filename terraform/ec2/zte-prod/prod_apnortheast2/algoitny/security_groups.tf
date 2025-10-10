# Security Group for API Server
resource "aws_security_group" "api_server" {
  name        = "algoitny-api-server-${var.env_suffix}"
  description = "Security group for AlgoItny API Server"
  vpc_id      = data.terraform_remote_state.vpc.outputs.vpc_id

  tags = {
    Name        = "algoitny-api-server-${var.env_suffix}"
    Environment = var.env_suffix
    Service     = "algoitny-api"
    ManagedBy   = "terraform"
  }
}

# Ingress rule - Allow HTTP from ALB Security Group
resource "aws_security_group_rule" "api_server_http_from_alb" {
  type                     = "ingress"
  from_port                = 8000
  to_port                  = 8000
  protocol                 = "tcp"
  source_security_group_id = data.terraform_remote_state.services.outputs.external_lb_security_group_id
  description              = "Allow HTTP from ALB"
  security_group_id        = aws_security_group.api_server.id
}

# Egress rule - Allow all outbound
resource "aws_security_group_rule" "api_server_egress_all" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  description       = "Allow all outbound traffic"
  security_group_id = aws_security_group.api_server.id
}

# Security Group for Worker
resource "aws_security_group" "worker" {
  name        = "algoitny-worker-${var.env_suffix}"
  description = "Security group for AlgoItny Celery Worker"
  vpc_id      = data.terraform_remote_state.vpc.outputs.vpc_id

  tags = {
    Name        = "algoitny-worker-${var.env_suffix}"
    Environment = var.env_suffix
    Service     = "algoitny-worker"
    ManagedBy   = "terraform"
  }
}

# Egress rule - Allow all outbound
resource "aws_security_group_rule" "worker_egress_all" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  description       = "Allow all outbound traffic"
  security_group_id = aws_security_group.worker.id
}
