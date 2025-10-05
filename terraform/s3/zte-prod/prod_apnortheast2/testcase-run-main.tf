# S3 Bucket for storing contents
resource "aws_s3_bucket" "testcase_run_main" {
  bucket = "${var.account_namespace}-testcase-run-${var.shard_id}"

  versioning {
    enabled = true
  }

  lifecycle_rule {
    enabled = true
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
  }

}

# S3 Bucket Public Access Block
resource "aws_s3_bucket_public_access_block" "testcase_run_main" {
  bucket = aws_s3_bucket.testcase_run_main.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Bucket Policy for CloudFront OAI access
resource "aws_s3_bucket_policy" "testcase_run_main" {
  bucket = aws_s3_bucket.testcase_run_main.id
  depends_on = [aws_s3_bucket_public_access_block.testcase_run_main]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontOAIGetObject"
        Effect = "Allow"
        Principal = {
          AWS = aws_cloudfront_origin_access_identity.testcase_run_cdn_distribution_origin_access_identity.iam_arn
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.testcase_run_main.arn}/*"
      },
      {
        Sid    = "AllowCloudFrontOAIListBucket"
        Effect = "Allow"
        Principal = {
          AWS = aws_cloudfront_origin_access_identity.testcase_run_cdn_distribution_origin_access_identity.iam_arn
        }
        Action   = "s3:ListBucket"
        Resource = aws_s3_bucket.testcase_run_main.arn
      }
    ]
  })
}

# Cloudfront Origin Access Identity 
resource "aws_cloudfront_origin_access_identity" "testcase_run_cdn_distribution_origin_access_identity" {
  comment = "Testcase.Run origin access identity in ${var.region_namespace}"
}

# Cloudfront Distribution
resource "aws_cloudfront_distribution" "testcase_run_cdn_distribution" {

  origin {
    domain_name = aws_s3_bucket.testcase_run_main.bucket_regional_domain_name
    origin_id   = "testcase_run_origin"

    s3_origin_config {
      # Set origin id created above
      origin_access_identity = aws_cloudfront_origin_access_identity.testcase_run_cdn_distribution_origin_access_identity.cloudfront_access_identity_path
    }

  }

  enabled         = true
  is_ipv6_enabled = true

  comment             = "Cloudfront configuration for *.testcase.run"
  default_root_object = "index.html"

  # Alias of cloudfront distribution
  aliases = var.public_testcase_run_cdn_domain_name != "sample" ? [var.public_testcase_run_cdn_domain_name] : []

  # Default Cache behavior 
  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "testcase_run_origin"
    compress         = false

    forwarded_values {
      query_string            = true
      query_string_cache_keys = ["d"]

      cookies {
        forward = "all"
      }
    }

    # List of Lambda Edge Association
    #lambda_function_association {
    #  event_type   = "viewer-request"
    #  lambda_arn   = "<< Lambda Edge ARN"
    #  include_body = true
    #}

    #lambda_function_association {
    #  event_type   = "origin-response"
    #  lambda_arn   = "<< Lambda Edge ARN"
    #  include_body = false
    #}

    #lambda_function_association {
    #  event_type = "viewer-response"
    #  lambda_arn   = "<< Lambda Edge ARN"
    #  include_body = false
    #}

    viewer_protocol_policy = "redirect-to-https"

    # cache TTL Setting
    min_ttl     = 0
    default_ttl = 1800
    max_ttl     = 1800

  }

  # List of Custom Cache behavior
  # This behavior will be applied before default
  ordered_cache_behavior {

    path_pattern = "*.gif"

    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "testcase_run_origin"
    compress         = false

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 3600

    forwarded_values {
      query_string            = true
      query_string_cache_keys = ["d"]

      cookies {
        forward = "all"
      }
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  # Certification Settings
  viewer_certificate {
    acm_certificate_arn            = var.public_testcase_run_cdn_domain_name != "sample" ? var.r53_variables.prod.star_testcase_run_acm_arn_useast1 : null
    cloudfront_default_certificate = var.public_testcase_run_cdn_domain_name == "sample" ? true : false
    minimum_protocol_version       = "TLSv1.1_2016"
    ssl_support_method             = var.public_testcase_run_cdn_domain_name != "sample" ? "sni-only" : null
  }

  # Cloudfront Logging Settings

  # You can set custom error response 
  custom_error_response {
    error_caching_min_ttl = 5
    error_code            = 404
    response_code         = 404
    response_page_path    = "/404.html"
  }

  custom_error_response {
    error_caching_min_ttl = 5
    error_code            = 500
    response_code         = 500
    response_page_path    = "/500.html"
  }

  custom_error_response {
    error_caching_min_ttl = 5
    error_code            = 502
    response_code         = 502
    response_page_path    = "/500.html"
  }

  # Tags of cloudfront
  tags = {
    Name = "sample.testcase.run"
  }
}

# Route 53 Record for cloudfront
resource "aws_route53_record" "testcase_run_cdn" {
  count   = var.public_testcase_run_cdn_domain_name != "sample" ? 1 : 0
  zone_id = var.r53_variables.prod.testcase_run_zone_id
  name    = var.public_testcase_run_cdn_domain_name
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.testcase_run_cdn_distribution.domain_name
    zone_id                = "Z2FDTNDATAQYW2"
    evaluate_target_health = false
  }
}

