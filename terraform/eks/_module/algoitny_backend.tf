# AlgoItny Backend Service IAM Role
# This role allows backend pods to access DynamoDB and S3

resource "aws_iam_role" "algoitny_backend" {
  name               = "eks-${var.cluster_name}-algoitny-backend"
  assume_role_policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "${local.openid_connect_provider_id}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "${local.openid_connect_provider_url}:sub": "system:serviceaccount:production:algoitny-backend-sa"
        }
      }
    }
  ]
}
POLICY
}

# IAM Policy for DynamoDB and S3 access
resource "aws_iam_policy" "algoitny_backend" {
  name   = "eks-${var.cluster_name}-algoitny-backend-policy"
  policy = <<-EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "DynamoDBAccess",
            "Effect": "Allow",
            "Action": [
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
            ],
            "Resource": [
                "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/algoitny_main",
                "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/algoitny_main/index/*"
            ]
        },
        {
            "Sid": "S3Access",
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::algoitny-testcases-zteapne2",
                "arn:aws:s3:::algoitny-testcases-zteapne2/*"
            ]
        },
        {
            "Sid": "S3ListBucket",
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket",
                "s3:GetBucketLocation"
            ],
            "Resource": "arn:aws:s3:::algoitny-testcases-zteapne2"
        }
    ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "algoitny_backend" {
  policy_arn = aws_iam_policy.algoitny_backend.arn
  role       = aws_iam_role.algoitny_backend.name
}

# Data source for current AWS account
data "aws_caller_identity" "current" {}
