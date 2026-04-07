from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import api, views

router = DefaultRouter()
router.register(r"services", api.ServiceViewSet)
router.register(r"health-checks", api.HealthCheckViewSet)
router.register(r"incidents", api.IncidentViewSet)
router.register(r"server-metrics", api.ServerMetricViewSet)
router.register(r"alert-rules", api.AlertRuleViewSet)
router.register(r"alerts", api.AlertViewSet)
router.register(r"system-logs", api.SystemLogViewSet)
router.register(r"quick-actions", api.QuickActionViewSet)

urlpatterns = [
    # Existing pages
    path("", views.ops_dashboard, name="dashboard"),
    path("servers/", views.servers_page, name="servers_page"),
    path("incidents/", views.incidents_page, name="incidents_page"),
    path("history/", views.history_page, name="history_page"),
    path("status/", views.status_page, name="status_page"),
    path("incidents/<int:pk>/", views.incident_detail, name="incident_detail"),

    # Existing HTMX partials
    path("partials/service-grid/", views.service_status_grid, name="service_grid"),
    path("partials/server-metrics/", views.server_metrics, name="server_metrics"),
    path("partials/incidents/", views.incident_timeline, name="incident_timeline"),
    path("partials/health-history/", views.health_history, name="health_history"),

    # New KPI / health partials
    path("partials/live-kpis/", views.live_kpis, name="live_kpis"),
    path("partials/system-health/", views.system_health, name="system_health"),

    # Alerts
    path("alerts/", views.alerts_page, name="alerts_page"),
    path("partials/alerts/", views.alerts_partial, name="alerts_partial"),
    path("alerts/<int:pk>/acknowledge/", views.acknowledge_alert, name="acknowledge_alert"),

    # Alert Rules
    path("alert-rules/", views.alert_rules_page, name="alert_rules_page"),
    path("alert-rules/create/", views.create_alert_rule, name="create_alert_rule"),
    path("alert-rules/<int:pk>/delete/", views.delete_alert_rule, name="delete_alert_rule"),

    # Threshold checking
    path("check-thresholds/", views.check_thresholds, name="check_thresholds"),

    # Charts (JSON)
    path("charts/response-times/", views.chart_response_times_all, name="chart_response_times_all"),
    path("charts/response-times/<slug:slug>/", views.chart_response_times, name="chart_response_times"),
    path("charts/server-history/", views.chart_server_history_all, name="chart_server_history_all"),
    path("charts/server-history/<str:hostname>/", views.chart_server_history, name="chart_server_history"),
    path("charts/incident-frequency/", views.chart_incident_frequency, name="chart_incident_frequency"),

    # Quick Actions
    path("partials/quick-actions/", views.quick_actions_panel, name="quick_actions_panel"),
    path("actions/<int:pk>/execute/", views.execute_action, name="execute_action"),
    path("actions/<int:pk>/status/", views.action_status, name="action_status"),

    # Log Viewer
    path("logs/", views.log_viewer, name="log_viewer"),
    path("partials/log-stream/", views.log_stream, name="log_stream"),

    # Presence
    path("presence/update/", views.update_presence, name="update_presence"),
    path("partials/online-users/", views.online_users, name="online_users"),

    # API
    path("api/", include(router.urls)),
]
