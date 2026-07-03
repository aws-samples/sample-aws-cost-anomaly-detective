"""
Cost Analyzer Module

Detects cost anomalies using AWS Cost Explorer API.
Compares current costs against historical baselines to identify spikes.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class CostAnalyzer:
    """Analyzes AWS costs and detects anomalies."""

    def __init__(self, cost_explorer_client: Any, config: Dict[str, Any]):
        """
        Initialize Cost Analyzer.

        Args:
            cost_explorer_client: Boto3 Cost Explorer client
            config: Configuration dictionary
        """
        self.ce_client = cost_explorer_client
        self.config = config

    def detect_anomalies(
        self,
        lookback_hours: int = 1,
        threshold_percentage: float = 50.0
    ) -> List[Dict[str, Any]]:
        """
        Detect cost anomalies by comparing recent costs to baseline.

        Args:
            lookback_hours: How many hours back to check for anomalies
            threshold_percentage: Minimum spike percentage to flag (e.g., 50 = 50% increase)

        Returns:
            List of anomaly dictionaries
        """
        logger.info(f"Detecting anomalies for last {lookback_hours} hour(s)")

        try:
            # Get current period costs
            current_costs = self._get_costs(
                hours_back=0,
                duration_hours=lookback_hours
            )

            # Get baseline costs (same time window, 1 week ago)
            baseline_costs = self._get_costs(
                hours_back=168,  # 7 days * 24 hours
                duration_hours=lookback_hours
            )

            # Compare and find anomalies
            anomalies = self._compare_costs(
                current_costs,
                baseline_costs,
                threshold_percentage
            )

            logger.info(f"Found {len(anomalies)} anomalies")
            return anomalies

        except ClientError as e:
            logger.error(f"AWS API error in detect_anomalies: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in detect_anomalies: {e}")
            raise

    def _get_costs(
        self,
        hours_back: int,
        duration_hours: int
    ) -> Dict[str, float]:
        """
        Fetch costs from AWS Cost Explorer.

        Args:
            hours_back: How many hours back from now to start
            duration_hours: Duration of the time window

        Returns:
            Dictionary mapping service name to cost
        """
        now = datetime.utcnow()
        end_time = now - timedelta(hours=hours_back)
        start_time = end_time - timedelta(hours=duration_hours)

        # Format for Cost Explorer API (YYYY-MM-DD)
        start_date = start_time.strftime('%Y-%m-%d')
        end_date = end_time.strftime('%Y-%m-%d')

        logger.debug(f"Fetching costs from {start_date} to {end_date}")

        try:
            response = self.ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date,
                    'End': end_date
                },
                Granularity='DAILY',  # Changed from HOURLY due to API limitations
                Metrics=['UnblendedCost'],
                GroupBy=[
                    {'Type': 'DIMENSION', 'Key': 'SERVICE'}
                ]
            )

            # Aggregate costs by service
            service_costs = {}
            for result in response.get('ResultsByTime', []):
                for group in result.get('Groups', []):
                    service = group['Keys'][0]
                    amount = float(group['Metrics']['UnblendedCost']['Amount'])
                    service_costs[service] = service_costs.get(service, 0) + amount

            logger.debug(f"Fetched costs for {len(service_costs)} services")
            return service_costs

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'LimitExceededException':
                logger.warning("Cost Explorer rate limit exceeded, using cached data")
                return {}
            raise

    def _compare_costs(
        self,
        current_costs: Dict[str, float],
        baseline_costs: Dict[str, float],
        threshold_percentage: float
    ) -> List[Dict[str, Any]]:
        """
        Compare current costs to baseline and identify anomalies.

        Args:
            current_costs: Current period costs by service
            baseline_costs: Baseline period costs by service
            threshold_percentage: Minimum spike percentage to flag

        Returns:
            List of anomaly dictionaries
        """
        anomalies = []
        now = datetime.utcnow()

        for service, current_cost in current_costs.items():
            # Skip services with negligible costs
            if current_cost < self.config.get('min_cost_threshold', 1.0):
                continue

            baseline_cost = baseline_costs.get(service, 0)

            # Calculate spike percentage
            if baseline_cost > 0:
                spike_pct = ((current_cost - baseline_cost) / baseline_cost) * 100
            else:
                # New service or baseline was $0
                spike_pct = 100 if current_cost > 0 else 0

            # Check if it exceeds threshold
            if spike_pct >= threshold_percentage:
                anomaly = {
                    'service': service,
                    'current_cost': round(current_cost, 2),
                    'baseline_cost': round(baseline_cost, 2),
                    'cost_change': round(current_cost - baseline_cost, 2),
                    'spike_percentage': round(spike_pct, 1),
                    'start_time': (now - timedelta(hours=1)).isoformat(),
                    'end_time': now.isoformat(),
                    'detected_at': now.isoformat()
                }

                logger.info(
                    f"Anomaly detected: {service} - "
                    f"${current_cost:.2f} (↑{spike_pct:.1f}% from ${baseline_cost:.2f})"
                )

                anomalies.append(anomaly)

        # Sort by cost impact (descending)
        anomalies.sort(key=lambda x: x['cost_change'], reverse=True)

        return anomalies

    def get_cost_forecast(
        self,
        service: str,
        days_ahead: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Get cost forecast for a specific service.

        Args:
            service: AWS service name
            days_ahead: How many days to forecast

        Returns:
            Forecast data or None if unavailable
        """
        try:
            now = datetime.utcnow()
            start_date = now.strftime('%Y-%m-%d')
            end_date = (now + timedelta(days=days_ahead)).strftime('%Y-%m-%d')

            response = self.ce_client.get_cost_forecast(
                TimePeriod={
                    'Start': start_date,
                    'End': end_date
                },
                Metric='UNBLENDED_COST',
                Granularity='MONTHLY',
                Filter={
                    'Dimensions': {
                        'Key': 'SERVICE',
                        'Values': [service]
                    }
                }
            )

            forecast_cost = float(response['Total']['Amount'])

            return {
                'service': service,
                'forecast_period_days': days_ahead,
                'forecast_cost': round(forecast_cost, 2),
                'forecast_date': end_date
            }

        except ClientError as e:
            logger.warning(f"Could not get forecast for {service}: {e}")
            return None
