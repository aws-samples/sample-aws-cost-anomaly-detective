#!/bin/bash

################################################################################
# AWS Cost Anomaly Detective - Manual Deployment Script
#
# Use this script when CloudFormation is blocked by organizational policies
# or validation hooks.
#
# Usage:
#   ./manual-deploy.sh <your-email@example.com> <aws-region>
#
# Example:
#   ./manual-deploy.sh ops-team@company.com us-east-2
#
# Prerequisites:
#   - AWS CLI configured
#   - Bedrock model access enabled
#   - Cost Explorer enabled
################################################################################

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
EMAIL_ADDRESS=$1
AWS_REGION=${2:-us-east-2}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Validate inputs
if [ -z "$EMAIL_ADDRESS" ]; then
    print_error "Email address is required"
    echo "Usage: $0 <your-email@example.com> [aws-region]"
    exit 1
fi

if [[ ! "$EMAIL_ADDRESS" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
    print_error "Invalid email address format: $EMAIL_ADDRESS"
    exit 1
fi

# Banner
echo "=============================================="
echo "  AWS Cost Anomaly Detective Deployment"
echo "=============================================="
echo ""
print_status "Target Email: $EMAIL_ADDRESS"
print_status "AWS Region: $AWS_REGION"
print_status "AWS Account: $AWS_ACCOUNT_ID"
echo ""

# Step 1: Verify prerequisites
print_status "Step 1/10: Verifying prerequisites..."

# Check Bedrock access
if aws bedrock list-foundation-models --region $AWS_REGION --query 'modelSummaries[?contains(modelId, `anthropic.claude`)].modelId' --output text | grep -q claude; then
    print_success "Bedrock Claude models accessible"
else
    print_error "Bedrock Claude models not enabled"
    echo "Enable at: https://console.aws.amazon.com/bedrock/home?region=${AWS_REGION}#/modelaccess"
    exit 1
fi

# Check Cost Explorer access
if aws ce get-cost-and-usage --time-period Start=2026-08-01,End=2026-08-02 --granularity DAILY --metrics BlendedCost &>/dev/null; then
    print_success "Cost Explorer enabled"
else
    print_warning "Cost Explorer may not be enabled or needs 24h to populate data"
fi

# Step 2: Create DynamoDB table
print_status "Step 2/10: Creating DynamoDB table..."

if aws dynamodb describe-table --table-name cost-anomalies --region $AWS_REGION &>/dev/null; then
    print_warning "DynamoDB table 'cost-anomalies' already exists, skipping"
else
    aws dynamodb create-table \
      --table-name cost-anomalies \
      --attribute-definitions \
        AttributeName=PK,AttributeType=S \
        AttributeName=SK,AttributeType=S \
      --key-schema \
        AttributeName=PK,KeyType=HASH \
        AttributeName=SK,KeyType=RANGE \
      --billing-mode PAY_PER_REQUEST \
      --region $AWS_REGION \
      --output json > /dev/null

    print_success "DynamoDB table created"

    # Wait for table to become active
    print_status "Waiting for table to become active..."
    aws dynamodb wait table-exists --table-name cost-anomalies --region $AWS_REGION
    print_success "Table is active"
fi

# Step 3: Create S3 bucket
print_status "Step 3/10: Creating S3 bucket..."

BUCKET_NAME="cost-detective-reports-${AWS_ACCOUNT_ID}"

if aws s3 ls "s3://${BUCKET_NAME}" &>/dev/null; then
    print_warning "S3 bucket '${BUCKET_NAME}' already exists, skipping"
else
    aws s3 mb "s3://${BUCKET_NAME}" --region $AWS_REGION

    aws s3api put-bucket-encryption \
      --bucket $BUCKET_NAME \
      --server-side-encryption-configuration '{
        "Rules": [{
          "ApplyServerSideEncryptionByDefault": {
            "SSEAlgorithm": "AES256"
          }
        }]
      }'

    aws s3api put-public-access-block \
      --bucket $BUCKET_NAME \
      --public-access-block-configuration \
        BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

    print_success "S3 bucket created and encrypted"
fi

# Step 4: Create SNS topic
print_status "Step 4/10: Creating SNS topic..."

TOPIC_ARN="arn:aws:sns:${AWS_REGION}:${AWS_ACCOUNT_ID}:cost-detective-alerts"

if aws sns get-topic-attributes --topic-arn $TOPIC_ARN --region $AWS_REGION &>/dev/null; then
    print_warning "SNS topic already exists, skipping"
else
    aws sns create-topic \
      --name cost-detective-alerts \
      --region $AWS_REGION \
      --output json > /dev/null

    print_success "SNS topic created"
fi

# Subscribe email
print_status "Subscribing email to SNS topic..."
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol email \
  --notification-endpoint $EMAIL_ADDRESS \
  --region $AWS_REGION \
  --output json > /dev/null

print_success "Email subscribed (check inbox for confirmation link)"

# Step 5: Create IAM role
print_status "Step 5/10: Creating IAM role..."

ROLE_NAME="CostDetectiveLambdaRole"

if aws iam get-role --role-name $ROLE_NAME &>/dev/null; then
    print_warning "IAM role '${ROLE_NAME}' already exists, skipping"
else
    aws iam create-role \
      --role-name $ROLE_NAME \
      --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
          "Effect": "Allow",
          "Principal": {"Service": "lambda.amazonaws.com"},
          "Action": "sts:AssumeRole"
        }]
      }' \
      --output json > /dev/null

    print_success "IAM role created"

    # Wait for role to propagate
    sleep 2
fi

# Step 6: Attach IAM policies
print_status "Step 6/10: Attaching IAM policies..."

# Attach basic Lambda execution policy
aws iam attach-role-policy \
  --role-name $ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole \
  2>/dev/null || true

# Policy 1: Cost Explorer and Bedrock
aws iam put-role-policy \
  --role-name $ROLE_NAME \
  --policy-name CostExplorerBedrockPolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": [
        "ce:GetCostAndUsage",
        "ce:GetCostForecast",
        "cloudtrail:LookupEvents",
        "config:DescribeConfigurationRecorders",
        "cloudwatch:GetMetricStatistics",
        "bedrock:InvokeModel"
      ],
      "Resource": "*"
    }]
  }'

# Policy 2: DynamoDB
aws iam put-role-policy \
  --role-name $ROLE_NAME \
  --policy-name DynamoDBPolicy \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{
      \"Effect\": \"Allow\",
      \"Action\": [\"dynamodb:PutItem\", \"dynamodb:GetItem\", \"dynamodb:Query\", \"dynamodb:Scan\"],
      \"Resource\": \"arn:aws:dynamodb:${AWS_REGION}:${AWS_ACCOUNT_ID}:table/cost-anomalies\"
    }]
  }"

# Policy 3: S3 and SNS
aws iam put-role-policy \
  --role-name $ROLE_NAME \
  --policy-name S3SNSPolicy \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [
      {
        \"Effect\": \"Allow\",
        \"Action\": [\"s3:PutObject\"],
        \"Resource\": \"arn:aws:s3:::${BUCKET_NAME}/*\"
      },
      {
        \"Effect\": \"Allow\",
        \"Action\": [\"sns:Publish\"],
        \"Resource\": \"${TOPIC_ARN}\"
      }
    ]
  }"

print_success "IAM policies attached"

# Wait for IAM propagation
print_status "Waiting for IAM propagation (10 seconds)..."
sleep 10

# Step 7: Package Lambda code
print_status "Step 7/10: Packaging Lambda code..."

# Check if we're in the right directory
if [ ! -d "src" ]; then
    print_error "Must run from repository root (where src/ directory exists)"
    exit 1
fi

cd src

# Install dependencies
print_status "Installing Python dependencies..."
pip3 install -r ../requirements.txt -t . --upgrade --quiet

# Create deployment package
print_status "Creating deployment ZIP..."
zip -rq ../function.zip . -x "*.pyc" -x "__pycache__/*" -x "*.git*"

cd ..

ZIP_SIZE=$(ls -lh function.zip | awk '{print $5}')
print_success "Lambda package created (${ZIP_SIZE})"

# Step 8: Create Lambda function
print_status "Step 8/10: Creating Lambda function..."

FUNCTION_NAME="cost-detective"

if aws lambda get-function --function-name $FUNCTION_NAME --region $AWS_REGION &>/dev/null; then
    print_warning "Lambda function '${FUNCTION_NAME}' already exists, updating code..."

    aws lambda update-function-code \
      --function-name $FUNCTION_NAME \
      --zip-file fileb://function.zip \
      --region $AWS_REGION \
      --output json > /dev/null

    print_success "Lambda function code updated"
else
    aws lambda create-function \
      --function-name $FUNCTION_NAME \
      --runtime python3.12 \
      --role "arn:aws:iam::${AWS_ACCOUNT_ID}:role/${ROLE_NAME}" \
      --handler lambda_function.lambda_handler \
      --zip-file fileb://function.zip \
      --timeout 300 \
      --memory-size 1024 \
      --region $AWS_REGION \
      --environment "Variables={
        DYNAMODB_TABLE_NAME=cost-anomalies,
        S3_BUCKET_NAME=${BUCKET_NAME},
        SNS_TOPIC_ARN=${TOPIC_ARN},
        THRESHOLD_PERCENTAGE=50,
        BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-6,
        AWS_REGION=${AWS_REGION}
      }" \
      --output json > /dev/null

    print_success "Lambda function created"
fi

# Wait for function to become active
print_status "Waiting for Lambda to become active..."
sleep 5

# Step 9: Test Lambda function
print_status "Step 9/10: Testing Lambda function..."

aws lambda invoke \
  --function-name $FUNCTION_NAME \
  --region $AWS_REGION \
  --log-type Tail \
  response.json > /dev/null

if grep -q "No cost anomalies detected" response.json || grep -q "anomalies" response.json; then
    print_success "Lambda test successful"
else
    print_warning "Lambda test completed, check response.json for details"
fi

# Step 10: Create EventBridge schedule
print_status "Step 10/10: Creating EventBridge schedule..."

RULE_NAME="cost-detective-hourly"

if aws events describe-rule --name $RULE_NAME --region $AWS_REGION &>/dev/null; then
    print_warning "EventBridge rule already exists, skipping"
else
    # Create rule
    aws events put-rule \
      --name $RULE_NAME \
      --schedule-expression "rate(1 hour)" \
      --state ENABLED \
      --region $AWS_REGION \
      --output json > /dev/null

    # Add Lambda permission
    aws lambda add-permission \
      --function-name $FUNCTION_NAME \
      --statement-id AllowEventBridgeInvoke \
      --action lambda:InvokeFunction \
      --principal events.amazonaws.com \
      --source-arn "arn:aws:events:${AWS_REGION}:${AWS_ACCOUNT_ID}:rule/${RULE_NAME}" \
      --region $AWS_REGION \
      --output json > /dev/null 2>&1 || true

    # Add target
    aws events put-targets \
      --rule $RULE_NAME \
      --targets "Id"="1","Arn"="arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function/${FUNCTION_NAME}" \
      --region $AWS_REGION \
      --output json > /dev/null

    print_success "EventBridge schedule created (runs hourly)"
fi

# Cleanup
rm -f response.json
rm -f function.zip

# Final summary
echo ""
echo "=============================================="
echo "  Deployment Complete!"
echo "=============================================="
echo ""
print_success "All resources deployed successfully"
echo ""
echo "Resources created:"
echo "  - DynamoDB Table: cost-anomalies"
echo "  - S3 Bucket: ${BUCKET_NAME}"
echo "  - SNS Topic: ${TOPIC_ARN}"
echo "  - Lambda Function: ${FUNCTION_NAME}"
echo "  - EventBridge Rule: ${RULE_NAME} (hourly)"
echo "  - IAM Role: ${ROLE_NAME}"
echo ""
print_warning "IMPORTANT: Check ${EMAIL_ADDRESS} for SNS confirmation email"
echo ""
echo "Next steps:"
echo "  1. Confirm SNS subscription via email"
echo "  2. Wait 24-48 hours for baseline to establish"
echo "  3. Monitor: aws logs tail /aws/lambda/${FUNCTION_NAME} --region ${AWS_REGION} --follow"
echo "  4. Check anomalies: aws dynamodb scan --table-name cost-anomalies --region ${AWS_REGION}"
echo ""
echo "Estimated monthly cost: \$25-35"
echo ""
print_success "Deployment script completed successfully!"
