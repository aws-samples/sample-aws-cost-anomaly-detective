"""
Context Enricher Module

Enriches cost anomalies with contextual data from CloudTrail, AWS Config, and CloudWatch.
Helps AI understand WHY costs changed by correlating with configuration changes and events.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class ContextEnricher:
    """Enriches cost anomalies with AWS context data."""

    def __init__(
        self,
        cloudtrail_client: Any,
        config_client: Any,
        cloudwatch_client: Any,
        config: Dict[str, Any]
    ):
        """
        Initialize Context Enricher.

        Args:
            cloudtrail_client: Boto3 CloudTrail client
            config_client: Boto3 Config client
            cloudwatch_client: Boto3 CloudWatch Logs client
            config: Configuration dictionary
        """
        self.cloudtrail = cloudtrail_client
        self.config_service = config_client
        self.cloudwatch = cloudwatch_client
        self.config = config

    def enrich(
        self,
        service: str,
        time_range: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Enrich anomaly with contextual data.

        Args:
            service: AWS service name (e.g., "AWS Lambda")
            time_range: Dict with 'start' and 'end' ISO timestamps

        Returns:
            Dict with enriched context data
        """
        logger.info(f"Enriching context for {service}")

        context = {
            'service': service,
            'time_range': time_range,
            'cloudtrail_events': [],
            'config_changes': [],
            'metrics': {}
        }

        try:
            # Get CloudTrail events
            context['cloudtrail_events'] = self._get_cloudtrail_events(
                service, time_range
            )

            # Get AWS Config changes
            context['config_changes'] = self._get_config_changes(
                service, time_range
            )

            # Get CloudWatch metrics (if available for this service)
            context['metrics'] = self._get_cloudwatch_metrics(
                service, time_range
            )

            logger.info(
                f"Context enriched: {len(context['cloudtrail_events'])} events, "
                f"{len(context['config_changes'])} config changes"
            )

        except Exception as e:
            logger.error(f"Error enriching context: {e}")

        return context

    def _get_cloudtrail_events(
        self,
        service: str,
        time_range: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Fetch relevant CloudTrail events.

        Args:
            service: AWS service name
            time_range: Time range dict

        Returns:
            List of relevant CloudTrail events
        """
        try:
            # Map service names to CloudTrail event sources
            service_mapping = {
                'AWS Lambda': 'lambda.amazonaws.com',
                'Amazon Elastic Compute Cloud - Compute': 'ec2.amazonaws.com',
                'Amazon Relational Database Service': 'rds.amazonaws.com',
                'Amazon Simple Storage Service': 's3.amazonaws.com',
                'Amazon DynamoDB': 'dynamodb.amazonaws.com',
                'Amazon Elastic Container Service': 'ecs.amazonaws.com'
            }

            event_source = service_mapping.get(service)
            if not event_source:
                logger.debug(f"No CloudTrail mapping for service: {service}")
                return []

            start_time = datetime.fromisoformat(time_range['start'])
            end_time = datetime.fromisoformat(time_range['end'])

            # Extend lookback to catch changes made before the cost spike
            lookback_start = start_time - timedelta(hours=24)

            logger.debug(f"Querying CloudTrail from {lookback_start} to {end_time}")

            response = self.cloudtrail.lookup_events(
                LookupAttributes=[
                    {
                        'AttributeKey': 'EventSource',
                        'AttributeValue': event_source
                    }
                ],
                StartTime=lookback_start,
                EndTime=end_time,
                MaxResults=50  # CloudTrail limit
            )

            events = []
            for event in response.get('Events', []):
                events.append({
                    'EventName': event.get('EventName'),
                    'EventTime': event.get('EventTime').isoformat(),
                    'Username': event.get('Username', 'Unknown'),
                    'ResourceType': event.get('ResourceType'),
                    'ResourceName': event.get('ResourceName'),
                    'EventSource': event.get('EventSource')
                })

            # Filter for significant events (modify, create, update operations)
            significant_events = [
                e for e in events
                if any(keyword in e['EventName'].lower()
                       for keyword in ['create', 'modify', 'update', 'put', 'run'])
            ]

            logger.info(f"Found {len(significant_events)} significant CloudTrail events")
            return significant_events

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDeniedException':
                logger.warning("No CloudTrail access - skipping event enrichment")
            else:
                logger.error(f"CloudTrail error: {e}")
            return []

    def _get_config_changes(
        self,
        service: str,
        time_range: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Fetch AWS Config resource changes.

        Args:
            service: AWS service name
            time_range: Time range dict

        Returns:
            List of configuration changes
        """
        try:
            # Map service names to Config resource types
            resource_type_mapping = {
                'AWS Lambda': 'AWS::Lambda::Function',
                'Amazon Elastic Compute Cloud - Compute': 'AWS::EC2::Instance',
                'Amazon Relational Database Service': 'AWS::RDS::DBInstance',
                'Amazon Simple Storage Service': 'AWS::S3::Bucket',
                'Amazon DynamoDB': 'AWS::DynamoDB::Table',
                'Amazon Elastic Container Service': 'AWS::ECS::Service'
            }

            resource_type = resource_type_mapping.get(service)
            if not resource_type:
                logger.debug(f"No Config mapping for service: {service}")
                return []

            start_time = datetime.fromisoformat(time_range['start'])
            end_time = datetime.fromisoformat(time_range['end'])
            lookback_start = start_time - timedelta(hours=24)

            # Note: This is a simplified version. In production, you'd need to:
            # 1. List all resources of this type
            # 2. Get configuration history for each
            # 3. Filter by time range

            logger.debug(f"Config changes query for {resource_type}")

            # For demo purposes, returning empty list
            # Full implementation would query config history here
            return []

        except ClientError as e:
            logger.warning(f"Config service error: {e}")
            return []

    def _get_cloudwatch_metrics(
        self,
        service: str,
        time_range: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Fetch relevant CloudWatch metrics.

        Args:
            service: AWS service name
            time_range: Time range dict

        Returns:
            Dict of metric data
        """
        try:
            # Service-specific metric mappings
            metric_mappings = {
                'AWS Lambda': {
                    'namespace': 'AWS/Lambda',
                    'metrics': ['Invocations', 'Duration', 'Errors', 'Throttles']
                },
                'Amazon Elastic Compute Cloud - Compute': {
                    'namespace': 'AWS/EC2',
                    'metrics': ['CPUUtilization', 'NetworkIn', 'NetworkOut']
                },
                'Amazon Relational Database Service': {
                    'namespace': 'AWS/RDS',
                    'metrics': ['CPUUtilization', 'DatabaseConnections', 'ReadIOPS']
                }
            }

            mapping = metric_mappings.get(service)
            if not mapping:
                logger.debug(f"No CloudWatch mapping for service: {service}")
                return {}

            start_time = datetime.fromisoformat(time_range['start'])
            end_time = datetime.fromisoformat(time_range['end'])

            # For simplicity, return summary statistics
            # Full implementation would query GetMetricStatistics API

            metrics = {
                'namespace': mapping['namespace'],
                'metrics_available': mapping['metrics'],
                'note': 'Full metric data requires resource-specific queries'
            }

            logger.debug(f"Metrics context for {service}: {metrics}")
            return metrics

        except Exception as e:
            logger.warning(f"CloudWatch metrics error: {e}")
            return {}
