from datetime import date, timedelta

from django.core.management.base import BaseCommand

from myos_app.models import RecurringExpenseTemplate, Transaction


def add_months(current_date, months):
    month = current_date.month - 1 + months
    year = current_date.year + month // 12
    month = month % 12 + 1
    day = min(
        current_date.day,
        [
            31,
            29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
            31,
            30,
            31,
            30,
            31,
            31,
            30,
            31,
            30,
            31,
        ][month - 1],
    )
    return date(year, month, day)


class Command(BaseCommand):
    help = "Auto-generate transactions for recurring expense templates that are due."

    def handle(self, *args, **options):
        today = date.today()
        generated = 0

        for template in RecurringExpenseTemplate.objects.select_related("category").filter(is_active=True):
            while template.next_due_date <= today:
                if template.end_date and template.next_due_date > template.end_date:
                    template.is_active = False
                    template.save(update_fields=["is_active", "updated_at"])
                    break

                Transaction.objects.create(
                    tx_date=template.next_due_date,
                    description=f"Recurring: {template.name}",
                    category=template.category,
                    account=template.account,
                    tx_type=Transaction.TYPE_EXPENSE,
                    amount=template.amount,
                    tags=["recurring", template.cadence],
                    notes="Auto-generated from recurring template",
                )
                generated += 1

                if template.cadence == RecurringExpenseTemplate.CADENCE_WEEKLY:
                    template.next_due_date += timedelta(days=7)
                elif template.cadence == RecurringExpenseTemplate.CADENCE_YEARLY:
                    template.next_due_date = add_months(template.next_due_date, 12)
                else:
                    template.next_due_date = add_months(template.next_due_date, 1)

                template.save(update_fields=["next_due_date", "updated_at"])

        self.stdout.write(self.style.SUCCESS(f"Generated {generated} recurring transactions."))
