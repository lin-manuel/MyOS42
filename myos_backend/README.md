# MyOS Backend

Production-oriented Django backend for MyOS with:
- Custom user model + JWT auth
- OTP verification flow
- Modular domain apps
- DRF APIs + server-rendered template support
- Service-layer business logic
- Security middleware, audit logs, and encrypted sensitive fields

## Quick Start

This is the API/backend Django project. The server-rendered web application is a separate Django project in `../myos_project`.

For a local SQLite setup from this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Generate a private Django secret and Fernet key, then replace `DJANGO_SECRET_KEY` and `FERNET_KEY` in `.env`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Then initialize and run the backend:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The sample environment uses SQLite for a simple local run. To use the provided PostgreSQL container instead, configure `.env` and start the compose stack:

```bash
docker compose up --build
```

Compose supplies its own PostgreSQL connection settings; set a private `DJANGO_SECRET_KEY` and `FERNET_KEY` in `.env` before using it with real data. The sample `myos/myos` database credentials are only for the local Compose database.

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
