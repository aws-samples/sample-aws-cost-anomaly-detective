# Screenshot Guide

**Instructions for adding screenshots after AWS approval and deployment**

This document lists where screenshots should be added to enhance the documentation.

---

## Priority 1: README Screenshots

### 1. Slack Alert Example
**Location**: `README.md` after "Example Output" section  
**File**: `images/slack-alert-example.png`

**What to capture**:
- Full Slack message showing cost anomaly
- Include severity emoji, cost impact, root cause
- Show action buttons (View Report, Cost Explorer)
- Capture in light mode for better visibility

**Recommended size**: 800x600px

---

### 2. Architecture Diagram
**Location**: `README.md` in Architecture section  
**File**: `images/architecture-diagram.png`

**What to create**:
- Use draw.io or similar tool
- Show: EventBridge → Lambda → Bedrock → Alerts flow
- Include: CloudWatch, Cost Explorer, CloudTrail inputs
- Output: DynamoDB, S3, SNS/Slack
- AWS icon library recommended

**Recommended size**: 1200x800px

---

### 3. AWS Console - Cost Explorer
**Location**: `README.md` or `docs/` folder  
**File**: `images/cost-explorer-spike.png`

**What to capture**:
- Cost Explorer graph showing cost spike
- Highlight the anomaly period
- Show service breakdown
- Anonymize account details

**Recommended size**: 1000x600px

---

## Priority 2: Workshop Screenshots

### 4. CloudFormation Deployment
**Location**: `docs/WORKSHOP.md` Module 2  
**File**: `images/cloudformation-deploy.png`

**What to capture**:
- CloudFormation console showing stack creation
- Highlight parameters section
- Show "CREATE_COMPLETE" status

---

### 5. Lambda Function View
**Location**: `docs/WORKSHOP.md` Module 3  
**File**: `images/lambda-function.png`

**What to capture**:
- Lambda console showing function details
- Environment variables (redact sensitive values)
- Configured triggers (EventBridge)

---

### 6. CloudWatch Logs
**Location**: `docs/WORKSHOP.md` Module 3  
**File**: `images/cloudwatch-logs.png`

**What to capture**:
- CloudWatch Logs showing successful execution
- Highlight key log messages:
  - "Detected anomaly"
  - "Bedrock analysis complete"
  - "Alert sent"

---

## Priority 3: Blog Post Screenshots

### 7. S3 Report Example
**Location**: `docs/BLOG.md`  
**File**: `images/s3-report.png`

**What to capture**:
- S3 bucket with report files
- One report opened in browser/viewer
- Show JSON structure

---

### 8. DynamoDB Table
**Location**: `docs/BLOG.md`  
**File**: `images/dynamodb-anomalies.png`

**What to capture**:
- DynamoDB console showing anomaly records
- Show PK/SK structure
- Highlight stored analysis

---

### 9. Before/After Cost Comparison
**Location**: `docs/BLOG.md` or README  
**File**: `images/cost-comparison.png`

**What to capture**:
- Side-by-side graph showing:
  - Before: Unnoticed cost spike growing
  - After: Alert caught spike immediately
- Annotate savings amount

---

## Screenshot Guidelines

### General Requirements

✅ **DO**:
- Use light mode for better visibility
- Anonymize sensitive data (account IDs, emails, real costs)
- Use sample/demo data where possible
- Crop to relevant area only
- Use high resolution (at least 1024px width)
- Add descriptive alt text in markdown
- Compress images (use tinypng.com or similar)

❌ **DON'T**:
- Include real customer data
- Show actual account numbers
- Include internal-only information
- Use dark mode (harder to see in docs)
- Include your personal email/username
- Show real cost amounts (use rounded/sample values)

---

### Example Markdown Format

```markdown
## Example Slack Alert

![Cost Anomaly Alert in Slack](images/slack-alert-example.png)

*Example Slack alert showing a cost spike detection with AI-powered root cause analysis*
```

---

### Anonymization Checklist

Before adding any screenshot, ensure:

- [ ] No real AWS account IDs (use 123456789012 or XXX-MASKED-XXX)
- [ ] No real email addresses (use example@example.com)
- [ ] No real employee names (use "John Doe" or similar)
- [ ] No actual cost amounts unless de minimis (use round numbers like $100, $500)
- [ ] No internal URLs or hostnames
- [ ] No API keys, tokens, or credentials visible
- [ ] No customer-specific resource names

---

## Tools for Creating Screenshots

### Recommended:
- **macOS**: Cmd+Shift+4 (select area)
- **Windows**: Snipping Tool or Win+Shift+S
- **Browser**: Full page screenshots via DevTools

### Editing:
- **Annotations**: Skitch, Monosnap, Snagit
- **Anonymization**: GIMP, Photoshop (blur sensitive data)
- **Compression**: TinyPNG, ImageOptim

### Diagrams:
- **draw.io** (diagrams.net)
- **Lucidchart**
- **AWS Architecture Icons**: https://aws.amazon.com/architecture/icons/

---

## Post-Deployment Checklist

After adding screenshots:

1. [ ] Create `images/` directory
2. [ ] Add all screenshots per list above
3. [ ] Verify images load in GitHub preview
4. [ ] Check file sizes (<500KB each)
5. [ ] Update alt text for accessibility
6. [ ] Test README renders correctly on GitHub
7. [ ] Commit: `git add images/ && git commit -m "Add screenshots"`
8. [ ] Push to GitHub

---

## Optional: Video Walkthrough

Consider adding a 2-3 minute demo video:

**Content**:
- Quick architecture overview
- Live deployment demo
- Slack alert demonstration
- CloudWatch logs inspection

**Where to host**:
- YouTube (AWS channel or personal)
- Link from README: `[![Demo Video](thumbnail.png)](video-url)`

---

**Note**: Screenshots should only be added AFTER getting AWS approval and deploying in a demo/sandbox account. Do not use production accounts for screenshots.
