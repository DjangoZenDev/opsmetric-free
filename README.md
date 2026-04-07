# OpsMetric Free

**Real-time Metrics Operations Dashboard — Free Edition**
*By DjangoZen - https://djangozen.com*

This is the **free version** of OpsMetric. It includes core functionality to help you evaluate the product.

## Free Features
- Service status grid with health indicators
- Server metrics overview (CPU, memory, disk)
- Incident management and tracking
- Public status page with uptime bars

## Pro Features (Upgrade Required)
- Live KPI cards with 5-second polling
- Threshold alert system with custom rules
- Interactive trend charts (response time, server metrics, incidents)
- Live log viewer with 3-second tailing
- Quick actions for common operations
- User presence tracking
- Alert management and acknowledgment

**Upgrade to OpsMetric Pro:** https://djangozen.com

## Quick Start

1. Create virtual environment:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run migrations and seed data:
```bash
python manage.py migrate
python manage.py seed_data
```

4. Start server:
```bash
python manage.py runserver
```

5. Login: **admin** / **admin**

---
*Free version by DjangoZen. Upgrade to Pro at https://djangozen.com*
*Copyright 2026 DjangoZen. All Rights Reserved.*
