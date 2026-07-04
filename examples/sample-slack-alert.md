# Sample Slack Alert

This is an example of what users see in Slack when a cost anomaly is detected.

---

## Alert Message

```
🚨 AWS Cost Anomaly Detected

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SERVICE: Amazon RDS
ACCOUNT: Production (123456789012)
SEVERITY: High
DETECTED: 2026-07-03 14:30:00 UTC

💰 COST IMPACT:
• Current Cost: $450.75
• Baseline Cost: $180.25
• Change: $270.50 (↑150%)
• Monthly Projection: $13,522.50

🔍 ROOT CAUSE:
Database instance prod-database-1 was manually upgraded from 
db.t3.large to db.r5.2xlarge at 2:15 PM by john.doe@company.com. 
CloudWatch metrics show the instance was significantly over-provisioned 
with average CPU at 15% and max at 28%, suggesting the upgrade was 
unnecessary.

💡 RECOMMENDATION:
1. Review the reason for the instance upgrade with john.doe@company.com
   Expected Savings: N/A
   Urgency: Immediate

2. Revert to db.t3.large if the upgrade was not required
   Expected Savings: $270/month
   Urgency: High

3. Implement approval workflow for production database changes >$100/month
   Expected Savings: Prevention
   Urgency: Medium

💵 ESTIMATED SAVINGS: $3,240/year if reverted to db.t3.large

📊 EXECUTIVE SUMMARY:
An unnecessary database upgrade increased costs by 150%. The instance 
was over-provisioned with low CPU utilization (15% average). Reverting 
the change would save $3,240 annually with no performance impact.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[View Full Report] [View in Cost Explorer]

🤖 Powered by Amazon Bedrock (Claude 4.5 Haiku)
```

---

## Interactive Elements

The Slack alert includes:

- **View Full Report** button → Opens S3 report URL
- **View in Cost Explorer** button → Deep links to AWS Console
- **Threaded responses** for team discussion
- **Emoji indicators** for severity (🚨 Critical, ⚠️ High, ⚡ Medium, ℹ️ Low)

---

## Alert Frequency

- **Deduplication**: Same service won't alert again within 24 hours
- **Configurable threshold**: Only alerts if spike >50% (default)
- **Minimum cost**: Ignores services costing <$1/hour (configurable)

---

## Screenshot Placeholder

> **TODO**: Add actual Slack screenshot here once deployed
> 
> Screenshot should show:
> - Full alert message in Slack channel
> - Action buttons (View Report, View in Cost Explorer)
> - Thread with team discussion
> - Multiple alerts showing different severity levels
