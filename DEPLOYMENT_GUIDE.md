# Deployment Guide - AWS Cost Anomaly Detective

**Production-ready deployment with security hardening and operational best practices**

---

## Prerequisites

- AWS CLI installed and configured
- Appropriate IAM permissions
- Email address for alerts
- (Optional) Slack webhook URL
- Valid Anthropic API key or AWS Bedrock access

---

## Step 1: Deploy Cross-Account Role (Optional)

If deploying from a different AWS account:

```bash
aws cloudformation create-stack \
  --stack-name cost-detective-deployment-role \
  --template-body file://cross-account-deployment-role.yaml \
  --parameters ParameterKey=TrustedAccountId,ParameterValue=YOUR_MGMT_ACCOUNT_ID \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

---

## Step 2: Deploy Main Stack with Termination Protection

```bash
aws cloudformation create-stack \
  --stack-name cost-detective \
  --template-body file://cloudformation/deployment-template.yaml \
  --parameters \
    ParameterKey=AlertEmail,ParameterValue=your-email@example.com \
    ParameterKey=SlackWebhookUrl,ParameterValue=https://hooks.slack.com/services/YOUR/WEBHOOK \
    ParameterKey=ThresholdPercentage,ParameterValue=50 \
    ParameterKey=ScheduleExpression,ParameterValue="rate(1 hour)" \
    ParameterKey=MonthlyBudgetLimit,ParameterValue=20 \
  --capabilities CAPABILITY_IAM \
  --enable-termination-protection \
  --region us-east-1
```

**Important:** `--enable-termination-protection` prevents accidental stack deletion.

---

## Step 3: Confirm SNS Subscriptions

You will receive **three** confirmation emails:

1. **AlertTopic** - Regular cost anomaly alerts
2. **DLQAlarmTopic** - Operational/failure alerts  
3. **CostBudget** - Budget notifications (80%, 100% actual + forecast)

Click "Confirm subscription" in all three emails.

---

## Step 4: Package and Deploy Lambda Code

```bash
# Navigate to source directory
cd src

# Install dependencies
pip install -r ../requirements.txt -t .

# Package function
zip -r ../function.zip .

# Return to root
cd ..

# Deploy code to Lambda
aws lambda update-function-code \
  --function-name cost-detective \
  --zip-file fileb://function.zip \
  --region us-east-1
```

---

## Step 5: Validate Deployment

### Check Stack Status

```bash
aws cloudformation describe-stacks \
  --stack-name cost-detective \
  --query 'Stacks[0].StackStatus' \
  --output text \
  --region us-east-1
```

Expected output: `CREATE_COMPLETE`

### Verify Termination Protection

```bash
aws cloudformation describe-stacks \
  --stack-name cost-detective \
  --query 'Stacks[0].EnableTerminationProtection' \
  --output text \
  --region us-east-1
```

Expected output: `True`

### Test Lambda Function

```bash
aws lambda invoke \
  --function-name cost-detective \
  --payload '{}' \
  --region us-east-1 \
  response.json

cat response.json
```

### Monitor Lambda Logs

```bash
aws logs tail /aws/lambda/cost-detective --follow --region us-east-1
```

---

## Stack Termination Protection

### Why It's Enabled

- Prevents accidental deletion of production stack
- Protects data resources (DynamoDB, S3) from inadvertent removal
- Requires explicit disabling before deletion

### How to Delete Stack (When Needed)

**Step 1: Disable termination protection**

```bash
aws cloudformation update-termination-protection \
  --stack-name cost-detective \
  --no-enable-termination-protection \
  --region us-east-1
```

**Step 2: Delete the stack**

```bash
aws cloudformation delete-stack \
  --stack-name cost-detective \
  --region us-east-1
```

**Note:** Even after stack deletion:
- DynamoDB table will be retained (`DeletionPolicy: Retain`)
- S3 buckets will be retained (`DeletionPolicy: Retain`)
- You must manually delete these resources if truly no longer needed

### Manual Resource Cleanup (After Stack Deletion)

```bash
# Delete DynamoDB table
aws dynamodb delete-table \
  --table-name cost-anomalies \
  --region us-east-1

# Empty and delete S3 buckets
aws s3 rm s3://cost-detective-reports-$(aws sts get-caller-identity --query Account --output text) --recursive
aws s3 rb s3://cost-detective-reports-$(aws sts get-caller-identity --query Account --output text)

aws s3 rm s3://cost-detective-logs-$(aws sts get-caller-identity --query Account --output text) --recursive
aws s3 rb s3://cost-detective-logs-$(aws sts get-caller-identity --query Account --output text)

# Delete backup vault (must be empty first)
aws backup delete-backup-vault \
  --backup-vault-name cost-detective-backup-vault \
  --region us-east-1
```

---

## Testing

### Test 1: Lambda Execution

```bash
aws lambda invoke \
  --function-name cost-detective \
  --payload '{}' \
  response.json

# Check for errors
cat response.json
```

### Test 2: DLQ Functionality

```bash
# Trigger a failure (modify payload to cause error)
aws lambda invoke \
  --function-name cost-detective \
  --payload '{"force_error": true}' \
  response.json

# Check DLQ for messages
aws sqs receive-message \
  --queue-url $(aws sqs get-queue-url --queue-name cost-detective-dlq --query QueueUrl --output text) \
  --region us-east-1

# Check if DLQ alarm triggered
aws cloudwatch describe-alarm-history \
  --alarm-name cost-detective-dlq-messages \
  --max-records 5 \
  --region us-east-1
```

### Test 3: S3 Versioning

```bash
# Create test file
echo "version 1" > test.txt

# Upload to S3
aws s3 cp test.txt s3://cost-detective-reports-$(aws sts get-caller-identity --query Account --output text)/test.txt

# Modify and re-upload
echo "version 2" > test.txt
aws s3 cp test.txt s3://cost-detective-reports-$(aws sts get-caller-identity --query Account --output text)/test.txt

# List versions
aws s3api list-object-versions \
  --bucket cost-detective-reports-$(aws sts get-caller-identity --query Account --output text) \
  --prefix test.txt

# Should show 2 versions
```

### Test 4: Backup Plan

```bash
# Check backup plan
aws backup list-backup-plans \
  --region us-east-1

# After first scheduled backup (daily at 5 AM UTC), check vault
aws backup list-recovery-points-by-backup-vault \
  --backup-vault-name cost-detective-backup-vault \
  --region us-east-1
```

### Test 5: Budget Alerts

```bash
# Check budget configuration
aws budgets describe-budget \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget-name cost-detective-monthly-budget

# Budget notifications will arrive via email when thresholds are crossed
```

---

## Monitoring

### CloudWatch Dashboard

Create a custom dashboard to monitor key metrics:

```bash
# Create dashboard.json file first, then:
aws cloudwatch put-dashboard \
  --dashboard-name cost-detective \
  --dashboard-body file://dashboard.json \
  --region us-east-1
```

**Recommended Metrics:**
- Lambda: Invocations, Errors, Duration, Throttles, Concurrent Executions
- DynamoDB: ConsumedReadCapacityUnits, ConsumedWriteCapacityUnits
- SQS (DLQ): ApproximateNumberOfMessagesVisible
- S3: BucketSizeBytes, NumberOfObjects

### Active Alarms

The deployment includes 4 CloudWatch alarms:

1. **cost-detective-lambda-errors** - Function failures
2. **cost-detective-lambda-throttles** - Concurrency limit hit
3. **cost-detective-lambda-duration** - Approaching timeout
4. **cost-detective-dlq-messages** - Failed events in DLQ

Check alarm status:

```bash
aws cloudwatch describe-alarms \
  --alarm-name-prefix cost-detective \
  --region us-east-1
```

---

## Cost Management

### Expected Monthly Costs

| Service | Estimated Cost |
|---------|----------------|
| Lambda | $2-5 (hourly execution) |
| DynamoDB | $1-3 (on-demand) |
| S3 | $0.50-2 (storage + requests) |
| CloudWatch | $1-2 (logs + metrics) |
| Backup | $0.50-1 (daily backups) |
| Secrets Manager | $0.40 (if Slack enabled) |
| **Total** | **$5-15/month** |

### Budget Alerts

You'll receive email alerts at:
- **80% of budget** (actual spend)
- **100% of budget** (actual spend)
- **100% of budget** (forecasted spend)

### Cost Optimization

To reduce costs:

1. **Reduce execution frequency:**
   ```bash
   aws cloudformation update-stack \
     --stack-name cost-detective \
     --use-previous-template \
     --parameters \
       ParameterKey=ScheduleExpression,ParameterValue="rate(6 hours)" \
       ParameterKey=AlertEmail,UsePreviousValue=true \
       ParameterKey=SlackWebhookUrl,UsePreviousValue=true \
       ParameterKey=ThresholdPercentage,UsePreviousValue=true \
       ParameterKey=MonthlyBudgetLimit,UsePreviousValue=true \
     --capabilities CAPABILITY_IAM \
     --region us-east-1
   ```

2. **Reduce log retention:**
   ```bash
   aws logs put-retention-policy \
     --log-group-name /aws/lambda/cost-detective \
     --retention-in-days 7 \
     --region us-east-1
   ```

3. **Reduce S3 lifecycle:**
   Update `deployment-template.yaml` to expire reports after 30 days instead of 90.

---

## Troubleshooting

### Lambda Function Fails

**Check logs:**
```bash
aws logs tail /aws/lambda/cost-detective --since 1h --region us-east-1
```

**Common issues:**
- Missing Secrets Manager permissions (if Slack configured)
- Bedrock model not available in region
- Cost Explorer API throttling
- Insufficient Lambda timeout

### DLQ Has Messages

**Retrieve messages:**
```bash
aws sqs receive-message \
  --queue-url $(aws sqs get-queue-url --queue-name cost-detective-dlq --query QueueUrl --output text) \
  --max-number-of-messages 10 \
  --region us-east-1
```

**Analyze failures, fix issue, then purge DLQ:**
```bash
aws sqs purge-queue \
  --queue-url $(aws sqs get-queue-url --queue-name cost-detective-dlq --query QueueUrl --output text) \
  --region us-east-1
```

### No Alerts Received

**Check SNS subscriptions:**
```bash
aws sns list-subscriptions-by-topic \
  --topic-arn $(aws cloudformation describe-stacks --stack-name cost-detective --query 'Stacks[0].Outputs[?OutputKey==`SNSTopicArn`].OutputValue' --output text) \
  --region us-east-1
```

Subscription status should be `Confirmed`. If `PendingConfirmation`, check your email.

### Stack Update Fails

**Check stack events:**
```bash
aws cloudformation describe-stack-events \
  --stack-name cost-detective \
  --max-items 20 \
  --region us-east-1
```

Look for resources in `UPDATE_FAILED` status.

---

## Backup & Recovery

### Manual Backup

```bash
# Trigger on-demand backup
aws backup start-backup-job \
  --backup-vault-name cost-detective-backup-vault \
  --resource-arn $(aws dynamodb describe-table --table-name cost-anomalies --query Table.TableArn --output text) \
  --iam-role-arn $(aws cloudformation describe-stacks --stack-name cost-detective --query 'Stacks[0].Outputs[?OutputKey==`BackupRoleArn`].OutputValue' --output text) \
  --region us-east-1
```

### Restore from Backup

```bash
# List available recovery points
aws backup list-recovery-points-by-backup-vault \
  --backup-vault-name cost-detective-backup-vault \
  --region us-east-1

# Restore (replace RECOVERY_POINT_ARN with actual ARN from above)
aws backup start-restore-job \
  --recovery-point-arn RECOVERY_POINT_ARN \
  --metadata \
    targetTableName=cost-anomalies-restored \
  --iam-role-arn $(aws cloudformation describe-stacks --stack-name cost-detective --query 'Stacks[0].Outputs[?OutputKey==`BackupRoleArn`].OutputValue' --output text) \
  --region us-east-1
```

---

## Security Best Practices

### Rotate Secrets

If using Slack webhook:

```bash
# Update secret in Secrets Manager
aws secretsmanager update-secret \
  --secret-id cost-detective/slack-webhook \
  --secret-string '{"webhook_url": "NEW_WEBHOOK_URL"}' \
  --region us-east-1

# No Lambda restart needed - retrieved at runtime
```

### Review IAM Permissions

Periodically audit Lambda execution role:

```bash
aws iam get-role-policy \
  --role-name $(aws cloudformation describe-stacks --stack-name cost-detective --query 'Stacks[0].Outputs[?OutputKey==`LambdaRoleArn`].OutputValue' --output text | cut -d'/' -f2) \
  --policy-name CostDetectivePolicy \
  --region us-east-1
```

### Enable CloudTrail

If not already enabled:

```bash
aws cloudtrail create-trail \
  --name cost-detective-audit \
  --s3-bucket-name YOUR_CLOUDTRAIL_BUCKET \
  --is-multi-region-trail \
  --enable-log-file-validation
```

---

## Upgrade Guide

### Update CloudFormation Template

```bash
aws cloudformation update-stack \
  --stack-name cost-detective \
  --template-body file://cloudformation/deployment-template.yaml \
  --parameters \
    ParameterKey=AlertEmail,UsePreviousValue=true \
    ParameterKey=SlackWebhookUrl,UsePreviousValue=true \
    ParameterKey=ThresholdPercentage,UsePreviousValue=true \
    ParameterKey=ScheduleExpression,UsePreviousValue=true \
    ParameterKey=MonthlyBudgetLimit,UsePreviousValue=true \
  --capabilities CAPABILITY_IAM \
  --region us-east-1
```

### Update Lambda Code

```bash
cd src
pip install -r ../requirements.txt -t . --upgrade
zip -r ../function.zip .
cd ..

aws lambda update-function-code \
  --function-name cost-detective \
  --zip-file fileb://function.zip \
  --region us-east-1
```

---

## Support

- **AWS Documentation:** https://docs.aws.amazon.com/
- **Project Repository:** https://github.com/aws-samples/sample-aws-cost-anomaly-detective
- **CloudFormation Docs:** https://docs.aws.amazon.com/cloudformation/
- **Lambda Best Practices:** https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html

---

**Deployment Status:** Production-Ready ✅