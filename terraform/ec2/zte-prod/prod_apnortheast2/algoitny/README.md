# AlgoItny EC2 Auto Scaling Group Infrastructure

This Terraform configuration creates EC2 Auto Scaling Groups for the AlgoItny backend services (API and Worker). The ALB and Target Groups are managed separately in the `terraform/services/algoitnyapi` directory.

## Architecture Overview

```
Internet
    |
    v
[Application Load Balancer] (managed in services/algoitnyapi)
    |
    v
[API Server ASG] (t3.medium)
    |
    +-- Instance 1 (Docker: API)
    +-- Instance 2 (Docker: API)
    +-- Instance N...

[Worker ASG] (t3.large)
    |
    +-- Instance 1 (Docker: Celery Worker)
    +-- Instance 2 (Docker: Celery Worker)
    +-- Instance N...
```

## Components

### 1. IAM Roles (`iam_roles.tf`)
- **API Server Role**: Permissions for ECR, DynamoDB, S3, Secrets Manager, CloudWatch Logs, and ElastiCache
- **Worker Role**: Same permissions as API Server for background task processing
- Both roles include SSM Session Manager access for secure SSH-less access

### 2. Security Groups (`security_groups.tf`)
- **API Server Security Group**: Allows traffic from ALB Security Group on port 8000
- **Worker Security Group**: No inbound except SSH from VPC
- Both allow all outbound traffic

### 3. Launch Templates (`launch_templates.tf`)
- Uses Amazon Linux 2023 AMI
- Configures user data scripts to:
  - Install Docker and AWS CLI
  - Pull Docker image from ECR
  - Fetch secrets from AWS Secrets Manager
  - Start containerized application
- API: t3.medium with 30GB EBS
- Worker: t3.large with 50GB EBS

### 4. Auto Scaling Groups (`autoscaling_groups.tf`)
- **API ASG**:
  - Min: 2, Max: 10, Desired: 2
  - Target Tracking: CPU 70% and ALB Request Count
  - Health Check: ELB
  - Attached to existing ALB Target Group
- **Worker ASG**:
  - Min: 1, Max: 5, Desired: 2
  - Target Tracking: CPU 70%
  - Health Check: EC2

### 5. User Data Scripts
- **`user_data_api.sh`**: Initializes API server container on port 8000
- **`user_data_worker.sh`**: Initializes Celery worker container

Both scripts:
- Install Docker, Docker Compose, AWS CLI v2, CloudWatch Agent
- Configure CloudWatch Logs
- Fetch secrets from AWS Secrets Manager
- Authenticate with ECR and pull Docker image
- Start containerized service with environment variables

## Prerequisites

1. **VPC Infrastructure**: Existing VPC with public and private subnets
2. **ECR Repository**: Docker images pushed to ECR
3. **DynamoDB**: `algoitny_main` table created
4. **ElastiCache Redis**: Redis cluster for Celery broker
5. **Secrets Manager**: `algoitny-secrets` with required keys:
   - `SECRET_KEY`
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `GEMINI_API_KEY`
   - `OPENAI_API_KEY`
   - `ANTHROPIC_API_KEY`
6. **Load Balancer**: ALB and Target Groups created in `terraform/services/algoitnyapi`

## Configuration

### 1. Update `terraform.tfvars`

```hcl
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
```

### 2. Verify Remote State References

The configuration references these remote states:
- **VPC**: `terraform/vpc/zte_apnortheast2/terraform.tfstate`
- **ECR**: `terraform/ecr/zte-prod/prod_apnortheast2/terraform.tfstate`
- **Databases**: `terraform/databases/zte-prod/zte_apnortheast2/algoitny/terraform.tfstate`
- **Services**: `terraform/services/algoitnyapi/zte_apnortheast2/terraform.tfstate`

Update `remote_state.tf` if your state paths differ.

## Deployment

### Step 1: Deploy Services (ALB, Target Groups)

```bash
cd terraform/services/algoitnyapi/zte_apnortheast2
terraform init
terraform apply
```

This creates:
- Application Load Balancer (External & Internal)
- Target Groups for API traffic
- Security Groups for ALB
- Route53 DNS records

### Step 2: Deploy Auto Scaling Groups

```bash
cd terraform/ec2/zte-prod/prod_apnortheast2/algoitny
terraform init
terraform plan
terraform apply
```

This creates:
- Launch Templates for API and Worker
- Auto Scaling Groups
- IAM Roles and Instance Profiles
- Security Groups for EC2 instances
- CloudWatch Alarms

### Step 3: Verify Deployment

```bash
# Check ASG status
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names algoitny-api-asg-prod algoitny-worker-asg-prod

# Check ALB Target Group health
aws elbv2 describe-target-health \
  --target-group-arn $(terraform output -raw external_target_group_arn)

# Test API health endpoint
curl https://api.testcase.run/api/health/
```

## Updating Docker Images

### 1. Build and Push New Image

```bash
# Build Docker image
cd backend
docker build -t algoitny:v1.0.0 .

# Tag for ECR
ECR_URL=$(aws ecr describe-repositories --repository-names algoitny --query 'repositories[0].repositoryUri' --output text)
docker tag algoitny:v1.0.0 $ECR_URL:v1.0.0

# Login to ECR
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin $ECR_URL

# Push image
docker push $ECR_URL:v1.0.0
```

### 2. Update Auto Scaling Group

```bash
# Update image tag in terraform.tfvars
image_tag = "v1.0.0"

# Apply changes (updates Launch Template)
terraform apply

# Trigger instance refresh for gradual rollout
aws autoscaling start-instance-refresh \
  --auto-scaling-group-name algoitny-api-asg-prod \
  --preferences MinHealthyPercentage=50

aws autoscaling start-instance-refresh \
  --auto-scaling-group-name algoitny-worker-asg-prod \
  --preferences MinHealthyPercentage=50
```

## Monitoring

### CloudWatch Logs

- API Logs: `/aws/ec2/algoitny-api-prod`
- Worker Logs: `/aws/ec2/algoitny-worker-prod`

### CloudWatch Alarms

- `algoitny-api-high-cpu-prod`: API CPU > 80%
- `algoitny-worker-high-cpu-prod`: Worker CPU > 80%

### Metrics to Monitor

- **ASG Metrics**: Instance count, scaling activities
- **ALB Metrics**: Request count, latency, 4xx/5xx errors (from services module)
- **Target Group Metrics**: Healthy/unhealthy host count
- **EC2 Metrics**: CPU, Memory, Network

## Troubleshooting

### 1. Instances Not Healthy in Target Group

```bash
# Check instance logs via SSM
INSTANCE_ID=$(aws ec2 describe-instances \
  --filters "Name=tag:Service,Values=algoitny-api" "Name=instance-state-name,Values=running" \
  --query 'Reservations[0].Instances[0].InstanceId' --output text)

aws ssm start-session --target $INSTANCE_ID

# On instance:
sudo tail -f /var/log/user-data.log
sudo docker logs algoitny-api
```

### 2. Container Startup Failures

Common issues:
- **Secrets Manager access denied**: Check IAM role in `iam_roles.tf`
- **ECR pull failed**: Verify ECR repository policy and IAM role
- **Health check failed**:
  - Check application logs: `docker logs algoitny-api`
  - Verify `/api/health/` endpoint returns 200
  - Check security group allows ALB traffic on port 8000

### 3. Scaling Issues

```bash
# Check ASG activity
aws autoscaling describe-scaling-activities \
  --auto-scaling-group-name algoitny-api-asg-prod \
  --max-records 10

# Check scaling policies
aws autoscaling describe-policies \
  --auto-scaling-group-name algoitny-api-asg-prod
```

### 4. Target Group Connection Issues

```bash
# Verify security group allows ALB -> EC2 traffic
aws ec2 describe-security-group-rules \
  --filters "Name=group-id,Values=sg-xxxxx" \
  --query 'SecurityGroupRules[?FromPort==`8000`]'

# Check if EC2 instance can reach Redis
aws ssm start-session --target $INSTANCE_ID
curl -v telnet://your-redis-endpoint:6379
```

## Integration with Services Module

This EC2 module integrates with the existing services module:

### Services Module Provides:
- ALB (External & Internal)
- Target Groups
- Security Groups for ALB
- Route53 DNS records

### This EC2 Module Provides:
- Auto Scaling Groups
- EC2 Launch Templates
- IAM Roles for EC2
- Security Groups for EC2
- Attachment to existing Target Groups

### Data Flow:
```
[Services Remote State]
    ↓ (provides)
- external_target_group_arn
- external_lb_security_group_id
- external_lb_arn_suffix
    ↓ (consumed by)
[EC2 Module]
    ↓ (creates)
- Auto Scaling Groups
- EC2 Instances
    ↓ (registers to)
[ALB Target Group]
```

## Cost Optimization

1. **Use Spot Instances** (optional):
   - Add spot instance configuration to launch template
   - 50-70% cost savings for worker instances
   - Not recommended for API servers due to interruptions

2. **Scheduled Scaling**:
   - Scale down during off-peak hours
   - Use scheduled actions in ASG

3. **Right-size Instances**:
   - Monitor CPU/Memory usage in CloudWatch
   - Adjust instance types based on actual usage
   - Consider t3a instances (10% cheaper than t3)

## Security Best Practices

1. **Secrets Management**: All secrets stored in AWS Secrets Manager
2. **IAM Least Privilege**: Each service has minimal required permissions
3. **Network Isolation**: Private subnets for instances, public for ALB only
4. **Encryption**: EBS volumes encrypted, HTTPS enforced
5. **Session Manager**: SSH access via SSM, no SSH keys needed
6. **IMDSv2**: Instance metadata v2 enforced

## Outputs

After applying, the following outputs are available:

```bash
terraform output api_server_asg_name    # API ASG name
terraform output worker_asg_name        # Worker ASG name
terraform output api_server_security_group_id  # API SG ID
terraform output worker_security_group_id      # Worker SG ID
```

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

Note: This will NOT destroy the ALB and Target Groups (managed by services module). Destroy those separately if needed.
