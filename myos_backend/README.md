# MyOS Backend

Production-oriented Django backend for MyOS with:
- Custom user model + JWT auth
- OTP verification flow
- Modular domain apps
- DRF APIs + server-rendered template support
- Service-layer business logic
- Security middleware, audit logs, and encrypted sensitive fields

## Quick Start

1. Create venv and install dependencies.
2. Copy `.env.example` to `.env` and configure values.
3. Run migrations and start server:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Recommended from repo root:

```bash
./scripts/bootstrap_backend.sh
./scripts/check_backend_runtime.sh
./scripts/run_backend_api.sh
```

## Apps
- `users`
- `projects`
- `finance`
- `diary`
- `media`
- `bucket`
- `notifications`
- `api`
- `common`
- `education`
- `events`
