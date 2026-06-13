from datetime import date

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand

from myos_app.views import _get_reminder_store, _parse_date


class Command(BaseCommand):
    help = "Send due reminder notifications via email."

    def handle(self, *args, **options):
        today = date.today()
        lookahead_days = max(0, getattr(settings, "MYOS_REMINDER_EMAIL_LOOKAHEAD_DAYS", 1))
        recipient = getattr(settings, "MYOS_REMINDER_EMAIL_RECIPIENT", "") or getattr(settings, "MYOS_NOTIFICATION_EMAIL", "")
        _, store = _get_reminder_store()
        sent = 0

        for reminder in store["reminders"]:
            if reminder.get("is_completed"):
                continue

            channel = reminder.get("channel", "in_app")
            if channel != "email":
                continue

            reminder_date = _parse_date(reminder.get("reminder_date"))
            if not reminder_date:
                continue

            delta_days = (reminder_date - today).days
            if delta_days < 0 or delta_days > lookahead_days:
                continue

            if not recipient:
                self.stdout.write("MYOS_REMINDER_EMAIL_RECIPIENT not set. Skipping.")
                continue

            subject = f"MyOS Reminder: {reminder.get('title', 'Scheduled reminder')}"
            body_lines = [
                "MyOS Reminder",
                "",
                f"Title: {reminder.get('title', '')}",
                f"Scheduled: {reminder_date.strftime('%A, %B %d, %Y')}",
            ]
            reminder_time = reminder.get("reminder_time") or ""
            if reminder_time:
                body_lines.append(f"Time: {reminder_time}")
            body_lines.extend(
                [
                    f"Details: {reminder.get('details', 'No details provided.')}",
                    "",
                    "---",
                    "This reminder was set in your MyOS Personal Operating System.",
                    "Visit your dashboard: http://localhost:8000/",
                ]
            )
            body = "\n".join(body_lines)

            try:
                send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [recipient], fail_silently=False)
                sent += 1
                self.stdout.write(f"Sent: {reminder.get('title')}")
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"Failed to send {reminder.get('title')}: {exc}"))

        self.stdout.write(self.style.SUCCESS(f"Sent {sent} reminder emails."))
