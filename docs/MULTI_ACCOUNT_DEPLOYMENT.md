# Multi-Account Deployment Guide

**For AWS Organizations with Multiple Accounts**

This guide explains how to deploy AWS Cost Anomaly Detective in an AWS Organization with a management (payer) account and multiple member accounts.

---

## 🏢 Architecture Overview

```
AWS Organization
│
├─ Management Account (Payer)
│  └─ 📊 Cost Anomaly Detective (DEPLOY HERE)
│     ├─ Lambda Function
│     ├─ EventBridge Rule (hourly)
│     ├─ DynamoDB Table
│     ├─ S3 Bucket (reports)
│     └─ SNS Topic (alerts)
│
└─ Member Accounts
   ├─ Production Account
   ├─ Development Account
   └─ Staging Account
```

---

## ✅ Why Deploy in Management Account?

### Cost Explorer Access
- **Management account sees ALL costs** across the organization
- Member accounts only see their own costs
- Org-wide anomaly detection requires management account access

### CloudTrail Access
- Management account can access org-wide CloudTrail
- Can correlate cost spikes with changes in any member account

### Centralized Alerting
- One deployment monitors entire organization
- Single SNS topic/Slack channel for all alerts
- Easier to manage than N deployments

---

## 🚀 Deployment Steps

### Step 1: Enable Cost Explorer in Management Account

```bash
# Verify you're in management account
aws sts get-caller-identity

# Cost Explorer should already be enabled in management account
# Verify access:
aws ce get-cost-and-usage \
  --time-period Start=2026-07-01,End=2026-07-02 \
  --granularity DAILY \
  --metrics BlendedCost
```

### Step 2: Enable Organizational CloudTrail (Optional but Recommended)

This allows detection of which account/user caused a cost spike.

```bash
# Create organizational trail (if not exists)
aws cloudtrail create-trail \
  --name organization-trail \
  --s3-bucket-name org-cloudtrail-bucket-${ACCOUNT_ID} \
  --is-organization-trail

# Start logging
aws cloudtrail start-logging --name organization-trail
```

### Step 3: Deploy Cost Anomaly Detective

Use the standard deployment in the management account:

```bash
# Clone repository
git clone https://github.com/aws-samples/sample-aws-cost-anomaly-detective.git
cd aws-cost-anomaly-detective

# Deploy CloudFormation (in management account)
aws cloudformation deploy \
  --template-file cloudformation/deployment-template.yaml \
  --stack-name cost-detective-org \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    AlertEmail=finops-team@company.com \
    SlackWebhookUrl=https://hooks.slack.com/services/YOUR/WEBHOOK
```

### Step 4: Configure Account-Specific Alerts (Optional)

If you want different alerts for different accounts, use SNS topic subscriptions:

```bash
# Create account-specific topics
aws sns create-topic --name cost-alerts-production
aws sns create-topic --name cost-alerts-development

# Update Lambda to route alerts based on account ID
```

---

## 🔧 Configuration for Organizations

### Environment Variables

Update Lambda environment to enable org-wide scanning:

```bash
aws lambda update-function-configuration \
  --function-name cost-detective \
  --environment Variables="{
    DYNAMODB_TABLE_NAME=cost-anomalies,
    S3_BUCKET_NAME=cost-detective-reports-org,
    SNS_TOPIC_ARN=arn:aws:sns:us-east-1:123456789012:cost-alerts,
    SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK,
    THRESHOLD_PERCENTAGE=50,
    ORG_MODE=true,
    MANAGEMENT_ACCOUNT_ID=123456789012
  }"
```

### config.yaml Settings

```yaml
# Organization settings
organization:
  enabled: true
  management_account_id: "123456789012"
  
  # Optional: Account-specific thresholds
  account_overrides:
    - account_id: "111111111111"  # Production
      account_name: "Production"
      threshold_percentage: 30     # More sensitive
      alert_severity: "High"
    
    - account_id: "222222222222"  # Development
      account_name: "Development"
      threshold_percentage: 100    # Less sensitive
      alert_severity: "Low"

# Alert routing by account
alerting:
  rules:
    - account_id: "111111111111"
      sns_topic: "arn:aws:sns:us-east-1:123456789012:prod-alerts"
      slack_channel: "#prod-costs"
    
    - account_id: "222222222222"
      sns_topic: "arn:aws:sns:us-east-1:123456789012:dev-alerts"
      slack_channel: "#dev-costs"
```

---

## 📊 Example Alert (Multi-Account)

```
🚨 Cost Anomaly Detected

Account: Production (111111111111)
Service: Amazon RDS
Spike: $450 (+180%)

Root Cause:
Database instance prod-db-1 changed from db.t3.large 
to db.r5.2xlarge at 2:15 PM by user john.doe@company.com 
in account 111111111111

Recommendation: Revert or use Aurora Serverless

[View Full Report] [Create Ticket]
```

---

## 🔐 IAM Permissions

### Management Account Role

The Lambda role in management account needs:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ce:GetCostAndUsage",
        "ce:GetCostForecast",
        "organizations:ListAccounts",
        "organizations:DescribeAccount"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudtrail:LookupEvents"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "cloudtrail:IsOrganizationTrail": "true"
        }
      }
    }
  ]
}
```

---

## 🎯 Cost Attribution

### Identifying Which Account Caused the Spike

Cost Anomaly Detective automatically attributes costs:

1. **Cost Explorer** shows which account incurred the cost
2. **CloudTrail** shows which user in which account made changes
3. **Alert includes** both account ID and account name

Example code (already implemented):

```python
def get_account_name(account_id):
    """Get friendly account name from Organizations."""
    org = boto3.client('organizations')
    try:
        response = org.describe_account(AccountId=account_id)
        return response['Account']['Name']
    except:
        return account_id
```

---

## 📈 Reporting

### Organization-Wide Dashboard

Cost Detective can generate org-wide reports:

```bash
# Generate monthly org report
aws lambda invoke \
  --function-name cost-detective \
  --payload '{"report_type": "org_summary", "period": "monthly"}' \
  response.json
```

Report includes:
- Total org cost vs budget
- Top 5 cost-generating accounts
- Account-by-account anomaly summary
- Month-over-month trends

---

## 🚨 Common Issues

### Issue 1: "Access Denied" to Cost Explorer

**Problem**: Lambda can't access Cost Explorer  
**Solution**: Verify Lambda is deployed in management account

```bash
aws sts get-caller-identity
# Verify Account ID matches your management account
```

### Issue 2: Can't See Member Account Costs

**Problem**: Only seeing management account costs  
**Solution**: Enable Cost Explorer in management account for org-wide view

```bash
# Cost Explorer is automatically enabled for orgs
# Verify in console: https://console.aws.amazon.com/cost-management/
```

### Issue 3: CloudTrail Events Missing

**Problem**: Can't identify who made changes in member accounts  
**Solution**: Enable organizational CloudTrail

```bash
aws cloudtrail create-trail \
  --name org-trail \
  --s3-bucket-name org-trail-bucket \
  --is-organization-trail
```

---

## 💰 Cost Breakdown (Organization)

**For an org with 10 accounts:**

| Component | Cost | Notes |
|-----------|------|-------|
| Lambda (1 run/hour) | $2/month | Scans all 10 accounts |
| CloudWatch API | $10/month | 10 accounts × metrics |
| Bedrock API | $20/month | Analyzes anomalies |
| DynamoDB | $2/month | Stores alerts |
| S3 | $1/month | Report storage |
| **Total** | **~$35/month** | For entire organization |

**Per-account cost**: ~$3.50/account/month

**ROI**: One caught misconfiguration saving $1,000/month = 28x ROI

---

## 🎓 Best Practices

### 1. Start with High Thresholds

Begin with 100% threshold for dev/test accounts:

```yaml
account_overrides:
  - account_id: "dev-account-id"
    threshold_percentage: 100
```

Lower thresholds as you baseline normal patterns.

### 2. Use Tag-Based Routing

Route alerts based on cost allocation tags:

```python
# In Lambda handler
cost_center = get_tag(resource, 'CostCenter')
if cost_center == 'Engineering':
    send_to_channel('#engineering-costs')
elif cost_center == 'Marketing':
    send_to_channel('#marketing-costs')
```

### 3. Weekly Digest for Leadership

Send weekly summaries to leadership:

```yaml
scheduled_reports:
  - schedule: "cron(0 9 ? * MON *)"  # Monday 9am
    recipients: ["cfo@company.com"]
    report_type: "weekly_summary"
    include_forecasts: true
```

### 4. Exclude Known Patterns

Exclude expected cost events:

```yaml
exclusions:
  - account_id: "111111111111"
    service: "Amazon EC2"
    reason: "Monthly batch processing"
    days_of_week: [1]  # Mondays
    expected_spike: 200
```

---

## 🔄 Migration from Single-Account

If you already have single-account deployments:

### Step 1: Deploy to Management Account
Follow deployment steps above

### Step 2: Consolidate DynamoDB Data (Optional)
```bash
# Export from member account tables
aws dynamodb scan --table-name cost-anomalies > old-data.json

# Import to management account table
aws dynamodb batch-write-item --request-items file://old-data.json
```

### Step 3: Delete Member Account Deployments
```bash
# In each member account
aws cloudformation delete-stack --stack-name cost-detective
```

---

## 📞 Support

For multi-account deployment questions:
- **GitHub Issues**: https://github.com/aws-samples/sample-aws-cost-anomaly-detective/issues
- **Tag**: `multi-account` or `organizations`

---

## 🎯 Summary

✅ **Deploy in management account** for org-wide visibility  
✅ **One deployment** monitors all member accounts  
✅ **Account-specific alerts** via configuration  
✅ **Cost attribution** automatically tracked  
✅ **~$35/month** for entire organization  

**Ready to deploy? Follow the steps above!** 🚀
