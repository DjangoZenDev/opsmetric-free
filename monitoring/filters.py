import django_filters

from .models import Alert, AlertRule, HealthCheck, Incident, ServerMetric, Service, SystemLog


class ServiceFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=Service.STATUS_CHOICES)
    name = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Service
        fields = ["status", "name"]


class HealthCheckFilter(django_filters.FilterSet):
    service = django_filters.NumberFilter(field_name="service__id")
    is_healthy = django_filters.BooleanFilter()
    checked_after = django_filters.DateTimeFilter(field_name="checked_at", lookup_expr="gte")
    checked_before = django_filters.DateTimeFilter(field_name="checked_at", lookup_expr="lte")

    class Meta:
        model = HealthCheck
        fields = ["service", "is_healthy"]


class IncidentFilter(django_filters.FilterSet):
    severity = django_filters.ChoiceFilter(choices=Incident.SEVERITY_CHOICES)
    status = django_filters.ChoiceFilter(choices=Incident.STATUS_CHOICES)
    service = django_filters.NumberFilter(field_name="service__id")
    active = django_filters.BooleanFilter(method="filter_active")

    class Meta:
        model = Incident
        fields = ["severity", "status", "service"]

    def filter_active(self, queryset, name, value):
        if value:
            return queryset.exclude(status="resolved")
        return queryset.filter(status="resolved")


class ServerMetricFilter(django_filters.FilterSet):
    hostname = django_filters.CharFilter(lookup_expr="icontains")
    recorded_after = django_filters.DateTimeFilter(field_name="recorded_at", lookup_expr="gte")
    recorded_before = django_filters.DateTimeFilter(field_name="recorded_at", lookup_expr="lte")

    class Meta:
        model = ServerMetric
        fields = ["hostname"]


class AlertFilter(django_filters.FilterSet):
    severity = django_filters.ChoiceFilter(choices=Alert._meta.get_field("severity").choices)
    is_acknowledged = django_filters.BooleanFilter()
    service = django_filters.NumberFilter(field_name="service__id")

    class Meta:
        model = Alert
        fields = ["severity", "is_acknowledged", "service"]


class AlertRuleFilter(django_filters.FilterSet):
    metric_type = django_filters.ChoiceFilter(choices=AlertRule.METRIC_TYPE_CHOICES)
    severity = django_filters.ChoiceFilter(choices=AlertRule._meta.get_field("severity").choices)
    is_active = django_filters.BooleanFilter()
    service = django_filters.NumberFilter(field_name="service__id")

    class Meta:
        model = AlertRule
        fields = ["metric_type", "severity", "is_active", "service"]


class SystemLogFilter(django_filters.FilterSet):
    level = django_filters.ChoiceFilter(choices=SystemLog.LEVEL_CHOICES)
    source = django_filters.CharFilter(lookup_expr="icontains")
    timestamp_after = django_filters.DateTimeFilter(field_name="timestamp", lookup_expr="gte")
    timestamp_before = django_filters.DateTimeFilter(field_name="timestamp", lookup_expr="lte")

    class Meta:
        model = SystemLog
        fields = ["level", "source"]
