"""
AWS Cost Anomaly Detective - Main Lambda Handler

This Lambda function detects cost anomalies using AI-powered analysis with Amazon Bedrock.
It correlates cost data with configuration changes, audit logs, and metrics to provide
intelligent root cause analysis and remediation recommendations.

Author: AWS Solutions Architect Team
License: Apache 2.0
"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

import boto3
from botocore.exceptions import ClientError

from cost_analyzer import CostAnalyzer
from context_enricher import ContextEnricher
from bedrock_client import BedrockAnalyzer
from alerting import AlertManager
from utils import setup_logging, load_config, DynamoDBStore

# Setup logging
logger = setup_logging(__name__)

# Initialize AWS clients
cost_explorer = boto3.client('ce')
cloudtrail = boto3.client('cloudtrail')
config_service = boto3.client('config')
cloudwatch = boto3.client('logs')
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for cost anomaly detection.

    Args:
        event: Lambda event (EventBridge schedule or CloudWatch Alarm)
        context: Lambda context object

    Returns:
        Dict with status and summary of anomalies detected
    """
    try:
        logger.info("Cost Anomaly Detective triggered")
        logger.debug(f"Event: {json.dumps(event)}")

        # Load configuration
        config = load_config()

        # Initialize components
        cost_analyzer = CostAnalyzer(cost_explorer, config)
        context_enricher = ContextEnricher(
            cloudtrail, config_service, cloudwatch, config
        )
        bedrock_analyzer = BedrockAnalyzer(config)
        alert_manager = AlertManager(config)
        db_store = DynamoDBStore(
            dynamodb.Table(config['dynamodb_table_name'])
        )

        # Step 1: Analyze costs and detect anomalies
        logger.info("Step 1: Analyzing costs...")
        anomalies = cost_analyzer.detect_anomalies(
            lookback_hours=config.get('lookback_hours', 1),
            threshold_percentage=config.get('threshold_percentage', 50)
        )

        if not anomalies:
            logger.info("No cost anomalies detected")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'No anomalies detected'})
            }

        logger.info(f"Detected {len(anomalies)} cost anomalies")

        # Step 2: Process each anomaly
        results = []
        for anomaly in anomalies:
            try:
                result = process_anomaly(
                    anomaly,
                    context_enricher,
                    bedrock_analyzer,
                    alert_manager,
                    db_store,
                    config
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing anomaly {anomaly['service']}: {e}")
                continue

        # Step 3: Generate summary
        summary = generate_summary(results)
        logger.info(f"Processing complete: {summary}")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'anomalies_detected': len(anomalies),
                'anomalies_processed': len(results),
                'summary': summary
            })
        }

    except Exception as e:
        logger.error(f"Fatal error in lambda_handler: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def process_anomaly(
    anomaly: Dict[str, Any],
    context_enricher: ContextEnricher,
    bedrock_analyzer: BedrockAnalyzer,
    alert_manager: AlertManager,
    db_store: DynamoDBStore,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process a single cost anomaly through the full pipeline.

    Args:
        anomaly: Cost anomaly data from CostAnalyzer
        context_enricher: Component for enriching with AWS context
        bedrock_analyzer: AI analysis component
        alert_manager: Alerting component
        db_store: DynamoDB storage component
        config: Configuration dictionary

    Returns:
        Dict with processing results
    """
    service = anomaly['service']
    logger.info(f"Processing anomaly for service: {service}")

    # Check if this is a duplicate (already alerted recently)
    if db_store.is_duplicate_anomaly(service, hours=config.get('dedupe_hours', 24)):
        logger.info(f"Skipping duplicate anomaly for {service}")
        return {'service': service, 'status': 'duplicate', 'alerted': False}

    # Step 2: Enrich with context
    logger.info(f"Step 2: Enriching context for {service}...")
    context_data = context_enricher.enrich(
        service=service,
        time_range={
            'start': anomaly['start_time'],
            'end': anomaly['end_time']
        }
    )

    # Step 3: Get historical patterns
    logger.info(f"Step 3: Retrieving historical patterns for {service}...")
    historical_anomalies = db_store.get_past_anomalies(
        service=service,
        lookback_days=config.get('history_lookback_days', 30)
    )

    # Step 4: AI Analysis with Bedrock
    logger.info(f"Step 4: Running AI analysis with Bedrock for {service}...")
    analysis = bedrock_analyzer.analyze(
        anomaly_data=anomaly,
        context_data=context_data,
        historical_patterns=historical_anomalies
    )

    # Step 5: Store results
    logger.info(f"Step 5: Storing analysis for {service}...")
    anomaly_record = {
        'service': service,
        'timestamp': anomaly['end_time'],
        'cost_change': anomaly['cost_change'],
        'spike_percentage': anomaly['spike_percentage'],
        'analysis': analysis,
        'context': context_data,
        'resolved': False
    }
    db_store.store_anomaly(anomaly_record)

    # Step 6: Save detailed report to S3
    if config.get('s3_bucket_name'):
        logger.info(f"Step 6: Saving report to S3 for {service}...")
        save_report_to_s3(anomaly_record, config['s3_bucket_name'])

    # Step 7: Send alerts
    logger.info(f"Step 7: Sending alerts for {service}...")
    alert_result = alert_manager.send_alert(
        anomaly=anomaly,
        analysis=analysis,
        severity=analysis.get('severity', 'Medium')
    )

    return {
        'service': service,
        'status': 'processed',
        'severity': analysis.get('severity'),
        'estimated_savings': analysis.get('estimated_savings'),
        'alerted': alert_result['success']
    }


def save_report_to_s3(anomaly_record: Dict[str, Any], bucket_name: str) -> None:
    """
    Save detailed anomaly report to S3.

    Args:
        anomaly_record: Complete anomaly data with analysis
        bucket_name: S3 bucket name
    """
    try:
        timestamp = datetime.fromisoformat(anomaly_record['timestamp'])
        date_prefix = timestamp.strftime('%Y-%m-%d')
        service = anomaly_record['service'].replace(' ', '-').lower()
        time_suffix = timestamp.strftime('%H-%M')

        # Save JSON report
        json_key = f"reports/{date_prefix}/{service}-{time_suffix}.json"
        s3.put_object(
            Bucket=bucket_name,
            Key=json_key,
            Body=json.dumps(anomaly_record, indent=2, default=str),
            ContentType='application/json'
        )
        logger.info(f"Saved JSON report to s3://{bucket_name}/{json_key}")

        # Save CloudFormation remediation if available
        if 'cloudformation_template' in anomaly_record['analysis']:
            cf_key = f"remediation/{date_prefix}/{service}-fix-{time_suffix}.yaml"
            s3.put_object(
                Bucket=bucket_name,
                Key=cf_key,
                Body=anomaly_record['analysis']['cloudformation_template'],
                ContentType='text/yaml'
            )
            logger.info(f"Saved remediation to s3://{bucket_name}/{cf_key}")

    except Exception as e:
        logger.error(f"Error saving to S3: {e}")


def generate_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate a summary of processing results.

    Args:
        results: List of processing results for each anomaly

    Returns:
        Summary dictionary
    """
    summary = {
        'total': len(results),
        'by_severity': {'Critical': 0, 'High': 0, 'Medium': 0, 'Low': 0},
        'total_estimated_savings': 0,
        'alerts_sent': 0
    }

    for result in results:
        if result.get('severity'):
            summary['by_severity'][result['severity']] += 1

        if result.get('estimated_savings'):
            # Parse savings like "$850/month" to float
            savings_str = result['estimated_savings'].replace('$', '').replace('/month', '').replace(',', '')
            try:
                summary['total_estimated_savings'] += float(savings_str)
            except ValueError:
                pass

        if result.get('alerted'):
            summary['alerts_sent'] += 1

    return summary


# For local testing
if __name__ == "__main__":
    # Simulate EventBridge trigger
    test_event = {
        'source': 'aws.events',
        'detail-type': 'Scheduled Event'
    }

    class MockContext:
        function_name = 'cost-detective-local-test'
        request_id = 'test-request-id'

    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2))
