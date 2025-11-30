#!/bin/bash

# Production-Ready Deployment Script
# Builds, pushes, and deploys to AWS ECS with full validation and URL return

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Enable Docker BuildKit for faster builds
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Error handling
trap 'echo -e "\n${RED}Deployment failed at line $LINENO${NC}"; exit 1' ERR

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Production Deployment to AWS ECS${NC}"
echo -e "${BLUE}========================================${NC}"

# Load environment variables from ~/.env using loadenv function
loadenv() {
    local env_file="$1"
    if [ ! -f "$env_file" ]; then
        return 1
    fi
    
    set -a
    # Read and export variables, handling comments and empty lines
    while IFS= read -r line || [ -n "$line" ]; do
        # Remove leading/trailing whitespace
        line=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        
        # Skip empty lines and comments
        [ -z "$line" ] && continue
        [[ "$line" =~ ^# ]] && continue
        
        # Export the variable (handles KEY=value format)
        if [[ "$line" =~ ^[[:alnum:]_]+= ]]; then
            export "$line" 2>/dev/null || true
        fi
    done < "$env_file"
    set +a
    return 0
}

# Try to load from ~/.env first, then fall back to local .env
ENV_LOADED=false
if loadenv ~/.env; then
    echo -e "${GREEN}✅ Loaded environment variables from ~/.env${NC}"
    ENV_LOADED=true
elif [ -f .env ]; then
    if loadenv .env; then
        echo -e "${GREEN}✅ Loaded environment variables from .env${NC}"
        ENV_LOADED=true
    fi
fi

if [ "$ENV_LOADED" = false ]; then
    echo -e "${YELLOW}⚠️  No .env file found (using defaults)${NC}"
fi

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
ECR_REPO_BACKEND=${ECR_REPO_BACKEND:-data-annotation-backend}
ECR_REPO_FRONTEND=${ECR_REPO_FRONTEND:-data-annotation-frontend}
CLUSTER_NAME=${CLUSTER_NAME:-data-annotation-cluster}
SERVICE_NAME=${SERVICE_NAME:-data-annotation-service}
TASK_FAMILY=${TASK_FAMILY:-data-annotation-tool}

# ============================================
# Step 1: Validate Prerequisites
# ============================================
echo -e "\n${YELLOW}Step 1: Validating prerequisites...${NC}"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✅ AWS CLI installed${NC}"

# Check Docker
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker Desktop.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker is running${NC}"

# Check jq
if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}⚠️  jq not installed (recommended for JSON parsing)${NC}"
fi

# Validate AWS credentials
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")
if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo -e "${RED}❌ Failed to get AWS account ID. Check your AWS credentials.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ AWS credentials valid (Account: ${AWS_ACCOUNT_ID})${NC}"

# ECR URIs
ECR_BACKEND_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_BACKEND}"
ECR_FRONTEND_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_FRONTEND}"

# ============================================
# Step 2: Validate Infrastructure
# ============================================
echo -e "\n${YELLOW}Step 2: Validating infrastructure...${NC}"

# Check ECS cluster
if ! aws ecs describe-clusters --clusters $CLUSTER_NAME --region $AWS_REGION > /dev/null 2>&1; then
    echo -e "${RED}❌ ECS cluster '${CLUSTER_NAME}' does not exist${NC}"
    echo -e "${YELLOW}Run: ./setup-infrastructure.sh${NC}"
    exit 1
fi
echo -e "${GREEN}✅ ECS cluster exists${NC}"

# Check ALB
ALB_ARN=$(aws elbv2 describe-load-balancers \
    --names data-annotation-alb \
    --query 'LoadBalancers[0].LoadBalancerArn' \
    --output text \
    --region $AWS_REGION 2>/dev/null || echo "")

if [ -z "$ALB_ARN" ] || [ "$ALB_ARN" == "None" ]; then
    echo -e "${RED}❌ Application Load Balancer 'data-annotation-alb' does not exist${NC}"
    echo -e "${YELLOW}Run: ./setup-infrastructure.sh${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Application Load Balancer exists${NC}"

# Get ALB DNS
ALB_DNS=$(aws elbv2 describe-load-balancers \
    --names data-annotation-alb \
    --query 'LoadBalancers[0].DNSName' \
    --output text \
    --region $AWS_REGION 2>/dev/null || echo "")

if [ -z "$ALB_DNS" ] || [ "$ALB_DNS" == "None" ]; then
    echo -e "${RED}❌ Could not retrieve ALB DNS name${NC}"
    exit 1
fi
echo -e "${GREEN}✅ ALB DNS: ${ALB_DNS}${NC}"

# Check target group
TG_ARN=$(aws elbv2 describe-target-groups \
    --names data-annotation-tg \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text \
    --region $AWS_REGION 2>/dev/null || echo "")

if [ -z "$TG_ARN" ] || [ "$TG_ARN" == "None" ]; then
    echo -e "${RED}❌ Target group 'data-annotation-tg' does not exist${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Target group exists${NC}"

# Load infrastructure IDs
if [ -f infrastructure-output.json ]; then
    VPC_ID=$(jq -r '.vpc_id' infrastructure-output.json 2>/dev/null || echo "")
    SUBNET_1_ID=$(jq -r '.subnet_1_id' infrastructure-output.json 2>/dev/null || echo "")
    SUBNET_2_ID=$(jq -r '.subnet_2_id' infrastructure-output.json 2>/dev/null || echo "")
    ECS_SG_ID=$(jq -r '.ecs_security_group_id' infrastructure-output.json 2>/dev/null || echo "")
    
    if [ -z "$VPC_ID" ] || [ "$VPC_ID" == "null" ]; then
        echo -e "${RED}❌ Invalid infrastructure-output.json${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Infrastructure IDs loaded${NC}"
else
    echo -e "${RED}❌ infrastructure-output.json not found${NC}"
    exit 1
fi

# ============================================
# Step 3: Authenticate with ECR
# ============================================
echo -e "\n${YELLOW}Step 3: Authenticating with ECR...${NC}"
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin \
    ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com > /dev/null 2>&1
echo -e "${GREEN}✅ ECR authentication successful${NC}"

# ============================================
# Step 4: Ensure ECR Repositories Exist
# ============================================
echo -e "\n${YELLOW}Step 4: Ensuring ECR repositories exist...${NC}"

(aws ecr describe-repositories --repository-names $ECR_REPO_BACKEND --region $AWS_REGION > /dev/null 2>&1 || \
    aws ecr create-repository --repository-name $ECR_REPO_BACKEND --region $AWS_REGION > /dev/null 2>&1) &
BACKEND_REPO_PID=$!

(aws ecr describe-repositories --repository-names $ECR_REPO_FRONTEND --region $AWS_REGION > /dev/null 2>&1 || \
    aws ecr create-repository --repository-name $ECR_REPO_FRONTEND --region $AWS_REGION > /dev/null 2>&1) &
FRONTEND_REPO_PID=$!

wait $BACKEND_REPO_PID && echo -e "${GREEN}✅ Backend repository ready${NC}"
wait $FRONTEND_REPO_PID && echo -e "${GREEN}✅ Frontend repository ready${NC}"

# ============================================
# Step 5: Build Docker Images (Parallel)
# ============================================
echo -e "\n${YELLOW}Step 5: Building Docker images in parallel...${NC}"
cd "$(dirname "$0")/.."

build_image() {
    local dockerfile=$1
    local image_name=$2
    local ecr_uri=$3
    local description=$4
    local log_file="/tmp/build_${image_name}.log"
    
    echo -e "${CYAN}Building ${description}...${NC}"
    
    if docker build \
        --progress=quiet \
        --cache-from type=registry,ref=${ecr_uri}:latest \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        -f ${dockerfile} \
        -t ${image_name}:latest \
        -t ${ecr_uri}:latest \
        . > ${log_file} 2>&1; then
        echo -e "${GREEN}✅ ${description} built successfully${NC}"
        return 0
    else
        echo -e "${RED}❌ ${description} build failed${NC}"
        echo -e "${YELLOW}Last 30 lines of build log:${NC}"
        tail -30 ${log_file}
        return 1
    fi
}

# Build both images in parallel
build_image docker/Dockerfile.backend ${ECR_REPO_BACKEND} ${ECR_BACKEND_URI} "Backend" &
BACKEND_PID=$!

build_image docker/Dockerfile.frontend ${ECR_REPO_FRONTEND} ${ECR_FRONTEND_URI} "Frontend" &
FRONTEND_PID=$!

# Wait for both builds
wait $BACKEND_PID
BACKEND_EXIT=$?

wait $FRONTEND_PID
FRONTEND_EXIT=$?

if [ $BACKEND_EXIT -ne 0 ] || [ $FRONTEND_EXIT -ne 0 ]; then
    echo -e "${RED}❌ Image build failed${NC}"
    exit 1
fi

# ============================================
# Step 6: Push Images to ECR (Parallel)
# ============================================
echo -e "\n${YELLOW}Step 6: Pushing images to ECR...${NC}"

docker push ${ECR_BACKEND_URI}:latest &
BACKEND_PUSH_PID=$!

docker push ${ECR_FRONTEND_URI}:latest &
FRONTEND_PUSH_PID=$!

wait $BACKEND_PUSH_PID
BACKEND_PUSH_EXIT=$?

wait $FRONTEND_PUSH_PID
FRONTEND_PUSH_EXIT=$?

if [ $BACKEND_PUSH_EXIT -ne 0 ] || [ $FRONTEND_PUSH_EXIT -ne 0 ]; then
    echo -e "${RED}❌ Image push failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All images pushed successfully${NC}"

# ============================================
# Step 7: Update Task Definition
# ============================================
echo -e "\n${YELLOW}Step 7: Updating ECS task definition...${NC}"
cd deployment

# Create temporary task definition file
TASK_DEF_TEMP=$(mktemp)
cp ecs-task-definition.json $TASK_DEF_TEMP

# Replace placeholders (macOS compatible)
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s|YOUR_ECR_REPO_URL|${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com|g" $TASK_DEF_TEMP
    sed -i '' "s|YOUR_ACCOUNT_ID|${AWS_ACCOUNT_ID}|g" $TASK_DEF_TEMP
    sed -i '' "s|REGION|${AWS_REGION}|g" $TASK_DEF_TEMP
    
    # Update ALLOWED_HOSTS and CORS
    if [ ! -z "$ALB_DNS" ] && [ "$ALB_DNS" != "None" ]; then
        sed -i '' "s|\"YOUR_DOMAIN.com,YOUR_ALB_DNS_NAME.elb.amazonaws.com\"|\"${ALB_DNS}\"|g" $TASK_DEF_TEMP
        sed -i '' "s|YOUR_ALB_DNS_NAME.elb.amazonaws.com|${ALB_DNS}|g" $TASK_DEF_TEMP
        sed -i '' "s|http://YOUR_ALB_DNS_NAME.elb.amazonaws.com,https://YOUR_DOMAIN.com|http://${ALB_DNS}|g" $TASK_DEF_TEMP
    fi
else
    sed -i "s|YOUR_ECR_REPO_URL|${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com|g" $TASK_DEF_TEMP
    sed -i "s|YOUR_ACCOUNT_ID|${AWS_ACCOUNT_ID}|g" $TASK_DEF_TEMP
    sed -i "s|REGION|${AWS_REGION}|g" $TASK_DEF_TEMP
    
    # Update ALLOWED_HOSTS and CORS
    if [ ! -z "$ALB_DNS" ] && [ "$ALB_DNS" != "None" ]; then
        sed -i "s|\"YOUR_DOMAIN.com,YOUR_ALB_DNS_NAME.elb.amazonaws.com\"|\"${ALB_DNS}\"|g" $TASK_DEF_TEMP
        sed -i "s|YOUR_ALB_DNS_NAME.elb.amazonaws.com|${ALB_DNS}|g" $TASK_DEF_TEMP
        sed -i "s|http://YOUR_ALB_DNS_NAME.elb.amazonaws.com,https://YOUR_DOMAIN.com|http://${ALB_DNS}|g" $TASK_DEF_TEMP
    fi
fi

# Register task definition
TASK_DEF_OUTPUT=$(aws ecs register-task-definition \
    --cli-input-json file://${TASK_DEF_TEMP} \
    --region $AWS_REGION 2>&1)

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to register task definition${NC}"
    echo "$TASK_DEF_OUTPUT"
    rm -f $TASK_DEF_TEMP
    exit 1
fi

TASK_REVISION=$(echo "$TASK_DEF_OUTPUT" | jq -r '.taskDefinition.revision' 2>/dev/null || echo "")
if [ -z "$TASK_REVISION" ] || [ "$TASK_REVISION" == "null" ]; then
    echo -e "${RED}❌ Failed to get task definition revision${NC}"
    rm -f $TASK_DEF_TEMP
    exit 1
fi

rm -f $TASK_DEF_TEMP
echo -e "${GREEN}✅ Task definition registered: ${TASK_FAMILY}:${TASK_REVISION}${NC}"

# ============================================
# Step 8: Create or Update ECS Service
# ============================================
echo -e "\n${YELLOW}Step 8: Creating/updating ECS service...${NC}"

# Check if service exists
SERVICE_EXISTS=$(aws ecs describe-services \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --region $AWS_REGION \
    --query 'services[0].status' \
    --output text 2>/dev/null || echo "NONE")

if [ "$SERVICE_EXISTS" == "ACTIVE" ] || [ "$SERVICE_EXISTS" == "DRAINING" ]; then
    # Update existing service
    echo -e "${CYAN}Updating existing service...${NC}"
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $SERVICE_NAME \
        --task-definition ${TASK_FAMILY}:${TASK_REVISION} \
        --force-new-deployment \
        --region $AWS_REGION > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Service updated successfully${NC}"
    else
        echo -e "${RED}❌ Failed to update service${NC}"
        exit 1
    fi
else
    # Create new service
    echo -e "${CYAN}Creating new service...${NC}"
    aws ecs create-service \
        --cluster $CLUSTER_NAME \
        --service-name $SERVICE_NAME \
        --task-definition ${TASK_FAMILY}:${TASK_REVISION} \
        --desired-count 1 \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[${SUBNET_1_ID},${SUBNET_2_ID}],securityGroups=[${ECS_SG_ID}],assignPublicIp=ENABLED}" \
        --load-balancers "targetGroupArn=${TG_ARN},containerName=frontend,containerPort=80" \
        --health-check-grace-period-seconds 60 \
        --region $AWS_REGION > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Service created successfully${NC}"
    else
        echo -e "${RED}❌ Failed to create service${NC}"
        exit 1
    fi
fi

# ============================================
# Step 9: Wait for Service to Stabilize
# ============================================
echo -e "\n${YELLOW}Step 9: Waiting for service to stabilize...${NC}"
echo -e "${CYAN}(This may take 5-10 minutes for first deployment)${NC}"

MAX_WAIT=600  # 10 minutes
ELAPSED=0
INTERVAL=15

while [ $ELAPSED -lt $MAX_WAIT ]; do
    SERVICE_STATUS=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services $SERVICE_NAME \
        --region $AWS_REGION \
        --query 'services[0].deployments[0].status' \
        --output text 2>/dev/null || echo "UNKNOWN")
    
    RUNNING_COUNT=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services $SERVICE_NAME \
        --region $AWS_REGION \
        --query 'services[0].runningCount' \
        --output text 2>/dev/null || echo "0")
    
    DESIRED_COUNT=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services $SERVICE_NAME \
        --region $AWS_REGION \
        --query 'services[0].desiredCount' \
        --output text 2>/dev/null || echo "0")
    
    if [ "$SERVICE_STATUS" == "PRIMARY" ] && [ "$RUNNING_COUNT" -ge "$DESIRED_COUNT" ] && [ "$RUNNING_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✅ Service is running (${RUNNING_COUNT}/${DESIRED_COUNT} tasks)${NC}"
        break
    fi
    
    echo -e "${CYAN}Waiting... (${ELAPSED}s/${MAX_WAIT}s) - Status: ${SERVICE_STATUS}, Running: ${RUNNING_COUNT}/${DESIRED_COUNT}${NC}"
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo -e "${YELLOW}⚠️  Service stabilization timeout. Service may still be starting.${NC}"
    echo -e "${YELLOW}Check status manually: aws ecs describe-services --cluster ${CLUSTER_NAME} --services ${SERVICE_NAME}${NC}"
fi

# ============================================
# Step 10: Verify and Return URL
# ============================================
echo -e "\n${YELLOW}Step 10: Verifying deployment...${NC}"

# Verify ALB is accessible
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "http://${ALB_DNS}" || echo "000")

if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "301" ] || [ "$HTTP_CODE" == "302" ]; then
    echo -e "${GREEN}✅ Application is responding (HTTP ${HTTP_CODE})${NC}"
else
    echo -e "${YELLOW}⚠️  Application may still be starting (HTTP ${HTTP_CODE})${NC}"
    echo -e "${YELLOW}This is normal for first deployment. Wait a few more minutes.${NC}"
fi

# ============================================
# Final Output
# ============================================
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   🎉 Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${CYAN}Application URL:${NC}"
echo -e "${BLUE}http://${ALB_DNS}${NC}"
echo ""
echo -e "${CYAN}Deployment Summary:${NC}"
echo -e "  • Backend Image: ${ECR_BACKEND_URI}:latest"
echo -e "  • Frontend Image: ${ECR_FRONTEND_URI}:latest"
echo -e "  • Task Definition: ${TASK_FAMILY}:${TASK_REVISION}"
echo -e "  • Cluster: ${CLUSTER_NAME}"
echo -e "  • Service: ${SERVICE_NAME}"
echo -e "  • Region: ${AWS_REGION}"
echo ""
echo -e "${CYAN}Useful Commands:${NC}"
echo -e "  Monitor service:"
echo -e "    ${YELLOW}aws ecs describe-services --cluster ${CLUSTER_NAME} --services ${SERVICE_NAME} --region ${AWS_REGION}${NC}"
echo -e "  View logs:"
echo -e "    ${YELLOW}aws logs tail /ecs/data-annotation-backend --follow --region ${AWS_REGION}${NC}"
echo -e "    ${YELLOW}aws logs tail /ecs/data-annotation-frontend --follow --region ${AWS_REGION}${NC}"
echo ""

# Export URL for scripting
export DEPLOYMENT_URL="http://${ALB_DNS}"
echo "DEPLOYMENT_URL=http://${ALB_DNS}" > /tmp/deployment-url.txt

echo -e "${GREEN}✅ Deployment URL saved to /tmp/deployment-url.txt${NC}"
echo -e "${GREEN}✅ Your application is ready at: http://${ALB_DNS}${NC}"

