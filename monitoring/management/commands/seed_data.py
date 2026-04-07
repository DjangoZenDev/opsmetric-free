import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from monitoring.models import (
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


class Command(BaseCommand):
    help = "Seeds the database with sample monitoring data for OpsMetric Pro."

    def handle(self, *args, **options):
        self.stdout.write("Seeding OpsMetric Pro database...")

        # Clear existing data
        SystemLog.objects.all().delete()
        ActionExecution.objects.all().delete()
        QuickAction.objects.all().delete()
        Alert.objects.all().delete()
        AlertRule.objects.all().delete()
        UserPresence.objects.all().delete()
        ServerMetric.objects.all().delete()
        IncidentUpdate.objects.all().delete()
        Incident.objects.all().delete()
        HealthCheck.objects.all().delete()
        Service.objects.all().delete()

        # Create superuser
        if not User.objects.filter(username="admin").exists():
            admin_user = User.objects.create_superuser(
                username="admin", email="admin@opsmetric.io", password="admin",
                first_name="Admin", last_name="User",
            )
            self.stdout.write(self.style.SUCCESS("  Created superuser: admin / admin"))
        else:
            admin_user = User.objects.get(username="admin")

        # Create operator users
        operators = [admin_user]
        for uname, first, last in [("ops.lead", "Sarah", "Chen"), ("sre.eng", "Mike", "Johnson")]:
            u, created = User.objects.get_or_create(
                username=uname,
                defaults={"first_name": first, "last_name": last, "email": f"{uname}@opsmetric.io"},
            )
            if created:
                u.set_password("operator123")
                u.save()
            operators.append(u)
        self.stdout.write(self.style.SUCCESS("  Created operator users"))

        now = timezone.now()

        # ── Services ──
        services_data = [
            {"name": "API Gateway", "slug": "api-gateway", "url": "https://api.opsmetric.io", "status": "operational", "uptime": 99.98, "category": "infrastructure", "description": "Main API gateway handling all incoming requests"},
            {"name": "Web Application", "slug": "web-application", "url": "https://app.opsmetric.io", "status": "operational", "uptime": 99.95, "category": "application", "description": "Primary web application frontend"},
            {"name": "Database Cluster", "slug": "database-cluster", "url": "https://db.opsmetric.io", "status": "operational", "uptime": 99.99, "category": "database", "description": "PostgreSQL primary + replicas"},
            {"name": "Auth Service", "slug": "auth-service", "url": "https://auth.opsmetric.io", "status": "degraded", "uptime": 98.50, "category": "application", "description": "Authentication and authorization service"},
            {"name": "CDN / Assets", "slug": "cdn-assets", "url": "https://cdn.opsmetric.io", "status": "operational", "uptime": 99.97, "category": "infrastructure", "description": "Content delivery network for static assets"},
            {"name": "Email Service", "slug": "email-service", "url": "https://mail.opsmetric.io", "status": "operational", "uptime": 99.80, "category": "external", "description": "Transactional email delivery"},
            {"name": "Search Engine", "slug": "search-engine", "url": "https://search.opsmetric.io", "status": "partial_outage", "uptime": 95.20, "category": "application", "description": "Elasticsearch cluster for full-text search"},
            {"name": "Payment Processing", "slug": "payment-processing", "url": "https://pay.opsmetric.io", "status": "operational", "uptime": 99.99, "category": "external", "description": "Stripe payment processing integration"},
            {"name": "Message Queue", "slug": "message-queue", "url": "https://mq.opsmetric.io", "status": "operational", "uptime": 99.90, "category": "infrastructure", "description": "RabbitMQ message broker"},
            {"name": "Redis Cache", "slug": "redis-cache", "url": "https://cache.opsmetric.io", "status": "operational", "uptime": 99.95, "category": "cache", "description": "Redis caching layer"},
        ]

        services = []
        for sd in services_data:
            svc = Service.objects.create(
                name=sd["name"], slug=sd["slug"], url=sd["url"],
                status=sd["status"], uptime_percentage=Decimal(str(sd["uptime"])),
                category=sd["category"], description=sd["description"],
                last_checked=now - timedelta(seconds=random.randint(10, 300)),
            )
            services.append(svc)
        self.stdout.write(self.style.SUCCESS(f"  Created {len(services)} services"))

        # ── Health Checks (24h) ──
        hc_count = 0
        for svc in services:
            is_degraded = svc.status in ("degraded", "partial_outage", "major_outage")
            for i in range(48):
                check_time = now - timedelta(minutes=i * 30, seconds=random.randint(0, 59))
                if is_degraded:
                    rt = random.randint(300, 3000)
                    healthy = random.random() > 0.3
                    code = 200 if healthy else random.choice([500, 502, 503])
                else:
                    rt = random.randint(15, 250)
                    healthy = random.random() > 0.02
                    code = 200 if healthy else 500
                HealthCheck.objects.create(
                    service=svc, response_time_ms=rt, status_code=code,
                    is_healthy=healthy, checked_at=check_time,
                )
                hc_count += 1
        self.stdout.write(self.style.SUCCESS(f"  Created {hc_count} health checks"))

        # ── Incidents ──
        incidents_data = [
            {
                "title": "Elevated latency on Auth Service", "service": services[3],
                "severity": "medium", "status": "identified",
                "started": now - timedelta(hours=2, minutes=15),
                "updates": [
                    ("investigating", "Reports of slow auth responses", -135),
                    ("identified", "Connection pool exhaustion on auth-db-02", -90),
                ],
            },
            {
                "title": "Search Engine partial failure", "service": services[6],
                "severity": "high", "status": "monitoring",
                "started": now - timedelta(hours=5, minutes=45),
                "updates": [
                    ("investigating", "Search query failures reported", -345),
                    ("identified", "Corrupted shard on search-node-03", -240),
                    ("monitoring", "Shard rebuild at 85%", -60),
                ],
            },
            {
                "title": "CDN cache invalidation delay", "service": services[4],
                "severity": "low", "status": "resolved",
                "started": now - timedelta(days=1, hours=3),
                "resolved": now - timedelta(days=1, hours=1),
                "updates": [
                    ("investigating", "Stale cache headers detected", -1620),
                    ("resolved", "Force-purged CDN cache", -1500),
                ],
            },
            {
                "title": "Database replication lag spike", "service": services[2],
                "severity": "critical", "status": "resolved",
                "started": now - timedelta(days=3),
                "resolved": now - timedelta(days=3) + timedelta(hours=4),
                "updates": [
                    ("investigating", "Replication lag >30s", -4320),
                    ("identified", "Large batch write bottleneck", -4260),
                    ("monitoring", "Batch throttled, lag decreasing", -4200),
                    ("resolved", "Replication lag normal (<1s)", -4080),
                ],
            },
        ]
        for inc_data in incidents_data:
            inc = Incident.objects.create(
                title=inc_data["title"], service=inc_data["service"],
                severity=inc_data["severity"], status=inc_data["status"],
                started_at=inc_data["started"], resolved_at=inc_data.get("resolved"),
            )
            for status, msg, offset_min in inc_data["updates"]:
                IncidentUpdate.objects.create(
                    incident=inc, message=msg, status=status,
                    created_at=now + timedelta(minutes=offset_min),
                    created_by=random.choice(operators).get_full_name(),
                )
        self.stdout.write(self.style.SUCCESS(f"  Created {len(incidents_data)} incidents"))

        # ── Server Metrics (24h, every 5 min) ──
        hostnames = [
            ("prod-web-01", 25, 55, 42), ("prod-web-02", 30, 60, 42),
            ("prod-web-03", 20, 50, 42), ("prod-api-01", 45, 70, 38),
            ("prod-api-02", 40, 65, 38), ("prod-db-01", 15, 80, 65),
            ("prod-db-02", 12, 75, 62), ("prod-cache-01", 8, 30, 15),
        ]
        sm_count = 0
        for hostname, base_cpu, base_mem, base_disk in hostnames:
            for i in range(288):
                ts = now - timedelta(minutes=i * 5)
                ServerMetric.objects.create(
                    hostname=hostname,
                    cpu_percent=round(max(0, min(100, base_cpu + random.uniform(-10, 15))), 1),
                    memory_percent=round(max(0, min(100, base_mem + random.uniform(-5, 10))), 1),
                    disk_percent=round(max(0, min(100, base_disk + random.uniform(-1, 2))), 1),
                    network_in=random.randint(100_000_000, 5_000_000_000),
                    network_out=random.randint(50_000_000, 3_000_000_000),
                    load_average=round(random.uniform(0.5, 4.0), 2),
                    process_count=random.randint(80, 350),
                    uptime_seconds=random.randint(86400, 8640000),
                    recorded_at=ts,
                )
                sm_count += 1
        self.stdout.write(self.style.SUCCESS(f"  Created {sm_count} server metrics"))

        # ── Alert Rules ──
        rules = [
            AlertRule.objects.create(name="High API Response Time", service=services[0], metric_type="response_time", operator="gt", threshold=500, severity="medium", cooldown_minutes=15),
            AlertRule.objects.create(name="Auth Response Critical", service=services[3], metric_type="response_time", operator="gt", threshold=2000, severity="critical", cooldown_minutes=5),
            AlertRule.objects.create(name="CPU Warning", metric_type="cpu", operator="gt", threshold=80, severity="high", cooldown_minutes=10),
            AlertRule.objects.create(name="Memory Critical", metric_type="memory", operator="gt", threshold=90, severity="critical", cooldown_minutes=5),
            AlertRule.objects.create(name="Disk Warning", metric_type="disk", operator="gt", threshold=85, severity="medium", cooldown_minutes=30),
            AlertRule.objects.create(name="Uptime Degraded", metric_type="uptime", operator="lt", threshold=99.5, severity="high", cooldown_minutes=60),
        ]
        self.stdout.write(self.style.SUCCESS(f"  Created {len(rules)} alert rules"))

        # ── Alerts ──
        alerts = [
            (rules[1], services[3], "Auth Service response time 2450ms > 2000ms threshold", "critical", 2450, 2000, False),
            (rules[0], services[0], "API Gateway response time 650ms > 500ms threshold", "medium", 650, 500, False),
            (rules[5], services[6], "Search Engine uptime 95.2% < 99.5% threshold", "high", 95.2, 99.5, False),
            (rules[5], services[3], "Auth Service uptime 98.5% < 99.5% threshold", "high", 98.5, 99.5, True),
            (rules[2], None, "prod-db-01 CPU at 82% > 80% threshold", "high", 82, 80, True),
        ]
        for i, (rule, svc, msg, sev, val, thresh, acked) in enumerate(alerts):
            Alert.objects.create(
                rule=rule, service=svc, message=msg, severity=sev,
                current_value=val, threshold_value=thresh,
                is_acknowledged=acked,
                triggered_at=now - timedelta(hours=i * 2, minutes=random.randint(0, 59)),
                acknowledged_at=(now - timedelta(hours=1)) if acked else None,
                acknowledged_by=admin_user if acked else None,
            )
        self.stdout.write(self.style.SUCCESS(f"  Created {len(alerts)} alerts"))

        # ── Quick Actions ──
        actions = [
            ("Restart API Gateway", "Gracefully restart the API gateway", "restart_service", services[0], "bolt", "emerald"),
            ("Clear Redis Cache", "Flush all Redis cache entries", "clear_cache", services[9], "trash", "amber"),
            ("Run Health Checks", "Execute health checks on all services", "run_health_check", None, "heart", "blue"),
            ("Scale Web Servers", "Add a web server instance", "scale_up", services[0], "arrow-up", "violet"),
            ("Flush System Logs", "Archive and clear old logs", "flush_logs", None, "archive", "gray"),
            ("Restart Auth Service", "Restart authentication service", "restart_service", services[3], "refresh", "orange"),
        ]
        for name, desc, atype, svc, icon, color in actions:
            QuickAction.objects.create(name=name, description=desc, action_type=atype, target_service=svc, icon=icon, color=color)
        self.stdout.write(self.style.SUCCESS(f"  Created {len(actions)} quick actions"))

        # ── System Logs ──
        log_sources = ["api-gateway", "web-app", "auth-service", "db-cluster", "search-engine", "scheduler", "deploy-bot", "monitor"]
        log_templates = [
            ("info", "Request processed in {ms}ms"),
            ("info", "Health check passed for {service}"),
            ("info", "Cache hit ratio: {pct}%"),
            ("info", "Deployment v2.{v1}.{v2} completed"),
            ("warning", "Response time elevated: {ms}ms"),
            ("warning", "Connection pool at {pct}% capacity"),
            ("warning", "Memory at {pct}% on {host}"),
            ("error", "Health check failed: {service} timeout"),
            ("error", "Database connection refused on {host}"),
            ("error", "Payment webhook failed: HTTP 502"),
            ("critical", "Service {service} is DOWN"),
            ("critical", "Disk at 95% on {host}"),
            ("debug", "Query executed in {ms}ms"),
            ("debug", "Cache miss for key: session:{id}"),
            ("info", "Backup completed: {size}MB compressed"),
            ("info", "Auto-scaling: adding web instance"),
        ]
        for i in range(200):
            source = random.choice(log_sources)
            level, msg_tpl = random.choice(log_templates)
            msg = msg_tpl.format(
                ms=random.randint(10, 5000), service=random.choice([s.name for s in services]),
                pct=random.randint(50, 99), v1=random.randint(1, 9), v2=random.randint(0, 20),
                host=random.choice([h[0] for h in hostnames]),
                id=random.randint(10000, 99999), size=random.randint(100, 900),
            )
            SystemLog.objects.create(
                source=source, level=level, message=msg,
                metadata={"source_ip": f"10.0.{random.randint(1, 10)}.{random.randint(1, 254)}"},
                timestamp=now - timedelta(minutes=i * 3, seconds=random.randint(0, 59)),
            )
        self.stdout.write(self.style.SUCCESS("  Created 200 system log entries"))

        # ── User Presence ──
        for user in operators:
            UserPresence.objects.update_or_create(
                user=user, defaults={"current_page": "/", "last_seen": now - timedelta(seconds=random.randint(0, 30))},
            )
        self.stdout.write(self.style.SUCCESS(f"  Created {len(operators)} user presences"))

        self.stdout.write(self.style.SUCCESS("\nOpsMetric Pro seeding complete!"))
        self.stdout.write("Login: admin / admin")
        self.stdout.write("Operators: ops.lead / operator123, sre.eng / operator123")
