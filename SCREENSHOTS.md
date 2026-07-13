# Screenshot Guide

**✅ Screenshots Added and Anonymized**

This document lists the deployment screenshots that have been added to the repository. All screenshots have been anonymized with account IDs and sensitive information redacted.

---

## ✅ Deployment Screenshots Included

All screenshots have been captured from a demo deployment and anonymized. Located in `docs/screenshots/`:

### 1. DynamoDB Table ✅
![DynamoDB Table](docs/screenshots/01-dynamodb-table.png)  
**Shows**: Cost anomaly history storage table with anonymized data

### 2. S3 Bucket ✅
![S3 Bucket](docs/screenshots/02-s3-bucket.png)  
**Shows**: S3 bucket for detailed anomaly reports (JSON)

### 3. SNS Topic ✅
![SNS Topic](docs/screenshots/03-sns-topic.png)  
**Shows**: SNS topic configuration for email alerts

### 4. Lambda Function Overview ✅
![Lambda Overview](docs/screenshots/04-lambda-overview.png)  
**Shows**: Lambda function with EventBridge trigger configured

### 5. Lambda Configuration ✅
![Lambda Config](docs/screenshots/05-lambda-config.png)  
**Shows**: Lambda environment variables and settings (sensitive values redacted)

### 6. Lambda Test Execution ✅
![Lambda Test](docs/screenshots/06-lambda-test.png)  
**Shows**: Successful test execution with sample anomaly detection

### 7. IAM Role ✅
![IAM Role](docs/screenshots/07-iam-role.png)  
**Shows**: Lambda execution role with trust policy

### 8. IAM Policy ✅
![IAM Policy](docs/screenshots/08-iam-policy.png)  
**Shows**: IAM policy permissions (account ID anonymized)

### 9. EventBridge Rule ✅
![EventBridge Rule](docs/screenshots/09-eventbridge-rule.png)  
**Shows**: Scheduled EventBridge rule triggering Lambda hourly

### 10. CloudWatch Logs ✅
![CloudWatch Logs](docs/screenshots/10-cloudwatch-logs.png)  
**Shows**: Execution logs with anomaly detection and Bedrock analysis

---

## Architecture Diagram ✅

📊 **[architecture-diagram.drawio](architecture-diagram.drawio)** (Draw.io XML - editable)  
**Shows**: Complete architecture flow from EventBridge → Lambda → Bedrock → Outputs  
**Edit at**: https://app.diagrams.net

---

## Anonymization Applied ✅

All screenshots have been reviewed and anonymized according to AWS guidelines:

### Completed Anonymization Checklist

- ✅ No real AWS account IDs (replaced with redacted blocks)
- ✅ No real email addresses (redacted)
- ✅ No real employee names
- ✅ No actual cost amounts (sample data used)
- ✅ No internal URLs or hostnames
- ✅ No API keys, tokens, or credentials visible
- ✅ No customer-specific resource names

**Anonymization Commit**: `9d280d5` - "Add anonymized deployment screenshots showing AWS infrastructure"  
**Additional Redaction**: `3971bf2` - "Fix missed account number in IAM policy ARN"

---

## How Screenshots Are Used

### In README.md
The README references screenshots in a collapsible section showing the deployed AWS infrastructure:

```markdown
<details>
<summary>View Deployed AWS Resources</summary>

### DynamoDB Table
![DynamoDB Table](docs/screenshots/01-dynamodb-table.png)

### S3 Bucket
![S3 Bucket](docs/screenshots/02-s3-bucket.png)
...
</details>
```

This provides visual proof of the working deployment without cluttering the main README.

---

## Screenshot Standards

All screenshots follow these standards:

✅ **Quality**:
- High resolution (1024px+ width)
- Light mode for visibility
- Cropped to relevant areas
- Compressed for fast loading

✅ **Security**:
- Account IDs redacted with black boxes
- Email addresses removed
- Sensitive ARNs partially masked
- Sample data only

✅ **Accessibility**:
- Descriptive alt text
- Sequential numbering for easy reference
- Organized in `docs/screenshots/` directory

---

## Future Screenshot Updates

If additional screenshots are needed:

1. Deploy in demo/sandbox account only
2. Use sample data (no production)
3. Apply anonymization before committing
4. Follow naming convention: `##-description.png`
5. Update this guide with new screenshots
6. Commit with clear message about anonymization

**Tools for Anonymization**:
- **macOS Preview**: Shapes/annotations to cover text
- **GIMP/Photoshop**: Blur or black boxes
- **Monosnap**: Built-in annotation tools

---

## Status Summary

| Component | Status | Location |
|-----------|--------|----------|
| Deployment Screenshots | ✅ Complete | `docs/screenshots/` (10 files) |
| Architecture Diagram | ✅ Complete | `docs/architecture-diagram.drawio` |
| Anonymization Review | ✅ Complete | All sensitive data redacted |
| README Integration | ✅ Complete | Collapsible section added |
| aws-samples Ready | ✅ Complete | Public release approved |

---

**Last Updated**: July 12, 2026  
**Status**: All screenshots complete and anonymized for aws-samples publication
