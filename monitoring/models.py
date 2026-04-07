from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Service(models.Model):
    STATUS_CHOICES = [
        ("operational", "Operational"),
        ("degraded", "Degraded"),
        ("partial_outage", "Partial Outage"),
        ("major_outage", "Major Outage"),
    ]

    CATEGORY_CHOICES = [
        ("infrastructure", "Infrastructure"),
        ("application", "Application"),
        ("database", "Database"),
        ("cache", "Cache"),
        ("external", "External"),
    ]

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True, default="")
    url = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="operational")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="application")
    uptime_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    last_checked = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def status_color(self):
        return {
            "operational": "#10b981",
            "degraded": "#f59e0b",
            "partial_outage": "#f97316",
            "major_outage": "#ef4444",
        }.get(self.status, "#6b7280")

    @property
    def status_bg_class(self):
        return {
            "operational": "bg-emerald-500",
            "degraded": "bg-yellow-500",
            "partial_outage": "bg-orange-500",
            "major_outage": "bg-red-500",
        }.get(self.status, "bg-gray-500")


class HealthCheck(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="health_checks")
    response_time_ms = models.IntegerField(default=0)
    status_code = models.IntegerField(default=200)
    is_healthy = models.BooleanField(default=True)
    checked_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-checked_at"]

    def __str__(self):
        return f"{self.service.name} - {self.checked_at:%Y-%m-%d %H:%M}"


class Incident(models.Model):
    SEVERITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    STATUS_CHOICES = [
        ("investigating", "Investigating"),
        ("identified", "Identified"),
        ("monitoring", "Monitoring"),
        ("resolved", "Resolved"),
    ]

    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default="medium")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="investigating")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="incidents")
    started_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return self.title

    @property
    def severity_color(self):
        return {
            "low": "bg-blue-500",
            "medium": "bg-yellow-500",
            "high": "bg-orange-500",
            "critical": "bg-red-500",
        }.get(self.severity, "bg-gray-500")

    @property
    def duration(self):
        end = self.resolved_at or timezone.now()
        delta = end - self.started_at
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

    @property
    def is_active(self):
        return self.status != "resolved"


class IncidentUpdate(models.Model):
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name="updates")
    message = models.TextField()
    status = models.CharField(max_length=20, choices=Incident.STATUS_CHOICES)
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.CharField(max_length=150, blank=True, default="System")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Update on {self.incident.title} at {self.created_at:%H:%M}"


class ServerMetric(models.Model):
    hostname = models.CharField(max_length=200)
    cpu_percent = models.FloatField(default=0)
    memory_percent = models.FloatField(default=0)
    disk_percent = models.FloatField(default=0)
    network_in = models.BigIntegerField(default=0, help_text="Bytes received")
    network_out = models.BigIntegerField(default=0, help_text="Bytes sent")
    load_average = models.FloatField(default=0)
    process_count = models.IntegerField(default=0)
    uptime_seconds = models.BigIntegerField(default=0)
    recorded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-recorded_at"]

    def __str__(self):
        return f"{self.hostname} - {self.recorded_at:%Y-%m-%d %H:%M}"

    @property
    def network_in_display(self):
        return self._format_bytes(self.network_in)

    @property
    def network_out_display(self):
        return self._format_bytes(self.network_out)

    @property
    def uptime_display(self):
        days = self.uptime_seconds // 86400
        hours = (self.uptime_seconds % 86400) // 3600
        return f"{days}d {hours}h"

    @staticmethod
    def _format_bytes(num_bytes):
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if abs(num_bytes) < 1024.0:
                return f"{num_bytes:.1f} {unit}"
            num_bytes /= 1024.0
        return f"{num_bytes:.1f} PB"


class AlertRule(models.Model):
    METRIC_TYPE_CHOICES = [
        ("response_time", "Response Time (ms)"),
        ("uptime", "Uptime (%)"),
        ("cpu", "CPU Usage (%)"),
        ("memory", "Memory Usage (%)"),
        ("disk", "Disk Usage (%)"),
    ]

    OPERATOR_CHOICES = [
        ("gt", "Greater than"),
        ("lt", "Less than"),
        ("gte", "Greater or equal"),
        ("lte", "Less or equal"),
        ("eq", "Equal to"),
    ]

    name = models.CharField(max_length=200)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="alert_rules", null=True, blank=True)
    metric_type = models.CharField(max_length=20, choices=METRIC_TYPE_CHOICES)
    operator = models.CharField(max_length=5, choices=OPERATOR_CHOICES, default="gt")
    threshold = models.FloatField()
    severity = models.CharField(max_length=10, choices=Incident.SEVERITY_CHOICES, default="medium")
    is_active = models.BooleanField(default=True)
    last_triggered = models.DateTimeField(null=True, blank=True)
    cooldown_minutes = models.IntegerField(default=15)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        svc = self.service.name if self.service else "All"
        return f"{self.name} ({svc}: {self.get_metric_type_display()} {self.get_operator_display()} {self.threshold})"

    @property
    def can_trigger(self):
        if not self.is_active:
            return False
        if not self.last_triggered:
            return True
        return timezone.now() - self.last_triggered > timedelta(minutes=self.cooldown_minutes)

    def evaluate(self, current_value):
        ops = {
            "gt": lambda v, t: v > t,
            "lt": lambda v, t: v < t,
            "gte": lambda v, t: v >= t,
            "lte": lambda v, t: v <= t,
            "eq": lambda v, t: v == t,
        }
        return ops.get(self.operator, lambda v, t: False)(current_value, self.threshold)


class Alert(models.Model):
    rule = models.ForeignKey(AlertRule, on_delete=models.CASCADE, related_name="alerts")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="alerts", null=True, blank=True)
    message = models.CharField(max_length=500)
    severity = models.CharField(max_length=10, choices=Incident.SEVERITY_CHOICES, default="medium")
    current_value = models.FloatField(default=0)
    threshold_value = models.FloatField(default=0)
    is_acknowledged = models.BooleanField(default=False)
    triggered_at = models.DateTimeField(auto_now_add=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ["-triggered_at"]

    def __str__(self):
        return f"[{self.severity}] {self.message}"


class SystemLog(models.Model):
    LEVEL_CHOICES = [
        ("debug", "Debug"),
        ("info", "Info"),
        ("warning", "Warning"),
        ("error", "Error"),
        ("critical", "Critical"),
    ]

    source = models.CharField(max_length=200)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default="info")
    message = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"[{self.level.upper()}] {self.source}: {self.message[:80]}"

    @property
    def level_color(self):
        return {
            "debug": "text-gray-400",
            "info": "text-blue-400",
            "warning": "text-yellow-400",
            "error": "text-orange-400",
            "critical": "text-red-400",
        }.get(self.level, "text-gray-400")

    @property
    def level_bg(self):
        return {
            "debug": "bg-gray-800",
            "info": "bg-blue-900/30",
            "warning": "bg-yellow-900/30",
            "error": "bg-orange-900/30",
            "critical": "bg-red-900/30",
        }.get(self.level, "bg-gray-800")


class QuickAction(models.Model):
    ACTION_TYPE_CHOICES = [
        ("restart_service", "Restart Service"),
        ("clear_cache", "Clear Cache"),
        ("run_health_check", "Run Health Check"),
        ("scale_up", "Scale Up"),
        ("flush_logs", "Flush Logs"),
        ("custom", "Custom Command"),
    ]

    name = models.CharField(max_length=200)
    description = models.CharField(max_length=500, blank=True, default="")
    action_type = models.CharField(max_length=20, choices=ACTION_TYPE_CHOICES)
    target_service = models.ForeignKey(
        Service, on_delete=models.SET_NULL, null=True, blank=True, related_name="quick_actions"
    )
    is_enabled = models.BooleanField(default=True)
    icon = models.CharField(max_length=50, default="bolt")
    color = models.CharField(max_length=20, default="emerald")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ActionExecution(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    action = models.ForeignKey(QuickAction, on_delete=models.CASCADE, related_name="executions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    output = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.action.name} - {self.get_status_display()}"

    @property
    def duration(self):
        if self.completed_at and self.started_at:
            delta = self.completed_at - self.started_at
            return f"{delta.total_seconds():.1f}s"
        return "..."


class UserPresence(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="presence"
    )
    last_seen = models.DateTimeField(auto_now=True)
    current_page = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        verbose_name_plural = "User presences"

    def __str__(self):
        return f"{self.user.username} - {'online' if self.is_online else 'offline'}"

    @property
    def is_online(self):
        return (timezone.now() - self.last_seen).total_seconds() < 60
