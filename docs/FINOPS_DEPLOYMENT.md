# FinOps Account Deployment Pattern

**For Enterprise Customers with Restricted Management Accounts**

---

## Overview

Many enterprise customers **cannot deploy directly to their management (payer) account** due to security policies, compliance requirements, or change control restrictions.

**Solution:** Deploy Cost Anomaly Detective in a **FinOps/Tools account** and use **cross-account IAM roles** to query Cost Explorer in the management account.

**Benefits:**
- ✅ Full org-wide cost visibility maintained
- ✅ Management account stays minimal and locked down (1 IAM role only)
- ✅ More secure than deploying everything in management account
- ✅ Meets enterprise security and compliance requirements
- ✅ Same cost, same functionality

---

## Architecture

### High-Level Flow

```
┌──────────────────────────────┐
│   MANAGEMENT ACCOUNT         │
│   (Minimal Footprint)        │
│                              │
│  ┌────────────────────┐      │
│  │ Cost Explorer      │◄─────┼──── Read-Only API Access
│  │ (org-wide costs)   │      │
│  └────────────────────┘      │
│                              │
│  ┌────────────────────┐      │
│  │ IAM Role           │      │
│  │ (read-only trust)  │      │
│  └────────────────────┘      │
└──────────────────────────────┘
         ▲
         │ STS AssumeRole
         │ (with ExternalId)
         │
┌────────┴─────────────────────┐
│   FINOPS ACCOUNT             │
│   (All Resources Deployed)   │
│                              │
│  Lambda ──┬─► Bedrock        │
│           ├─► DynamoDB       │
│           ├─► S3 Bucket      │
│           └─► SNS Topic      │
│                              │
│  EventBridge (hourly)        │
│  CloudWatch Logs             │
└──────────────────────────────┘
```

### What's Cross-Account vs Local

**Cross-Account (Only 2 things):**
- 🔍 **Cost Explorer** - Queries org-wide cost data from management account
- 📋 **CloudTrail** (optional) - Gets who made changes (if organizational trail exists)

**Local in FinOps Account:**
- 💻 **All infrastructure** - Lambda, DynamoDB, S3, SNS, EventBridge, IAM role
- 💾 **All storage** - Anomaly records, detailed reports
- 📧 **All alerting** - Email, Slack notifications
- 📊 **All logging** - CloudWatch Logs

**Key Point:** Only Cost Explorer queries cross-account. Everything else is local. Same $30/month operating cost.

---

## Security Comparison

### FinOps Account Deployment (Recommended) ✅

**Management Account:**
- 1 IAM role (read-only billing permissions)
- No compute, no storage
- Minimal attack surface

**FinOps Account:**
- All Lambda, DynamoDB, S3, SNS resources
- Isolated failure domain
- Clear ownership

### Direct Management Account Deployment ❌

**Management Account:**
- Lambda (compute with code execution)
- DynamoDB (storage)
- S3 (storage)
- SNS (alerting)
- Large attack surface
- Mixed billing + tools

**Why FinOps Deployment is MORE Secure:**
1. **Smaller blast radius** - Malicious code contained to FinOps account
2. **Principle of least privilege** - Management account has read-only billing access only
3. **Separation of duties** - Clear boundary between billing data and tooling
4. **Easier compliance** - Audit scope is cleaner

---

## Deployment Steps

### Prerequisites

- Management account access (one-time setup for IAM role)
- FinOps account access (where resources will be deployed)
- AWS CLI configured
- Python 3.12+

### Step 1: Create Cross-Account Role in Management Account

**Option A: CloudFormation (Recommended)**

Save this as `cross-account-role.yaml`:

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Cost Detective Cross-Account IAM Role for FinOps Account'

Parameters:
  FinOpsAccountId:
    Type: String
    Description: AWS Account ID of the FinOps account
    AllowedPattern: '[0-9]{12}'
  
  ExternalId:
    Type: String
    Description: External ID for STS AssumeRole (change this!)
    Default: cost-detective-cross-account-2026
    MinLength: 8

Resources:
  CostDetectiveCrossAccountRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: CostDetectiveCrossAccountRole
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              AWS: !Sub 'arn:aws:iam::${FinOpsAccountId}:root'
            Action: 'sts:AssumeRole'
            Condition:
              StringEquals:
                'sts:ExternalId': !Ref ExternalId
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/AWSBillingReadOnlyAccess
      Policies:
        - PolicyName: CostExplorerAccess
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - ce:GetCostAndUsage
                  - ce:GetCostForecast
                  - ce:GetDimensionValues
                  - ce:GetTags
                  - organizations:ListAccounts
                  - organizations:DescribeOrganization
                Resource: '*'
        - PolicyName: CloudTrailReadAccess
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - cloudtrail:LookupEvents
                Resource: '*'

Outputs:
  RoleArn:
    Description: ARN of the cross-account role
    Value: !GetAtt CostDetectiveCrossAccountRole.Arn
    Export:
      Name: CostDetectiveCrossAccountRoleArn
```

Deploy to management account:

```bash
aws cloudformation deploy \
  --template-file cross-account-role.yaml \
  --stack-name cost-detective-cross-account-role \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    FinOpsAccountId=999888777666 \
    ExternalId=cost-detective-cross-account-2026 \
  --region us-east-1

# Get the role ARN (save this!)
aws cloudformation describe-stacks \
  --stack-name cost-detective-cross-account-role \
  --query 'Stacks[0].Outputs[?OutputKey==`RoleArn`].OutputValue' \
  --output text \
  --region us-east-1
```

**Option B: Manual CLI**

```bash
# Set variables
FINOPS_ACCOUNT_ID="999888777666"
EXTERNAL_ID="cost-detective-cross-account-2026"  # Change this!
MANAGEMENT_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create trust policy
cat > trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::${FINOPS_ACCOUNT_ID}:root"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "${EXTERNAL_ID}"
        }
      }
    }
  ]
}
EOF

# Create IAM role
aws iam create-role \
  --role-name CostDetectiveCrossAccountRole \
  --assume-role-policy-document file://trust-policy.json \
  --description "Cross-account role for Cost Detective in FinOps account" \
  --region us-east-1

# Attach billing read-only policy
aws iam attach-role-policy \
  --role-name CostDetectiveCrossAccountRole \
  --policy-arn arn:aws:iam::aws:policy/AWSBillingReadOnlyAccess \
  --region us-east-1

# Create Cost Explorer access policy
cat > cost-explorer-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ce:GetCostAndUsage",
        "ce:GetCostForecast",
        "ce:GetDimensionValues",
        "ce:GetTags",
        "organizations:ListAccounts",
        "organizations:DescribeOrganization",
        "cloudtrail:LookupEvents"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# Attach Cost Explorer policy
aws iam put-role-policy \
  --role-name CostDetectiveCrossAccountRole \
  --policy-name CostExplorerAccess \
  --policy-document file://cost-explorer-policy.json \
  --region us-east-1

# Get role ARN (save this!)
aws iam get-role \
  --role-name CostDetectiveCrossAccountRole \
  --query 'Role.Arn' \
  --output text \
  --region us-east-1
```

**Save these values:**
- Role ARN: `arn:aws:iam::123456789012:role/CostDetectiveCrossAccountRole`
- External ID: `cost-detective-cross-account-2026`
- Management Account ID: `123456789012`

---

### Step 2: Deploy to FinOps Account

Switch to FinOps account credentials, then deploy using your preferred method.

#### **Option A: CloudFormation**

Use the standard deployment template and add these parameters:

```bash
aws cloudformation deploy \
  --template-file cloudformation/deployment-template.yaml \
  --stack-name cost-detective \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    AlertEmail=your-email@example.com \
    CrossAccountRoleArn=arn:aws:iam::123456789012:role/CostDetectiveCrossAccountRole \
    CrossAccountExternalId=cost-detective-cross-account-2026 \
    ManagementAccountId=123456789012 \
  --region us-east-2
```

#### **Option B: Manual CLI**

Follow the [MANUAL_DEPLOYMENT_GUIDE.md](../MANUAL_DEPLOYMENT_GUIDE.md) and add these environment variables to Lambda:

```bash
# After creating Lambda function, add cross-account environment variables
aws lambda update-function-configuration \
  --function-name cost-detective \
  --environment Variables="{
    DYNAMODB_TABLE_NAME=cost-anomalies,
    S3_BUCKET_NAME=cost-detective-reports-ACCOUNT_ID,
    SNS_TOPIC_ARN=arn:aws:sns:us-east-2:ACCOUNT_ID:cost-detective-alerts,
    THRESHOLD_PERCENTAGE=50,
    BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-6,
    AWS_REGION=us-east-2,
    CROSS_ACCOUNT_ROLE_ARN=arn:aws:iam::123456789012:role/CostDetectiveCrossAccountRole,
    CROSS_ACCOUNT_EXTERNAL_ID=cost-detective-cross-account-2026,
    MANAGEMENT_ACCOUNT_ID=123456789012
  }" \
  --region us-east-2
```

---

### Step 3: Update Lambda Code for Cross-Account Access

The Lambda function needs code changes to assume the cross-account role. Add this helper function:

```python
import boto3
import os

def get_cost_explorer_client():
    """
    Returns Cost Explorer client.
    Uses cross-account role if CROSS_ACCOUNT_ROLE_ARN is set,
    otherwise uses local account credentials.
    """
    cross_account_role_arn = os.environ.get('CROSS_ACCOUNT_ROLE_ARN')
    external_id = os.environ.get('CROSS_ACCOUNT_EXTERNAL_ID')
    
    if cross_account_role_arn:
        # Cross-account access via STS AssumeRole
        sts_client = boto3.client('sts')
        
        try:
            assumed_role = sts_client.assume_role(
                RoleArn=cross_account_role_arn,
                RoleSessionName='CostDetectiveCrossAccount',
                ExternalId=external_id,
                DurationSeconds=3600  # 1 hour
            )
            
            credentials = assumed_role['Credentials']
            
            # Create Cost Explorer client with temporary credentials
            ce_client = boto3.client(
                'ce',
                region_name='us-east-1',  # Cost Explorer is always us-east-1
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken']
            )
            
            print(f"✅ Using cross-account Cost Explorer from management account")
            
        except Exception as e:
            print(f"❌ Failed to assume cross-account role: {str(e)}")
            raise
    else:
        # Local account access
        ce_client = boto3.client('ce', region_name='us-east-1')
        print(f"✅ Using local Cost Explorer")
    
    return ce_client

# Usage in lambda_handler
def lambda_handler(event, context):
    ce = get_cost_explorer_client()  # Use this instead of boto3.client('ce')
    
    # Rest of your code unchanged...
    response = ce.get_cost_and_usage(...)
```

---

### Step 4: Update Lambda IAM Role

The Lambda execution role in the FinOps account needs permission to assume the cross-account role:

```bash
# Add STS AssumeRole permission to Lambda role
cat > assume-role-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": "arn:aws:iam::123456789012:role/CostDetectiveCrossAccountRole"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name CostDetectiveLambdaRole \
  --policy-name AssumeRolePolicy \
  --policy-document file://assume-role-policy.json \
  --region us-east-2
```

---

### Step 5: Test Cross-Account Access

Test that Lambda can assume the cross-account role:

```bash
# Trigger Lambda manually
aws lambda invoke \
  --function-name cost-detective \
  --region us-east-2 \
  response.json

# Check logs for success message
aws logs tail /aws/lambda/cost-detective --region us-east-2 --since 5m
```

Look for:
```
✅ Using cross-account Cost Explorer from management account
```

---

## Verification & Testing

### 1. Test Cross-Account Role Assumption

From FinOps account:

```bash
aws sts assume-role \
  --role-arn arn:aws:iam::123456789012:role/CostDetectiveCrossAccountRole \
  --role-session-name TestCrossAccount \
  --external-id cost-detective-cross-account-2026
```

**Expected:** Returns temporary credentials (AccessKeyId, SecretAccessKey, SessionToken)

### 2. Test Cost Explorer Query

Use the temporary credentials from above:

```bash
export AWS_ACCESS_KEY_ID="ASIAxxxxxxxxxxxx"
export AWS_SECRET_ACCESS_KEY="xxxxxxxxxxxxxxxx"
export AWS_SESSION_TOKEN="xxxxxxxxxxxxxxxx"

aws ce get-cost-and-usage \
  --time-period Start=2026-08-01,End=2026-08-18 \
  --granularity DAILY \
  --metrics BlendedCost \
  --region us-east-1
```

**Expected:** Returns org-wide cost data from all accounts

### 3. Test Lambda Execution

```bash
# Invoke Lambda
aws lambda invoke \
  --function-name cost-detective \
  --region us-east-2 \
  response.json && cat response.json

# Check CloudWatch Logs
aws logs tail /aws/lambda/cost-detective --region us-east-2 --follow
```

**Expected:** Lambda successfully queries Cost Explorer and completes without errors

---

## Troubleshooting

### Error: "User is not authorized to perform: sts:AssumeRole"

**Cause:** Lambda execution role missing permission to assume cross-account role

**Fix:**
```bash
aws iam put-role-policy \
  --role-name CostDetectiveLambdaRole \
  --policy-name AssumeRolePolicy \
  --policy-document file://assume-role-policy.json
```

### Error: "Not authorized to perform: sts:AssumeRole on resource"

**Cause:** Trust policy on management account role doesn't allow FinOps account

**Fix:** Update trust policy in management account to include FinOps account ID

### Error: "Access Denied" when querying Cost Explorer

**Cause:** Cross-account role missing Cost Explorer permissions

**Fix:** Attach `AWSBillingReadOnlyAccess` and ensure Cost Explorer policy includes `ce:GetCostAndUsage`

### Lambda Times Out

**Cause:** Cost Explorer queries can be slow for large organizations

**Fix:** Increase Lambda timeout to 5 minutes (300 seconds):
```bash
aws lambda update-function-configuration \
  --function-name cost-detective \
  --timeout 300 \
  --region us-east-2
```

---

## Cost Impact

**Q: Does cross-account access add cost?**

**A: No.** The cost is identical to deploying in management account.

| Service | Cost |
|---------|------|
| STS AssumeRole API | $0 (1M free/month, you use ~720/month) |
| Cross-account data transfer | $0 (API calls, no data egress) |
| Additional infrastructure | $0 (same resources) |
| **Total Additional Cost** | **$0/month** |

**Monthly Operating Cost:** $25-35/month (same as management account deployment)

---

## Multi-Account Monitoring

### Member Account Visibility

**Q: Can Cost Detective see costs from member accounts?**

**A: Yes!** Cost Explorer in the management account automatically aggregates costs from all member accounts in the organization.

When you deploy in FinOps account with cross-account role:
1. Lambda in FinOps account assumes role in management account
2. Queries Cost Explorer in management account (org-wide view)
3. Gets cost data for ALL member accounts (no additional setup needed)

### Member Account CloudTrail

**Q: Can I see who made changes in member accounts?**

**A: Yes, if you have organizational CloudTrail enabled.**

- **Organizational CloudTrail** (in management account) captures events from all member accounts
- Cost Detective queries this via cross-account role
- Attributes changes to specific users/roles across the organization

If you don't have organizational CloudTrail:
- You'll still see the cost spike and AI analysis
- Attribution will be limited to service/resource level, not user level

---

## Security Best Practices

### 1. Use Strong External IDs

Generate a unique External ID:
```bash
# Generate random External ID
openssl rand -base64 32
```

Update in both:
- Management account trust policy
- FinOps account Lambda environment variable

### 2. Limit Role Duration

Set maximum session duration on the cross-account role:
```bash
aws iam update-role \
  --role-name CostDetectiveCrossAccountRole \
  --max-session-duration 3600  # 1 hour
```

### 3. Enable CloudTrail Logging

Monitor when the cross-account role is assumed:
```bash
# In management account, filter CloudTrail for AssumeRole events
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=AssumeRole \
  --region us-east-1
```

### 4. Use Least Privilege

The cross-account role only needs:
- `ce:GetCostAndUsage` (required)
- `ce:GetCostForecast` (optional)
- `cloudtrail:LookupEvents` (optional, for attribution)
- `organizations:ListAccounts` (optional, for account names)

Remove permissions you don't need.

### 5. Regular Access Review

Audit cross-account role usage monthly:
```bash
# Check when role was last used
aws iam get-role \
  --role-name CostDetectiveCrossAccountRole \
  --query 'Role.RoleLastUsed' \
  --region us-east-1
```

---

## Summary

### Management Account Changes (One-Time Setup)
- ✅ Create 1 IAM role (CostDetectiveCrossAccountRole)
- ✅ Attach read-only billing permissions
- ✅ Configure trust relationship with FinOps account

### FinOps Account Deployment
- ✅ Deploy all resources (Lambda, DynamoDB, S3, SNS, etc.)
- ✅ Configure Lambda environment variables with cross-account role ARN
- ✅ Update Lambda code to assume cross-account role
- ✅ Add STS AssumeRole permission to Lambda execution role

### Result
- ✅ Full org-wide cost visibility maintained
- ✅ Management account footprint: 1 IAM role only
- ✅ More secure than deploying in management account
- ✅ Same $30/month operating cost
- ✅ Meets enterprise compliance requirements

---

## Additional Resources

- [AWS Organizations Best Practices](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_best-practices.html)
- [Cross-Account IAM Roles](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_common-scenarios_aws-accounts.html)
- [Cost Explorer API Reference](https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/API_GetCostAndUsage.html)
- [Main Repository](../README.md)
- [Manual Deployment Guide](../MANUAL_DEPLOYMENT_GUIDE.md)
- [Multi-Account Deployment](MULTI_ACCOUNT_DEPLOYMENT.md)

---

**Document Version:** 1.0  
**Last Updated:** August 18, 2026  
**Maintainers:** AWS Cost Anomaly Detective Contributors
