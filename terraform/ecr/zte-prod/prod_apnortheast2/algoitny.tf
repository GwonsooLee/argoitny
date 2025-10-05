resource "aws_ecr_repository" "algoitny" {
  name = "algoitny"
}

resource "aws_ecr_repository_policy" "algoitny" {
  repository = aws_ecr_repository.algoitny.name

  policy = <<EOF
{
    "Version": "2008-10-17",
    "Statement": [
        {
            "Sid": "new policy",
            "Effect": "Allow",
            "Principal": {
              "AWS": [
                "arn:aws:iam::442863828268:root"
              ]
            },
            "Action": [
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr:BatchCheckLayerAvailability",
                "ecr:DescribeRepositories",
                "ecr:GetRepositoryPolicy",
                "ecr:ListImages"
            ]
        }
    ]
}
EOF
}
