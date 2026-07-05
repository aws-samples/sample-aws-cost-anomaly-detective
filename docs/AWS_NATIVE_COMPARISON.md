# AWS Cost Anomaly Detection: Reference Architecture Guide

## Overview

In June 2026, AWS launched [AI-powered Cost Investigations](https://aws.amazon.com/blogs/aws-cloud-financial-management/introducing-ai-powered-cost-investigations-for-cost-anomalies/) as part of AWS Cost Anomaly Detection. This document explains how this reference architecture relates to AWS's native feature and demonstrates extension patterns.

**Purpose of This Document:** Educational guide showing how to build custom FinOps automation that complements AWS Cost Anomaly Detection.

---

## Executive Summary

This reference architecture demonstrates patterns for:
- ✅ Building AI-powered operational tools with Amazon Bedrock
- ✅ Integrating Cost Explorer + CloudTrail + AWS Config
- ✅ Creating custom remediation workflows
- ✅ Extending AWS managed services with bespoke automation

| Aspect | AWS Native Feature (Production) | This Sample (Education/Extension) |
|--------|--------------------------------|-----------------------------------|
| **Purpose** | Production cost anomaly detection | Reference architecture & learning |
| **Use Case** | Managed cost investigation service | Learn integration patterns, build custom tools |
| **Support** | AWS Support, fully managed | Community (GitHub), self-managed |
| **Best For** | Production FinOps workflows | Learning, customization, extension |
| **Integration** | AWS Console + FinOps Agent | Demonstrates Slack, Jira, ticketing patterns |

---

## Feature Comparison Matrix

### 🔍 Detection & Analysis

| Feature | AWS Native | This Project | Notes |
|---------|-----------|--------------|-------|
| Anomaly Detection | ✅ Cost Explorer based | ✅ Cost Explorer based | Both use same data source |
| AI Root Cause Analysis | ✅ Amazon Q | ✅ Claude Sonnet 4.6 | Both provide natural language explanations |
| CloudTrail Correlation | ✅ Who/what/when | ✅ Who/what/when | Both identify responsible users/API calls |
| AWS Config Integration | ⚠️ Not mentioned | ✅ Resource config changes | This project tracks infrastructure changes |
| Usage vs Rate Classification | ✅ Automatic | ✅ Automatic | Both distinguish usage spikes from pricing changes |
| Conversational Follow-ups | ✅ Ask questions via Q | ❌ Static reports | AWS allows interactive exploration |

**Winner:** Tie - Both provide excellent AI-powered analysis. AWS has conversational interface; this project has AWS Config integration.

---

### 🔧 Remediation & Action

| Feature | AWS Native | This Project | Notes |
|---------|-----------|--------------|-------|
| Remediation Recommendations | ❌ Analysis only | ✅ Step-by-step remediation | AWS stops at "what happened" |
| Auto-generated IaC Code | ❌ Not provided | ✅ CloudFormation + Terraform | This project generates fix code |
| Automated Response | ❌ Manual handoff to engineering | ✅ Optional auto-apply | This project can auto-remediate |
| Approval Workflows | ❌ Not applicable | ✅ Configurable | Human-in-loop before changes |

**Winner:** This Project - AWS identifies problems; this project provides solutions.

---

### 🔔 Alerting & Integration

| Feature | AWS Native | This Project | Notes |
|---------|-----------|--------------|-------|
| AWS Console Alerts | ✅ Native UI | ⚠️ External (link to reports) | AWS has tighter console integration |
| Email Notifications | ⚠️ Via SNS separately | ✅ Built-in | This project includes email |
| Slack Integration | ⚠️ Via FinOps Agent | ✅ Native Slack webhooks | This project has direct Slack support |
| Jira/ServiceNow | ❌ Not mentioned | ✅ Auto-create tickets | This project integrates with ticketing |
| PagerDuty | ❌ Not mentioned | ✅ Critical anomaly paging | This project can page on-call |
| Custom Webhooks | ❌ Not mentioned | ✅ Any HTTP endpoint | This project is extensible |

**Winner:** This Project - Far more integration options.

---

### 💾 Data & Visibility

| Feature | AWS Native | This Project | Notes |
|---------|-----------|--------------|-------|
| Historical Trending | ✅ 90-day comparisons | ✅ Unlimited (your DynamoDB) | This project lets you keep all history |
| Raw Data Access | ❌ AWS-controlled | ✅ Full S3 + DynamoDB access | This project gives you the data |
| Custom Queries | ⚠️ Via Q conversational | ✅ Direct SQL/API queries | This project allows programmatic access |
| Data Export | ❌ Not mentioned | ✅ JSON reports in S3 | This project stores everything |
| API Access | ❌ Console-only | ✅ Lambda invocation + DynamoDB API | This project is fully programmable |

**Winner:** This Project - You own and control the data.

---

### ⚙️ Customization & Control

| Feature | AWS Native | This Project | Notes |
|---------|-----------|--------------|-------|
| Custom Thresholds | ❌ AWS-defined | ✅ Per-service, per-account | This project lets you set your own rules |
| Alert Frequency | ⚠️ AWS-controlled | ✅ Configurable (15min to daily) | This project offers flexibility |
| Exclusion Rules | ⚠️ Limited | ✅ Tag-based exclusions | This project can ignore specific resources |
| AI Prompt Tuning | ❌ Closed source | ✅ Modify prompts | This project lets you change AI behavior |
| Custom Metrics | ❌ Not supported | ✅ Add your own data sources | This project is extensible |
| White-label Branding | ❌ AWS-branded | ✅ Customize alerts/reports | This project can be branded |

**Winner:** This Project - Open source means full customization.

---

### 💰 Cost Comparison

#### AWS Native Feature

**Requirements:**
- Amazon Q Developer subscription: **$25/user/month**
- CloudWatch Logs Insights (cross-account queries): **$0.005/GB scanned**

**Typical Monthly Cost:**
- 10 users with Q Developer: **$250/month**
- CloudWatch queries (~10GB/month): **~$0.50/month**
- **Total: ~$250/month**

**Break-even:** If you already have Q Developer for other uses (code generation, chat), the incremental cost is minimal.

---

#### This Open-Source Project

**Pay-as-you-go:**
- Lambda: 720 invocations/month @ 1GB, 1min avg: **~$1**
- Cost Explorer API: 1,440 calls/month: **~$1.44**
- Bedrock (Claude): ~50 anomalies/month @ 4K tokens: **~$25**
- DynamoDB: On-demand, ~100 items/month: **<$1**
- S3: ~5GB storage: **<$1**
- SNS: ~50 emails/month: **<$1**
- CloudWatch Logs: ~1GB/month: **~$1**

**Total: ~$30/month**

**Cost Advantage:** **88% cheaper** ($30 vs $250) if you don't already have Q Developer.

---

### 🔒 Security & Compliance

| Feature | AWS Native | This Project | Notes |
|---------|-----------|--------------|-------|
| IAM Permissions | ✅ AWS-managed | ✅ Least-privilege roles | Both follow AWS best practices |
| Data Encryption | ✅ AWS-managed | ✅ S3/DynamoDB encryption | Both encrypt at rest |
| Audit Trail | ✅ CloudTrail | ✅ CloudTrail + Lambda logs | Both are auditable |
| VPC Support | ⚠️ Not required | ✅ Optional VPC deployment | This project can run in VPC |
| Secrets Management | ⚠️ Not applicable | ✅ Secrets Manager for Slack tokens | This project uses Secrets Manager |

**Winner:** Tie - Both are secure. This project offers VPC isolation option.

---

### 🚀 Deployment & Maintenance

| Feature | AWS Native | This Project | Notes |
|---------|-----------|--------------|-------|
| Setup Time | ⏱️ ~5 minutes | ⏱️ ~15 minutes | AWS is faster to enable |
| Maintenance Required | ✅ None (managed) | ⚠️ Update Lambda when models change | AWS handles updates automatically |
| Upgrades | ✅ Automatic | ⚠️ Manual git pull + redeploy | AWS advantage |
| Support | ✅ AWS Support | ⚠️ Community (GitHub Issues) | AWS has professional support |
| SLA | ✅ AWS SLA | ❌ Best-effort | AWS has guarantees |

**Winner:** AWS Native - Fully managed means less operational overhead.

---

## Gap Analysis: What AWS Doesn't Provide (Yet)

Based on the [AWS announcement blog post](https://aws.amazon.com/blogs/aws-cloud-financial-management/introducing-ai-powered-cost-investigations-for-cost-anomalies/), AWS's feature does NOT provide:

### 1. ❌ Remediation Code Generation
- **AWS:** Identifies problem, you figure out the fix
- **This Project:** Generates CloudFormation/Terraform code to apply fix

### 2. ❌ Native Slack Integration
- **AWS:** FinOps Agent can post to workflows, but no direct Slack webhooks mentioned
- **This Project:** Rich Slack alerts with interactive buttons

### 3. ❌ Ticketing System Integration
- **AWS:** Manual handoff to engineering team (per blog walkthrough)
- **This Project:** Auto-creates Jira/ServiceNow tickets

### 4. ❌ Customizable Thresholds
- **AWS:** Uses AWS-defined anomaly detection
- **This Project:** Set your own thresholds per service/account

### 5. ❌ Data Export/API Access
- **AWS:** Console-based, no mention of programmatic access
- **This Project:** Full API access, JSON reports in S3

### 6. ❌ Historical Data Ownership
- **AWS:** AWS controls the data
- **This Project:** You own it in your DynamoDB/S3

### 7. ❌ Multi-cloud Extension
- **AWS:** AWS-only
- **This Project:** Extensible to Azure/GCP cost APIs

### 8. ❌ White-label Customization
- **AWS:** AWS-branded
- **This Project:** Customize alerts/reports with your branding

---

## When to Use Each Solution

### ✅ Choose AWS Native Feature When:

1. **You already have Amazon Q Developer licenses** ($25/user)
   - Incremental cost is minimal
   - You're already using Q for code generation/chat

2. **You want zero operational overhead**
   - Fully managed, no Lambda to maintain
   - Automatic updates, AWS support

3. **You prefer AWS-native integrations**
   - Tight console integration
   - Works with FinOps Agent

4. **You need conversational follow-ups**
   - Ask Q follow-up questions
   - Interactive exploration

5. **You don't need remediation automation**
   - Analysis is enough
   - Your team will manually fix issues

---

### ✅ Choose This Open-Source Project When:

1. **You want to minimize costs**
   - $30/month vs $250/month (10 users)
   - 88% cost savings

2. **You need auto-remediation**
   - CloudFormation/Terraform code generation
   - Optional auto-apply with approval workflows

3. **You require custom integrations**
   - Slack, Jira, ServiceNow, PagerDuty
   - Custom webhooks for your internal tools

4. **You want full data ownership**
   - Store in your DynamoDB/S3
   - Unlimited historical retention
   - Programmatic access via API

5. **You need customization**
   - Modify AI prompts
   - Custom thresholds per service
   - Add your own data sources

6. **You want to learn the architecture**
   - Educational: see exactly how it works
   - Reference for building similar tools
   - Extend to your specific needs

7. **You're building a FinOps platform**
   - Use as a component in larger system
   - Integrate with your existing tools
   - Multi-cloud future roadmap

---

## Hybrid Approach: Use Both

**You can combine both solutions:**

1. **Use AWS Native for ad-hoc investigation**
   - When FinOps team needs to deep-dive
   - Conversational Q interface for exploration

2. **Use This Project for automation**
   - Automated alerting to Slack/Jira
   - Auto-generated remediation code
   - Historical trending in your BI tools

**Example workflow:**
```
1. Cost spike detected
2. This project sends Slack alert with AI analysis + remediation code
3. If team needs deeper investigation → Use AWS Q for conversational follow-up
4. Apply fix from generated CloudFormation code
5. Historical data stored in your DynamoDB for reporting
```

---

## Migration Path

### From This Project → AWS Native

If AWS adds remediation and integration features:

1. Disable Lambda EventBridge trigger (keep function for manual use)
2. Enable AWS Cost Anomaly Detection AI investigations
3. Configure FinOps Agent to post to your Slack/ticketing systems
4. Export historical data from DynamoDB for archival

**Data migration:** Export DynamoDB to S3 for historical records

---

### From AWS Native → This Project

If you want more control/cost savings:

1. Deploy this project's CloudFormation template
2. Historical data: AWS's investigations are in CloudWatch Logs, export to S3
3. Configure Slack/email/ticketing integrations
4. Test in parallel for 1 month before switching
5. Cancel Amazon Q licenses if not used for other features

---

## Conclusion

**Both solutions are excellent. Choose based on your needs:**

| Priority | Recommendation |
|----------|----------------|
| **Lowest Cost** | This Project ($30 vs $250/month) |
| **Zero Ops Overhead** | AWS Native (fully managed) |
| **Auto-Remediation** | This Project (generates IaC code) |
| **Conversational Exploration** | AWS Native (Q interface) |
| **Custom Integrations** | This Project (Slack, Jira, etc.) |
| **Data Ownership** | This Project (your S3/DynamoDB) |
| **Fastest Setup** | AWS Native (5 min vs 15 min) |
| **Customization** | This Project (open source) |

---

**AWS's native feature validates the approach.** The fact that AWS built this proves the market need and the value of AI-powered cost intelligence. This open-source project offers an alternative for teams that need remediation, customization, and cost savings.

**Not competitors—complementary solutions.** Some organizations may use both: AWS Native for ad-hoc investigation, this project for automated alerting and remediation.

---

**Last Updated:** July 5, 2026  
**AWS Feature Announced:** June 9, 2026  
**AWS Blog:** https://aws.amazon.com/blogs/aws-cloud-financial-management/introducing-ai-powered-cost-investigations-for-cost-anomalies/
