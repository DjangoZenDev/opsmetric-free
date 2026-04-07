from django.contrib import admin

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
    UserPresence,
)


class HealthCheckInline(admin.TabularInline):
    model = HealthCheck
    extra = 0
    readonly_fields = ("checked_at",)


class IncidentUpdateInline(admin.StackedInline):
    model = IncidentUpdate
    extra = 0


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "uptime_percentage", "last_checked")
    list_filter = ("status",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [HealthCheckInline]


@admin.register(HealthCheck)
class HealthCheckAdmin(admin.ModelAdmin):
    list_display = ("service", "response_time_ms", "status_code", "is_healthy", "checked_at")
    list_filter = ("is_healthy", "service")
    date_hierarchy = "checked_at"


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ("title", "severity", "status", "service", "started_at", "resolved_at")
    list_filter = ("severity", "status", "service")
    search_fields = ("title", "description")
    inlines = [IncidentUpdateInline]


@admin.register(IncidentUpdate)
class IncidentUpdateAdmin(admin.ModelAdmin):
    list_display = ("incident", "status", "created_by", "created_at")
    list_filter = ("status",)


@admin.register(ServerMetric)
class ServerMetricAdmin(admin.ModelAdmin):
    list_display = ("hostname", "cpu_percent", "memory_percent", "disk_percent", "recorded_at")
    list_filter = ("hostname",)
    date_hierarchy = "recorded_at"


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "metric_type", "operator", "threshold", "severity", "is_active", "last_triggered")
    list_filter = ("metric_type", "severity", "is_active")
    search_fields = ("name",)


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("message", "severity", "rule", "service", "is_acknowledged", "triggered_at")
    list_filter = ("severity", "is_acknowledged", "service")
    search_fields = ("message",)
    date_hierarchy = "triggered_at"


@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ("source", "level", "message", "timestamp")
    list_filter = ("level", "source")
    search_fields = ("message", "source")
    date_hierarchy = "timestamp"


@admin.register(QuickAction)
class QuickActionAdmin(admin.ModelAdmin):
    list_display = ("name", "action_type", "target_service", "is_enabled")
    list_filter = ("action_type", "is_enabled")
    search_fields = ("name",)


@admin.register(ActionExecution)
class ActionExecutionAdmin(admin.ModelAdmin):
    list_display = ("action", "user", "status", "started_at", "completed_at")
    list_filter = ("status", "action")
    date_hierarchy = "started_at"


@admin.register(UserPresence)
class UserPresenceAdmin(admin.ModelAdmin):
    list_display = ("user", "last_seen", "current_page")
    search_fields = ("user__username",)
