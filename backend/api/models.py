"""Django models for AlgoItny"""
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


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
        ]

    def __str__(self):
        return self.email


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
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Extensible metadata field for storing additional information (e.g., execution_count, difficulty, etc.)'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

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
            # Index for language filtering
            models.Index(fields=['language', '-created_at'], name='problem_language_created_idx'),
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
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Extensible metadata field for storing additional information (e.g., execution time, memory usage, etc.)'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

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


class ScriptGenerationJob(models.Model):
    """Script generation job model for tracking async script generation"""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    platform = models.CharField(max_length=50)
    problem_id = models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    problem_url = models.URLField(blank=True, null=True)
    tags = models.JSONField(default=list, blank=True)
    solution_code = models.TextField(blank=True, null=True)
    language = models.CharField(max_length=50)
    constraints = models.TextField()

    # Job status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    celery_task_id = models.CharField(max_length=255, blank=True, null=True)

    # Result
    generator_code = models.TextField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'script_generation_jobs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['celery_task_id']),
        ]

    def __str__(self):
        return f"{self.platform} - {self.problem_id}: {self.status}"
