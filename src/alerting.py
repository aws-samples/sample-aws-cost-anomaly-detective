"""
Alerting Module

Sends cost anomaly alerts via SNS (email) and Slack.
Formats alerts with rich context and actionable recommendations.
"""

import json
import logging
from typing import Dict, Any, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class AlertManager:
    """Manages alerting for cost anomalies."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Alert Manager.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.sns_client = boto3.client('sns')

        # Severity emoji mapping
        self.severity_emojis = {
            'Critical': '🚨',
            'High': '⚠️',
            'Medium': '⚡',
            'Low': 'ℹ️'
        }

    def send_alert(
        self,
        anomaly: Dict[str, Any],
        analysis: Dict[str, Any],
        severity: str = 'Medium'
    ) -> Dict[str, bool]:
        """
        Send alert via all configured channels.

        Args:
            anomaly: Cost anomaly data
            analysis: AI analysis results
            severity: Alert severity level

        Returns:
            Dict with success status for each channel
        """
        results = {
            'sns': False,
            'slack': False,
            'success': False
        }

        # Send SNS alert
        if self.config.get('sns_topic_arn'):
            results['sns'] = self._send_sns_alert(anomaly, analysis, severity)

        # Send Slack alert
        if self.config.get('slack_webhook_url'):
            results['slack'] = self._send_slack_alert(anomaly, analysis, severity)

        # Overall success if at least one channel succeeded
        results['success'] = results['sns'] or results['slack']

        return results

    def _send_sns_alert(
        self,
        anomaly: Dict[str, Any],
        analysis: Dict[str, Any],
        severity: str
    ) -> bool:
        """
        Send alert via Amazon SNS (email).

        Args:
            anomaly: Cost anomaly data
            analysis: AI analysis results
            severity: Alert severity

        Returns:
            True if successful
        """
        try:
            topic_arn = self.config['sns_topic_arn']

            # Build email subject
            emoji = self.severity_emojis.get(severity, '📊')
            subject = (
                f"{emoji} Cost Anomaly Alert: {anomaly['service']} "
                f"(+{anomaly['spike_percentage']:.1f}%)"
            )

            # Build email body
            body = self._format_email_body(anomaly, analysis, severity)

            # Publish to SNS
            response = self.sns_client.publish(
                TopicArn=topic_arn,
                Subject=subject[:100],  # SNS subject limit
                Message=body,
                MessageAttributes={
                    'severity': {
                        'DataType': 'String',
                        'StringValue': severity
                    },
                    'service': {
                        'DataType': 'String',
                        'StringValue': anomaly['service']
                    }
                }
            )

            logger.info(f"SNS alert sent: MessageId={response['MessageId']}")
            return True

        except ClientError as e:
            logger.error(f"SNS send failed: {e}")
            return False
        except KeyError as e:
            logger.error(f"Missing config for SNS: {e}")
            return False

    def _send_slack_alert(
        self,
        anomaly: Dict[str, Any],
        analysis: Dict[str, Any],
        severity: str
    ) -> bool:
        """
        Send alert via Slack webhook.

        Args:
            anomaly: Cost anomaly data
            analysis: AI analysis results
            severity: Alert severity

        Returns:
            True if successful
        """
        try:
            webhook_url = self.config['slack_webhook_url']

            # Build Slack message blocks
            blocks = self._format_slack_blocks(anomaly, analysis, severity)

            payload = {
                'blocks': blocks,
                'text': f"Cost Anomaly: {anomaly['service']}"  # Fallback text
            }

            # Send to Slack
            request = Request(
                webhook_url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )

            response = urlopen(request, timeout=10)

            if response.status == 200:
                logger.info("Slack alert sent successfully")
                return True
            else:
                logger.warning(f"Slack returned status {response.status}")
                return False

        except URLError as e:
            logger.error(f"Slack webhook failed: {e}")
            return False
        except KeyError as e:
            logger.error(f"Missing config for Slack: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected Slack error: {e}")
            return False

    def _format_email_body(
        self,
        anomaly: Dict[str, Any],
        analysis: Dict[str, Any],
        severity: str
    ) -> str:
        """Format alert as email body."""

        emoji = self.severity_emojis.get(severity, '📊')

        body = f"""{emoji} AWS Cost Anomaly Detected

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SERVICE: {anomaly['service']}
SEVERITY: {severity}
DETECTED: {anomaly['detected_at']}

💰 COST IMPACT:
• Current Cost: ${anomaly['current_cost']:.2f}
• Baseline Cost: ${anomaly['baseline_cost']:.2f}
• Change: ${anomaly['cost_change']:.2f} (↑{anomaly['spike_percentage']:.1f}%)

🔍 ROOT CAUSE:
{analysis.get('root_cause', 'Analysis in progress...')}

💡 RECOMMENDATION:
"""

        # Add remediation steps
        remediation = analysis.get('remediation_steps', [])
        if remediation:
            for i, step in enumerate(remediation[:3], 1):
                if isinstance(step, dict):
                    body += f"\n{i}. {step.get('action', 'N/A')}"
                    body += f"\n   Expected Savings: {step.get('expected_savings', 'TBD')}"
                    body += f"\n   Urgency: {step.get('urgency', 'Unknown')}"
        else:
            body += "\nManual investigation required."

        # Add estimated savings
        if analysis.get('estimated_savings'):
            body += f"\n\n💵 ESTIMATED SAVINGS: {analysis['estimated_savings']}"

        # Add executive summary
        if analysis.get('executive_summary'):
            body += f"\n\n📊 EXECUTIVE SUMMARY:\n{analysis['executive_summary']}"

        body += "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        body += "\n\nThis alert was generated by AWS Cost Anomaly Detective"
        body += "\nPowered by Amazon Bedrock (Claude 3.5 Sonnet)"

        return body

    def _format_slack_blocks(
        self,
        anomaly: Dict[str, Any],
        analysis: Dict[str, Any],
        severity: str
    ) -> list:
        """Format alert as Slack blocks (rich formatting)."""

        emoji = self.severity_emojis.get(severity, '📊')

        # Severity color mapping
        colors = {
            'Critical': '#FF0000',
            'High': '#FF6B00',
            'Medium': '#FFB800',
            'Low': '#36C5F0'
        }
        color = colors.get(severity, '#36C5F0')

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} Cost Anomaly Detected: {anomaly['service']}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*💰 Current Cost:*\n${anomaly['current_cost']:.2f}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*📊 Change:*\n↑{anomaly['spike_percentage']:.1f}%"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*🎯 Severity:*\n{severity}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*🕐 Detected:*\n{anomaly['detected_at'][:16]}"
                    }
                ]
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🔍 Root Cause:*\n{analysis.get('root_cause', 'Analysis in progress...')}"
                }
            }
        ]

        # Add recommendation
        remediation = analysis.get('remediation_steps', [])
        if remediation and isinstance(remediation[0], dict):
            first_step = remediation[0]
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*💡 Recommendation:*\n{first_step.get('action', 'N/A')}\n\n"
                        f"💵 Estimated Savings: *{first_step.get('expected_savings', 'TBD')}*"
                    )
                }
            })

        # Add action buttons (if S3 report URL available)
        if self.config.get('s3_bucket_name'):
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View Full Report"
                        },
                        "url": self._get_report_url(anomaly),
                        "style": "primary"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View in Cost Explorer"
                        },
                        "url": self._get_cost_explorer_url(anomaly)
                    }
                ]
            })

        # Footer
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "🤖 Powered by Amazon Bedrock (Claude 3.5 Sonnet)"
                }
            ]
        })

        return blocks

    def _get_report_url(self, anomaly: Dict[str, Any]) -> str:
        """Generate S3 report URL (presigned)."""
        # Simplified - would generate actual presigned URL
        bucket = self.config.get('s3_bucket_name', 'cost-detective-reports')
        service = anomaly['service'].replace(' ', '-').lower()
        return f"https://s3.console.aws.amazon.com/s3/buckets/{bucket}"

    def _get_cost_explorer_url(self, anomaly: Dict[str, Any]) -> str:
        """Generate AWS Cost Explorer console URL."""
        region = self.config.get('aws_region', 'us-east-1')
        return (
            f"https://console.aws.amazon.com/cost-management/home"
            f"?region={region}#/cost-explorer"
        )
