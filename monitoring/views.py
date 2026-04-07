from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count
from django.db.models.functions import TruncDate
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (
    ActionExecution,
    Alert,
    AlertRule,
    HealthCheck,
    Incident,
    QuickAction,
    ServerMetric,
    Service,
    SystemLog,
    UserPresence,
)


# ---------------------------------------------------------------------------
# Helper: compute KPI data
# ---------------------------------------------------------------------------

def _compute_kpis():
    now = timezone.now()
    one_hour_ago = now - timedelta(hours=1)

    total_services = Service.objects.count()
    healthy_count = Service.objects.filter(status="operational").count()
    healthy_pct = (healthy_count / total_services * 100) if total_services else 100

    active_incidents_count = Incident.objects.exclude(status="resolved").count()
    unacknowledged_alerts_count = Alert.objects.filter(is_acknowledged=False).count()

    avg_response_time = (
        HealthCheck.objects.filter(checked_at__gte=one_hour_ago)
        .aggregate(avg=Avg("response_time_ms"))["avg"]
    ) or 0
    avg_response_time = round(avg_response_time, 1)

    # Health score: services health 40%, no incidents 30%, response time 30%
    services_score = healthy_pct  # 0-100
    incident_score = 100 if active_incidents_count == 0 else max(0, 100 - active_incidents_count * 20)
    # Response time score: 0ms=100, >=2000ms=0
    response_score = max(0, min(100, 100 - (avg_response_time / 2000) * 100))

    system_health_score = round(
        services_score * 0.4 + incident_score * 0.3 + response_score * 0.3
    )
    system_health_score = max(0, min(100, system_health_score))

    return {
        "total_services": total_services,
        "healthy_count": healthy_count,
        "healthy_pct": round(healthy_pct, 1),
        "active_incidents_count": active_incidents_count,
        "avg_response_time": avg_response_time,
        "unacknowledged_alerts_count": unacknowledged_alerts_count,
        "system_health_score": system_health_score,
    }


# ---------------------------------------------------------------------------
# Existing views (preserved)
# ---------------------------------------------------------------------------

@login_required
def ops_dashboard(request):
    services = Service.objects.all()
    active_incidents = Incident.objects.exclude(status="resolved").select_related("service")
    all_operational = not services.exclude(status="operational").exists()

    if services.filter(status="major_outage").exists():
        overall_status = "Major Outage"
        overall_class = "bg-red-500"
    elif services.filter(status="partial_outage").exists():
        overall_status = "Partial Outage"
        overall_class = "bg-orange-500"
    elif services.filter(status="degraded").exists():
        overall_status = "Degraded Performance"
        overall_class = "bg-yellow-500"
    else:
        overall_status = "All Systems Operational"
        overall_class = "bg-emerald-500"

    hostnames = ServerMetric.objects.values_list("hostname", flat=True).distinct()
    latest_metrics = []
    for hostname in hostnames:
        metric = ServerMetric.objects.filter(hostname=hostname).first()
        if metric:
            latest_metrics.append(metric)

    kpis = _compute_kpis()

    context = {
        "services": services,
        "active_incidents": active_incidents,
        "all_operational": all_operational,
        "overall_status": overall_status,
        "overall_class": overall_class,
        "server_metrics": latest_metrics,
        "now": timezone.now(),
        **kpis,
    }
    return render(request, "monitoring/dashboard.html", context)


@login_required
def service_status_grid(request):
    services = Service.objects.all()
    return render(request, "monitoring/partials/service_grid.html", {"services": services})


@login_required
def server_metrics(request):
    hostnames = ServerMetric.objects.values_list("hostname", flat=True).distinct()
    latest_metrics = []
    for hostname in hostnames:
        metric = ServerMetric.objects.filter(hostname=hostname).first()
        if metric:
            latest_metrics.append(metric)
    return render(request, "monitoring/partials/server_gauges.html", {"server_metrics": latest_metrics})


@login_required
def incident_timeline(request):
    active_incidents = Incident.objects.exclude(status="resolved").select_related("service")
    return render(request, "monitoring/partials/incident_list.html", {"active_incidents": active_incidents})


@login_required
def incident_detail(request, pk):
    incident = get_object_or_404(
        Incident.objects.select_related("service").prefetch_related("updates"),
        pk=pk,
    )
    return render(request, "monitoring/incident_detail.html", {"incident": incident})


@login_required
def health_history(request):
    services = Service.objects.all()
    service_health = []
    for service in services:
        checks = (
            HealthCheck.objects.filter(service=service)
            .order_by("-checked_at")[:20]
        )
        checks_list = list(reversed(checks))
        avg_response = checks.aggregate(avg=Avg("response_time_ms"))["avg"] or 0
        service_health.append({
            "service": service,
            "checks": checks_list,
            "avg_response_time": round(avg_response),
        })
    return render(request, "monitoring/partials/health_sparkline.html", {"service_health": service_health})


@login_required
def servers_page(request):
    hostnames = ServerMetric.objects.values_list("hostname", flat=True).distinct()
    latest_metrics = []
    for hostname in hostnames:
        metric = ServerMetric.objects.filter(hostname=hostname).first()
        if metric:
            latest_metrics.append(metric)
    return render(request, "monitoring/servers.html", {"server_metrics": latest_metrics})


@login_required
def incidents_page(request):
    active_incidents = Incident.objects.exclude(status="resolved").select_related("service")
    return render(request, "monitoring/incidents.html", {
        "active_incidents": active_incidents,
    })


@login_required
def history_page(request):
    resolved_incidents = Incident.objects.filter(status="resolved").select_related("service").order_by("-resolved_at")
    all_incidents = Incident.objects.all().select_related("service").order_by("-started_at")
    return render(request, "monitoring/history.html", {
        "resolved_incidents": resolved_incidents,
        "all_incidents": all_incidents,
    })


def status_page(request):
    services = Service.objects.all()
    active_incidents = Incident.objects.exclude(status="resolved").select_related("service")
    recent_incidents = Incident.objects.filter(status="resolved").select_related("service")[:10]

    all_operational = not services.exclude(status="operational").exists()

    if services.filter(status="major_outage").exists():
        overall_status = "Major Outage"
        overall_class = "bg-red-500"
        overall_text_class = "text-red-400"
    elif services.filter(status="partial_outage").exists():
        overall_status = "Partial Outage"
        overall_class = "bg-orange-500"
        overall_text_class = "text-orange-400"
    elif services.filter(status="degraded").exists():
        overall_status = "Degraded Performance"
        overall_class = "bg-yellow-500"
        overall_text_class = "text-yellow-400"
    else:
        overall_status = "All Systems Operational"
        overall_class = "bg-emerald-500"
        overall_text_class = "text-emerald-400"

    context = {
        "services": services,
        "active_incidents": active_incidents,
        "recent_incidents": recent_incidents,
        "all_operational": all_operational,
        "overall_status": overall_status,
        "overall_class": overall_class,
        "overall_text_class": overall_text_class,
        "now": timezone.now(),
    }
    return render(request, "monitoring/status_page.html", context)


# ---------------------------------------------------------------------------
# New HTMX partial views
# ---------------------------------------------------------------------------

@login_required
def live_kpis(request):
    kpis = _compute_kpis()
    return render(request, "monitoring/partials/live_kpis.html", kpis)


@login_required
def system_health(request):
    kpis = _compute_kpis()
    return render(request, "monitoring/partials/system_health.html", {
        "system_health_score": kpis["system_health_score"],
    })


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

@login_required
def alerts_page(request):
    alerts_qs = Alert.objects.select_related("rule", "service").all()
    severity = request.GET.get("severity")
    if severity:
        alerts_qs = alerts_qs.filter(severity=severity)
    paginator = Paginator(alerts_qs, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "monitoring/alerts.html", {
        "page_obj": page_obj,
        "severity_filter": severity,
        "severity_choices": [("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")],
    })


@login_required
def alerts_partial(request):
    alerts = Alert.objects.select_related("rule", "service").filter(is_acknowledged=False)[:10]
    return render(request, "monitoring/partials/alerts_panel.html", {"alerts": alerts})


@login_required
@require_POST
def acknowledge_alert(request, pk):
    alert = get_object_or_404(Alert, pk=pk)
    alert.is_acknowledged = True
    alert.acknowledged_at = timezone.now()
    alert.acknowledged_by = request.user
    alert.save()
    alerts = Alert.objects.select_related("rule", "service").filter(is_acknowledged=False)[:10]
    return render(request, "monitoring/partials/alerts_panel.html", {"alerts": alerts})


# ---------------------------------------------------------------------------
# Alert Rules
# ---------------------------------------------------------------------------

@login_required
def alert_rules_page(request):
    rules = AlertRule.objects.select_related("service").all()
    services = Service.objects.all()
    return render(request, "monitoring/alert_rules.html", {
        "rules": rules,
        "services": services,
        "metric_type_choices": AlertRule.METRIC_TYPE_CHOICES,
        "operator_choices": AlertRule.OPERATOR_CHOICES,
        "severity_choices": [("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")],
    })


@login_required
@require_POST
def create_alert_rule(request):
    service_id = request.POST.get("service")
    service = Service.objects.filter(pk=service_id).first() if service_id else None
    AlertRule.objects.create(
        name=request.POST.get("name", ""),
        service=service,
        metric_type=request.POST.get("metric_type", "response_time"),
        operator=request.POST.get("operator", "gt"),
        threshold=float(request.POST.get("threshold", 0)),
        severity=request.POST.get("severity", "medium"),
        cooldown_minutes=int(request.POST.get("cooldown_minutes", 15)),
    )
    return redirect("alert_rules_page")


@login_required
@require_POST
def delete_alert_rule(request, pk):
    rule = get_object_or_404(AlertRule, pk=pk)
    rule.delete()
    return redirect("alert_rules_page")


# ---------------------------------------------------------------------------
# Threshold checking
# ---------------------------------------------------------------------------

@login_required
def check_thresholds(request):
    now = timezone.now()
    rules = AlertRule.objects.filter(is_active=True).select_related("service")
    alerts_created = []

    for rule in rules:
        if not rule.can_trigger:
            continue

        current_value = None

        if rule.metric_type == "response_time":
            qs = HealthCheck.objects.all()
            if rule.service:
                qs = qs.filter(service=rule.service)
            latest = qs.first()
            if latest:
                current_value = float(latest.response_time_ms)

        elif rule.metric_type == "uptime":
            if rule.service:
                current_value = float(rule.service.uptime_percentage)
            else:
                avg = Service.objects.aggregate(avg=Avg("uptime_percentage"))["avg"]
                current_value = float(avg) if avg is not None else None

        elif rule.metric_type in ("cpu", "memory", "disk"):
            field_map = {"cpu": "cpu_percent", "memory": "memory_percent", "disk": "disk_percent"}
            field = field_map[rule.metric_type]
            latest = ServerMetric.objects.first()
            if latest:
                current_value = float(getattr(latest, field))

        if current_value is not None and rule.evaluate(current_value):
            svc_name = rule.service.name if rule.service else "All services"
            alert = Alert.objects.create(
                rule=rule,
                service=rule.service,
                message=f"{rule.name}: {svc_name} {rule.get_metric_type_display()} is {current_value} "
                        f"({rule.get_operator_display()} {rule.threshold})",
                severity=rule.severity,
                current_value=current_value,
                threshold_value=rule.threshold,
            )
            rule.last_triggered = now
            rule.save(update_fields=["last_triggered"])
            alerts_created.append({
                "rule": rule.name,
                "alert_id": alert.pk,
                "current_value": current_value,
                "threshold": rule.threshold,
            })

    return JsonResponse({"alerts_created": alerts_created, "total": len(alerts_created)})


# ---------------------------------------------------------------------------
# Charts (JSON endpoints)
# ---------------------------------------------------------------------------

@login_required
def chart_response_times_all(request):
    """Aggregate response times across all services (last 24h)."""
    since = timezone.now() - timedelta(hours=24)
    checks = (
        HealthCheck.objects.filter(checked_at__gte=since)
        .order_by("checked_at")
        .values_list("checked_at", "response_time_ms")
    )
    data = {
        "labels": [c[0].strftime("%H:%M") for c in checks],
        "values": [c[1] for c in checks],
    }
    return JsonResponse(data)


@login_required
def chart_server_history_all(request):
    """Aggregate server metrics across first hostname (last 24h)."""
    since = timezone.now() - timedelta(hours=24)
    hostname = ServerMetric.objects.values_list("hostname", flat=True).first()
    if not hostname:
        return JsonResponse({"labels": [], "cpu": [], "memory": [], "disk": []})
    metrics = (
        ServerMetric.objects.filter(hostname=hostname, recorded_at__gte=since)
        .order_by("recorded_at")
        .values_list("recorded_at", "cpu_percent", "memory_percent", "disk_percent")
    )
    data = {
        "labels": [m[0].strftime("%H:%M") for m in metrics],
        "cpu": [m[1] for m in metrics],
        "memory": [m[2] for m in metrics],
        "disk": [m[3] for m in metrics],
    }
    return JsonResponse(data)


@login_required
def chart_response_times(request, slug):
    service = get_object_or_404(Service, slug=slug)
    since = timezone.now() - timedelta(hours=24)
    checks = (
        HealthCheck.objects.filter(service=service, checked_at__gte=since)
        .order_by("checked_at")
        .values_list("checked_at", "response_time_ms")
    )
    data = {
        "labels": [c[0].isoformat() for c in checks],
        "values": [c[1] for c in checks],
    }
    return JsonResponse(data)


@login_required
def chart_server_history(request, hostname):
    since = timezone.now() - timedelta(hours=24)
    metrics = (
        ServerMetric.objects.filter(hostname=hostname, recorded_at__gte=since)
        .order_by("recorded_at")
        .values_list("recorded_at", "cpu_percent", "memory_percent", "disk_percent")
    )
    data = {
        "labels": [m[0].isoformat() for m in metrics],
        "cpu": [m[1] for m in metrics],
        "memory": [m[2] for m in metrics],
        "disk": [m[3] for m in metrics],
    }
    return JsonResponse(data)


@login_required
def chart_incident_frequency(request):
    since = timezone.now() - timedelta(days=30)
    daily = (
        Incident.objects.filter(started_at__gte=since)
        .annotate(date=TruncDate("started_at"))
        .values("date")
        .annotate(count=Count("id"))
        .order_by("date")
    )
    data = {
        "labels": [entry["date"].isoformat() for entry in daily],
        "values": [entry["count"] for entry in daily],
    }
    return JsonResponse(data)


# ---------------------------------------------------------------------------
# Quick Actions
# ---------------------------------------------------------------------------

@login_required
def quick_actions_panel(request):
    actions = QuickAction.objects.filter(is_enabled=True)
    return render(request, "monitoring/partials/quick_actions.html", {"actions": actions})


@login_required
@require_POST
def execute_action(request, pk):
    action = get_object_or_404(QuickAction, pk=pk)
    now = timezone.now()

    # Simulated output per action type
    output_map = {
        "restart_service": "Service restarted successfully",
        "clear_cache": "Cache cleared (245 entries)",
        "run_health_check": "Health check completed: all endpoints responding",
        "scale_up": "Scaled up to 3 instances successfully",
        "flush_logs": "Flushed 1,247 log entries",
        "custom": "Custom command executed successfully",
    }
    output = output_map.get(action.action_type, "Action completed")

    execution = ActionExecution.objects.create(
        action=action,
        user=request.user,
        status="success",
        output=output,
        completed_at=now,
    )
    return render(request, "monitoring/partials/action_result.html", {"execution": execution})


@login_required
def action_status(request, pk):
    execution = get_object_or_404(ActionExecution, pk=pk)
    return render(request, "monitoring/partials/action_result.html", {"execution": execution})


# ---------------------------------------------------------------------------
# Log Viewer
# ---------------------------------------------------------------------------

@login_required
def log_viewer(request):
    return render(request, "monitoring/log_viewer.html")


@login_required
def log_stream(request):
    logs_qs = SystemLog.objects.all()
    level = request.GET.get("level")
    if level:
        logs_qs = logs_qs.filter(level=level)
    logs = logs_qs[:50]
    return render(request, "monitoring/partials/log_entries.html", {"logs": logs})


# ---------------------------------------------------------------------------
# Presence
# ---------------------------------------------------------------------------

@login_required
@require_POST
def update_presence(request):
    current_page = request.POST.get("current_page", "")
    UserPresence.objects.update_or_create(
        user=request.user,
        defaults={"current_page": current_page},
    )
    return HttpResponse(status=204)


@login_required
def online_users(request):
    threshold = timezone.now() - timedelta(seconds=60)
    presences = UserPresence.objects.filter(last_seen__gte=threshold).select_related("user")
    return render(request, "monitoring/partials/online_users.html", {"presences": presences})
