"""
Amazon Bedrock AI Analyzer

Uses Claude Sonnet 4.6 to analyze cost anomalies and provide intelligent
root cause analysis and remediation recommendations.
"""

import json
import logging
from typing import Dict, Any, List
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class BedrockAnalyzer:
    """AI-powered cost anomaly analyzer using Amazon Bedrock."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Bedrock Analyzer.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.bedrock_runtime = boto3.client(
            'bedrock-runtime',
            region_name=config.get('bedrock_region', 'us-east-1')
        )
        self.model_id = config.get(
            'bedrock_model_id',
            'anthropic.claude-sonnet-4-6'
        )

    def analyze(
        self,
        anomaly_data: Dict[str, Any],
        context_data: Dict[str, Any],
        historical_patterns: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze cost anomaly using AI.

        Args:
            anomaly_data: Cost anomaly information
            context_data: Enriched context (CloudTrail, Config, metrics)
            historical_patterns: Past similar anomalies

        Returns:
            Analysis results with root cause, remediation, etc.
        """
        logger.info(f"Starting AI analysis for {anomaly_data['service']}")

        try:
            # Build the analysis prompt
            prompt = self._build_prompt(
                anomaly_data,
                context_data,
                historical_patterns
            )

            # Call Bedrock
            response = self._invoke_bedrock(prompt)

            # Parse and validate response
            analysis = self._parse_response(response)

            logger.info(f"AI analysis complete for {anomaly_data['service']}")
            return analysis

        except Exception as e:
            logger.error(f"Error in Bedrock analysis: {e}")
            # Return fallback analysis
            return self._fallback_analysis(anomaly_data)

    def _build_prompt(
        self,
        anomaly_data: Dict[str, Any],
        context_data: Dict[str, Any],
        historical_patterns: List[Dict[str, Any]]
    ) -> str:
        """Build the AI analysis prompt."""

        service = anomaly_data['service']
        current_cost = anomaly_data['current_cost']
        baseline_cost = anomaly_data['baseline_cost']
        spike_pct = anomaly_data['spike_percentage']

        prompt = f"""You are an expert AWS cost optimization analyst. Analyze this cost anomaly and provide actionable insights.

## Cost Anomaly Details
- **AWS Service**: {service}
- **Current Cost**: ${current_cost:.2f}
- **Baseline Cost** (1 week ago): ${baseline_cost:.2f}
- **Change**: ${anomaly_data['cost_change']:.2f} (↑{spike_pct:.1f}%)
- **Time Period**: {anomaly_data['start_time']} to {anomaly_data['end_time']}

## Context Data

### Configuration Changes (AWS Config)
{self._format_config_changes(context_data.get('config_changes', []))}

### API Activity (CloudTrail)
{self._format_cloudtrail_events(context_data.get('cloudtrail_events', []))}

### CloudWatch Metrics
{self._format_metrics(context_data.get('metrics', {}))}

### Historical Patterns
{self._format_historical(historical_patterns)}

## Your Task
Analyze this data and provide a comprehensive assessment. Return your analysis in JSON format:

```json
{{
  "root_cause": "Clear explanation of WHY costs increased (be specific)",
  "severity": "Critical|High|Medium|Low",
  "confidence": "High|Medium|Low",
  "contributing_factors": [
    "Factor 1 with specific details",
    "Factor 2 with specific details"
  ],
  "impact_assessment": {{
    "financial_impact": "$X per day/month",
    "affected_resources": ["resource-id-1", "resource-id-2"],
    "business_impact": "Description of business impact"
  }},
  "remediation_steps": [
    {{
      "step": 1,
      "action": "Specific action to take",
      "expected_savings": "$X/month",
      "risk": "Low|Medium|High",
      "urgency": "Immediate|This week|This month"
    }}
  ],
  "prevention_recommendations": [
    "How to prevent this in the future"
  ],
  "estimated_savings": "$X/month",
  "executive_summary": "2-3 sentence non-technical explanation for leadership",
  "technical_details": "Detailed technical explanation for DevOps teams"
}}
```

Be specific and actionable. Reference actual resource IDs, timestamps, and users when available in the context data.
"""

        return prompt

    def _format_config_changes(self, config_changes: List[Dict]) -> str:
        """Format AWS Config changes for prompt."""
        if not config_changes:
            return "No configuration changes detected in the time period."

        formatted = []
        for change in config_changes[:10]:  # Limit to 10 most recent
            formatted.append(
                f"- **{change.get('resourceType', 'Unknown')}**: "
                f"{change.get('resourceId', 'N/A')} - "
                f"{change.get('configurationItemStatus', 'N/A')} at "
                f"{change.get('resourceCreationTime', 'N/A')}"
            )

        return "\n".join(formatted) if formatted else "No changes found."

    def _format_cloudtrail_events(self, events: List[Dict]) -> str:
        """Format CloudTrail events for prompt."""
        if not events:
            return "No relevant API calls detected in the time period."

        formatted = []
        for event in events[:15]:  # Limit to 15 most relevant
            formatted.append(
                f"- **{event.get('EventName', 'Unknown')}** by "
                f"{event.get('Username', 'Unknown')} at "
                f"{event.get('EventTime', 'N/A')}"
            )

        return "\n".join(formatted) if formatted else "No events found."

    def _format_metrics(self, metrics: Dict) -> str:
        """Format CloudWatch metrics for prompt."""
        if not metrics:
            return "No metrics data available."

        formatted = []
        for metric_name, values in metrics.items():
            if isinstance(values, dict):
                formatted.append(f"- **{metric_name}**: {json.dumps(values)}")
            else:
                formatted.append(f"- **{metric_name}**: {values}")

        return "\n".join(formatted) if formatted else "No metrics found."

    def _format_historical(self, historical: List[Dict]) -> str:
        """Format historical anomalies for prompt."""
        if not historical:
            return "No similar past anomalies found."

        formatted = []
        for item in historical[:5]:  # Limit to 5 most recent
            if 'analysis' in item and 'root_cause' in item['analysis']:
                formatted.append(
                    f"- **{item.get('timestamp', 'Unknown date')}**: "
                    f"{item['analysis']['root_cause'][:100]}..."
                )

        return "\n".join(formatted) if formatted else "No historical patterns."

    def _invoke_bedrock(self, prompt: str) -> Dict[str, Any]:
        """
        Invoke Amazon Bedrock with the analysis prompt.

        Args:
            prompt: Analysis prompt

        Returns:
            Bedrock response
        """
        # Claude Sonnet 4.6 request format
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4000,
            "temperature": 0.2,  # Lower temperature for more deterministic analysis
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        try:
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )

            response_body = json.loads(response['body'].read())
            return response_body

        except ClientError as e:
            logger.error(f"Bedrock API error: {e}")
            raise

    def _parse_response(self, bedrock_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse and validate Bedrock response.

        Args:
            bedrock_response: Raw Bedrock response

        Returns:
            Parsed analysis dict
        """
        try:
            # Extract content from Claude response
            content = bedrock_response['content'][0]['text']

            # Extract JSON from markdown code blocks if present
            if '```json' in content:
                start = content.find('```json') + 7
                end = content.find('```', start)
                json_str = content[start:end].strip()
            elif '```' in content:
                start = content.find('```') + 3
                end = content.find('```', start)
                json_str = content[start:end].strip()
            else:
                json_str = content

            analysis = json.loads(json_str)

            # Validate required fields
            required_fields = [
                'root_cause', 'severity', 'remediation_steps',
                'estimated_savings', 'executive_summary'
            ]

            for field in required_fields:
                if field not in analysis:
                    logger.warning(f"Missing field in AI response: {field}")
                    analysis[field] = "Not provided"

            return analysis

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error(f"Error parsing Bedrock response: {e}")
            raise

    def _fallback_analysis(self, anomaly_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provide fallback analysis if Bedrock fails.

        Args:
            anomaly_data: Cost anomaly data

        Returns:
            Basic analysis dict
        """
        logger.warning("Using fallback analysis (Bedrock unavailable)")

        return {
            "root_cause": f"Cost increase detected for {anomaly_data['service']} "
                          f"but detailed analysis unavailable. Manual investigation required.",
            "severity": "Medium",
            "confidence": "Low",
            "contributing_factors": [
                "Automatic analysis failed",
                "Manual review recommended"
            ],
            "remediation_steps": [
                {
                    "step": 1,
                    "action": "Review AWS Cost Explorer for detailed cost breakdown",
                    "expected_savings": "Unknown",
                    "risk": "Low",
                    "urgency": "This week"
                }
            ],
            "estimated_savings": "Unknown",
            "executive_summary": f"{anomaly_data['service']} costs increased by "
                                f"{anomaly_data['spike_percentage']:.1f}%. "
                                f"Manual investigation needed.",
            "technical_details": "Automated analysis unavailable. "
                                "Check CloudWatch, CloudTrail, and Config for recent changes.",
            "fallback_mode": True
        }
