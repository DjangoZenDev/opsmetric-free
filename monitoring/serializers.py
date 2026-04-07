from rest_framework import serializers

from .models import (
    ActionExecution,
    Alert,
    AlertRule,
    HealthCheck,
    Incident,
    IncidentUpdate,
    QuickAction,
    ServerMetric,
    Service,
    SystemLog,
)


class ServiceSerializer(serializers.ModelSerializer):
    status_color = serializers.ReadOnlyField()
    status_bg_class = serializers.ReadOnlyField()

    class Meta:
        model = Service
        fields = [
            "id", "name", "slug", "description", "url", "status", "category",
            "uptime_percentage", "last_checked", "status_color", "status_bg_class",
            "created_at", "updated_at",
        ]
        read_only_fields = ["slug", "created_at", "updated_at"]


class HealthCheckSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)

    class Meta:
        model = HealthCheck
        fields = [
            "id", "service", "service_name", "response_time_ms",
            "status_code", "is_healthy", "checked_at",
        ]


class IncidentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncidentUpdate
        fields = ["id", "incident", "message", "status", "created_at", "created_by"]
        read_only_fields = ["created_at"]


class IncidentSerializer(serializers.ModelSerializer):
    updates = IncidentUpdateSerializer(many=True, read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True)
    severity_color = serializers.ReadOnlyField()
    duration = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()

    class Meta:
        model = Incident
        fields = [
            "id", "title", "description", "severity", "status", "service",
            "service_name", "severity_color", "duration", "is_active",
            "started_at", "resolved_at", "created_at", "updated_at", "updates",
        ]
        read_only_fields = ["created_at", "updated_at"]


class ServerMetricSerializer(serializers.ModelSerializer):
    network_in_display = serializers.ReadOnlyField()
    network_out_display = serializers.ReadOnlyField()
    uptime_display = serializers.ReadOnlyField()

    class Meta:
        model = ServerMetric
        fields = [
            "id", "hostname", "cpu_percent", "memory_percent", "disk_percent",
            "network_in", "network_out", "network_in_display", "network_out_display",
            "load_average", "process_count", "uptime_seconds", "uptime_display",
            "recorded_at",
        ]


class AlertRuleSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True, default=None)

    class Meta:
        model = AlertRule
        fields = [
            "id", "name", "service", "service_name", "metric_type", "operator",
            "threshold", "severity", "is_active", "last_triggered",
            "cooldown_minutes", "created_at",
        ]
        read_only_fields = ["created_at", "last_triggered"]


class AlertSerializer(serializers.ModelSerializer):
    rule_name = serializers.CharField(source="rule.name", read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True, default=None)

    class Meta:
        model = Alert
        fields = [
            "id", "rule", "rule_name", "service", "service_name", "message",
            "severity", "current_value", "threshold_value", "is_acknowledged",
            "triggered_at", "acknowledged_at", "acknowledged_by",
        ]
        read_only_fields = ["triggered_at"]


class SystemLogSerializer(serializers.ModelSerializer):
    level_color = serializers.ReadOnlyField()
    level_bg = serializers.ReadOnlyField()

    class Meta:
        model = SystemLog
        fields = [
            "id", "source", "level", "message", "metadata",
            "timestamp", "level_color", "level_bg",
        ]
        read_only_fields = ["timestamp"]


class QuickActionSerializer(serializers.ModelSerializer):
    target_service_name = serializers.CharField(
        source="target_service.name", read_only=True, default=None
    )

    class Meta:
        model = QuickAction
        fields = [
            "id", "name", "description", "action_type", "target_service",
            "target_service_name", "is_enabled", "icon", "color", "created_at",
        ]
        read_only_fields = ["created_at"]


class ActionExecutionSerializer(serializers.ModelSerializer):
    action_name = serializers.CharField(source="action.name", read_only=True)
    duration = serializers.ReadOnlyField()

    class Meta:
        model = ActionExecution
        fields = [
            "id", "action", "action_name", "user", "status", "output",
            "started_at", "completed_at", "duration",
        ]
        read_only_fields = ["started_at"]
