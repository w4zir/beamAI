"""
Unit tests for Prometheus alerting rules.

Tests verify:
- Alert rules are syntactically correct
- Alert condition evaluation logic
- Alert labels are correctly set
- Alert severity classification
- Alert annotations are properly formatted

These tests validate the alert rules defined in monitoring/prometheus/alerts.yml
without requiring a running Prometheus instance.
"""
import pytest
import yaml
from pathlib import Path
from typing import Dict, Any, List


# Path to alerts.yml file
ALERTS_FILE = Path(__file__).parent.parent.parent / "monitoring" / "prometheus" / "alerts.yml"


def load_alerts_file() -> Dict[str, Any]:
    """Load and parse the alerts.yml file."""
    if not ALERTS_FILE.exists():
        pytest.skip(f"Alerts file not found: {ALERTS_FILE}")
    
    with open(ALERTS_FILE, 'r') as f:
        return yaml.safe_load(f)


def get_alert_rules() -> List[Dict[str, Any]]:
    """Get all alert rules from the alerts file."""
    alerts_config = load_alerts_file()
    rules = []
    
    for group in alerts_config.get('groups', []):
        for rule in group.get('rules', []):
            if 'alert' in rule:  # Only alert rules, not recording rules
                rules.append(rule)
    
    return rules


def get_alert_by_name(alert_name: str) -> Dict[str, Any]:
    """Get a specific alert rule by name."""
    rules = get_alert_rules()
    for rule in rules:
        if rule.get('alert') == alert_name:
            return rule
    raise ValueError(f"Alert '{alert_name}' not found")


class TestAlertRulesSyntax:
    """Test that alert rules are syntactically correct."""
    
    def test_alerts_file_exists(self):
        """Test that alerts.yml file exists."""
        assert ALERTS_FILE.exists(), f"Alerts file not found: {ALERTS_FILE}"
    
    def test_alerts_file_is_valid_yaml(self):
        """Test that alerts.yml is valid YAML."""
        try:
            load_alerts_file()
        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML in alerts.yml: {e}")
    
    def test_alerts_file_has_groups(self):
        """Test that alerts.yml has groups section."""
        alerts_config = load_alerts_file()
        assert 'groups' in alerts_config, "Alerts file missing 'groups' section"
        assert len(alerts_config['groups']) > 0, "Alerts file has no groups"
    
    def test_all_alerts_have_required_fields(self):
        """Test that all alert rules have required fields."""
        rules = get_alert_rules()
        assert len(rules) > 0, "No alert rules found"
        
        required_fields = ['alert', 'expr', 'for', 'labels', 'annotations']
        
        for rule in rules:
            for field in required_fields:
                assert field in rule, f"Alert '{rule.get('alert', 'unknown')}' missing required field: {field}"
    
    def test_alert_expressions_are_valid_promql(self):
        """Test that alert expressions are valid PromQL (basic syntax check)."""
        rules = get_alert_rules()
        
        for rule in rules:
            expr = rule.get('expr', '')
            assert expr, f"Alert '{rule.get('alert')}' has empty expression"
            
            # Basic PromQL syntax checks
            assert not expr.startswith('|'), f"Alert '{rule.get('alert')}' expression should not start with pipe"
            assert '>' in expr or '<' in expr or '==' in expr, f"Alert '{rule.get('alert')}' expression should contain comparison operator"


class TestAlertRuleDefinitions:
    """Test that all required alert rules are defined."""
    
    def test_p99_latency_high_alert_exists(self):
        """Test that p99_latency_high alert exists."""
        alert = get_alert_by_name('p99_latency_high')
        assert alert is not None
    
    def test_error_rate_high_alert_exists(self):
        """Test that error_rate_high alert exists."""
        alert = get_alert_by_name('error_rate_high')
        assert alert is not None
    
    def test_zero_result_rate_high_alert_exists(self):
        """Test that zero_result_rate_high alert exists."""
        alert = get_alert_by_name('zero_result_rate_high')
        assert alert is not None
    
    def test_db_pool_exhausted_alert_exists(self):
        """Test that db_pool_exhausted alert exists."""
        alert = get_alert_by_name('db_pool_exhausted')
        assert alert is not None
    
    def test_cache_hit_rate_low_alert_exists(self):
        """Test that cache_hit_rate_low alert exists."""
        alert = get_alert_by_name('cache_hit_rate_low')
        assert alert is not None


class TestAlertLabels:
    """Test that alert labels are correctly set."""
    
    def test_p99_latency_high_labels(self):
        """Test p99_latency_high alert labels."""
        alert = get_alert_by_name('p99_latency_high')
        labels = alert.get('labels', {})
        
        assert 'severity' in labels, "Alert missing 'severity' label"
        assert labels['severity'] == 'critical', "Alert severity should be 'critical'"
        assert 'service' in labels, "Alert missing 'service' label"
        assert 'alert_type' in labels, "Alert missing 'alert_type' label"
        assert labels['alert_type'] == 'latency', "Alert type should be 'latency'"
    
    def test_error_rate_high_labels(self):
        """Test error_rate_high alert labels."""
        alert = get_alert_by_name('error_rate_high')
        labels = alert.get('labels', {})
        
        assert labels['severity'] == 'critical', "Alert severity should be 'critical'"
        assert labels['alert_type'] == 'errors', "Alert type should be 'errors'"
    
    def test_zero_result_rate_high_labels(self):
        """Test zero_result_rate_high alert labels."""
        alert = get_alert_by_name('zero_result_rate_high')
        labels = alert.get('labels', {})
        
        assert labels['severity'] == 'warning', "Alert severity should be 'warning'"
        assert labels['alert_type'] == 'search_quality', "Alert type should be 'search_quality'"
    
    def test_db_pool_exhausted_labels(self):
        """Test db_pool_exhausted alert labels."""
        alert = get_alert_by_name('db_pool_exhausted')
        labels = alert.get('labels', {})
        
        assert labels['severity'] == 'critical', "Alert severity should be 'critical'"
        assert labels['alert_type'] == 'database', "Alert type should be 'database'"
    
    def test_cache_hit_rate_low_labels(self):
        """Test cache_hit_rate_low alert labels."""
        alert = get_alert_by_name('cache_hit_rate_low')
        labels = alert.get('labels', {})
        
        assert labels['severity'] == 'warning', "Alert severity should be 'warning'"
        assert labels['alert_type'] == 'cache', "Alert type should be 'cache'"


class TestAlertSeverity:
    """Test that alert severity is correctly classified."""
    
    def test_critical_alerts(self):
        """Test that critical alerts have correct severity."""
        critical_alerts = ['p99_latency_high', 'error_rate_high', 'db_pool_exhausted']
        
        for alert_name in critical_alerts:
            alert = get_alert_by_name(alert_name)
            labels = alert.get('labels', {})
            assert labels.get('severity') == 'critical', f"Alert '{alert_name}' should be critical"
    
    def test_warning_alerts(self):
        """Test that warning alerts have correct severity."""
        warning_alerts = ['zero_result_rate_high', 'cache_hit_rate_low']
        
        for alert_name in warning_alerts:
            alert = get_alert_by_name(alert_name)
            labels = alert.get('labels', {})
            assert labels.get('severity') == 'warning', f"Alert '{alert_name}' should be warning"


class TestAlertExpressions:
    """Test that alert expressions are correctly formatted."""
    
    def test_p99_latency_high_expression(self):
        """Test p99_latency_high alert expression."""
        alert = get_alert_by_name('p99_latency_high')
        expr = alert.get('expr', '')
        
        assert 'histogram_quantile' in expr, "Expression should use histogram_quantile"
        assert '0.99' in expr, "Expression should calculate p99"
        assert 'http_request_duration_seconds' in expr, "Expression should use http_request_duration_seconds"
        assert '> 0.5' in expr, "Expression should check for > 0.5 (500ms)"
    
    def test_error_rate_high_expression(self):
        """Test error_rate_high alert expression."""
        alert = get_alert_by_name('error_rate_high')
        expr = alert.get('expr', '')
        
        assert 'http_errors_total' in expr, "Expression should use http_errors_total"
        assert 'http_requests_total' in expr, "Expression should use http_requests_total"
        assert '> 0.01' in expr, "Expression should check for > 1%"
        assert '/' in expr, "Expression should divide errors by requests"
    
    def test_zero_result_rate_high_expression(self):
        """Test zero_result_rate_high alert expression."""
        alert = get_alert_by_name('zero_result_rate_high')
        expr = alert.get('expr', '')
        
        assert 'search_zero_results_total' in expr, "Expression should use search_zero_results_total"
        assert 'http_requests_total' in expr, "Expression should use http_requests_total"
        assert 'endpoint="/search"' in expr, "Expression should filter for /search endpoint"
        assert '> 0.1' in expr, "Expression should check for > 10%"
    
    def test_db_pool_exhausted_expression(self):
        """Test db_pool_exhausted alert expression."""
        alert = get_alert_by_name('db_pool_exhausted')
        expr = alert.get('expr', '')
        
        assert 'db_connection_pool_size' in expr, "Expression should use db_connection_pool_size"
        assert 'state="total"' in expr, "Expression should check total connections"
        assert 'state="active"' in expr, "Expression should check active connections"
        assert '< 2' in expr, "Expression should check for < 2 available connections"
    
    def test_cache_hit_rate_low_expression(self):
        """Test cache_hit_rate_low alert expression."""
        alert = get_alert_by_name('cache_hit_rate_low')
        expr = alert.get('expr', '')
        
        assert 'cache_hits_total' in expr, "Expression should use cache_hits_total"
        assert 'cache_misses_total' in expr, "Expression should use cache_misses_total"
        assert '< 0.5' in expr, "Expression should check for < 50%"
        assert '/' in expr, "Expression should divide hits by (hits + misses)"


class TestAlertDurations:
    """Test that alert durations are correctly set."""
    
    def test_p99_latency_high_duration(self):
        """Test p99_latency_high alert duration."""
        alert = get_alert_by_name('p99_latency_high')
        assert alert.get('for') == '5m', "Alert should fire after 5 minutes"
    
    def test_error_rate_high_duration(self):
        """Test error_rate_high alert duration."""
        alert = get_alert_by_name('error_rate_high')
        assert alert.get('for') == '2m', "Alert should fire after 2 minutes"
    
    def test_zero_result_rate_high_duration(self):
        """Test zero_result_rate_high alert duration."""
        alert = get_alert_by_name('zero_result_rate_high')
        assert alert.get('for') == '10m', "Alert should fire after 10 minutes"
    
    def test_db_pool_exhausted_duration(self):
        """Test db_pool_exhausted alert duration."""
        alert = get_alert_by_name('db_pool_exhausted')
        assert alert.get('for') == '2m', "Alert should fire after 2 minutes"
    
    def test_cache_hit_rate_low_duration(self):
        """Test cache_hit_rate_low alert duration."""
        alert = get_alert_by_name('cache_hit_rate_low')
        assert alert.get('for') == '10m', "Alert should fire after 10 minutes"


class TestAlertAnnotations:
    """Test that alert annotations are properly formatted."""
    
    def test_all_alerts_have_summary(self):
        """Test that all alerts have summary annotation."""
        rules = get_alert_rules()
        
        for rule in rules:
            annotations = rule.get('annotations', {})
            assert 'summary' in annotations, f"Alert '{rule.get('alert')}' missing 'summary' annotation"
            assert annotations['summary'], f"Alert '{rule.get('alert')}' has empty 'summary'"
    
    def test_all_alerts_have_description(self):
        """Test that all alerts have description annotation."""
        rules = get_alert_rules()
        
        for rule in rules:
            annotations = rule.get('annotations', {})
            assert 'description' in annotations, f"Alert '{rule.get('alert')}' missing 'description' annotation"
            assert annotations['description'], f"Alert '{rule.get('alert')}' has empty 'description'"
    
    def test_all_alerts_have_runbook_url(self):
        """Test that all alerts have runbook_url annotation."""
        rules = get_alert_rules()
        
        for rule in rules:
            annotations = rule.get('annotations', {})
            assert 'runbook_url' in annotations, f"Alert '{rule.get('alert')}' missing 'runbook_url' annotation"
            assert 'runbook' in annotations['runbook_url'].lower(), f"Alert '{rule.get('alert')}' runbook_url should reference runbook"
    
    def test_p99_latency_high_annotations(self):
        """Test p99_latency_high alert annotations."""
        alert = get_alert_by_name('p99_latency_high')
        annotations = alert.get('annotations', {})
        
        assert 'p99 latency' in annotations.get('summary', '').lower(), "Summary should mention p99 latency"
        assert '0.5s' in annotations.get('description', '') or '500ms' in annotations.get('description', ''), "Description should mention threshold"
    
    def test_error_rate_high_annotations(self):
        """Test error_rate_high alert annotations."""
        alert = get_alert_by_name('error_rate_high')
        annotations = alert.get('annotations', {})
        
        assert 'error rate' in annotations.get('summary', '').lower(), "Summary should mention error rate"
        assert '1%' in annotations.get('description', '') or '0.01' in annotations.get('description', ''), "Description should mention threshold"


class TestAlertConditionEvaluation:
    """Test alert condition evaluation logic (conceptual tests)."""
    
    def test_p99_latency_high_condition(self):
        """Test p99_latency_high condition logic."""
        alert = get_alert_by_name('p99_latency_high')
        expr = alert.get('expr', '')
        
        # Condition should check if p99 > 0.5s
        assert '> 0.5' in expr, "Condition should check for > 0.5s"
        assert 'histogram_quantile(0.99' in expr, "Condition should calculate p99"
        
        # Should use 5-minute window
        assert '[5m]' in expr, "Condition should use 5-minute window"
    
    def test_error_rate_high_condition(self):
        """Test error_rate_high condition logic."""
        alert = get_alert_by_name('error_rate_high')
        expr = alert.get('expr', '')
        
        # Condition should calculate error rate
        assert 'http_errors_total' in expr and 'http_requests_total' in expr, "Condition should use error and request metrics"
        assert '> 0.01' in expr, "Condition should check for > 1%"
        
        # Should use 2-minute window
        assert '[2m]' in expr, "Condition should use 2-minute window"
    
    def test_zero_result_rate_high_condition(self):
        """Test zero_result_rate_high condition logic."""
        alert = get_alert_by_name('zero_result_rate_high')
        expr = alert.get('expr', '')
        
        # Condition should calculate zero-result rate
        assert 'search_zero_results_total' in expr, "Condition should use zero-results metric"
        assert '> 0.1' in expr, "Condition should check for > 10%"
        
        # Should use 10-minute window
        assert '[10m]' in expr, "Condition should use 10-minute window"
    
    def test_db_pool_exhausted_condition(self):
        """Test db_pool_exhausted condition logic."""
        alert = get_alert_by_name('db_pool_exhausted')
        expr = alert.get('expr', '')
        
        # Condition should check available connections
        assert 'db_connection_pool_size' in expr, "Condition should use connection pool metric"
        assert '< 2' in expr, "Condition should check for < 2 available"
        assert 'total' in expr and 'active' in expr, "Condition should calculate available = total - active"
    
    def test_cache_hit_rate_low_condition(self):
        """Test cache_hit_rate_low condition logic."""
        alert = get_alert_by_name('cache_hit_rate_low')
        expr = alert.get('expr', '')
        
        # Condition should calculate cache hit rate
        assert 'cache_hits_total' in expr and 'cache_misses_total' in expr, "Condition should use cache hit/miss metrics"
        assert '< 0.5' in expr, "Condition should check for < 50%"
        
        # Should use 10-minute window
        assert '[10m]' in expr, "Condition should use 10-minute window"

