# IAM Role for API Server
resource "aws_iam_role" "api_server" {
  name               = "algoitny-api-server-${var.env_suffix}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name        = "algoitny-api-server-${var.env_suffix}"
    Environment = var.env_suffix
    Service     = "algoitny-api"
    ManagedBy   = "terraform"
  }
}

# IAM Policy for API Server
resource "aws_iam_policy" "api_server" {
  name        = "algoitny-api-server-policy-${var.env_suffix}"
  description = "Policy for AlgoItny API Server"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ECRAccess"
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:DescribeRepositories",
          "ecr:ListImages"
        ]
        Resource = "*"
      },
      {
        Sid    = "DynamoDBAccess"
        Effect = "Allow"
        Action = [
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem",
          "dynamodb:ConditionCheckItem",
          "dynamodb:PutItem",
          "dynamodb:DescribeTable",
          "dynamodb:DeleteItem",
          "dynamodb:GetItem",
          "dynamodb:Scan",
          "dynamodb:Query",
          "dynamodb:UpdateItem"
        ]
        Resource = [
          "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/algoitny_main",
          "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/algoitny_main/index/*"
        ]
      },
      {
        Sid    = "S3Access"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = [
          "arn:aws:s3:::algoitny-testcases-zteapne2",
          "arn:aws:s3:::algoitny-testcases-zteapne2/*"
        ]
      },
      {
        Sid    = "SecretsManagerAccess"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:algoitny/prod/apnortheast2-*"
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/ec2/algoitny-api-*"
      },
      {
        Sid    = "SQSAccess"
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:GetQueueUrl",
          "sqs:GetQueueAttributes"
        ]
        Resource = "arn:aws:sqs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:algoitny-jobs-*"
      }
    ]
  })

  tags = {
    Name        = "algoitny-api-server-policy-${var.env_suffix}"
    Environment = var.env_suffix
    Service     = "algoitny-api"
    ManagedBy   = "terraform"
  }
}

resource "aws_iam_role_policy_attachment" "api_server" {
  role       = aws_iam_role.api_server.name
  policy_arn = aws_iam_policy.api_server.arn
}

# Attach SSM policy for Session Manager access
resource "aws_iam_role_policy_attachment" "api_server_ssm" {
  role       = aws_iam_role.api_server.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# IAM Instance Profile for API Server
resource "aws_iam_instance_profile" "api_server" {
  name = "algoitny-api-server-${var.env_suffix}"
  role = aws_iam_role.api_server.name

  tags = {
    Name        = "algoitny-api-server-${var.env_suffix}"
    Environment = var.env_suffix
    Service     = "algoitny-api"
    ManagedBy   = "terraform"
  }
}

# IAM Role for Worker
resource "aws_iam_role" "worker" {
  name               = "algoitny-worker-${var.env_suffix}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name        = "algoitny-worker-${var.env_suffix}"
    Environment = var.env_suffix
    Service     = "algoitny-worker"
    ManagedBy   = "terraform"
  }
}

# IAM Policy for Worker
resource "aws_iam_policy" "worker" {
  name        = "algoitny-worker-policy-${var.env_suffix}"
  description = "Policy for AlgoItny Worker (Celery)"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ECRAccess"
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:DescribeRepositories",
          "ecr:ListImages"
        ]
        Resource = "*"
      },
      {
        Sid    = "DynamoDBAccess"
        Effect = "Allow"
        Action = [
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem",
          "dynamodb:ConditionCheckItem",
          "dynamodb:PutItem",
          "dynamodb:DescribeTable",
          "dynamodb:DeleteItem",
          "dynamodb:GetItem",
          "dynamodb:Scan",
          "dynamodb:Query",
          "dynamodb:UpdateItem"
        ]
        Resource = [
          "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/algoitny_main",
          "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/algoitny_main/index/*"
        ]
      },
      {
        Sid    = "S3Access"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = [
          "arn:aws:s3:::algoitny-testcases-zteapne2",
          "arn:aws:s3:::algoitny-testcases-zteapne2/*"
        ]
      },
      {
        Sid    = "SecretsManagerAccess"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:algoitny/prod/apnortheast2-*"
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/ec2/algoitny-worker-*"
      },
      {
        Sid    = "SQSAccess"
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:GetQueueUrl",
          "sqs:SendMessage",
          "sqs:ChangeMessageVisibility",
          "sqs:CreateQueue"
        ]
        Resource = "arn:aws:sqs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"
      },
      {
        Sid      = "SQSListQueues"
        Effect   = "Allow"
        Action   = ["sqs:ListQueues"]
        Resource = "*"
      }
    ]
  })

  tags = {
    Name        = "algoitny-worker-policy-${var.env_suffix}"
    Environment = var.env_suffix
    Service     = "algoitny-worker"
    ManagedBy   = "terraform"
  }
}

resource "aws_iam_role_policy_attachment" "worker" {
  role       = aws_iam_role.worker.name
  policy_arn = aws_iam_policy.worker.arn
}

# Attach SSM policy for Session Manager access
resource "aws_iam_role_policy_attachment" "worker_ssm" {
  role       = aws_iam_role.worker.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# IAM Instance Profile for Worker
resource "aws_iam_instance_profile" "worker" {
  name = "algoitny-worker-${var.env_suffix}"
  role = aws_iam_role.worker.name

  tags = {
    Name        = "algoitny-worker-${var.env_suffix}"
    Environment = var.env_suffix
    Service     = "algoitny-worker"
    ManagedBy   = "terraform"
  }
}

# Data source for current AWS account
data "aws_caller_identity" "current" {}
