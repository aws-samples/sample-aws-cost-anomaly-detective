"""
Utility Functions

Helper functions for logging, configuration, and DynamoDB operations.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from decimal import Decimal


def setup_logging(name: str) -> logging.Logger:
    """
    Setup standardized logging.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)

    # Set level from environment or default to INFO
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Only add handler if none exist (prevents duplicates in Lambda)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def load_config() -> Dict[str, Any]:
    """
    Load configuration from environment variables.

    Returns:
        Configuration dictionary
    """
    config = {
        # Analysis settings
        'lookback_hours': int(os.environ.get('LOOKBACK_HOURS', '1')),
        'threshold_percentage': float(os.environ.get('THRESHOLD_PERCENTAGE', '50')),
        'min_cost_threshold': float(os.environ.get('MIN_COST_THRESHOLD', '1.0')),
        'dedupe_hours': int(os.environ.get('DEDUPE_HOURS', '24')),
        'history_lookback_days': int(os.environ.get('HISTORY_LOOKBACK_DAYS', '30')),

        # Bedrock settings
        'bedrock_region': os.environ.get('BEDROCK_REGION', 'us-east-1'),
        'bedrock_model_id': os.environ.get(
            'BEDROCK_MODEL_ID',
            'anthropic.claude-3-5-sonnet-20241022-v2:0'
        ),

        # Storage
        'dynamodb_table_name': os.environ.get('DYNAMODB_TABLE_NAME', 'cost-anomalies'),
        's3_bucket_name': os.environ.get('S3_BUCKET_NAME'),

        # Alerting
        'sns_topic_arn': os.environ.get('SNS_TOPIC_ARN'),
        'slack_webhook_url': os.environ.get('SLACK_WEBHOOK_URL'),

        # AWS settings
        'aws_region': os.environ.get('AWS_REGION', 'us-east-1')
    }

    return config


class DynamoDBStore:
    """DynamoDB operations for anomaly storage and retrieval."""

    def __init__(self, table: Any):
        """
        Initialize DynamoDB store.

        Args:
            table: Boto3 DynamoDB Table resource
        """
        self.table = table
        self.logger = logging.getLogger(__name__)

    def store_anomaly(self, anomaly: Dict[str, Any]) -> bool:
        """
        Store anomaly record in DynamoDB.

        Args:
            anomaly: Anomaly data

        Returns:
            True if successful
        """
        try:
            # Convert floats to Decimal for DynamoDB
            item = self._prepare_for_dynamodb(anomaly)

            # Add primary key
            timestamp = anomaly['timestamp']
            service = anomaly['service']

            item['PK'] = f"ANOMALY#{timestamp}"
            item['SK'] = f"SERVICE#{service}"
            item['GSI1PK'] = f"SERVICE#{service}"  # For querying by service
            item['GSI1SK'] = timestamp

            self.table.put_item(Item=item)

            self.logger.info(f"Stored anomaly: {service} at {timestamp}")
            return True

        except Exception as e:
            self.logger.error(f"Error storing anomaly: {e}")
            return False

    def is_duplicate_anomaly(
        self,
        service: str,
        hours: int = 24
    ) -> bool:
        """
        Check if similar anomaly was already reported recently.

        Args:
            service: AWS service name
            hours: Lookback period in hours

        Returns:
            True if duplicate found
        """
        try:
            cutoff_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

            response = self.table.query(
                IndexName='GSI1',
                KeyConditionExpression=(
                    'GSI1PK = :service AND GSI1SK > :cutoff'
                ),
                ExpressionAttributeValues={
                    ':service': f"SERVICE#{service}",
                    ':cutoff': cutoff_time
                },
                Limit=1
            )

            is_duplicate = len(response.get('Items', [])) > 0

            if is_duplicate:
                self.logger.info(f"Duplicate anomaly detected for {service}")

            return is_duplicate

        except Exception as e:
            self.logger.error(f"Error checking duplicates: {e}")
            return False  # On error, allow the alert (fail open)

    def get_past_anomalies(
        self,
        service: str,
        lookback_days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get historical anomalies for a service.

        Args:
            service: AWS service name
            lookback_days: How many days back to search

        Returns:
            List of past anomaly records
        """
        try:
            cutoff_time = (
                datetime.utcnow() - timedelta(days=lookback_days)
            ).isoformat()

            response = self.table.query(
                IndexName='GSI1',
                KeyConditionExpression=(
                    'GSI1PK = :service AND GSI1SK > :cutoff'
                ),
                ExpressionAttributeValues={
                    ':service': f"SERVICE#{service}",
                    ':cutoff': cutoff_time
                },
                Limit=10  # Last 10 anomalies
            )

            items = response.get('Items', [])

            # Convert Decimal back to float
            historical = [
                self._prepare_from_dynamodb(item) for item in items
            ]

            self.logger.info(
                f"Retrieved {len(historical)} historical anomalies for {service}"
            )

            return historical

        except Exception as e:
            self.logger.error(f"Error retrieving history: {e}")
            return []

    def _prepare_for_dynamodb(self, data: Any) -> Any:
        """
        Convert floats to Decimal for DynamoDB storage.

        Args:
            data: Data structure to convert

        Returns:
            DynamoDB-compatible data
        """
        if isinstance(data, dict):
            return {k: self._prepare_for_dynamodb(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._prepare_for_dynamodb(item) for item in data]
        elif isinstance(data, float):
            return Decimal(str(data))
        else:
            return data

    def _prepare_from_dynamodb(self, data: Any) -> Any:
        """
        Convert Decimal back to float from DynamoDB.

        Args:
            data: Data structure to convert

        Returns:
            Python-native data types
        """
        if isinstance(data, dict):
            return {k: self._prepare_from_dynamodb(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._prepare_from_dynamodb(item) for item in data]
        elif isinstance(data, Decimal):
            return float(data)
        else:
            return data


def format_currency(amount: float) -> str:
    """
    Format amount as currency.

    Args:
        amount: Dollar amount

    Returns:
        Formatted string
    """
    return f"${amount:,.2f}"


def calculate_monthly_projection(daily_cost: float) -> float:
    """
    Project monthly cost from daily cost.

    Args:
        daily_cost: Daily cost

    Returns:
        Projected monthly cost
    """
    return daily_cost * 30


def truncate_string(text: str, max_length: int = 100) -> str:
    """
    Truncate string to max length.

    Args:
        text: String to truncate
        max_length: Maximum length

    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."
