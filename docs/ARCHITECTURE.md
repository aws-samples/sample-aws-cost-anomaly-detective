# Architecture

## Overview

AWS Cost Anomaly Detective is a serverless, event-driven solution that automatically detects cost spikes, performs AI-powered root cause analysis, and sends actionable alerts.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           AWS Cost Anomaly Detective                      │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│  EventBridge     │
│  (Hourly)        │──────┐
└──────────────────┘      │
                          │ Trigger
                          ▼
              ┌───────────────────────┐
              │   Lambda Function     │
              │   (cost-detective)    │
              │   Python 3.12         │
              │   1024MB / 5min       │
              └───────────────────────┘
                        │
        ┌───────────────┼───────────────────────┐
        │               │                       │
        ▼               ▼                       ▼
┌──────────────┐  ┌──────────────┐    ┌──────────────┐
│ AWS Cost     │  │  CloudTrail  │    │ AWS Config   │
│ Explorer API │  │  API         │    │ API          │
│              │  │              │    │              │
│ • GetCost    │  │ • LookupEvent│    │ • GetConfig  │
│   AndUsage   │  │   s          │    │   History    │
└──────────────┘  └──────────────┘    └──────────────┘
        │
        │ Cost data
        ▼
┌─────────────────────────────────────────┐
│      AI Analysis (Amazon Bedrock)        │
│                                          │
│  Claude Sonnet 4.6                       │
│  • Root cause analysis                   │
│  • Context correlation                   │
│  • Remediation recommendations           │
│  • CloudFormation code generation        │
└─────────────────────────────────────────┘
        │
        │ Enriched insights
        ▼
┌───────────────┬────────────────┬──────────────────┐
│               │                │                  │
▼               ▼                ▼                  ▼
┌──────────┐  ┌────────┐  ┌──────────┐  ┌────────────────┐
│ DynamoDB │  │   S3   │  │   SNS    │  │  CloudWatch    │
│          │  │        │  │          │  │  Logs          │
│ Store    │  │ Reports│  │ Email    │  │                │
│ anomalies│  │ (JSON) │  │ alerts   │  │ Execution logs │
└──────────┘  └────────┘  └──────────┘  └────────────────┘
```

---

## Component Details

### 1. Trigger (EventBridge)

**Type:** Scheduled rule  
**Frequency:** Hourly (configurable: 15min, 1hr, 6hr, daily)  
**Purpose:** Automatically invoke Lambda on schedule

**Configuration:**
```yaml
ScheduleExpression: rate(1 hour)
State: ENABLED
```

---

### 2. Lambda Function (cost-detective)

**Runtime:** Python 3.12  
**Memory:** 1024 MB  
**Timeout:** 5 minutes  
**Trigger:** EventBridge scheduled rule

**Environment Variables:**
- `DYNAMODB_TABLE_NAME` - DynamoDB table for storing anomalies
- `S3_BUCKET_NAME` - S3 bucket for detailed reports
- `SNS_TOPIC_ARN` - SNS topic for email alerts
- `THRESHOLD_PERCENTAGE` - Minimum spike % to alert (default: 50)
- `BEDROCK_REGION` - Region for Bedrock API calls
- `LOG_LEVEL` - Logging verbosity (INFO, DEBUG)

**IAM Permissions:**
- Cost Explorer: `GetCostAndUsage`, `GetCostForecast`
- CloudTrail: `LookupEvents`
- AWS Config: `GetResourceConfigHistory`
- CloudWatch: `StartQuery`, `GetQueryResults`
- Bedrock: `InvokeModel`
- DynamoDB: `PutItem`, `Query`, `GetItem`
- S3: `PutObject`
- SNS: `Publish`

---

### 3. Data Sources

#### AWS Cost Explorer API
**Purpose:** Fetch cost data for anomaly detection

**Queries:**
- Current period costs (last 1 hour/day)
- Baseline costs (1 week ago, same time window)
- Service-level breakdown
- Daily granularity (hourly not available for all accounts)

**Logic:**
```python
current_costs = get_costs(hours_back=0, duration=1)
baseline_costs = get_costs(hours_back=168, duration=1)  # 1 week ago

spike_percentage = ((current - baseline) / baseline) * 100
if spike_percentage > threshold:
    trigger_analysis()
```

#### CloudTrail API
**Purpose:** Identify WHO made WHAT changes

**Queries:**
- API calls for services with cost spikes
- Time window: Last 24 hours before spike
- User identity, event name, event time
- Source IP, user agent

**Example events captured:**
- EC2: `RunInstances`, `ModifyInstanceAttribute`
- RDS: `CreateDBInstance`, `ModifyDBInstance`
- Lambda: `UpdateFunctionConfiguration`

#### AWS Config API
**Purpose:** Track resource configuration changes

**Queries:**
- Configuration history for affected resources
- Changes in instance types, sizes, counts
- Tag modifications
- Relationship tracking (which resources changed together)

#### CloudWatch Logs Insights
**Purpose:** Application-level context

**Queries:**
- Error rates during spike period
- Invocation patterns
- Performance metrics
- Custom application logs

---

### 4. AI Analysis (Amazon Bedrock)

**Model:** Claude Sonnet 4.6 (`anthropic.claude-sonnet-4-6`)  
**Temperature:** 0.2 (deterministic analysis)  
**Max Tokens:** 4000

**Input to AI:**
```
- Cost spike data (service, current cost, baseline, %)
- CloudTrail events (API calls, users, timestamps)
- Config changes (resource modifications)
- CloudWatch metrics (usage patterns)
- Historical anomalies (past patterns)
```

**AI Analysis Output:**
```json
{
  "root_cause": "Lambda memory increased from 128MB to 3GB",
  "severity": "High",
  "user_responsible": "john.doe@company.com",
  "timestamp": "2026-07-05T14:23:00Z",
  "cost_impact": {
    "current_monthly": 4500,
    "projected_annual": 54000,
    "vs_baseline": "+300%"
  },
  "remediation_steps": [
    "Revert memory to 1024MB (sufficient for P95)",
    "Enable Lambda Power Tuning",
    "Add approval workflow for memory > 512MB"
  ],
  "cloudformation_code": "...",
  "executive_summary": "Non-technical explanation for stakeholders"
}
```

**Value of AI:**
- Correlates multiple data sources automatically
- Explains causation, not just correlation
- Generates actionable recommendations
- Creates infrastructure-as-code for fixes
- Provides executive-friendly summaries

---

### 5. Storage & Alerting

#### DynamoDB (cost-anomalies)
**Purpose:** Store anomaly history for trend analysis

**Schema:**
```
PK: "ANOMALY#{timestamp}"
SK: "SERVICE#{service_name}"
GSI1PK: "SERVICE#{service_name}"  (for querying by service)
GSI1SK: "{timestamp}"

Attributes:
- service_name
- current_cost, baseline_cost, spike_percentage
- root_cause, severity
- detected_at, resolved_at
- remediation_steps
- status (open, investigating, resolved)
```

**Benefits:**
- Detect repeat offenders
- Track resolution time
- Historical trending
- Deduplication (don't re-alert for same issue)

#### S3 (cost-detective-reports-{account-id})
**Purpose:** Detailed analysis reports (JSON)

**File Structure:**
```
reports/
  2026-07-05/
    14-23-00-lambda-spike.json
    15-45-00-rds-anomaly.json
  2026-07-06/
    09-12-00-ec2-spike.json
```

**Lifecycle:** 90-day retention (configurable)

**Report Contents:**
- Full AI analysis
- Raw cost data
- CloudTrail events (complete)
- Config changes (complete)
- CloudWatch metrics
- Remediation code

#### SNS (cost-anomaly-alerts)
**Purpose:** Real-time email notifications

**Notification Format:**
```
Subject: 🚨 Cost Spike: Lambda +200% ($4,500/month projected)

Body:
- Service: AWS Lambda
- Spike: +200% ($150 current vs $50 baseline)
- Root Cause: Memory increased 128MB → 3GB by john.doe@company.com
- Projected Impact: $4,500/month ($54,000/year)
- Remediation: [Steps]
- Detailed Report: [S3 link]
```

**Subscribers:**
- FinOps team
- Engineering leadership
- On-call engineers (via integration with PagerDuty/Slack)

#### CloudWatch Logs
**Purpose:** Function execution logs

**Log Groups:**
- `/aws/lambda/cost-detective`
- Retention: 30 days (configurable)

---

## Data Flow

### Execution Sequence

```
1. EventBridge triggers Lambda (every hour)
   ↓
2. Lambda: Fetch current costs from Cost Explorer
   ↓
3. Lambda: Fetch baseline costs (1 week ago)
   ↓
4. Lambda: Compare current vs baseline
   ↓
5. IF spike detected (>threshold):
   ├─→ Query CloudTrail for recent API calls
   ├─→ Query Config for configuration changes
   ├─→ Query CloudWatch for metrics
   ↓
6. Lambda: Package all context data
   ↓
7. Lambda: Send to Bedrock for AI analysis
   ↓
8. Bedrock: Returns root cause + recommendations
   ↓
9. Lambda: Store anomaly in DynamoDB
   ↓
10. Lambda: Save detailed report to S3
   ↓
11. Lambda: Send alert via SNS
   ↓
12. SNS: Deliver email to subscribers
```

**Execution Time:** ~30-60 seconds per run  
**Cost per execution:** ~$0.01 (Bedrock dominates cost)

---

## Deployment Architecture

### Single Account Deployment
```
┌─────────────────────────────────────────┐
│         AWS Account (Production)        │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │   Cost Anomaly Detective        │   │
│  │   - Lambda, DynamoDB, S3        │   │
│  │   - Monitors this account only  │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### Multi-Account Deployment (AWS Organizations)
```
┌────────────────────────────────────────────────────────┐
│           Management Account (Payer)                    │
│                                                         │
│  ┌────────────────────────────────────────────┐        │
│  │   Cost Anomaly Detective (DEPLOY HERE)    │        │
│  │   - Org-wide Cost Explorer access         │        │
│  │   - Cross-account CloudTrail              │        │
│  └────────────────────────────────────────────┘        │
└─────────────────────┬──────────────────────────────────┘
                      │
          ┌───────────┼───────────┐
          │           │           │
          ▼           ▼           ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐
    │ Account │ │ Account │ │ Account │
    │   Dev   │ │  Prod   │ │ Staging │
    └─────────┘ └─────────┘ └─────────┘
    
    Cost Explorer in management account
    can see costs across ALL member accounts
```

**Why management account?**
- Only management account has org-wide Cost Explorer access
- Can detect cross-account spending patterns
- Centralized monitoring for entire organization

See [Multi-Account Deployment Guide](MULTI_ACCOUNT_DEPLOYMENT.md) for details.

---

## Security Architecture

### IAM Least Privilege
```
Lambda Execution Role:
├── AWSLambdaBasicExecutionRole (AWS Managed)
│   └── CloudWatch Logs write access
│
└── CostDetectivePolicy (Customer Managed)
    ├── Cost Explorer: Read only
    ├── CloudTrail: LookupEvents only (no modification)
    ├── Config: Read only
    ├── Bedrock: InvokeModel only (specific model)
    ├── DynamoDB: Read/Write to specific table
    ├── S3: PutObject to specific bucket
    └── SNS: Publish to specific topic
```

### Data Protection
- **S3 Encryption:** AES-256 (at rest)
- **DynamoDB Encryption:** Enabled by default
- **SNS:** Email in transit (TLS)
- **Bedrock:** Data not used for model training
- **CloudWatch Logs:** Encrypted

### Network Security
- **No VPC required** (fully serverless, AWS API endpoints)
- **PrivateLink option:** Deploy Lambda in VPC with VPC endpoints for APIs
- **Public IP:** Not required

---

## Cost Breakdown

### Monthly Operating Costs (Estimated)

| Service | Usage | Cost |
|---------|-------|------|
| **Lambda** | 720 invocations/month @ 1GB, 1min avg | ~$1 |
| **Cost Explorer API** | 1,440 API calls/month (2 per invocation) | ~$1.44 |
| **Bedrock (Claude Sonnet 4.6)** | ~50 anomalies/month @ 4K tokens output | ~$25 |
| **DynamoDB** | On-demand, ~100 items/month | <$1 |
| **S3** | ~5GB storage, ~100 PutObject/month | <$1 |
| **SNS** | ~50 email deliveries/month | <$1 |
| **CloudWatch Logs** | ~1GB/month, 30-day retention | ~$1 |
| **CloudTrail** | LookupEvents (no additional cost if trail exists) | $0 |
| **Config** | (no additional cost if already enabled) | $0 |
| **Total** | | **~$30/month** |

**Note:** Cost scales with:
- Number of anomalies detected (Bedrock calls)
- Frequency of Lambda execution (hourly vs daily)
- Size of AWS environment (more services = more Cost Explorer calls)

**Typical ROI:** First anomaly detected ($1,000+ spike) pays for years of operation

---

## Scalability

### Current Limits
- **Lambda timeout:** 5 minutes (adjustable to 15 min)
- **Lambda memory:** 1024 MB (adjustable up to 10 GB)
- **Cost Explorer API:** 5 requests/second (AWS limit)
- **Bedrock API:** Account-level quotas (request increase if needed)

### Scaling Considerations
- **Large AWS environment (100+ services):**
  - Increase Lambda timeout
  - Implement pagination for Cost Explorer queries
  - Consider batching Bedrock analysis

- **High anomaly volume:**
  - Implement priority queuing (high-cost spikes first)
  - Add deduplication logic (don't re-analyze same issue)
  - Rate limiting on alerts (max N per hour)

- **Multi-region:**
  - Deploy Lambda in each region
  - Aggregate to central DynamoDB (global tables)
  - Regional S3 buckets with cross-region replication

---

## Monitoring & Observability

### Lambda Metrics (CloudWatch)
- **Invocations:** Should be ~24/day (hourly)
- **Duration:** Typically 30-60 seconds
- **Errors:** Should be 0 (investigate if >1%)
- **Throttles:** Should be 0

### Custom Metrics
- **Anomalies detected per day:** Track trends
- **Average spike percentage:** Indicates severity
- **Time to detection:** How quickly after spike occurs
- **False positive rate:** Refine threshold if high

### Alarms
```yaml
AnomalyDetectionFailureAlarm:
  Metric: Lambda Errors
  Threshold: > 2 errors in 5 minutes
  Action: SNS notification to engineers

HighCostSpikeAlarm:
  Metric: Custom - Anomalies detected
  Threshold: > 10 in 1 hour
  Action: Page on-call engineer
```

---

## Troubleshooting

### Common Issues

**1. "No anomalies detected" (but costs are high)**
- Check `THRESHOLD_PERCENTAGE` (default 50% - may be too high)
- Verify Cost Explorer has data (new accounts may lag)
- Check Lambda logs for API errors

**2. "Date validation error" from Cost Explorer**
- Fixed in current version (checks start < end date)
- Ensure account has historical cost data

**3. "Bedrock throttling errors"**
- Request quota increase via AWS Support
- Reduce Lambda frequency (hourly → daily)
- Implement exponential backoff retry logic

**4. "Email alerts not received"**
- Confirm SNS subscription (check email for confirmation link)
- Check spam folder
- Verify SNS topic has correct permissions

---

## Future Enhancements

### Planned Features
- [ ] Slack integration (interactive alerts with action buttons)
- [ ] Auto-remediation (optional - apply fixes automatically)
- [ ] Forecasting (predict overspend before it happens)
- [ ] Budget guardrails (stop resources before exceeding budget)
- [ ] Custom rules engine (user-defined anomaly patterns)
- [ ] Integration with ServiceNow/Jira (auto-create tickets)

### Roadmap
See [GitHub Issues](https://github.com/aws-samples/sample-aws-cost-anomaly-detective/issues) for feature requests and roadmap.

---

## References

- [Multi-Account Deployment Guide](MULTI_ACCOUNT_DEPLOYMENT.md)
- [Workshop Tutorial](WORKSHOP.md)
- [AWS Cost Explorer API Documentation](https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/API_Operations_AWS_Cost_Explorer_Service.html)
- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Architecture Blog Post](BLOG.md)
