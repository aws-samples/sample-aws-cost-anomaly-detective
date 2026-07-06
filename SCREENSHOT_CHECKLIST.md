# Cost Anomaly Detective - Screenshot Checklist

**Account:** XXXXXXXXXXXX (Management Account)  
**Region:** us-east-1  
**Date Deployed:** July 5, 2026

---

## 📸 Required Screenshots

### ✅ 1. DynamoDB Table
**URL:** https://us-east-1.console.aws.amazon.com/dynamodbv2/home?region=us-east-1#table?name=cost-anomalies

**Show:**
- [ ] Table name: `cost-anomalies`
- [ ] Table status: Active
- [ ] Billing mode: On-demand
- [ ] Primary key: PK (partition), SK (sort)
- [ ] Global Secondary Index: GSI1 visible
- [ ] Item count (0 initially, will grow as anomalies are detected)

**File name:** `01-dynamodb-table.png`

---

### ✅ 2. S3 Bucket
**URL:** https://s3.console.aws.amazon.com/s3/buckets/cost-detective-reports-XXXXXXXXXXXX

**Show:**
- [ ] Bucket name: `cost-detective-reports-XXXXXXXXXXXX`
- [ ] Region: us-east-1
- [ ] Block all public access: On
- [ ] Default encryption: Enabled (AES-256)
- [ ] Bucket policies (optional - show it's empty/default)

**File name:** `02-s3-bucket.png`

**Bonus screenshot (after first report):**
- [ ] Objects tab showing sample report files
- File name: `02b-s3-reports.png`

---

### ✅ 3. SNS Topic
**URL:** https://us-east-1.console.aws.amazon.com/sns/v3/home?region=us-east-1#/topic/arn:aws:sns:us-east-1:XXXXXXXXXXXX:cost-anomaly-alerts

**Show:**
- [ ] Topic name: `cost-anomaly-alerts`
- [ ] Topic ARN
- [ ] Subscriptions: 1 email subscription
- [ ] Subscription status: **Confirmed** (make sure to confirm email first!)

**File name:** `03-sns-topic.png`

**Action required:** Check email `user@example.com` and confirm subscription before screenshot!

---

### ✅ 4. Lambda Function Overview
**URL:** https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/functions/cost-detective

**Show:**
- [ ] Function name: `cost-detective`
- [ ] Runtime: Python 3.12
- [ ] Memory: 1024 MB
- [ ] Timeout: 5 minutes (300 seconds)
- [ ] Last modified timestamp
- [ ] Function ARN

**File name:** `04-lambda-overview.png`

---

### ✅ 5. Lambda Configuration
**URL:** (same as above, click "Configuration" tab)

**Show:**
- [ ] Environment variables:
  - DYNAMODB_TABLE_NAME
  - S3_BUCKET_NAME
  - SNS_TOPIC_ARN
  - THRESHOLD_PERCENTAGE
  - BEDROCK_REGION
  - LOG_LEVEL
- [ ] Execution role: CostDetectiveLambdaRole

**File name:** `05-lambda-config.png`

---

### ✅ 6. Lambda Test Execution
**URL:** (same as above, click "Test" tab)

**Show:**
- [ ] Test event configuration
- [ ] Execution result: Success
- [ ] Response showing: `{"statusCode": 200, "body": "{\"message\": \"No anomalies detected\"}"}`
- [ ] Execution duration and memory used
- [ ] CloudWatch log output snippet

**File name:** `06-lambda-test.png`

**How to capture:** 
1. Click "Test" button
2. Use default test event
3. Wait for execution to complete
4. Screenshot the results

---

### ✅ 7. IAM Role Permissions
**URL:** https://us-east-1.console.aws.amazon.com/iam/home#/roles/details/CostDetectiveLambdaRole

**Show:**
- [ ] Role name: CostDetectiveLambdaRole
- [ ] Trusted entities: lambda.amazonaws.com
- [ ] Attached policies:
  - AWSLambdaBasicExecutionRole (AWS managed)
  - CostDetectivePolicy (customer managed)

**File name:** `07-iam-role.png`

---

### ✅ 8. IAM Custom Policy Details
**URL:** (same as above, click on CostDetectivePolicy)

**Show:**
- [ ] Policy permissions including:
  - Cost Explorer (ce:GetCostAndUsage)
  - CloudTrail (cloudtrail:LookupEvents)
  - AWS Config access
  - DynamoDB access
  - S3 PutObject
  - SNS Publish
  - Bedrock InvokeModel

**File name:** `08-iam-policy.png`

---

### ✅ 9. EventBridge Rule
**URL:** https://us-east-1.console.aws.amazon.com/events/home?region=us-east-1#/eventbus/default/rules/cost-detective-schedule

**Show:**
- [ ] Rule name: cost-detective-schedule
- [ ] Event pattern type: Schedule
- [ ] Schedule expression: rate(1 hour)
- [ ] State: Enabled
- [ ] Target: Lambda function cost-detective

**File name:** `09-eventbridge-rule.png`

---

### ✅ 10. CloudWatch Logs
**URL:** https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups/log-group/$252Faws$252Flambda$252Fcost-detective

**Show:**
- [ ] Log group: /aws/lambda/cost-detective
- [ ] Recent log streams (multiple entries showing scheduled executions)
- [ ] Sample log entries showing successful execution:
  - "Cost Anomaly Detective triggered"
  - "Step 1: Analyzing costs..."
  - "No cost anomalies detected"

**File name:** `10-cloudwatch-logs.png`

---

### ✅ 11. Architecture Diagram (Optional)
Create a simple architecture diagram showing:
- EventBridge → Lambda
- Lambda → Cost Explorer API
- Lambda → CloudTrail API
- Lambda → AWS Config API
- Lambda → Bedrock API
- Lambda → DynamoDB (store anomalies)
- Lambda → S3 (save reports)
- Lambda → SNS (send alerts)

**File name:** `11-architecture-diagram.png`

**Tool suggestion:** Use draw.io, Lucidchart, or AWS Architecture Icons

---

### ✅ 12. Sample Alert Email (After First Anomaly)
**Show:**
- [ ] Email from AWS Notifications
- [ ] Subject: Cost anomaly alert
- [ ] Body with anomaly details
- [ ] Service name, cost change, spike percentage
- [ ] AI-generated analysis and recommendations

**File name:** `12-email-alert.png`

**Note:** This will only be available once an actual anomaly is detected

---

## 📋 Anonymization Checklist

Before adding screenshots to public repository:

- [ ] Redact/blur AWS Account ID: ~~XXXXXXXXXXXX~~ → `XXXXXXXXXXXX`
- [ ] Redact email addresses: ~~user@example.com~~ → `user@example.com`
- [ ] Keep resource names visible (they're generic)
- [ ] Keep AWS service names visible
- [ ] Keep region visible (us-east-1)
- [ ] Blur any cost amounts if showing real data
- [ ] Blur any CloudTrail user names if present

---

## 🎯 Priority Order

**Must-have (for README):**
1. Lambda function overview (#4)
2. Architecture diagram (#11)
3. Sample test execution (#6)

**Should-have (for comprehensive docs):**
4. EventBridge schedule (#9)
5. DynamoDB table (#1)
6. IAM role (#7)

**Nice-to-have (for deep-dive):**
7. Everything else

---

## 📁 Where to Save

Once you have screenshots:

```bash
mkdir -p docs/screenshots
# Place screenshots in: docs/screenshots/
# Update README.md with: ![Lambda](docs/screenshots/04-lambda-overview.png)
```

---

## 🚀 Next Steps After Screenshots

1. Update `README.md` with screenshot references
2. Update `docs/BLOG.md` with deployment evidence
3. Commit and push to GitHub
4. Submit to aws-samples with complete documentation

---

**Status:** ⏳ Waiting for screenshots  
**Deployed:** ✅ July 5, 2026  
**Account:** XXXXXXXXXXXX
