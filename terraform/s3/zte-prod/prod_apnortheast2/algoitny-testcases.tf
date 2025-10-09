# S3 Bucket for storing contents
resource "aws_s3_bucket" "algoitny_testcases" {
  bucket = "algoitny-testcases-${var.shard_id}"

  versioning {
    enabled = false
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
resource "aws_s3_bucket_public_access_block" "algoitny_testcases" {
  bucket = aws_s3_bucket.algoitny_testcases.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
