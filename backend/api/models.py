"""Django models for AlgoItny"""
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings


class SubscriptionPlan(models.Model):
    """Subscription plan model with configurable limits"""
    name = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True)

    # Limits
    max_hints_per_day = models.IntegerField(default=5, help_text='Maximum hints per day')
    max_executions_per_day = models.IntegerField(default=50, help_text='Maximum code executions per day')
    max_problems = models.IntegerField(default=-1, help_text='Maximum problems (-1 for unlimited)')

    # Features
    can_view_all_problems = models.BooleanField(default=True, help_text='Can view all registered problems')
    can_register_problems = models.BooleanField(default=False, help_text='Can register new problems')

    # Metadata
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'subscription_plans'
        ordering = ['name']

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    """Custom user manager"""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        # Get or create admin plan
        admin_plan, _ = SubscriptionPlan.objects.get_or_create(
            name='Admin',
            defaults={
                'description': 'Full access plan for administrators',
                'max_hints_per_day': -1,
                'max_executions_per_day': -1,
                'max_problems': -1,
                'can_view_all_problems': True,
                'can_register_problems': True,
                'is_active': True,
            }
        )
        extra_fields.setdefault('subscription_plan', admin_plan)

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model with Google OAuth"""
    email = models.EmailField(unique=True, db_index=True)
    name = models.CharField(max_length=255, blank=True)
    picture = models.URLField(blank=True)
    google_id = models.CharField(max_length=255, unique=True, null=True, blank=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Subscription plan (legacy Django ORM field - kept for compatibility)
    subscription_plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        db_index=True
    )

    # DynamoDB subscription plan ID (used for actual plan lookups)
    subscription_plan_id_dynamodb = models.IntegerField(null=True, blank=True, db_index=True)

    # Fix reverse accessor clashes
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        related_name='api_users',
        related_query_name='api_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        related_name='api_users',
        related_query_name='api_user',
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'users'
        indexes = [
            # Composite index for filtering active users by creation date
            models.Index(fields=['is_active', '-created_at'], name='user_active_created_idx'),
            # Index for subscription plan filtering
            models.Index(fields=['subscription_plan', 'is_active'], name='user_plan_active_idx'),
        ]

    def __str__(self):
        return self.email

    def is_admin(self):
        """Check if user is an admin based on ADMIN_EMAILS setting"""
        return self.email in settings.ADMIN_EMAILS

    def get_plan_limits(self):
        """Get subscription plan limits from DynamoDB, or defaults if no plan"""
        # Try to get plan from DynamoDB first
        if self.subscription_plan_id_dynamodb:
            try:
                from api.dynamodb.client import DynamoDBClient
                from api.dynamodb.repositories import SubscriptionPlanRepository

                table = DynamoDBClient.get_table()
                plan_repo = SubscriptionPlanRepository(table)
                plan = plan_repo.get_plan(self.subscription_plan_id_dynamodb)

                if plan:
                    return {
                        'max_hints_per_day': plan.get('max_hints_per_day', 5),
                        'max_executions_per_day': plan.get('max_executions_per_day', 50),
                    }
            except Exception:
                # If DynamoDB lookup fails, fall through to defaults
                pass

        # Fallback: check legacy Django ORM subscription_plan
        if self.subscription_plan:
            return {
                'max_hints_per_day': self.subscription_plan.max_hints_per_day,
                'max_executions_per_day': self.subscription_plan.max_executions_per_day,
                'max_problems': self.subscription_plan.max_problems,
                'can_view_all_problems': self.subscription_plan.can_view_all_problems,
                'can_register_problems': self.subscription_plan.can_register_problems,
            }

        # Default limits for users without a plan
        return {
            'max_hints_per_day': 5,
            'max_executions_per_day': 50,
            'max_problems': -1,
            'can_view_all_problems': True,
            'can_register_problems': False,
        }


class ProblemQuerySet(models.QuerySet):
    """Custom QuerySet for Problem model with optimized queries"""

    def with_test_cases(self):
        """Prefetch test cases to avoid N+1 queries"""
        return self.prefetch_related('test_cases')

    def active(self):
        """Filter out soft-deleted problems"""
        return self.filter(is_deleted=False)

    def completed(self):
        """Filter only completed problems"""
        return self.filter(is_completed=True, is_deleted=False)

    def drafts(self):
        """Filter only draft problems"""
        return self.filter(is_completed=False, is_deleted=False)

    def needs_review(self):
        """Filter problems that need admin review"""
        return self.filter(needs_review=True, is_deleted=False)

    def verified(self):
        """Filter problems verified by admin"""
        return self.filter(verified_by_admin=True, is_deleted=False)

    def with_test_case_count(self):
        """Annotate with test case count"""
        from django.db.models import Count
        return self.annotate(test_case_count=Count('test_cases'))

    def by_platform(self, platform):
        """Filter by platform"""
        return self.filter(platform=platform)

    def minimal_fields(self):
        """Select only minimal fields for list views"""
        return self.only(
            'id', 'platform', 'problem_id', 'title', 'problem_url',
            'tags', 'language', 'is_completed', 'created_at'
        )


class ProblemManager(models.Manager):
    """Custom manager for Problem model"""

    def get_queryset(self):
        return ProblemQuerySet(self.model, using=self._db)

    def with_test_cases(self):
        return self.get_queryset().with_test_cases()

    def active(self):
        return self.get_queryset().active()

    def completed(self):
        return self.get_queryset().completed()

    def drafts(self):
        return self.get_queryset().drafts()

    def needs_review(self):
        return self.get_queryset().needs_review()

    def verified(self):
        return self.get_queryset().verified()

    def with_test_case_count(self):
        return self.get_queryset().with_test_case_count()

    def minimal_fields(self):
        return self.get_queryset().minimal_fields()

    def by_platform(self, platform):
        return self.get_queryset().by_platform(platform)


class Problem(models.Model):
    """Problem model"""
    platform = models.CharField(max_length=50, db_index=True)
    problem_id = models.CharField(max_length=50, db_index=True)
    title = models.CharField(max_length=255, db_index=True)
    problem_url = models.URLField(blank=True, null=True, help_text='Full URL to the problem')
    tags = models.JSONField(default=list, blank=True, help_text='List of tags for the problem')
    solution_code = models.TextField(blank=True, null=True, help_text='Solution code for the problem')
    language = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    constraints = models.TextField(blank=True, null=True, help_text='Input constraints for the problem')
    is_completed = models.BooleanField(default=False, db_index=True, help_text='Whether the problem is completed/registered')
    is_deleted = models.BooleanField(default=False, db_index=True, help_text='Whether the problem is deleted (soft delete)')
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True, help_text='Timestamp when the problem was deleted')
    deleted_reason = models.TextField(blank=True, null=True, help_text='Reason for deletion')
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Extensible metadata field for storing additional information (e.g., execution_count, difficulty, etc.)'
    )

    # Admin review fields
    needs_review = models.BooleanField(
        default=False,
        db_index=True,
        help_text='Flag if test cases pass locally but fail on actual platform'
    )
    review_notes = models.TextField(
        blank=True,
        null=True,
        help_text='Admin notes about test case issues or review status'
    )
    verified_by_admin = models.BooleanField(
        default=False,
        db_index=True,
        help_text='Whether test cases have been verified by admin'
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp when admin reviewed the problem'
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = ProblemManager()

    class Meta:
        db_table = 'problems'
        unique_together = ('platform', 'problem_id')
        indexes = [
            # Composite index for platform + problem_id lookups (already covered by unique_together)
            models.Index(fields=['platform', 'problem_id'], name='problem_platform_id_idx'),
            # Index for filtering by platform and ordering by creation date
            models.Index(fields=['platform', '-created_at'], name='problem_platform_created_idx'),
            # Index for completion status filtering with creation date ordering
            models.Index(fields=['is_completed', '-created_at'], name='problem_completed_created_idx'),
            # Index for language filtering with creation date ordering
            models.Index(fields=['language', '-created_at'], name='problem_language_created_idx'),
            # Composite index for soft delete filtering (exclude deleted items)
            models.Index(fields=['is_deleted', 'is_completed', '-created_at'], name='problem_deleted_completed_idx'),
            # Index for admin review filtering
            models.Index(fields=['needs_review', 'is_deleted', '-created_at'], name='problem_needs_review_idx'),
            models.Index(fields=['verified_by_admin', 'is_deleted', '-created_at'], name='problem_verified_idx'),
        ]

    def __str__(self):
        return f"{self.platform} - {self.problem_id}: {self.title}"


class TestCase(models.Model):
    """Test case model"""
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='test_cases', db_index=True)
    input = models.TextField()
    output = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'test_cases'
        ordering = ['created_at']  # Consistent ordering for retrieval
        indexes = [
            models.Index(fields=['problem', 'created_at']),  # Composite index for efficient filtering and ordering
        ]

    def __str__(self):
        return f"TestCase for {self.problem}"


class SearchHistoryQuerySet(models.QuerySet):
    """Custom QuerySet for SearchHistory model with optimized queries"""

    def with_user(self):
        """Select related user to avoid N+1 queries"""
        return self.select_related('user')

    def with_problem(self):
        """Select related problem to avoid N+1 queries"""
        return self.select_related('problem')

    def public(self):
        """Filter only public search history"""
        return self.filter(is_code_public=True)

    def for_user(self, user):
        """Filter search history for a specific user"""
        return self.filter(user=user)

    def by_platform(self, platform):
        """Filter by platform"""
        return self.filter(platform=platform)

    def by_language(self, language):
        """Filter by language"""
        return self.filter(language=language)

    def minimal_fields(self):
        """Select only minimal fields for list views"""
        return self.only(
            'id', 'user_id', 'user__email', 'user_identifier',
            'platform', 'problem_number', 'problem_title', 'language',
            'passed_count', 'failed_count', 'total_count',
            'is_code_public', 'created_at', 'code'
        )


class SearchHistoryManager(models.Manager):
    """Custom manager for SearchHistory model"""

    def get_queryset(self):
        return SearchHistoryQuerySet(self.model, using=self._db)

    def with_user(self):
        return self.get_queryset().with_user()

    def with_problem(self):
        return self.get_queryset().with_problem()

    def public(self):
        return self.get_queryset().public()


class SearchHistory(models.Model):
    """
    Search history model

    IMPORTANT: platform, problem_number, and problem_title are intentionally kept
    as denormalized fields for query performance. This allows:
    1. Faster list queries without joining to Problem table
    2. Historical accuracy if problem details change
    3. Better support for anonymous user searches

    The redundancy is acceptable given the read-heavy nature of this table.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='search_history', null=True, blank=True, db_index=True)
    user_identifier = models.CharField(max_length=100, default='anonymous', db_index=True)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='search_history', db_index=True)

    # Denormalized fields for performance (see docstring)
    platform = models.CharField(max_length=50, db_index=True)
    problem_number = models.CharField(max_length=50)
    problem_title = models.CharField(max_length=255)

    language = models.CharField(max_length=50, db_index=True)
    code = models.TextField()
    result_summary = models.JSONField()
    passed_count = models.IntegerField()
    failed_count = models.IntegerField()
    total_count = models.IntegerField()
    is_code_public = models.BooleanField(default=False, db_index=True)
    test_results = models.JSONField(null=True, blank=True, help_text='Detailed test case results')
    hints = models.JSONField(
        null=True,
        blank=True,
        help_text='AI-generated hints to help user solve the problem (array of hint strings)'
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Extensible metadata field for storing additional information (e.g., execution time, memory usage, etc.)'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = SearchHistoryManager()

    class Meta:
        db_table = 'search_history'
        ordering = ['-created_at']
        indexes = [
            # Composite index for user's history ordered by date (most common query)
            models.Index(fields=['user', '-created_at'], name='sh_user_created_idx'),
            # Composite index for public history filtering
            models.Index(fields=['is_code_public', '-created_at'], name='sh_public_created_idx'),
            # Composite index for filtering by user identifier
            models.Index(fields=['user_identifier', '-created_at'], name='sh_userident_created_idx'),
            # Composite index for problem-specific history
            models.Index(fields=['problem', '-created_at'], name='sh_problem_created_idx'),
            # Index for filtering by platform
            models.Index(fields=['platform', '-created_at'], name='sh_platform_created_idx'),
            # Index for filtering by language
            models.Index(fields=['language', '-created_at'], name='sh_language_created_idx'),
        ]

    def __str__(self):
        return f"{self.user_identifier} - {self.problem_number}"


class BaseJob(models.Model):
    """Abstract base job model for all async jobs"""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    # Common fields
    platform = models.CharField(max_length=50, db_index=True)
    problem_id = models.CharField(max_length=50, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    celery_task_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.platform} - {self.problem_id}: {self.status}"


class ScriptGenerationJob(BaseJob):
    """Script generation job model for tracking async script generation"""
    title = models.CharField(max_length=255)
    problem_url = models.URLField(blank=True, null=True)
    tags = models.JSONField(default=list, blank=True)
    solution_code = models.TextField(blank=True, null=True)
    language = models.CharField(max_length=50)
    constraints = models.TextField()
    generator_code = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'script_generation_jobs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at'], name='sgj_status_created_idx'),
            models.Index(fields=['platform', 'problem_id'], name='sgj_platform_problem_idx'),
            models.Index(fields=['celery_task_id'], name='sgj_task_id_idx'),
        ]


class ProblemExtractionJob(BaseJob):
    """Problem extraction job model for tracking async problem extraction"""
    problem_url = models.URLField()
    problem_identifier = models.CharField(max_length=255, help_text='Human-readable identifier (e.g., 1520E)')

    class Meta:
        db_table = 'problem_extraction_jobs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at'], name='pej_status_created_idx'),
            models.Index(fields=['platform', 'problem_id'], name='pej_platform_problem_idx'),
            models.Index(fields=['celery_task_id'], name='pej_task_id_idx'),
        ]


class JobProgressHistory(models.Model):
    """Progress history for tracking job execution steps"""
    # Generic foreign key to support both ScriptGenerationJob and ProblemExtractionJob
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    job = GenericForeignKey('content_type', 'object_id')

    step = models.CharField(max_length=100, help_text='Step name (e.g., "Fetching problem", "Extracting constraints")')
    message = models.TextField(help_text='Detailed progress message')
    status = models.CharField(
        max_length=20,
        choices=[
            ('started', 'Started'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='in_progress'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'job_progress_history'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id', 'created_at'], name='jph_job_created_idx'),
        ]

    def __str__(self):
        return f"{self.step}: {self.status} at {self.created_at}"


class UsageLog(models.Model):
    """Usage log model for tracking user resource usage"""
    ACTION_CHOICES = [
        ('hint', 'Hint Request'),
        ('execution', 'Code Execution'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='usage_logs', db_index=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, db_index=True)
    problem = models.ForeignKey(Problem, on_delete=models.SET_NULL, null=True, blank=True, related_name='usage_logs')

    # Additional context
    metadata = models.JSONField(default=dict, blank=True, help_text='Additional context about the action')

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'usage_logs'
        ordering = ['-created_at']
        indexes = [
            # Composite index for user + action filtering with date ordering
            models.Index(fields=['user', 'action', '-created_at'], name='ul_user_action_created_idx'),
            # Composite index for daily usage queries (most common query pattern)
            models.Index(fields=['user', 'action', 'created_at'], name='ul_user_action_date_idx'),
            # Index for problem-specific usage
            models.Index(fields=['problem', '-created_at'], name='ul_problem_created_idx'),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.action} at {self.created_at}"


class TaskResult(models.Model):
    """Custom Celery task result model"""
    PENDING = 'PENDING'
    STARTED = 'STARTED'
    PROGRESS = 'PROGRESS'
    SUCCESS = 'SUCCESS'
    FAILURE = 'FAILURE'
    RETRY = 'RETRY'
    REVOKED = 'REVOKED'

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (STARTED, 'Started'),
        (PROGRESS, 'In Progress'),
        (SUCCESS, 'Success'),
        (FAILURE, 'Failure'),
        (RETRY, 'Retry'),
        (REVOKED, 'Revoked'),
    ]

    task_id = models.CharField(max_length=255, unique=True, primary_key=True, db_index=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default=PENDING, db_index=True)
    result = models.JSONField(null=True, blank=True, help_text='Task result or error information')
    traceback = models.TextField(null=True, blank=True, help_text='Exception traceback if failed')

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'task_results'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at'], name='tr_status_created_idx'),
        ]

    def __str__(self):
        return f"Task {self.task_id}: {self.status}"
