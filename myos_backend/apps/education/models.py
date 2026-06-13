from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.models import TimeStampedModel


def education_document_path(instance, filename):
    return f"education/user_{instance.user_id}/{filename}"


class EducationRecord(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="education_records")
    level = models.CharField(max_length=120)
    institution = models.CharField(max_length=180)
    start_year = models.PositiveIntegerField()
    end_year = models.PositiveIntegerField(null=True, blank=True)
    grade = models.CharField(max_length=60, blank=True, default="")
    study_hours = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-start_year", "-created_at"]

    def __str__(self):
        return f"{self.level} @ {self.institution}"


class Scholarship(TimeStampedModel):
    STATUS_DISCOVERED = "discovered"
    STATUS_APPLIED = "applied"
    STATUS_AWARDED = "awarded"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = (
        (STATUS_DISCOVERED, "Discovered"),
        (STATUS_APPLIED, "Applied"),
        (STATUS_AWARDED, "Awarded"),
        (STATUS_REJECTED, "Rejected"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="scholarships")
    name = models.CharField(max_length=180)
    country = models.CharField(max_length=120)
    deadline = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DISCOVERED)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["deadline", "-created_at"]

    def __str__(self):
        return self.name


class EducationDocument(TimeStampedModel):
    TYPE_TRANSCRIPT = "transcript"
    TYPE_CERTIFICATE = "certificate"
    TYPE_IDENTITY = "identity"
    TYPE_OTHER = "other"

    TYPE_CHOICES = (
        (TYPE_TRANSCRIPT, "Transcript"),
        (TYPE_CERTIFICATE, "Certificate"),
        (TYPE_IDENTITY, "Identity"),
        (TYPE_OTHER, "Other"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="education_documents")
    title = models.CharField(max_length=180)
    document_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    version = models.CharField(max_length=40, blank=True, default="v1")
    file = models.FileField(upload_to=education_document_path)
    expires_at = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["title", "-created_at"]

    def __str__(self):
        return self.title


class CollegeApplication(TimeStampedModel):
    STATUS_RESEARCHING = "researching"
    STATUS_APPLIED = "applied"
    STATUS_INTERVIEW = "interview"
    STATUS_OFFER_RECEIVED = "offer_received"
    STATUS_ACCEPTED = "accepted"
    STATUS_REJECTED = "rejected"
    STATUS_WITHDRAWN = "withdrawn"
    STATUS_DEFERRED = "deferred"

    STATUS_CHOICES = (
        (STATUS_RESEARCHING, "Researching"),
        (STATUS_APPLIED, "Applied"),
        (STATUS_INTERVIEW, "Interview"),
        (STATUS_OFFER_RECEIVED, "Offer Received"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_WITHDRAWN, "Withdrawn"),
        (STATUS_DEFERRED, "Deferred"),
    )

    DEGREE_BACHELOR = "bachelor"
    DEGREE_MASTER = "master"
    DEGREE_PHD = "phd"
    DEGREE_MBA = "mba"
    DEGREE_DIPLOMA = "diploma"
    DEGREE_CERTIFICATE = "certificate"

    DEGREE_LEVEL_CHOICES = (
        (DEGREE_BACHELOR, "Bachelor's"),
        (DEGREE_MASTER, "Master's"),
        (DEGREE_PHD, "PhD"),
        (DEGREE_MBA, "MBA"),
        (DEGREE_DIPLOMA, "Diploma"),
        (DEGREE_CERTIFICATE, "Certificate"),
    )

    PERSONAL_STATEMENT_NOT_STARTED = "not_started"
    PERSONAL_STATEMENT_DRAFT = "draft"
    PERSONAL_STATEMENT_REVIEWED = "reviewed"
    PERSONAL_STATEMENT_FINAL = "final"

    PERSONAL_STATEMENT_STATUS_CHOICES = (
        (PERSONAL_STATEMENT_NOT_STARTED, "Not Started"),
        (PERSONAL_STATEMENT_DRAFT, "Draft"),
        (PERSONAL_STATEMENT_REVIEWED, "Reviewed"),
        (PERSONAL_STATEMENT_FINAL, "Final"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="college_applications")
    university_name = models.CharField(max_length=220)
    program = models.CharField(max_length=220)
    degree_level = models.CharField(max_length=24, choices=DEGREE_LEVEL_CHOICES, default=DEGREE_BACHELOR)
    country = models.CharField(max_length=120, blank=True, default="")
    deadline = models.DateField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=STATUS_RESEARCHING)
    portal_url = models.URLField(blank=True, default="")
    application_ref = models.CharField(max_length=120, blank=True, default="")
    tuition_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    acceptance_rate = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
    )
    qs_rank = models.PositiveIntegerField(null=True, blank=True)
    personal_statement_status = models.CharField(
        max_length=24,
        choices=PERSONAL_STATEMENT_STATUS_CHOICES,
        default=PERSONAL_STATEMENT_NOT_STARTED,
    )
    rec_letters_required = models.PositiveIntegerField(default=0)
    rec_letters_collected = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["deadline", "-created_at"]

    def __str__(self):
        return f"{self.program} @ {self.university_name}"


class CollegeEssay(TimeStampedModel):
    STATUS_NOT_STARTED = "not_started"
    STATUS_DRAFTING = "drafting"
    STATUS_REVIEWING = "reviewing"
    STATUS_FINAL = "final"

    STATUS_CHOICES = (
        (STATUS_NOT_STARTED, "Not Started"),
        (STATUS_DRAFTING, "Drafting"),
        (STATUS_REVIEWING, "Reviewing"),
        (STATUS_FINAL, "Final"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="college_essays")
    application = models.ForeignKey(CollegeApplication, on_delete=models.CASCADE, related_name="essays")
    prompt = models.TextField()
    word_limit = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=STATUS_NOT_STARTED)
    draft_content = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Essay for {self.application}"


class LearningResource(TimeStampedModel):
    TYPE_BOOK = "book"
    TYPE_COURSE = "course"
    TYPE_PODCAST = "podcast"
    TYPE_YOUTUBE = "youtube"
    TYPE_MENTOR = "mentor"
    TYPE_TOOL = "tool"
    TYPE_OTHER = "other"

    TYPE_CHOICES = (
        (TYPE_BOOK, "Book"),
        (TYPE_COURSE, "Course"),
        (TYPE_PODCAST, "Podcast"),
        (TYPE_YOUTUBE, "YouTube"),
        (TYPE_MENTOR, "Mentor"),
        (TYPE_TOOL, "Tool"),
        (TYPE_OTHER, "Other"),
    )

    STATUS_ACTIVE = "active"
    STATUS_PAUSED = "paused"
    STATUS_ARCHIVED = "archived"

    STATUS_CHOICES = (
        (STATUS_ACTIVE, "Active"),
        (STATUS_PAUSED, "Paused"),
        (STATUS_ARCHIVED, "Archived"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="learning_resources")
    name = models.CharField(max_length=180)
    resource_type = models.CharField(max_length=24, choices=TYPE_CHOICES, default=TYPE_BOOK)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    url = models.URLField(blank=True, default="")
    rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    last_reviewed = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class WeeklyReflection(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="weekly_reflections")
    week_ending = models.DateField()
    what_learned = models.TextField(blank=True, default="")
    went_well = models.TextField(blank=True, default="")
    to_improve = models.TextField(blank=True, default="")
    next_week_focus = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-week_ending"]

    def __str__(self):
        return f"Reflection w/e {self.week_ending}"
