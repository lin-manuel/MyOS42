from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("education", "0002_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CollegeApplication",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("university_name", models.CharField(max_length=220)),
                ("program", models.CharField(max_length=220)),
                ("degree_level", models.CharField(choices=[("bachelor", "Bachelor's"), ("master", "Master's"), ("phd", "PhD"), ("mba", "MBA"), ("diploma", "Diploma"), ("certificate", "Certificate")], default="bachelor", max_length=24)),
                ("country", models.CharField(blank=True, default="", max_length=120)),
                ("deadline", models.DateField(blank=True, null=True)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("status", models.CharField(choices=[("researching", "Researching"), ("applied", "Applied"), ("interview", "Interview"), ("offer_received", "Offer Received"), ("accepted", "Accepted"), ("rejected", "Rejected"), ("withdrawn", "Withdrawn"), ("deferred", "Deferred")], default="researching", max_length=24)),
                ("portal_url", models.URLField(blank=True, default="")),
                ("application_ref", models.CharField(blank=True, default="", max_length=120)),
                ("tuition_fee", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, validators=[django.core.validators.MinValueValidator(Decimal("0.00"))])),
                ("acceptance_rate", models.FloatField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(100.0)])),
                ("qs_rank", models.PositiveIntegerField(blank=True, null=True)),
                ("personal_statement_status", models.CharField(choices=[("not_started", "Not Started"), ("draft", "Draft"), ("reviewed", "Reviewed"), ("final", "Final")], default="not_started", max_length=24)),
                ("rec_letters_required", models.PositiveIntegerField(default=0)),
                ("rec_letters_collected", models.PositiveIntegerField(default=0)),
                ("notes", models.TextField(blank=True, default="")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="college_applications", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["deadline", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="LearningResource",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=180)),
                ("resource_type", models.CharField(choices=[("book", "Book"), ("course", "Course"), ("podcast", "Podcast"), ("youtube", "YouTube"), ("mentor", "Mentor"), ("tool", "Tool"), ("other", "Other")], default="book", max_length=24)),
                ("status", models.CharField(choices=[("active", "Active"), ("paused", "Paused"), ("archived", "Archived")], default="active", max_length=24)),
                ("url", models.URLField(blank=True, default="")),
                ("rating", models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ("last_reviewed", models.DateField(blank=True, null=True)),
                ("notes", models.TextField(blank=True, default="")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="learning_resources", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="WeeklyReflection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("week_ending", models.DateField()),
                ("what_learned", models.TextField(blank=True, default="")),
                ("went_well", models.TextField(blank=True, default="")),
                ("to_improve", models.TextField(blank=True, default="")),
                ("next_week_focus", models.TextField(blank=True, default="")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="weekly_reflections", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-week_ending"],
            },
        ),
        migrations.CreateModel(
            name="CollegeEssay",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("prompt", models.TextField()),
                ("word_limit", models.PositiveIntegerField(blank=True, null=True)),
                ("status", models.CharField(choices=[("not_started", "Not Started"), ("drafting", "Drafting"), ("reviewing", "Reviewing"), ("final", "Final")], default="not_started", max_length=24)),
                ("draft_content", models.TextField(blank=True, default="")),
                ("application", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="essays", to="education.collegeapplication")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="college_essays", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-updated_at"],
            },
        ),
    ]
