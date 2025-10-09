# AlgoItny DynamoDB Terraform Configuration

This directory contains Terraform configuration for the AlgoItny DynamoDB table in production environment.

## Table Structure

### Main Table: `algoitny_main`

**Primary Keys:**
- `PK` (Hash Key): Partition key - String
- `SK` (Range Key): Sort key - String

### Global Secondary Indexes

#### GSI1: User Authentication Index
- **Hash Key:** `GSI1PK` (String)
- **Range Key:** `GSI1SK` (String)
- **Projection:** ALL
- **Purpose:** User lookup by email or Google ID

**Access Patterns:**
- Find user by email: `GSI1PK = EMAIL#{email}`
- Find user by Google ID: `GSI1PK = GID#{google_id}`

#### GSI2: Public History Timeline Index
- **Hash Key:** `GSI2PK` (String)
- **Range Key:** `GSI2SK` (String)
- **Projection:** KEYS_ONLY
- **Purpose:** Public code execution history feed

**Access Patterns:**
- Get public history: `GSI2PK = PUBLIC#HIST`, sorted by `GSI2SK` (timestamp)

#### GSI3: Problem Status Index
- **Hash Key:** `GSI3PK` (String)
- **Range Key:** `GSI3SK` (Number)
- **Projection:** ALL
- **Purpose:** Efficient querying of completed/draft problems

**Access Patterns:**
- List completed problems: `GSI3PK = PROB#COMPLETED`, sorted by `GSI3SK` (timestamp)
- List draft problems: `GSI3PK = PROB#DRAFT`, sorted by `GSI3SK` (timestamp)

## Features

### Data Protection
- ✅ **Point-in-Time Recovery (PITR):** 35-day backup window
- ✅ **Server-Side Encryption:** AWS managed keys
- ✅ **Deletion Protection:** Enabled in production
- ✅ **DynamoDB Streams:** NEW_AND_OLD_IMAGES for event processing

### Monitoring
- ✅ **CloudWatch Alarms:**
  - Read throttle events
  - Write throttle events
  - High read capacity (cost monitoring)

### Auto-Scaling
- ✅ **Billing Mode:** PAY_PER_REQUEST (on-demand)
- ✅ **TTL:** Enabled for automatic data expiration

## Usage

### Prerequisites
1. AWS credentials configured
2. S3 backend bucket: `zte-prod-apnortheast2-tfstate`
3. DynamoDB lock table: `terraform-lock`

### Initialize Terraform
```bash
cd /Users/gwonsoolee/algoitny/terraform/dynamodb/algoitny/prod_apnortheast2
terraform init
```

### Plan Changes
```bash
terraform plan
```

### Apply Changes
```bash
terraform apply
```

### Destroy (⚠️ Use with caution)
```bash
# Deletion protection must be disabled first
terraform apply -var="enable_deletion_protection=false"
terraform destroy
```

## Configuration Variables

### Required Variables
- `assume_role_arn`: IAM role ARN to assume
- `environment`: Environment name (default: "prod")
- `project_name`: Project name (default: "algoitny")

### Optional Variables
- `billing_mode`: PROVISIONED or PAY_PER_REQUEST (default: PAY_PER_REQUEST)
- `enable_streams`: Enable DynamoDB Streams (default: true)
- `stream_view_type`: Stream view type (default: NEW_AND_OLD_IMAGES)
- `enable_point_in_time_recovery`: Enable PITR (default: true)
- `enable_deletion_protection`: Enable deletion protection (default: true)
- `tags`: Additional resource tags (default: {})

## Outputs

- `table_name`: DynamoDB table name
- `table_arn`: Table ARN
- `table_stream_arn`: Stream ARN (for Lambda triggers)
- `gsi1_name`, `gsi2_name`, `gsi3_name`: GSI names

## Cost Optimization

### Current Configuration (PAY_PER_REQUEST)
- **Estimated Monthly Cost:** $0.50 - $5.00 (depends on traffic)
- **RCU Cost:** $0.25 per million read units
- **WCU Cost:** $1.25 per million write units

### Optimization Tips
1. **Use GSI3 for problem queries** - 99% cost reduction vs Scans
2. **Denormalize data** - Avoid N+1 query patterns
3. **Enable TTL** - Auto-delete old usage logs
4. **Monitor CloudWatch alarms** - Detect unusual usage patterns

## Related Documentation

- [Backend DynamoDB Schema](../../../../backend/api/dynamodb/table_schema.py)
- [Optimization Summary](../../../../backend/DYNAMODB_OPTIMIZATIONS_SUMMARY.md)
- [Single Table Design](../../../../backend/DYNAMODB_SINGLE_TABLE_DESIGN_V2.md)

## Support

For questions or issues:
- Check CloudWatch metrics: DynamoDB console → Metrics
- Review application logs: `docker logs algoitny-backend`
- DynamoDB admin (LocalStack): http://localhost:8001

---

**Last Updated:** 2025-10-09
**Managed By:** Terraform
**Environment:** Production (ap-northeast-2)
