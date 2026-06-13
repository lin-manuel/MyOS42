from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify


class UserProfile(models.Model):
    display_name = models.CharField(max_length=120, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    timezone = models.CharField(max_length=80, default="UTC")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name


class NotificationPreference(models.Model):
    scholarship_deadlines = models.BooleanField(default=True)
    task_due_alerts = models.BooleanField(default=True)
    diary_prompt = models.BooleanField(default=False)
    finance_alerts = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Notification Preferences"


class Task(models.Model):
    title = models.CharField(max_length=255)
    is_done = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.title


class DiaryEntry(models.Model):
    entry_date = models.DateField()
    mood = models.CharField(max_length=80, blank=True, default="")
    content = models.TextField(blank=True, default="")
    achievements = models.TextField(blank=True, default="")
    lessons = models.TextField(blank=True, default="")
    ideas = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-entry_date", "-id"]

    def __str__(self):
        return f"{self.entry_date} - {self.mood or 'No mood'}"


class PageFormData(models.Model):
    page_slug = models.CharField(max_length=50, unique=True)
    data = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["page_slug"]

    def __str__(self):
        return self.page_slug


def uploaded_document_path(instance, filename):
    safe_page = (instance.page_slug or "general").replace("/", "_")
    safe_key = (instance.field_key or "files").replace("/", "_")
    return f"uploads/{safe_page}/{safe_key}/{filename}"


class UploadedDocument(models.Model):
    page_slug = models.CharField(max_length=50, db_index=True)
    field_key = models.CharField(max_length=80, db_index=True)
    label = models.CharField(max_length=120, blank=True, default="")
    file = models.FileField(upload_to=uploaded_document_path)
    original_name = models.CharField(max_length=255, blank=True, default="")
    content_type = models.CharField(max_length=120, blank=True, default="")
    file_size = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at", "-id"]

    def __str__(self):
        return f"{self.page_slug}:{self.field_key}:{self.original_name or self.file.name}"


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BucketGoal(TimeStampedModel):
    CATEGORY_TRAVEL = "travel"
    CATEGORY_LEARNING = "learning"
    CATEGORY_WEALTH = "wealth"
    CATEGORY_EXPERIENCES = "experiences"
    CATEGORY_ACHIEVEMENTS = "achievements"
    CATEGORY_CHOICES = (
        (CATEGORY_TRAVEL, "Travel"),
        (CATEGORY_LEARNING, "Learning"),
        (CATEGORY_WEALTH, "Wealth"),
        (CATEGORY_EXPERIENCES, "Experiences"),
        (CATEGORY_ACHIEVEMENTS, "Achievements"),
    )

    STATUS_NOT_STARTED = "not_started"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"

    STATUS_CHOICES = (
        (STATUS_NOT_STARTED, "Not Started"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_COMPLETED, "Completed"),
    )

    PRIORITY_LOW = "low"
    PRIORITY_NORMAL = "normal"
    PRIORITY_HIGH = "high"

    PRIORITY_CHOICES = (
        (PRIORITY_LOW, "Low"),
        (PRIORITY_NORMAL, "Normal"),
        (PRIORITY_HIGH, "High"),
    )

    title = models.CharField(max_length=200)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, default=CATEGORY_EXPERIENCES)
    description = models.TextField(blank=True, default="")
    target_year = models.PositiveIntegerField(null=True, blank=True)
    estimated_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_NOT_STARTED)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default=PRIORITY_NORMAL)
    progress = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    class Meta:
        ordering = ["-updated_at", "-id"]

    def __str__(self):
        return self.title


class Category(TimeStampedModel):
    KIND_INCOME = "income"
    KIND_EXPENSE = "expense"
    KIND_SAVINGS = "savings"
    KIND_APPLICATION = "application"
    KIND_BUSINESS = "business"
    KIND_INVESTMENT = "investment"
    KIND_TRANSFER = "transfer"
    KIND_OTHER = "other"

    KIND_CHOICES = (
        (KIND_INCOME, "Income"),
        (KIND_EXPENSE, "Expense"),
        (KIND_SAVINGS, "Savings"),
        (KIND_APPLICATION, "Application"),
        (KIND_BUSINESS, "Business"),
        (KIND_INVESTMENT, "Investment"),
        (KIND_TRANSFER, "Transfer"),
        (KIND_OTHER, "Other"),
    )

    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=90, unique=True)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default=KIND_EXPENSE)
    color = models.CharField(max_length=16, default="#8B5A2B")
    icon = models.CharField(max_length=40, default="fa-wallet")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class SavingsGoal(TimeStampedModel):
    STATUS_ACTIVE = "active"
    STATUS_COMPLETED = "completed"
    STATUS_PAUSED = "paused"

    STATUS_CHOICES = (
        (STATUS_ACTIVE, "Active"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_PAUSED, "Paused"),
    )

    name = models.CharField(max_length=120)
    target_amount = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    starting_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))])
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    monthly_target_suggestion = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))])

    class Meta:
        ordering = ["deadline", "name"]

    def __str__(self):
        return self.name


class ApplicationCost(TimeStampedModel):
    TYPE_PASSPORT = "passport"
    TYPE_SAT = "sat"
    TYPE_IELTS = "ielts"
    TYPE_TOEFL = "toefl"
    TYPE_GOETHE = "goethe"
    TYPE_VISA = "visa"
    TYPE_CERTIFIED_DOCUMENTS = "certified_documents"
    TYPE_APPLICATION_FEES = "application_fees"
    TYPE_TRAVEL = "travel"
    TYPE_OTHER = "other"

    ITEM_TYPE_CHOICES = (
        (TYPE_PASSPORT, "Passport"),
        (TYPE_SAT, "SAT"),
        (TYPE_IELTS, "IELTS"),
        (TYPE_TOEFL, "TOEFL"),
        (TYPE_GOETHE, "Goethe"),
        (TYPE_VISA, "Visa"),
        (TYPE_CERTIFIED_DOCUMENTS, "Certified Documents"),
        (TYPE_APPLICATION_FEES, "Application Fees"),
        (TYPE_TRAVEL, "Travel"),
        (TYPE_OTHER, "Other"),
    )

    STATUS_PLANNED = "planned"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_PAID = "paid"
    STATUS_WAIVED = "waived"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = (
        (STATUS_PLANNED, "Planned"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_PAID, "Paid"),
        (STATUS_WAIVED, "Waived"),
        (STATUS_CANCELLED, "Cancelled"),
    )

    item_type = models.CharField(max_length=32, choices=ITEM_TYPE_CHOICES, default=TYPE_OTHER)
    estimated_cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))])
    actual_cost = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal("0.00"))])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PLANNED)
    deadline = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["deadline", "item_type"]

    def __str__(self):
        return self.get_item_type_display()


class ProjectBudget(TimeStampedModel):
    STATUS_ACTIVE = "active"
    STATUS_COMPLETED = "completed"
    STATUS_ON_HOLD = "on_hold"

    STATUS_CHOICES = (
        (STATUS_ACTIVE, "Active"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_ON_HOLD, "On Hold"),
    )

    project_name = models.CharField(max_length=160)
    budget_amount = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    manual_spent_adjustment = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))])
    roi_target_pct = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    roi_actual_pct = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)

    class Meta:
        ordering = ["project_name"]

    def __str__(self):
        return self.project_name


class Project(TimeStampedModel):
    STATUS_IDEA = "idea"
    STATUS_PENDING = "pending"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"

    STATUS_CHOICES = (
        (STATUS_IDEA, "Idea"),
        (STATUS_PENDING, "Pending"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_COMPLETED, "Completed"),
    )

    title = models.CharField(max_length=160)
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_IDEA)
    progress = models.PositiveSmallIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-updated_at", "-id"]

    def __str__(self):
        return self.title


class Transaction(TimeStampedModel):
    ACCOUNT_CASH = "cash"
    ACCOUNT_BANK = "bank"
    ACCOUNT_MOBILE_MONEY = "mobile_money"

    ACCOUNT_CHOICES = (
        (ACCOUNT_CASH, "Cash"),
        (ACCOUNT_BANK, "Bank"),
        (ACCOUNT_MOBILE_MONEY, "Mobile Money"),
    )

    TYPE_INCOME = "income"
    TYPE_EXPENSE = "expense"
    TYPE_TRANSFER = "transfer"
    TYPE_SAVINGS = "savings"

    TYPE_CHOICES = (
        (TYPE_INCOME, "Income"),
        (TYPE_EXPENSE, "Expense"),
        (TYPE_TRANSFER, "Transfer"),
        (TYPE_SAVINGS, "Savings"),
    )

    tx_date = models.DateField(db_index=True)
    description = models.CharField(max_length=220)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="transactions")
    account = models.CharField(max_length=20, choices=ACCOUNT_CHOICES, default=ACCOUNT_BANK)
    tx_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_EXPENSE)
    amount = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))], db_index=True)
    tags = models.JSONField(default=list, blank=True)
    savings_goal = models.ForeignKey("SavingsGoal", on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions")
    application_cost = models.ForeignKey("ApplicationCost", on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions")
    project_budget = models.ForeignKey("ProjectBudget", on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions")
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-tx_date", "-id"]
        indexes = [
            models.Index(fields=["tx_date", "category"]),
            models.Index(fields=["tx_date", "account"]),
        ]

    def __str__(self):
        return f"{self.tx_date} {self.description}"


class Budget(TimeStampedModel):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="budgets")
    period_start = models.DateField(db_index=True)
    monthly_limit = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    warning_threshold_pct = models.PositiveSmallIntegerField(default=90, validators=[MinValueValidator(1), MaxValueValidator(100)])
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-period_start", "category__name"]
        constraints = [
            models.UniqueConstraint(fields=["category", "period_start"], name="unique_budget_category_period"),
        ]

    def __str__(self):
        return f"{self.category.name} {self.period_start}"


class RecurringExpenseTemplate(TimeStampedModel):
    CADENCE_WEEKLY = "weekly"
    CADENCE_MONTHLY = "monthly"
    CADENCE_YEARLY = "yearly"

    CADENCE_CHOICES = (
        (CADENCE_WEEKLY, "Weekly"),
        (CADENCE_MONTHLY, "Monthly"),
        (CADENCE_YEARLY, "Yearly"),
    )

    name = models.CharField(max_length=140)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="recurring_templates")
    account = models.CharField(max_length=20, choices=Transaction.ACCOUNT_CHOICES, default=Transaction.ACCOUNT_BANK)
    amount = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    cadence = models.CharField(max_length=20, choices=CADENCE_CHOICES, default=CADENCE_MONTHLY)
    next_due_date = models.DateField(db_index=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["next_due_date", "name"]

    def __str__(self):
        return self.name


class FinanceAlert(TimeStampedModel):
    TYPE_BUDGET_OVERRUN = "budget_overrun"
    TYPE_DEADLINE = "deadline"
    TYPE_CASHFLOW = "cashflow"
    TYPE_GOAL_RISK = "goal_risk"

    ALERT_TYPE_CHOICES = (
        (TYPE_BUDGET_OVERRUN, "Budget Overrun"),
        (TYPE_DEADLINE, "Deadline"),
        (TYPE_CASHFLOW, "Cashflow"),
        (TYPE_GOAL_RISK, "Goal Risk"),
    )

    SEVERITY_INFO = "info"
    SEVERITY_WARNING = "warning"
    SEVERITY_CRITICAL = "critical"

    SEVERITY_CHOICES = (
        (SEVERITY_INFO, "Info"),
        (SEVERITY_WARNING, "Warning"),
        (SEVERITY_CRITICAL, "Critical"),
    )

    alert_type = models.CharField(max_length=32, choices=ALERT_TYPE_CHOICES)
    severity = models.CharField(max_length=16, choices=SEVERITY_CHOICES, default=SEVERITY_INFO)
    message = models.CharField(max_length=255)
    related_model = models.CharField(max_length=40, blank=True, default="")
    related_id = models.PositiveIntegerField(null=True, blank=True)
    period_key = models.CharField(max_length=20, default="")
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["alert_type", "related_model", "related_id", "period_key"],
                name="unique_finance_alert_scope",
            )
        ]

    def __str__(self):
        return self.message


def academic_file_upload_path(instance, filename):
    level = getattr(instance, "level_type", "general")
    return f"uploads/education/levels/{level}/{filename}"


def exam_file_upload_path(instance, filename):
    return f"uploads/education/exams/{instance.academic_level_id or 'general'}/{filename}"


def document_file_upload_path(instance, filename):
    return f"uploads/education/documents/{instance.document_type}/{filename}"


class AcademicLevel(TimeStampedModel):
    LEVEL_PRIMARY = "primary"
    LEVEL_SECONDARY = "secondary"
    LEVEL_UNIVERSITY = "university"
    LEVEL_CERTIFICATION = "certification"

    LEVEL_CHOICES = (
        (LEVEL_PRIMARY, "Primary School"),
        (LEVEL_SECONDARY, "Secondary School"),
        (LEVEL_UNIVERSITY, "University"),
        (LEVEL_CERTIFICATION, "Certifications / Courses"),
    )

    STATUS_COMPLETED = "completed"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_PLANNED = "planned"

    STATUS_CHOICES = (
        (STATUS_COMPLETED, "Completed"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_PLANNED, "Planned"),
    )

    level_type = models.CharField(max_length=24, choices=LEVEL_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PLANNED)
    school_name = models.CharField(max_length=180, blank=True, default="")
    admission_number = models.CharField(max_length=80, blank=True, default="")
    location = models.CharField(max_length=160, blank=True, default="")
    start_year = models.PositiveIntegerField(null=True, blank=True)
    end_year = models.PositiveIntegerField(null=True, blank=True)
    subjects_taken = models.TextField(blank=True, default="")
    grades = models.TextField(blank=True, default="")
    certification_exam_completed = models.BooleanField(default=False)
    certificate_file = models.FileField(upload_to=academic_file_upload_path, null=True, blank=True)

    # University and future-proof fields
    university_name = models.CharField(max_length=180, blank=True, default="")
    country = models.CharField(max_length=120, blank=True, default="")
    degree = models.CharField(max_length=120, blank=True, default="")
    major_program = models.CharField(max_length=180, blank=True, default="")
    expected_graduation_year = models.PositiveIntegerField(null=True, blank=True)
    student_number = models.CharField(max_length=80, blank=True, default="")
    gpa = models.CharField(max_length=20, blank=True, default="")
    transcript_file = models.FileField(upload_to=academic_file_upload_path, null=True, blank=True)
    research_topic = models.TextField(blank=True, default="")
    internships = models.TextField(blank=True, default="")
    clubs_activities = models.TextField(blank=True, default="")
    awards = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["level_type", "-updated_at", "-id"]

    def __str__(self):
        return f"{self.get_level_type_display()} - {self.school_name or 'Untitled'}"


class ExamCertification(TimeStampedModel):
    academic_level = models.ForeignKey(AcademicLevel, on_delete=models.CASCADE, related_name="exam_certifications")
    exam_name = models.CharField(max_length=120)
    exam_year = models.PositiveIntegerField(null=True, blank=True)
    candidate_number = models.CharField(max_length=80, blank=True, default="")
    grade_score = models.CharField(max_length=80, blank=True, default="")
    certificate_file = models.FileField(upload_to=exam_file_upload_path, null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-exam_year", "-updated_at", "-id"]

    def __str__(self):
        return f"{self.exam_name} ({self.exam_year or 'N/A'})"


class ApplicationDocument(TimeStampedModel):
    TYPE_PERSONAL_STATEMENT = "personal_statement"
    TYPE_CV = "cv_resume"
    TYPE_FINANCIAL_STATEMENT = "financial_statement"
    TYPE_TRANSCRIPT = "academic_transcript"
    TYPE_RECOMMENDATION = "recommendation_letter"
    TYPE_PASSPORT = "passport_copy"
    TYPE_CERTIFICATE = "certificate"
    TYPE_OTHER = "other"

    DOCUMENT_TYPE_CHOICES = (
        (TYPE_PERSONAL_STATEMENT, "Personal Statement"),
        (TYPE_CV, "CV / Resume"),
        (TYPE_FINANCIAL_STATEMENT, "Financial Statement"),
        (TYPE_TRANSCRIPT, "Academic Transcript"),
        (TYPE_RECOMMENDATION, "Recommendation Letter"),
        (TYPE_PASSPORT, "Passport Copy"),
        (TYPE_CERTIFICATE, "Certificate"),
        (TYPE_OTHER, "Other"),
    )

    title = models.CharField(max_length=180)
    document_type = models.CharField(max_length=32, choices=DOCUMENT_TYPE_CHOICES, default=TYPE_OTHER)
    file = models.FileField(upload_to=document_file_upload_path)
    version = models.CharField(max_length=40, blank=True, default="v1")
    notes = models.TextField(blank=True, default="")
    expiration_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["document_type", "-updated_at", "-id"]

    def __str__(self):
        return self.title


class Scholarship(TimeStampedModel):
    name = models.CharField(max_length=220)
    country = models.CharField(max_length=120, blank=True, default="")
    university = models.CharField(max_length=180, blank=True, default="")
    field_of_study = models.CharField(max_length=180, blank=True, default="")
    degree_level = models.CharField(max_length=120, blank=True, default="")
    official_website = models.URLField(blank=True, default="")
    application_deadline = models.DateField(null=True, blank=True)

    tuition_coverage = models.CharField(max_length=120, blank=True, default="")
    monthly_stipend = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal("0.00"))])
    travel_coverage = models.BooleanField(default=False)
    accommodation = models.BooleanField(default=False)
    other_benefits = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["application_deadline", "name"]

    def __str__(self):
        return self.name


class ScholarshipApplication(TimeStampedModel):
    STATUS_RESEARCHING = "researching"
    STATUS_PREPARING = "preparing_documents"
    STATUS_SUBMITTED = "application_submitted"
    STATUS_INTERVIEW = "interview_stage"
    STATUS_ACCEPTED = "accepted"
    STATUS_REJECTED = "rejected"
    STATUS_WAITLISTED = "waitlisted"

    STATUS_CHOICES = (
        (STATUS_RESEARCHING, "Researching"),
        (STATUS_PREPARING, "Preparing Documents"),
        (STATUS_SUBMITTED, "Application Submitted"),
        (STATUS_INTERVIEW, "Interview Stage"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_WAITLISTED, "Waitlisted"),
    )

    scholarship = models.OneToOneField(Scholarship, on_delete=models.CASCADE, related_name="application")
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_RESEARCHING)
    is_submitted = models.BooleanField(default=False)
    submission_date = models.DateField(null=True, blank=True)
    application_id = models.CharField(max_length=120, blank=True, default="")
    portal_link = models.URLField(blank=True, default="")
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-updated_at", "-id"]

    def __str__(self):
        return f"{self.scholarship.name} ({self.get_status_display()})"


class ScholarshipRequirement(TimeStampedModel):
    scholarship = models.ForeignKey(Scholarship, on_delete=models.CASCADE, related_name="requirements")
    requirement_name = models.CharField(max_length=180)
    is_required = models.BooleanField(default=True)
    is_completed = models.BooleanField(default=False)
    linked_document = models.ForeignKey(ApplicationDocument, on_delete=models.SET_NULL, null=True, blank=True, related_name="linked_requirements")
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.scholarship.name}: {self.requirement_name}"


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


def personal_vault_upload_path(instance, filename):
    file_type = getattr(instance, "file_type", "general")
    return f"uploads/personal_vault/{file_type}/{filename}"


class PersonalIdentityVault(TimeStampedModel):
    GENDER_MALE = "male"
    GENDER_FEMALE = "female"
    GENDER_OTHER = "other"
    GENDER_PREFER_NOT = "prefer_not_to_say"

    GENDER_CHOICES = (
        (GENDER_MALE, "Male"),
        (GENDER_FEMALE, "Female"),
        (GENDER_OTHER, "Other"),
        (GENDER_PREFER_NOT, "Prefer not to say"),
    )

    first_name = models.CharField(max_length=120, blank=True, default="")
    last_name = models.CharField(max_length=120, blank=True, default="")
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=24, choices=GENDER_CHOICES, blank=True, default="")
    nationality = models.CharField(max_length=120, blank=True, default="")
    languages = models.JSONField(default=list, blank=True)
    profile_photo = models.FileField(upload_to=personal_vault_upload_path, null=True, blank=True)

    class Meta:
        ordering = ["-updated_at", "-id"]

    def __str__(self):
        return f"Identity Vault ({self.first_name} {self.last_name})".strip()


class ContactInfo(TimeStampedModel):
    vault = models.OneToOneField(PersonalIdentityVault, on_delete=models.CASCADE, related_name="contact_info")
    primary_email = models.EmailField(blank=True, default="")
    secondary_email = models.EmailField(blank=True, default="")
    additional_emails = models.JSONField(default=list, blank=True)
    primary_phone = models.CharField(max_length=40, blank=True, default="")
    secondary_phone = models.CharField(max_length=40, blank=True, default="")
    other_phone_numbers = models.JSONField(default=list, blank=True)
    home_address = models.CharField(max_length=240, blank=True, default="")
    city = models.CharField(max_length=120, blank=True, default="")
    country = models.CharField(max_length=120, blank=True, default="")
    postal_code = models.CharField(max_length=40, blank=True, default="")

    class Meta:
        ordering = ["-updated_at", "-id"]

    def __str__(self):
        return f"Contact Info ({self.primary_email or 'No email'})"


class IdentityDocuments(TimeStampedModel):
    vault = models.OneToOneField(PersonalIdentityVault, on_delete=models.CASCADE, related_name="identity_documents")
    national_id_encrypted = models.TextField(blank=True, default="")
    passport_number_encrypted = models.TextField(blank=True, default="")
    passport_expiry = models.DateField(null=True, blank=True)
    drivers_license_encrypted = models.TextField(blank=True, default="")
    student_id_encrypted = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-updated_at", "-id"]

    def __str__(self):
        return "Identity Documents"


class IdentityUploadedFile(TimeStampedModel):
    TYPE_NATIONAL_ID = "national_id_scan"
    TYPE_PASSPORT = "passport_scan"
    TYPE_CERTIFICATE = "certificate"
    TYPE_ACADEMIC = "academic_document"
    TYPE_OTHER = "other"

    FILE_TYPE_CHOICES = (
        (TYPE_NATIONAL_ID, "National ID Scan"),
        (TYPE_PASSPORT, "Passport Scan"),
        (TYPE_CERTIFICATE, "Certificate"),
        (TYPE_ACADEMIC, "Academic Document"),
        (TYPE_OTHER, "Other Identity Document"),
    )

    vault = models.ForeignKey(PersonalIdentityVault, on_delete=models.CASCADE, related_name="uploaded_files")
    file_type = models.CharField(max_length=32, choices=FILE_TYPE_CHOICES, default=TYPE_OTHER)
    file = models.FileField(upload_to=personal_vault_upload_path)
    original_name = models.CharField(max_length=255, blank=True, default="")
    file_size = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-updated_at", "-id"]

    def __str__(self):
        return f"{self.file_type}: {self.original_name or self.file.name}"


class DigitalAccounts(TimeStampedModel):
    PLATFORM_GOOGLE = "google"
    PLATFORM_GITHUB = "github"
    PLATFORM_LINKEDIN = "linkedin"
    PLATFORM_TWITTER = "twitter_x"
    PLATFORM_INSTAGRAM = "instagram"
    PLATFORM_FACEBOOK = "facebook"
    PLATFORM_TIKTOK = "tiktok"
    PLATFORM_DISCORD = "discord"
    PLATFORM_REDDIT = "reddit"
    PLATFORM_CUSTOM = "custom"

    PLATFORM_CHOICES = (
        (PLATFORM_GOOGLE, "Google"),
        (PLATFORM_GITHUB, "GitHub"),
        (PLATFORM_LINKEDIN, "LinkedIn"),
        (PLATFORM_TWITTER, "Twitter / X"),
        (PLATFORM_INSTAGRAM, "Instagram"),
        (PLATFORM_FACEBOOK, "Facebook"),
        (PLATFORM_TIKTOK, "TikTok"),
        (PLATFORM_DISCORD, "Discord"),
        (PLATFORM_REDDIT, "Reddit"),
        (PLATFORM_CUSTOM, "Custom"),
    )

    vault = models.ForeignKey(PersonalIdentityVault, on_delete=models.CASCADE, related_name="digital_accounts")
    platform = models.CharField(max_length=24, choices=PLATFORM_CHOICES)
    custom_platform = models.CharField(max_length=120, blank=True, default="")
    username = models.CharField(max_length=180, blank=True, default="")
    email_used = models.EmailField(blank=True, default="")
    profile_link = models.URLField(blank=True, default="")
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["platform", "-updated_at", "-id"]

    def __str__(self):
        return f"{self.get_platform_display()} ({self.username})"


class SocialProfiles(TimeStampedModel):
    vault = models.OneToOneField(PersonalIdentityVault, on_delete=models.CASCADE, related_name="social_profiles")
    linkedin = models.URLField(blank=True, default="")
    twitter_x = models.URLField(blank=True, default="")
    instagram = models.URLField(blank=True, default="")
    github = models.URLField(blank=True, default="")
    portfolio_website = models.URLField(blank=True, default="")
    personal_blog = models.URLField(blank=True, default="")
    youtube_channel = models.URLField(blank=True, default="")

    class Meta:
        ordering = ["-updated_at", "-id"]

    def __str__(self):
        return "Social Profiles"


class PasswordReferences(TimeStampedModel):
    MANAGER_BITWARDEN = "bitwarden"
    MANAGER_1PASSWORD = "1password"
    MANAGER_PROTON_PASS = "proton_pass"
    MANAGER_OTHER = "other"

    PASSWORD_MANAGER_CHOICES = (
        (MANAGER_BITWARDEN, "Bitwarden"),
        (MANAGER_1PASSWORD, "1Password"),
        (MANAGER_PROTON_PASS, "Proton Pass"),
        (MANAGER_OTHER, "Other"),
    )

    vault = models.ForeignKey(PersonalIdentityVault, on_delete=models.CASCADE, related_name="password_references")
    platform = models.CharField(max_length=120)
    username = models.CharField(max_length=180, blank=True, default="")
    email_used = models.EmailField(blank=True, default="")
    password_hint = models.CharField(max_length=255, blank=True, default="")
    two_factor_enabled = models.BooleanField(default=False)
    backup_codes_location = models.CharField(max_length=255, blank=True, default="")
    password_manager = models.CharField(max_length=32, choices=PASSWORD_MANAGER_CHOICES, default=MANAGER_BITWARDEN)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["platform", "-updated_at", "-id"]

    def __str__(self):
        return f"{self.platform} ({self.username})"
