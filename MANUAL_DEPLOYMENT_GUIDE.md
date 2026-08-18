# Manual Deployment Guide - AWS Cost Anomaly Detective

**Use Case**: For AWS accounts with CloudFormation restrictions, organizational policies, or Early Validation hooks that block standard CloudFormation deployment.

**Time Required**: 15-20 minutes  
**Deployment Method**: AWS CLI (no CloudFormation)

---

## When to Use This Guide

Use manual deployment if you encounter:

- ❌ CloudFormation error: `AWS::EarlyValidation::PropertyValidation` failures
- ❌ Organizational policies blocking CloudFormation stack creation
- ❌ Service Control Policies (SCPs) restricting CloudFormation
- ❌ Preference for granular control over resource creation

**Advantages of Manual Deployment:**
- ✅ Bypasses CloudFormation validation hooks
- ✅ Works in highly restricted AWS accounts
- ✅ More control over individual resource configuration
- ✅ Easier to customize per-resource settings

---

## Prerequisites

Before starting, verify you have:

### 1. AWS CLI Access

```bash
aws sts get-caller-identity
```

Expected output showing your account ID and role.

### 2. Required Permissions

Your IAM user/role needs permissions to create:
- DynamoDB tables
- S3 buckets
- SNS topics
- Lambda functions
- IAM roles and policies
- EventBridge rules

### 3. Bedrock Model Access

```bash
# Verify Claude models are enabled
aws bedrock list-foundation-models \
  --region us-east-1 \
  --query 'modelSummaries[?contains(modelId, `anthropic.claude`)].[modelId,modelName]' \
  --output table
```

If empty, enable at: https://console.aws.amazon.com/bedrock/home#/modelaccess

### 4. Cost Explorer Enabled

```bash
# Verify Cost Explorer access
aws ce get-cost-and-usage \
  --time-period Start=2026-08-01,End=2026-08-14 \
  --granularity DAILY \
  --metrics BlendedCost \
  --query 'ResultsByTime[0]'
```

If error, enable at: https://console.aws.amazon.com/cost-management/

---

## Deployment Steps

### Step 1: Set Your Deployment Region

```bash
# Choose your region (must support Bedrock)
export AWS_REGION=us-east-2
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "Deploying to region: $AWS_REGION"
echo "Account ID: $AWS_ACCOUNT_ID"
```

**Supported Bedrock regions:** us-east-1, us-east-2, us-west-2, eu-west-1, eu-central-1, ap-southeast-1, ap-northeast-1

---

### Step 2: Create DynamoDB Table

```bash
aws dynamodb create-table \
  --table-name cost-anomalies \
  --attribute-definitions \
    AttributeName=PK,AttributeType=S \
    AttributeName=SK,AttributeType=S \
  --key-schema \
    AttributeName=PK,KeyType=HASH \
    AttributeName=SK,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region $AWS_REGION
```

**Verify creation:**
```bash
aws dynamodb describe-table \
  --table-name cost-anomalies \
  --region $AWS_REGION \
  --query 'Table.TableStatus'
```

Expected: `"ACTIVE"` (may take 10-30 seconds)

**Cost:** ~$1-3/month with typical usage (PAY_PER_REQUEST mode)

---

### Step 3: Create S3 Bucket for Reports

```bash
# Create bucket
aws s3 mb s3://cost-detective-reports-${AWS_ACCOUNT_ID} \
  --region $AWS_REGION

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket cost-detective-reports-${AWS_ACCOUNT_ID} \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# Block public access (security best practice)
aws s3api put-public-access-block \
  --bucket cost-detective-reports-${AWS_ACCOUNT_ID} \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

**Verify creation:**
```bash
aws s3 ls s3://cost-detective-reports-${AWS_ACCOUNT_ID}
```

**Cost:** ~$0.50-1/month for report storage

---

### Step 4: Create SNS Topic and Email Subscription

```bash
# Create SNS topic
aws sns create-topic \
  --name cost-detective-alerts \
  --region $AWS_REGION

# Subscribe your email (replace with your email)
aws sns subscribe \
  --topic-arn arn:aws:sns:${AWS_REGION}:${AWS_ACCOUNT_ID}:cost-detective-alerts \
  --protocol email \
  --notification-endpoint YOUR_EMAIL@example.com \
  --region $AWS_REGION
```

**Important:** Check your email inbox for confirmation link and click it!

**Verify subscription:**
```bash
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:${AWS_REGION}:${AWS_ACCOUNT_ID}:cost-detective-alerts \
  --region $AWS_REGION
```

Expected: `"SubscriptionArn": "arn:aws:sns:..."` (after email confirmation)

**Cost:** ~$0.50/month for notifications

---

### Step 5: Create IAM Role for Lambda

```bash
# Create the Lambda execution role
aws iam create-role \
  --role-name CostDetectiveLambdaRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach AWS managed policy for CloudWatch Logs
aws iam attach-role-policy \
  --role-name CostDetectiveLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

**Verify role creation:**
```bash
aws iam get-role --role-name CostDetectiveLambdaRole --query 'Role.Arn'
```

---

### Step 6: Attach Custom IAM Policies

**Policy 1: Cost Explorer, CloudTrail, Bedrock access**

```bash
aws iam put-role-policy \
  --role-name CostDetectiveLambdaRole \
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
```

**Policy 2: DynamoDB access**

```bash
aws iam put-role-policy \
  --role-name CostDetectiveLambdaRole \
  --policy-name DynamoDBPolicy \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{
      \"Effect\": \"Allow\",
      \"Action\": [\"dynamodb:PutItem\", \"dynamodb:GetItem\", \"dynamodb:Query\", \"dynamodb:Scan\"],
      \"Resource\": \"arn:aws:dynamodb:${AWS_REGION}:${AWS_ACCOUNT_ID}:table/cost-anomalies\"
    }]
  }"
```

**Policy 3: S3 and SNS access**

```bash
aws iam put-role-policy \
  --role-name CostDetectiveLambdaRole \
  --policy-name S3SNSPolicy \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [
      {
        \"Effect\": \"Allow\",
        \"Action\": [\"s3:PutObject\"],
        \"Resource\": \"arn:aws:s3:::cost-detective-reports-${AWS_ACCOUNT_ID}/*\"
      },
      {
        \"Effect\": \"Allow\",
        \"Action\": [\"sns:Publish\"],
        \"Resource\": \"arn:aws:sns:${AWS_REGION}:${AWS_ACCOUNT_ID}:cost-detective-alerts\"
      }
    ]
  }"
```

**Verify policies attached:**
```bash
aws iam list-role-policies --role-name CostDetectiveLambdaRole
```

Expected: `CostExplorerBedrockPolicy`, `DynamoDBPolicy`, `S3SNSPolicy`

---

### Step 7: Package Lambda Code

```bash
# Navigate to the repository
cd sample-aws-cost-anomaly-detective/src

# Install dependencies
pip3 install -r ../requirements.txt -t . --upgrade

# Create deployment package
zip -r ../function.zip . -x "*.pyc" -x "__pycache__/*" -x "*.git*"

cd ..

# Verify package size
ls -lh function.zip
```

Expected: ~30-35MB ZIP file

**Troubleshooting:**
- If `pip3` fails, install Python 3.12+
- If ZIP is >50MB, check for unnecessary files (use `-x` exclusions)

---

### Step 8: Create Lambda Function

```bash
aws lambda create-function \
  --function-name cost-detective \
  --runtime python3.12 \
  --role arn:aws:iam::${AWS_ACCOUNT_ID}:role/CostDetectiveLambdaRole \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://function.zip \
  --timeout 300 \
  --memory-size 1024 \
  --region $AWS_REGION \
  --environment Variables="{
    DYNAMODB_TABLE_NAME=cost-anomalies,
    S3_BUCKET_NAME=cost-detective-reports-${AWS_ACCOUNT_ID},
    SNS_TOPIC_ARN=arn:aws:sns:${AWS_REGION}:${AWS_ACCOUNT_ID}:cost-detective-alerts,
    THRESHOLD_PERCENTAGE=50,
    BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-6,
    AWS_REGION=${AWS_REGION}
  }"
```

**Configuration details:**
- **Timeout:** 300 seconds (5 minutes) - enough for Cost Explorer API calls
- **Memory:** 1024 MB - optimal for Bedrock inference
- **Runtime:** Python 3.12 - latest stable version
- **Threshold:** 50% - alerts when costs spike by 50% or more (configurable)

**Verify creation:**
```bash
aws lambda get-function \
  --function-name cost-detective \
  --region $AWS_REGION \
  --query 'Configuration.[FunctionName,State,LastUpdateStatus]'
```

Expected: `["cost-detective", "Active", "Successful"]`

**Cost:** ~$5-10/month with hourly execution

---

### Step 9: Test Lambda Function

```bash
# Invoke the function manually
aws lambda invoke \
  --function-name cost-detective \
  --region $AWS_REGION \
  --log-type Tail \
  response.json

# Check the response
cat response.json

# View CloudWatch logs
aws logs tail /aws/lambda/cost-detective \
  --region $AWS_REGION \
  --since 5m
```

**Expected log output:**
```
Cost Anomaly Detective triggered
Step 1: Analyzing costs...
No cost anomalies detected
```

**If errors occur**, see Troubleshooting section below.

---

### Step 10: Create EventBridge Schedule (Hourly Trigger)

```bash
# Create EventBridge rule to run every hour
aws events put-rule \
  --name cost-detective-hourly \
  --schedule-expression "rate(1 hour)" \
  --state ENABLED \
  --region $AWS_REGION

# Give EventBridge permission to invoke Lambda
aws lambda add-permission \
  --function-name cost-detective \
  --statement-id AllowEventBridgeInvoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:${AWS_REGION}:${AWS_ACCOUNT_ID}:rule/cost-detective-hourly \
  --region $AWS_REGION

# Link the rule to the Lambda function
aws events put-targets \
  --rule cost-detective-hourly \
  --targets "Id"="1","Arn"="arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:cost-detective" \
  --region $AWS_REGION
```

**Verify EventBridge rule:**
```bash
aws events describe-rule \
  --name cost-detective-hourly \
  --region $AWS_REGION
```

**Alternative schedules:**
- `rate(30 minutes)` - More frequent (higher Cost Explorer API cost)
- `rate(6 hours)` - Less frequent (lower cost)
- `rate(1 day)` - Daily check
- `cron(0 9 * * ? *)` - Daily at 9 AM UTC

---

## Post-Deployment Configuration

### Adjust Threshold Sensitivity

**Make more sensitive** (alert on smaller spikes):
```bash
aws lambda update-function-configuration \
  --function-name cost-detective \
  --region $AWS_REGION \
  --environment Variables="{
    DYNAMODB_TABLE_NAME=cost-anomalies,
    S3_BUCKET_NAME=cost-detective-reports-${AWS_ACCOUNT_ID},
    SNS_TOPIC_ARN=arn:aws:sns:${AWS_REGION}:${AWS_ACCOUNT_ID}:cost-detective-alerts,
    THRESHOLD_PERCENTAGE=30,
    BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-6,
    AWS_REGION=${AWS_REGION}
  }"
```

**Threshold recommendations:**
- **30-40%**: Production accounts (catch small anomalies)
- **50-75%**: Development/staging accounts
- **100%+**: Sandbox accounts (only major spikes)

### Add Slack Webhook (Optional)

```bash
aws lambda update-function-configuration \
  --function-name cost-detective \
  --region $AWS_REGION \
  --environment Variables="{
    DYNAMODB_TABLE_NAME=cost-anomalies,
    S3_BUCKET_NAME=cost-detective-reports-${AWS_ACCOUNT_ID},
    SNS_TOPIC_ARN=arn:aws:sns:${AWS_REGION}:${AWS_ACCOUNT_ID}:cost-detective-alerts,
    SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL,
    THRESHOLD_PERCENTAGE=50,
    BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-6,
    AWS_REGION=${AWS_REGION}
  }"
```

Get Slack webhook: https://api.slack.com/apps → Create App → Incoming Webhooks

### Change Bedrock Model

**Use Claude Opus for better analysis** (higher cost, better reasoning):
```bash
aws lambda update-function-configuration \
  --function-name cost-detective \
  --region $AWS_REGION \
  --environment "Variables={BEDROCK_MODEL_ID=anthropic.claude-opus-4-8,...}"
```

**Use Claude Haiku for lower cost** (cheaper, faster, less detailed):
```bash
aws lambda update-function-configuration \
  --function-name cost-detective \
  --region $AWS_REGION \
  --environment "Variables={BEDROCK_MODEL_ID=anthropic.claude-haiku-4-5-20251001-v1:0,...}"
```

---

## Monitoring & Maintenance

### View Recent Anomalies

```bash
# Scan DynamoDB table for recent alerts
aws dynamodb scan \
  --table-name cost-anomalies \
  --region $AWS_REGION \
  --limit 10 \
  --query 'Items[*].[PK.S,SK.S,service.S,cost_change.N,severity.S]' \
  --output table
```

### Check Lambda Execution History

```bash
# View recent executions
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=cost-detective \
  --start-time $(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum \
  --region $AWS_REGION
```

### View Lambda Logs (Live)

```bash
# Follow logs in real-time
aws logs tail /aws/lambda/cost-detective \
  --region $AWS_REGION \
  --follow
```

### Check S3 Reports

```bash
# List recent reports
aws s3 ls s3://cost-detective-reports-${AWS_ACCOUNT_ID}/ \
  --recursive \
  --human-readable \
  | tail -10
```

### Set Up CloudWatch Alarms (Recommended)

**Alert on Lambda failures:**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name cost-detective-errors \
  --alarm-description "Alert when Cost Detective Lambda fails" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 3600 \
  --evaluation-periods 1 \
  --threshold 3 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=cost-detective \
  --alarm-actions arn:aws:sns:${AWS_REGION}:${AWS_ACCOUNT_ID}:cost-detective-alerts \
  --region $AWS_REGION
```

---

## Troubleshooting

### Issue: Lambda Timeout

**Symptom:** Lambda times out after 300 seconds

**Solution:** Increase timeout
```bash
aws lambda update-function-configuration \
  --function-name cost-detective \
  --timeout 600 \
  --region $AWS_REGION
```

### Issue: "Access Denied" on Bedrock

**Symptom:** Error: "User is not authorized to perform: bedrock:InvokeModel"

**Solution:** Verify IAM policy and Bedrock model access
```bash
# Check IAM policy
aws iam get-role-policy \
  --role-name CostDetectiveLambdaRole \
  --policy-name CostExplorerBedrockPolicy

# Verify Bedrock access
aws bedrock list-foundation-models --region $AWS_REGION | grep claude
```

If no models listed, enable at console: https://console.aws.amazon.com/bedrock/

### Issue: "Access Denied" on Cost Explorer

**Symptom:** Error: "User is not authorized to perform: ce:GetCostAndUsage"

**Solution:** Check IAM policy
```bash
aws iam get-role-policy \
  --role-name CostDetectiveLambdaRole \
  --policy-name CostExplorerBedrockPolicy
```

Ensure `ce:GetCostAndUsage` is in the policy.

### Issue: No Anomalies Detected

**Possible causes:**

1. **Not enough baseline data** (wait 24-48 hours after Cost Explorer enablement)
2. **Threshold too high** (lower from 50% to 30%)
3. **No actual anomalies** (costs are stable - this is good!)

**Test with manual spike:**
```bash
# Launch a larger instance temporarily (creates cost spike)
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type m5.2xlarge \
  --count 1 \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Purpose,Value=TestAnomaly}]'

# Wait 1 hour, then check for alert
# Don't forget to terminate the instance!
```

### Issue: Email Not Received

**Symptom:** No email alerts despite anomalies

**Solution:** Confirm SNS subscription
```bash
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:${AWS_REGION}:${AWS_ACCOUNT_ID}:cost-detective-alerts \
  --region $AWS_REGION
```

If `"SubscriptionArn": "PendingConfirmation"`, check email spam folder for confirmation link.

### Issue: Lambda Package Too Large

**Symptom:** "Unzipped size must be smaller than 262144000 bytes"

**Solution:** Remove unnecessary dependencies
```bash
# Remove test files and documentation
cd src
find . -name "tests" -type d -exec rm -rf {} +
find . -name "*.md" -delete
zip -r ../function.zip . -x "*.pyc" -x "__pycache__/*"
```

---

## Cost Breakdown

**Monthly Operating Cost:**

| Service | Usage | Monthly Cost |
|---------|-------|--------------|
| Lambda | 720 invocations/month @ 1GB, 30s avg | $3-5 |
| Cost Explorer API | ~700 requests/month | $7 |
| Bedrock (Claude Sonnet 4.6) | ~500K tokens/month | $10-15 |
| DynamoDB | PAY_PER_REQUEST, low traffic | $1-3 |
| S3 | Report storage | $0.50-1 |
| SNS | Email notifications | $0.50 |
| CloudWatch Logs | 1-2GB/month | $0.50-1 |
| **Total** | | **$23-33/month** |

**Cost optimization tips:**
- Use Claude Haiku instead of Sonnet (saves ~$5-8/month)
- Run every 6 hours instead of hourly (saves ~$2-3/month)
- Set higher thresholds to reduce false positives (saves Bedrock tokens)

**ROI:** Catching one $500/month misconfigured resource = 15-20x monthly cost

---

## Uninstalling

### Delete All Resources

```bash
# Set variables (if not already set)
export AWS_REGION=us-east-2
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Delete EventBridge rule
aws events remove-targets \
  --rule cost-detective-hourly \
  --ids "1" \
  --region $AWS_REGION

aws events delete-rule \
  --name cost-detective-hourly \
  --region $AWS_REGION

# Delete Lambda function
aws lambda delete-function \
  --function-name cost-detective \
  --region $AWS_REGION

# Delete IAM role policies
aws iam delete-role-policy \
  --role-name CostDetectiveLambdaRole \
  --policy-name CostExplorerBedrockPolicy

aws iam delete-role-policy \
  --role-name CostDetectiveLambdaRole \
  --policy-name DynamoDBPolicy

aws iam delete-role-policy \
  --role-name CostDetectiveLambdaRole \
  --policy-name S3SNSPolicy

aws iam detach-role-policy \
  --role-name CostDetectiveLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam delete-role \
  --role-name CostDetectiveLambdaRole

# Delete SNS subscriptions and topic
SNS_TOPIC_ARN="arn:aws:sns:${AWS_REGION}:${AWS_ACCOUNT_ID}:cost-detective-alerts"
aws sns list-subscriptions-by-topic \
  --topic-arn $SNS_TOPIC_ARN \
  --region $AWS_REGION \
  --query 'Subscriptions[*].SubscriptionArn' \
  --output text | xargs -n1 aws sns unsubscribe --subscription-arn --region $AWS_REGION

aws sns delete-topic \
  --topic-arn $SNS_TOPIC_ARN \
  --region $AWS_REGION

# Empty and delete S3 bucket
aws s3 rm s3://cost-detective-reports-${AWS_ACCOUNT_ID} --recursive
aws s3 rb s3://cost-detective-reports-${AWS_ACCOUNT_ID}

# Delete DynamoDB table
aws dynamodb delete-table \
  --table-name cost-anomalies \
  --region $AWS_REGION
```

**Verify deletion:**
```bash
aws lambda list-functions --region $AWS_REGION | grep cost-detective
aws dynamodb list-tables --region $AWS_REGION | grep cost-anomalies
aws s3 ls | grep cost-detective
```

All commands should return empty results.

---

## Multi-Account Deployment

For AWS Organizations with multiple accounts, deploy in the **management (payer) account**:

1. Deploy all resources in management account (follow steps above)
2. Cost Explorer automatically sees all member account costs
3. CloudTrail organizational trail (optional) for cross-account event correlation

**Configuration for multi-account:**
```bash
# Add organizational permissions to IAM policy
aws iam put-role-policy \
  --role-name CostDetectiveLambdaRole \
  --policy-name OrganizationsPolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": [
        "organizations:ListAccounts",
        "organizations:DescribeAccount"
      ],
      "Resource": "*"
    }]
  }'
```

See [MULTI_ACCOUNT_DEPLOYMENT.md](docs/MULTI_ACCOUNT_DEPLOYMENT.md) for full multi-account guide.

---

## Comparison: Manual vs CloudFormation

| Aspect | Manual Deployment | CloudFormation |
|--------|------------------|----------------|
| **Time** | 15-20 minutes | 5-10 minutes |
| **Complexity** | More steps | Single command |
| **Flexibility** | Full control | Template-defined |
| **Troubleshooting** | Easier (step-by-step) | Harder (stack rollback) |
| **Works with SCPs** | ✅ Usually yes | ❌ May be blocked |
| **Updates** | Manual resource updates | Stack update |
| **Deletion** | Manual cleanup | Single stack delete |

**Recommendation:**
- Try CloudFormation first (faster, simpler)
- Use manual deployment if CloudFormation is blocked

---

## Next Steps

### After 24-48 Hours

1. **Check for anomalies:**
   ```bash
   aws dynamodb scan --table-name cost-anomalies --region $AWS_REGION
   ```

2. **Review CloudWatch Logs:**
   ```bash
   aws logs tail /aws/lambda/cost-detective --region $AWS_REGION --since 24h
   ```

3. **Tune threshold** based on false positive rate

### Enhancements

- **Add Slack integration** for real-time alerts
- **Create QuickSight dashboard** from DynamoDB data
- **Extend to multi-account** (AWS Organizations)
- **Add Jira ticket creation** for anomalies
- **Implement approval workflow** for auto-remediation

---

## Support

**GitHub Issues:**  
https://github.com/aws-samples/sample-aws-cost-anomaly-detective/issues

**Tag:** `manual-deployment` or `troubleshooting`

**AWS Support:**  
For Lambda, Bedrock, Cost Explorer issues (if you have a support plan)

---

## Quick Reference: All Commands in One Script

See [scripts/manual-deploy.sh](scripts/manual-deploy.sh) for a complete automated deployment script.

---

**Manual deployment complete!** Your Cost Anomaly Detective is now running and will alert you of cost spikes every hour.
