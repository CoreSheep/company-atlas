# Deployment Directory

This directory contains all files and scripts needed to deploy the Data Annotation Tool to AWS ECS.

## 🚀 Quick Start

### One-Command Deployment

```bash
cd deployment
./deploy-production.sh
```

The production deployment script will:
- ✅ Validate all prerequisites (AWS CLI, Docker, credentials)
- ✅ Check infrastructure (ECS cluster, ALB, target groups)
- ✅ Build and push Docker images in parallel
- ✅ Deploy to ECS with automatic service management
- ✅ Wait for service stabilization
- ✅ Return the application URL

### Get the Deployment URL

After deployment, the URL is displayed and saved:

```bash
# View URL
cat /tmp/deployment-url.txt

# Or use in scripts
source /tmp/deployment-url.txt && echo $DEPLOYMENT_URL
```

## 📁 Key Files

### Deployment Scripts

- **`deploy-production.sh`** ⭐ - **Main deployment script**: Production-ready deployment with full validation, parallel builds, and URL return

### Configuration Files

- `ecs-task-definition.json` - ECS task definition template (used by deployment script)
- `ecs-service-definition.json` - ECS service definition template (reference)
- `.env` - Environment variables (create from `.env.example` if needed)
- `.env.example` - Example environment variables file
- `.dockerignore` - Files excluded from Docker builds (located in project root)
- `.gitignore` - Git ignore rules for deployment directory

## 📋 Prerequisites

Before deploying, ensure you have:

- ✅ **AWS CLI** installed and configured (`aws configure`)
- ✅ **Docker Desktop** installed and running
- ✅ **jq** installed (recommended for JSON parsing)
- ✅ **AWS Account** with appropriate permissions
- ✅ **Infrastructure** already set up (ECS cluster, ALB, target groups, VPC, security groups)

## 🏗️ Initial Setup

### Prerequisites: Infrastructure Setup

Before deploying, ensure your AWS infrastructure is set up:

- **ECS Cluster** named `data-annotation-cluster`
- **Application Load Balancer** named `data-annotation-alb`
- **Target Group** named `data-annotation-tg`
- **VPC and Subnets** with public IP assignment enabled
- **Security Groups** configured for ALB and ECS tasks
- **IAM Roles** for ECS tasks with proper permissions
- **CloudWatch Log Groups** for `/ecs/data-annotation-backend` and `/ecs/data-annotation-frontend`
- **`infrastructure-output.json`** file with infrastructure resource IDs

The deployment script will validate that all required infrastructure exists before proceeding.

#### infrastructure-output.json Format

Create this file in the deployment directory with the following structure:

```json
{
  "vpc_id": "vpc-xxxxxxxxxxxxx",
  "subnet_1_id": "subnet-xxxxxxxxxxxxx",
  "subnet_2_id": "subnet-xxxxxxxxxxxxx",
  "alb_security_group_id": "sg-xxxxxxxxxxxxx",
  "ecs_security_group_id": "sg-xxxxxxxxxxxxx",
  "region": "us-east-1",
  "account_id": "123456789012"
}
```

### Deploy Application

```bash
./deploy-production.sh
```

The script will:
1. Validate all prerequisites and infrastructure
2. Build and push Docker images
3. Deploy to ECS
4. Return the application URL

**Note**: The script requires `infrastructure-output.json` file with infrastructure IDs. If this file doesn't exist, you'll need to create it or set up the infrastructure first.

## 🔄 Deployment Process

The `deploy-production.sh` script follows this flow:

1. **Validate Prerequisites** - Check AWS CLI, Docker, credentials
2. **Validate Infrastructure** - Verify ECS cluster, ALB, target groups exist
3. **Authenticate with ECR** - Login to AWS ECR
4. **Ensure ECR Repositories** - Create if they don't exist
5. **Build Docker Images** - Build backend and frontend in parallel
6. **Push Images to ECR** - Push both images in parallel
7. **Update Task Definition** - Register new task definition revision
8. **Create/Update ECS Service** - Deploy or update the service
9. **Wait for Stabilization** - Monitor until service is running
10. **Verify and Return URL** - Health check and display URL

## 🏛️ Architecture

```
Internet
   ↓
Application Load Balancer (ALB)
   ↓
ECS Service (Fargate)
   ├── Frontend Container (Nginx + React)
   └── Backend Container (Django + Gunicorn)
```

## ⚡ Performance Optimizations

The deployment includes several optimizations:

- **Parallel Builds** - Backend and frontend build simultaneously
- **Parallel Pushes** - Images push to ECR concurrently
- **BuildKit Cache** - Uses inline cache for faster rebuilds
- **Optimized Dockerfiles** - Layer caching for dependencies
- **.dockerignore** - Excludes unnecessary files (reduced from 33MB to 60KB)

**Expected Deployment Time**: ~10-15 minutes (first deployment), ~7-10 minutes (subsequent)

## 💰 Cost Estimate

- **Fargate**: ~$30-40/month (2 tasks, 0.5 vCPU, 1GB RAM each)
- **ALB**: ~$20/month
- **ECR**: ~$1-5/month (storage and transfer)
- **CloudWatch**: ~$5-10/month (logs and metrics)
- **Total**: ~$60-75/month

## 🔍 Monitoring

### Check Service Status

```bash
aws ecs describe-services \
  --cluster data-annotation-cluster \
  --services data-annotation-service \
  --region us-east-1
```

### View Logs

```bash
# Backend logs
aws logs tail /ecs/data-annotation-backend --follow --region us-east-1

# Frontend logs
aws logs tail /ecs/data-annotation-frontend --follow --region us-east-1
```

### Check ALB Health

```bash
aws elbv2 describe-target-health \
  --target-group-arn <TARGET_GROUP_ARN> \
  --region us-east-1
```

## 🛠️ Troubleshooting

### Common Issues

1. **Docker not running**
   ```bash
   # Start Docker Desktop, then retry
   ./deploy-production.sh
   ```

2. **AWS credentials invalid**
   ```bash
   aws configure
   ```

3. **Infrastructure missing**
   - Ensure ECS cluster, ALB, and target groups exist in AWS
   - Create `infrastructure-output.json` with required resource IDs:
     ```json
     {
       "vpc_id": "vpc-xxxxx",
       "subnet_1_id": "subnet-xxxxx",
       "subnet_2_id": "subnet-xxxxx",
       "ecs_security_group_id": "sg-xxxxx",
       "region": "us-east-1",
       "account_id": "123456789012"
     }
     ```

4. **Build fails**
   ```bash
   # Check build logs
   cat /tmp/build_data-annotation-backend.log
   cat /tmp/build_data-annotation-frontend.log
   ```

5. **Service not starting**
   ```bash
   # Check service events
   aws ecs describe-services \
     --cluster data-annotation-cluster \
     --services data-annotation-service \
     --region us-east-1 \
     --query 'services[0].events[:5]'
   
   # Check task status
   aws ecs list-tasks \
     --cluster data-annotation-cluster \
     --service-name data-annotation-service \
     --region us-east-1
   ```

6. **Missing infrastructure-output.json**
   - The script requires this file with infrastructure IDs
   - Create it manually or ensure infrastructure setup script generates it
   - Required fields: `vpc_id`, `subnet_1_id`, `subnet_2_id`, `ecs_security_group_id`

## 🔐 Security

- No hardcoded credentials
- Uses environment variables
- Secure ECR authentication
- Proper IAM role usage
- Secrets from AWS Secrets Manager

## ✨ Features

- **Idempotent** - Safe to run multiple times
- **Error Handling** - Comprehensive validation and error messages
- **Parallel Operations** - Faster deployments
- **URL Return** - Automatic URL retrieval and verification
- **Health Checks** - HTTP verification after deployment
- **Progress Tracking** - Real-time status updates

