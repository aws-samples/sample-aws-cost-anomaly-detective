# Deployment Methods Comparison

This document compares the three deployment methods for AWS Cost Anomaly Detective to help you choose the right approach for your environment.

---

## TL;DR - Which Method Should I Use?

```
┌─────────────────────────────────────────────────────────────┐
│  START: Do you have CloudFormation restrictions?            │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ├─ NO  ──> Use CloudFormation (Method 1) ✅
                 │
                 └─ YES ──> Use Manual Deployment (Method 2) ✅
```

---

## Method 1: CloudFormation Deployment ⭐ **Recommended**

### Quick Summary

Single command deploys everything in 5-10 minutes.

```bash
aws cloudformation deploy \
  --template-file cloudformation/deployment-template.yaml \
  --stack-name cost-detective \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    AlertEmail=your-email@example.com \
    ThresholdPercentage=50
```

### Pros ✅

- **Fastest:** 5-10 minutes total deployment time
- **Simplest:** Single command
- **Atomic:** All-or-nothing (no partial deployments)
- **Easy cleanup:** `aws cloudformation delete-stack` removes everything
- **Stack updates:** Change parameters without recreating resources
- **Infrastructure as Code:** Template is version-controlled and repeatable
- **CloudFormation features:** Drift detection, change sets, rollback on failure

### Cons ❌

- **May be blocked** by organizational policies or validation hooks
- **Less granular control** over individual resource configuration
- **Harder to debug** when stack creation fails (requires reading stack events)
- **Template syntax** can be verbose for complex configurations

### When to Use

✅ **Use CloudFormation if:**
- You have standard AWS account without special restrictions
- You want fastest deployment
- You prefer Infrastructure as Code approach
- You need easy cleanup and updates

❌ **Don't use CloudFormation if:**
- You get `AWS::EarlyValidation::PropertyValidation` errors
- Organizational policies block CloudFormation
- You need granular control over resource creation order
- You're in a highly restricted AWS environment

### Time Breakdown

| Step | Time |
|------|------|
| Prepare parameters | 1 min |
| Run deploy command | 1 min |
| Stack creation (AWS) | 3-5 min |
| Verify deployment | 2 min |
| **Total** | **7-9 min** |

### Files Needed

- `cloudformation/deployment-template.yaml` (provided)
- AWS CLI configured
- Bedrock access enabled

---

## Method 2: Manual CLI Deployment

### Quick Summary

Step-by-step resource creation using AWS CLI commands.

```bash
# Create each resource individually
aws dynamodb create-table ...
aws s3 mb ...
aws sns create-topic ...
aws iam create-role ...
aws lambda create-function ...
aws events put-rule ...
```

**Or use the automated script:**
```bash
./scripts/manual-deploy.sh your-email@example.com us-east-2
```

### Pros ✅

- **Bypasses CloudFormation restrictions** - works in restrictive accounts
- **Full control** over each resource and configuration
- **Easier troubleshooting** - see exactly which step fails
- **No organizational policy conflicts** with CloudFormation hooks
- **Flexible** - can customize each resource independently
- **Educational** - understand what each resource does

### Cons ❌

- **More time-consuming:** 15-20 minutes (or 10 minutes with script)
- **More commands** to run (10+ steps)
- **Manual cleanup** required (can't delete stack)
- **Harder to update** - must update each resource individually
- **No atomic rollback** - partial deployments possible if errors occur

### When to Use

✅ **Use Manual Deployment if:**
- CloudFormation deployment fails with validation errors
- Organizational policies block CloudFormation
- You're in a highly regulated/restricted AWS environment
- You need to customize individual resources
- You want to understand each component

❌ **Don't use Manual if:**
- CloudFormation works fine
- You want fastest deployment
- You prefer Infrastructure as Code

### Time Breakdown

| Step | Time |
|------|------|
| Create DynamoDB table | 1 min |
| Create S3 bucket | 1 min |
| Create SNS topic | 1 min |
| Create IAM role + policies | 3 min |
| Package Lambda code | 3 min |
| Deploy Lambda function | 2 min |
| Create EventBridge rule | 1 min |
| Test and verify | 3 min |
| **Total (manual)** | **15-20 min** |
| **Total (with script)** | **10 min** |

### Files Needed

- Source code in `src/` directory
- `requirements.txt`
- `scripts/manual-deploy.sh` (optional, for automation)

---

## Method 3: AWS Console (Not Recommended)

### Quick Summary

Click through AWS Console to create each resource manually.

### Pros ✅

- **Visual interface** - no CLI required
- **Guided wizards** for resource creation
- **Good for learning** AWS Console navigation

### Cons ❌

- **Very time-consuming:** 30-45 minutes
- **Error-prone:** Easy to misconfigure resources
- **Not repeatable:** Can't version control clicks
- **Hard to document:** No script to share
- **Difficult cleanup:** Must delete each resource manually

### When to Use

⚠️ **Only use Console if:**
- You're exploring AWS and learning the Console
- CLI is not available for some reason
- You need to see the visual interface

**For production deployments, use Method 1 or 2 instead.**

---

## Detailed Comparison Table

| Feature | CloudFormation | Manual CLI | AWS Console |
|---------|---------------|------------|-------------|
| **Deployment Time** | 5-10 min | 10-20 min | 30-45 min |
| **Commands Required** | 1 | 10+ (or 1 script) | 20+ clicks |
| **Skill Level** | Beginner | Intermediate | Beginner |
| **Repeatability** | Excellent | Good | Poor |
| **Version Control** | Yes (template) | Yes (script) | No |
| **Atomic Deployment** | Yes | No | No |
| **Easy Cleanup** | Yes (1 command) | No (10+ commands) | No (many clicks) |
| **Works in Restricted Accounts** | Sometimes | Yes | Yes |
| **Bypasses CloudFormation Hooks** | No | Yes | Yes |
| **Troubleshooting** | Hard | Easy | Medium |
| **Infrastructure as Code** | Yes | Partial | No |
| **Updates** | Easy | Manual | Manual |
| **Multi-Region** | Easy | Medium | Hard |
| **Documentation** | Self-documenting | Script documented | Must document separately |

---

## Common Deployment Scenarios

### Scenario 1: Standard AWS Account (Startup, SMB)

**Recommendation:** CloudFormation ⭐

**Why:**
- No organizational restrictions
- Fastest deployment
- Easy to tear down for testing
- Good for demos and POCs

**Steps:**
1. Enable Bedrock model access (one-time)
2. Run CloudFormation deploy command
3. Confirm SNS email subscription
4. Done!

---

### Scenario 2: Enterprise with Organizational Policies

**Recommendation:** Manual CLI Deployment

**Why:**
- CloudFormation may be blocked by SCPs or validation hooks
- Needs to comply with change management processes
- Requires detailed audit trail of each resource

**Steps:**
1. Run `./scripts/manual-deploy.sh` (or follow MANUAL_DEPLOYMENT_GUIDE.md)
2. Document each resource created for compliance
3. Confirm SNS email subscription
4. Submit to change management if required

---

### Scenario 3: Multi-Account AWS Organization

**Recommendation:** CloudFormation (in management account)

**Why:**
- Deploy once in management/payer account
- Monitors all member accounts automatically
- Easy to replicate to other organizations

**Steps:**
1. Deploy in management account using CloudFormation
2. Configure per-account thresholds
3. Set up organizational CloudTrail (optional)
4. Done!

See: [MULTI_ACCOUNT_DEPLOYMENT.md](docs/MULTI_ACCOUNT_DEPLOYMENT.md)

---

### Scenario 4: Highly Regulated Environment (Finance, Healthcare, Government)

**Recommendation:** Manual CLI Deployment (with documentation)

**Why:**
- Full control over each resource
- Can pause between steps for approvals
- Detailed audit trail
- No "magic" CloudFormation automation

**Steps:**
1. Follow MANUAL_DEPLOYMENT_GUIDE.md step-by-step
2. Document each step for compliance team
3. Get approval between steps if required
4. Test thoroughly before enabling schedule

---

## Migration Between Methods

### CloudFormation → Manual

**Scenario:** CloudFormation deployed, but you want to customize resources.

**Steps:**
1. Note all CloudFormation stack outputs
2. Delete CloudFormation stack: `aws cloudformation delete-stack --stack-name cost-detective`
3. Wait for deletion: `aws cloudformation wait stack-delete-complete --stack-name cost-detective`
4. Run manual deployment with same configuration
5. Verify everything works

**Data Loss:** No (DynamoDB data, S3 reports deleted with stack)

**Recommendation:** Export DynamoDB and S3 data before deletion if you want to keep history.

---

### Manual → CloudFormation

**Scenario:** Manually deployed, but you want easier management.

**Steps:**
1. Export resource configurations
2. Delete all manual resources (use MANUAL_DEPLOYMENT_GUIDE.md uninstall section)
3. Deploy via CloudFormation
4. Import old data if needed

**Data Loss:** Yes, unless you export first

---

## Cost Comparison

**All methods deploy the same resources = same monthly cost**

| Service | Monthly Cost |
|---------|--------------|
| Lambda | $3-5 |
| Cost Explorer API | $7 |
| Bedrock | $10-15 |
| DynamoDB | $1-3 |
| S3 | $0.50-1 |
| SNS | $0.50 |
| CloudWatch Logs | $0.50-1 |
| **Total** | **$23-33/month** |

**The deployment method does NOT affect ongoing costs.**

---

## Troubleshooting Decision Tree

```
Deployment Failed?
│
├─ CloudFormation Error: "AWS::EarlyValidation::PropertyValidation"
│  └─> Use Manual Deployment instead
│
├─ CloudFormation Error: "Access Denied" on specific resource
│  └─> Check IAM permissions for your user/role
│
├─ Manual Deployment: "Access Denied" on Bedrock
│  └─> Enable models at console.aws.amazon.com/bedrock/
│
├─ Manual Deployment: Lambda timeout
│  └─> Increase timeout: aws lambda update-function-configuration --timeout 600
│
└─ Any Deployment: No anomalies detected after 24h
   └─> Normal! Wait for baseline. Or create test spike to verify.
```

---

## Recommendations by Use Case

| Use Case | Method | Why |
|----------|--------|-----|
| **Quick Demo** | CloudFormation | Fastest setup, easy teardown |
| **Production (Standard Account)** | CloudFormation | Easy updates, IaC best practices |
| **Production (Restricted Account)** | Manual CLI | Bypasses restrictions |
| **Learning AWS** | Manual CLI | Understand each component |
| **Multi-Account Org** | CloudFormation | Easy replication |
| **Highly Regulated** | Manual CLI | Detailed control and audit |
| **CI/CD Pipeline** | CloudFormation | Version-controlled template |
| **One-Time Test** | CloudFormation | Fast cleanup |

---

## Next Steps After Deployment

**Regardless of deployment method:**

1. ✅ **Confirm SNS email subscription** (check inbox)
2. ✅ **Wait 24-48 hours** for baseline to establish
3. ✅ **Monitor CloudWatch Logs:** `aws logs tail /aws/lambda/cost-detective --follow`
4. ✅ **Check for anomalies:** `aws dynamodb scan --table-name cost-anomalies --limit 5`
5. ✅ **Tune threshold** based on your cost patterns
6. ✅ **Add Slack webhook** for real-time alerts (optional)

---

## Support

**For CloudFormation deployment issues:**
- Check stack events: `aws cloudformation describe-stack-events --stack-name cost-detective`
- Review template: `cloudformation/deployment-template.yaml`

**For Manual deployment issues:**
- Follow: [MANUAL_DEPLOYMENT_GUIDE.md](MANUAL_DEPLOYMENT_GUIDE.md)
- Run automated script: `./scripts/manual-deploy.sh`

**For all deployments:**
- GitHub Issues: https://github.com/aws-samples/sample-aws-cost-anomaly-detective/issues
- Tag: `deployment` or `troubleshooting`

---

## Summary

**Most users:** Start with CloudFormation (Method 1)

**If CloudFormation fails:** Use Manual Deployment (Method 2)

**Never use:** Console clicking (Method 3) for production

Both CloudFormation and Manual CLI deployments are fully supported and documented. Choose based on your environment's constraints, not personal preference.

**The end result is identical - same resources, same cost, same functionality.**
