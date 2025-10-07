"""Serializers for API"""
from rest_framework import serializers
from .models import User, Problem, TestCase, SearchHistory, ScriptGenerationJob, ProblemExtractionJob, SubscriptionPlan, UsageLog, JobProgressHistory


class UserSerializer(serializers.ModelSerializer):
    """User serializer"""
    is_admin = serializers.SerializerMethodField()
    subscription_plan_name = serializers.CharField(source='subscription_plan.name', read_only=True, allow_null=True)
    subscription_plan_description = serializers.CharField(source='subscription_plan.description', read_only=True, allow_null=True)

    def get_is_admin(self, obj):
        """Check if user is admin"""
        return obj.is_admin()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'name', 'picture', 'is_admin',
            'subscription_plan_name', 'subscription_plan_description',
            'created_at'
        ]
        read_only_fields = ['id', 'is_admin', 'subscription_plan_name', 'subscription_plan_description', 'created_at']


class TestCaseSerializer(serializers.ModelSerializer):
    """TestCase serializer"""
    class Meta:
        model = TestCase
        fields = ['id', 'input', 'output']
        read_only_fields = ['id']


class ProblemSerializer(serializers.ModelSerializer):
    """Problem serializer"""
    test_cases = TestCaseSerializer(many=True, read_only=True)
    test_case_count = serializers.SerializerMethodField()
    execution_count = serializers.SerializerMethodField()

    def get_test_case_count(self, obj):
        # OPTIMIZATION: Use annotated value if available, otherwise count
        # This prevents N+1 queries when using annotate(test_case_count=Count('test_cases'))
        if hasattr(obj, 'test_case_count_annotated'):
            return obj.test_case_count_annotated
        return obj.test_cases.count()

    def get_execution_count(self, obj):
        return obj.metadata.get('execution_count', 0) if obj.metadata else 0

    def to_representation(self, instance):
        """Ensure solution_code is base64 encoded when returning data"""
        import base64
        data = super().to_representation(instance)
        if data.get('solution_code'):
            try:
                # Check if already base64 encoded by trying to decode
                base64.b64decode(data['solution_code'])
                # If successful, it's already base64 - return as-is
            except:
                # Not base64, so encode it
                try:
                    encoded = base64.b64encode(data['solution_code'].encode('utf-8')).decode('utf-8')
                    data['solution_code'] = encoded
                except:
                    # If encoding fails, return as-is (for backwards compatibility)
                    pass
        return data

    class Meta:
        model = Problem
        fields = [
            'id', 'platform', 'problem_id', 'title', 'problem_url', 'tags',
            'solution_code', 'language', 'constraints', 'is_completed',
            'created_at', 'test_cases', 'test_case_count', 'execution_count',
            'metadata', 'needs_review', 'review_notes', 'verified_by_admin',
            'reviewed_at'
        ]
        read_only_fields = ['id', 'created_at', 'reviewed_at']


class ProblemListSerializer(serializers.ModelSerializer):
    """Problem list serializer (without test cases)"""
    test_case_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Problem
        fields = ['id', 'platform', 'problem_id', 'title', 'problem_url', 'tags', 'language', 'is_completed', 'created_at', 'test_case_count']
        read_only_fields = ['id', 'created_at', 'test_case_count']


class SearchHistorySerializer(serializers.ModelSerializer):
    """SearchHistory serializer"""
    user_email = serializers.EmailField(source='user.email', read_only=True, allow_null=True)

    class Meta:
        model = SearchHistory
        fields = [
            'id', 'user', 'user_email', 'user_identifier', 'problem',
            'platform', 'problem_number', 'problem_title', 'language',
            'code', 'result_summary', 'passed_count', 'failed_count',
            'total_count', 'is_code_public', 'test_results', 'hints', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'user_email', 'hints']


class SearchHistoryListSerializer(serializers.ModelSerializer):
    """SearchHistory list serializer (code only if public or owned by user)"""
    user_email = serializers.SerializerMethodField()
    has_hints = serializers.SerializerMethodField()

    def get_user_email(self, obj):
        """
        Get user email - optimized to avoid N+1 queries
        Uses only('user__email') from the view's select_related('user')
        """
        return obj.user.email if obj.user else None

    def get_has_hints(self, obj):
        """Check if this execution has hints"""
        return bool(obj.hints and len(obj.hints) > 0)

    class Meta:
        model = SearchHistory
        fields = [
            'id', 'user_email', 'user_identifier', 'platform',
            'problem_number', 'problem_title', 'language',
            'passed_count', 'failed_count', 'total_count',
            'is_code_public', 'created_at', 'code', 'has_hints'
        ]
        read_only_fields = ['id', 'created_at', 'user_email', 'has_hints']

    def to_representation(self, instance):
        data = super().to_representation(instance)

        # Show code if public OR if user is the owner
        request = self.context.get('request')
        is_owner = False

        if request and request.user and request.user.is_authenticated:
            # Check by user object
            if instance.user:
                is_owner = instance.user == request.user
            # Also check by email in user_identifier
            elif instance.user_identifier:
                is_owner = instance.user_identifier == request.user.email

        # Hide code if not public and not owner
        if not instance.is_code_public and not is_owner:
            data['code'] = None

        return data


class ProblemRegisterSerializer(serializers.Serializer):
    """Problem registration serializer"""
    platform = serializers.CharField(max_length=50, required=False, allow_blank=True)
    problem_id = serializers.CharField(max_length=50, required=False, allow_blank=True)
    title = serializers.CharField(max_length=255)
    problem_url = serializers.URLField(required=False, allow_blank=True)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        default=list
    )
    solution_code = serializers.CharField()
    language = serializers.CharField(max_length=50)
    constraints = serializers.CharField()

    def validate(self, data):
        """Validate that either problem_url or (platform + problem_id) is provided"""
        problem_url = data.get('problem_url')
        platform = data.get('platform')
        problem_id = data.get('problem_id')

        # If URL is provided, try to extract platform and problem_id
        if problem_url:
            from api.utils import ProblemURLParser
            extracted_platform, extracted_problem_id = ProblemURLParser.parse_url(problem_url)

            if extracted_platform and extracted_problem_id:
                # Override with extracted values
                data['platform'] = extracted_platform
                data['problem_id'] = extracted_problem_id
            elif not (platform and problem_id):
                # URL provided but couldn't parse, and no manual platform/id
                raise serializers.ValidationError(
                    'Could not extract problem info from URL. Please provide platform and problem_id manually.'
                )
        elif not (platform and problem_id):
            # No URL and no manual platform/id
            raise serializers.ValidationError(
                'Either problem_url or both platform and problem_id must be provided'
            )

        return data


class GenerateTestCasesSerializer(serializers.Serializer):
    """Generate test cases serializer"""
    platform = serializers.CharField(max_length=50)
    problem_id = serializers.CharField(max_length=50)
    title = serializers.CharField(max_length=255)
    problem_url = serializers.URLField(required=False, allow_blank=True)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        default=list
    )
    solution_code = serializers.CharField(required=False, allow_blank=True)
    language = serializers.CharField(max_length=50)
    constraints = serializers.CharField()


class ExecuteCodeSerializer(serializers.Serializer):
    """Execute code serializer"""
    code = serializers.CharField()
    language = serializers.CharField(max_length=50)
    problem_id = serializers.IntegerField()
    user_identifier = serializers.CharField(max_length=100, required=False, default='anonymous')
    is_code_public = serializers.BooleanField(default=False)


class ProblemSaveSerializer(serializers.ModelSerializer):
    """Problem save/draft serializer"""
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        default=list
    )

    class Meta:
        model = Problem
        fields = ['id', 'platform', 'problem_id', 'title', 'problem_url', 'tags', 'solution_code', 'language', 'constraints', 'is_completed']
        read_only_fields = ['id']

    def to_representation(self, instance):
        """Decode base64 solution_code when returning data"""
        import base64
        data = super().to_representation(instance)
        if data.get('solution_code'):
            try:
                # Decode base64 to string
                decoded = base64.b64decode(data['solution_code']).decode('utf-8')
                data['solution_code'] = decoded
            except:
                # If decoding fails, return as-is (for backwards compatibility)
                pass
        return data

    def validate_solution_code(self, value):
        """Encode solution_code to base64 before saving"""
        import base64
        if value:
            # Encode string to base64
            encoded = base64.b64encode(value.encode('utf-8')).decode('utf-8')
            return encoded
        return value

    def validate(self, data):
        """Validate that platform and problem_id are provided (required for drafts)"""
        platform = data.get('platform')
        problem_id = data.get('problem_id')
        problem_url = data.get('problem_url')

        # For drafts, we must have platform and problem_id
        if not (platform and problem_id):
            # Try to extract from URL if available
            if problem_url:
                from api.utils import ProblemURLParser
                extracted_platform, extracted_problem_id = ProblemURLParser.parse_url(problem_url)

                if extracted_platform and extracted_problem_id:
                    data['platform'] = extracted_platform
                    data['problem_id'] = extracted_problem_id
                else:
                    raise serializers.ValidationError(
                        'Could not extract problem info from URL. Please provide platform and problem_id.'
                    )
            else:
                raise serializers.ValidationError(
                    'Both platform and problem_id are required'
                )

        return data


class ScriptGenerationJobSerializer(serializers.ModelSerializer):
    """ScriptGenerationJob serializer"""
    class Meta:
        model = ScriptGenerationJob
        fields = [
            'id', 'platform', 'problem_id', 'title', 'problem_url', 'tags',
            'solution_code', 'language', 'constraints', 'status',
            'celery_task_id', 'generator_code', 'error_message',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'celery_task_id', 'generator_code', 'error_message', 'created_at', 'updated_at']


class ProblemExtractionJobSerializer(serializers.ModelSerializer):
    """ProblemExtractionJob serializer"""
    class Meta:
        model = ProblemExtractionJob
        fields = [
            'id', 'platform', 'problem_id', 'problem_url', 'problem_identifier',
            'status', 'celery_task_id', 'error_message',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'celery_task_id', 'error_message', 'created_at', 'updated_at']


class ExtractProblemInfoSerializer(serializers.Serializer):
    """Extract problem info from URL serializer"""
    problem_url = serializers.URLField(required=True, help_text='URL of the problem page')


class GenerateHintsSerializer(serializers.Serializer):
    """Generate hints serializer"""
    history_id = serializers.IntegerField(required=True, help_text='ID of the SearchHistory record')


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """SubscriptionPlan serializer"""
    user_count = serializers.SerializerMethodField()

    def get_user_count(self, obj):
        """Get number of users with this plan"""
        return obj.users.count()

    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'description', 'max_hints_per_day', 'max_executions_per_day',
            'max_problems', 'can_view_all_problems', 'can_register_problems',
            'is_active', 'user_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user_count', 'created_at', 'updated_at']


class UserManagementSerializer(serializers.ModelSerializer):
    """User management serializer for admins"""
    subscription_plan_name = serializers.CharField(source='subscription_plan.name', read_only=True, allow_null=True)
    is_admin = serializers.SerializerMethodField()
    usage_stats = serializers.SerializerMethodField()

    def get_is_admin(self, obj):
        """Check if user is admin"""
        return obj.is_admin()

    def get_usage_stats(self, obj):
        """Get user's usage statistics"""
        from django.utils import timezone
        from datetime import timedelta
        from api.models import UsageLog

        today = timezone.now().date()
        today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))

        hints_today = UsageLog.objects.filter(
            user=obj,
            action='hint',
            created_at__gte=today_start
        ).count()

        executions_today = UsageLog.objects.filter(
            user=obj,
            action='execution',
            created_at__gte=today_start
        ).count()

        return {
            'hints_today': hints_today,
            'executions_today': executions_today,
        }

    class Meta:
        model = User
        fields = [
            'id', 'email', 'name', 'picture', 'subscription_plan', 'subscription_plan_name',
            'is_admin', 'is_active', 'usage_stats', 'created_at'
        ]
        read_only_fields = ['id', 'email', 'name', 'picture', 'is_admin', 'created_at']


class UsageLogSerializer(serializers.ModelSerializer):
    """UsageLog serializer"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    problem_title = serializers.CharField(source='problem.title', read_only=True, allow_null=True)

    class Meta:
        model = UsageLog
        fields = ['id', 'user', 'user_email', 'action', 'problem', 'problem_title', 'metadata', 'created_at']
        read_only_fields = ['id', 'created_at']


class JobProgressHistorySerializer(serializers.ModelSerializer):
    """JobProgressHistory serializer"""
    class Meta:
        model = JobProgressHistory
        fields = ['id', 'step', 'message', 'status', 'created_at']
        read_only_fields = ['id', 'created_at']
