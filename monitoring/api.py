from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .filters import (
    AlertFilter,
    AlertRuleFilter,
    HealthCheckFilter,
    IncidentFilter,
    ServerMetricFilter,
    ServiceFilter,
    SystemLogFilter,
)
from .models import (
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
from .serializers import (
    AlertRuleSerializer,
    AlertSerializer,
    HealthCheckSerializer,
    IncidentSerializer,
    IncidentUpdateSerializer,
    QuickActionSerializer,
    ServerMetricSerializer,
    ServiceSerializer,
    SystemLogSerializer,
)


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    filterset_class = ServiceFilter
    search_fields = ["name", "slug"]
    ordering_fields = ["name", "status", "uptime_percentage", "last_checked"]
    lookup_field = "slug"

    @action(detail=True, methods=["get"])
    def health_checks(self, request, slug=None):
        service = self.get_object()
        checks = HealthCheck.objects.filter(service=service)[:50]
        serializer = HealthCheckSerializer(checks, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def incidents(self, request, slug=None):
        service = self.get_object()
        incidents = Incident.objects.filter(service=service)
        serializer = IncidentSerializer(incidents, many=True)
        return Response(serializer.data)


class HealthCheckViewSet(viewsets.ModelViewSet):
    queryset = HealthCheck.objects.select_related("service").all()
    serializer_class = HealthCheckSerializer
    filterset_class = HealthCheckFilter
    ordering_fields = ["checked_at", "response_time_ms"]


class IncidentViewSet(viewsets.ModelViewSet):
    queryset = Incident.objects.select_related("service").prefetch_related("updates").all()
    serializer_class = IncidentSerializer
    filterset_class = IncidentFilter
    search_fields = ["title", "description"]
    ordering_fields = ["started_at", "severity", "status"]

    @action(detail=True, methods=["post"])
    def add_update(self, request, pk=None):
        incident = self.get_object()
        serializer = IncidentUpdateSerializer(data={
            "incident": incident.pk,
            "message": request.data.get("message", ""),
            "status": request.data.get("status", incident.status),
            "created_by": request.data.get("created_by", "API"),
        })
        serializer.is_valid(raise_exception=True)
        serializer.save()

        if request.data.get("status"):
            incident.status = request.data["status"]
            if request.data["status"] == "resolved":
                from django.utils import timezone
                incident.resolved_at = timezone.now()
            incident.save()

        return Response(IncidentSerializer(incident).data)


class ServerMetricViewSet(viewsets.ModelViewSet):
    queryset = ServerMetric.objects.all()
    serializer_class = ServerMetricSerializer
    filterset_class = ServerMetricFilter
    search_fields = ["hostname"]
    ordering_fields = ["recorded_at", "cpu_percent", "memory_percent", "disk_percent"]

    @action(detail=False, methods=["get"])
    def latest(self, request):
        hostnames = ServerMetric.objects.values_list("hostname", flat=True).distinct()
        latest = []
        for hostname in hostnames:
            metric = ServerMetric.objects.filter(hostname=hostname).first()
            if metric:
                latest.append(metric)
        serializer = self.get_serializer(latest, many=True)
        return Response(serializer.data)


class AlertRuleViewSet(viewsets.ModelViewSet):
    queryset = AlertRule.objects.all()
    serializer_class = AlertRuleSerializer
    filterset_class = AlertRuleFilter
    search_fields = ["name"]
    ordering_fields = ["created_at", "severity", "metric_type"]


class AlertViewSet(viewsets.ModelViewSet):
    queryset = Alert.objects.select_related("rule", "service", "acknowledged_by").all()
    serializer_class = AlertSerializer
    filterset_class = AlertFilter
    search_fields = ["message"]
    ordering_fields = ["triggered_at", "severity", "is_acknowledged"]

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        alert = self.get_object()
        from django.utils import timezone as tz
        alert.is_acknowledged = True
        alert.acknowledged_at = tz.now()
        alert.acknowledged_by = request.user if request.user.is_authenticated else None
        alert.save()
        return Response(AlertSerializer(alert).data)


class SystemLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SystemLog.objects.all()
    serializer_class = SystemLogSerializer
    filterset_class = SystemLogFilter
    search_fields = ["message", "source"]
    ordering_fields = ["timestamp", "level"]


class QuickActionViewSet(viewsets.ModelViewSet):
    queryset = QuickAction.objects.all()
    serializer_class = QuickActionSerializer
    search_fields = ["name"]
    ordering_fields = ["name", "action_type", "created_at"]
