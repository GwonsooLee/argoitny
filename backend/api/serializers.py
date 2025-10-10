"""
Serializers for API - All using DynamoDB data (no Django ORM models)

All serializers now use serializers.Serializer (not ModelSerializer)
as all data comes from DynamoDB repositories.
"""
from rest_framework import serializers
import base64


class UserSerializer(serializers.Serializer):
    """User serializer for DynamoDB user dict or DynamoDBUser object"""
    id = serializers.IntegerField(read_only=True)
    user_id = serializers.IntegerField(read_only=True, required=False)
    email = serializers.EmailField(read_only=True)
    name = serializers.CharField(read_only=True, allow_blank=True, required=False)
    picture = serializers.URLField(read_only=True, allow_blank=True, required=False)
    is_admin = serializers.SerializerMethodField()
    subscription_plan_id = serializers.IntegerField(read_only=True, allow_null=True, required=False)
    is_active = serializers.BooleanField(read_only=True, required=False)
    is_staff = serializers.BooleanField(read_only=True, required=False)
    created_at = serializers.IntegerField(read_only=True, required=False)
    updated_at = serializers.IntegerField(read_only=True, required=False)

    def get_is_admin(self, obj):
        """Check if user is admin"""
        if hasattr(obj, 'is_admin') and callable(obj.is_admin):
            return obj.is_admin()
        # For dict-based objects
        from django.conf import settings
        email = obj.get('email') if isinstance(obj, dict) else getattr(obj, 'email', '')
        return email in settings.ADMIN_EMAILS


class TestCaseSerializer(serializers.Serializer):
    """TestCase serializer for DynamoDB test case dict"""
    testcase_id = serializers.CharField(read_only=True, required=False)
    input = serializers.CharField()
    output = serializers.CharField()
    created_at = serializers.IntegerField(read_only=True, required=False)


class ProblemSerializer(serializers.Serializer):
    """Problem serializer for DynamoDB problem dict"""
    platform = serializers.CharField(max_length=50)
    problem_id = serializers.CharField(max_length=50)
    title = serializers.CharField(max_length=255)
    problem_url = serializers.URLField(required=False, allow_blank=True)
    tags = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    solution_code = serializers.CharField(required=False, allow_blank=True)
    language = serializers.CharField(max_length=50, required=False)
    constraints = serializers.CharField(required=False, allow_blank=True)
    generator_code = serializers.CharField(required=False, allow_blank=True)
    is_completed = serializers.BooleanField(default=False, required=False)
    created_at = serializers.IntegerField(read_only=True, required=False)
    test_cases = TestCaseSerializer(many=True, read_only=True, required=False)
    test_case_count = serializers.IntegerField(read_only=True, required=False)
    execution_count = serializers.IntegerField(read_only=True, required=False, default=0)
    metadata = serializers.DictField(required=False, default=dict)

    def to_representation(self, instance):
        """Ensure solution_code is base64 encoded when returning data"""
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


class ProblemListSerializer(serializers.Serializer):
    """Problem list serializer (without test cases) for DynamoDB"""
    platform = serializers.CharField(read_only=True)
    problem_id = serializers.CharField(read_only=True)
    title = serializers.CharField(read_only=True)
    problem_url = serializers.URLField(read_only=True, required=False)
    tags = serializers.ListField(read_only=True, required=False)
    language = serializers.CharField(read_only=True, required=False)
    is_completed = serializers.BooleanField(read_only=True)
    created_at = serializers.IntegerField(read_only=True)
    test_case_count = serializers.IntegerField(read_only=True, required=False, default=0)


class SearchHistorySerializer(serializers.Serializer):
    """SearchHistory serializer for DynamoDB"""
    history_id = serializers.CharField(read_only=True)
    user_id = serializers.IntegerField(required=False, allow_null=True)
    user_email = serializers.EmailField(read_only=True, required=False, allow_null=True)
    user_identifier = serializers.CharField(max_length=100, default='anonymous')
    platform = serializers.CharField(max_length=50)
    problem_id = serializers.CharField(max_length=50)
    problem_title = serializers.CharField(max_length=255, required=False)
    language = serializers.CharField(max_length=50)
    code = serializers.CharField()
    result_summary = serializers.DictField()
    passed_count = serializers.IntegerField()
    failed_count = serializers.IntegerField()
    total_count = serializers.IntegerField()
    is_code_public = serializers.BooleanField(default=False)
    test_results = serializers.ListField(required=False, allow_null=True)
    hints = serializers.ListField(required=False, allow_null=True)
    created_at = serializers.IntegerField(read_only=True)
    metadata = serializers.DictField(required=False, default=dict)


class SearchHistoryListSerializer(serializers.Serializer):
    """SearchHistory list serializer (code only if public or owned by user)"""
    history_id = serializers.CharField(read_only=True)
    user_email = serializers.EmailField(read_only=True, required=False, allow_null=True)
    user_identifier = serializers.CharField(read_only=True)
    platform = serializers.CharField(read_only=True)
    problem_id = serializers.CharField(read_only=True)
    problem_title = serializers.CharField(read_only=True, required=False)
    language = serializers.CharField(read_only=True)
    passed_count = serializers.IntegerField(read_only=True)
    failed_count = serializers.IntegerField(read_only=True)
    total_count = serializers.IntegerField(read_only=True)
    is_code_public = serializers.BooleanField(read_only=True)
    created_at = serializers.IntegerField(read_only=True)
    code = serializers.CharField(read_only=True, required=False)
    has_hints = serializers.SerializerMethodField()

    def get_has_hints(self, obj):
        """Check if this execution has hints"""
        hints = obj.get('hints') if isinstance(obj, dict) else getattr(obj, 'hints', None)
        return bool(hints and len(hints) > 0)


class SubscriptionPlanSerializer(serializers.Serializer):
    """SubscriptionPlan serializer for DynamoDB"""
    plan_id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, allow_blank=True)
    max_hints_per_day = serializers.IntegerField(default=5)
    max_executions_per_day = serializers.IntegerField(default=50)
    max_problems = serializers.IntegerField(default=-1)
    can_view_all_problems = serializers.BooleanField(default=True)
    can_register_problems = serializers.BooleanField(default=False)
    is_active = serializers.BooleanField(default=True)
    created_at = serializers.IntegerField(read_only=True)
    updated_at = serializers.IntegerField(read_only=True)


# Simple request/response serializers
class GenerateTestCasesSerializer(serializers.Serializer):
    """Generate test cases serializer - solution_code fetched from existing Problem"""
    platform = serializers.CharField(max_length=50)
    problem_id = serializers.CharField(max_length=50)
    title = serializers.CharField(max_length=255)
    problem_url = serializers.URLField(required=False, allow_blank=True)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        default=list
    )
    language = serializers.CharField(max_length=50)
    constraints = serializers.CharField()


class RegisterProblemSerializer(serializers.Serializer):
    """Problem registration serializer"""
    problem_url = serializers.URLField()
    additional_context = serializers.CharField(required=False, allow_blank=True)


class ExecuteCodeSerializer(serializers.Serializer):
    """Code execution serializer"""
    code = serializers.CharField()
    language = serializers.CharField()
    platform = serializers.CharField()
    problem_id = serializers.CharField()
    is_code_public = serializers.BooleanField(default=False)
    user_identifier = serializers.CharField(required=False, default='anonymous')


class HintRequestSerializer(serializers.Serializer):
    """Hint request serializer"""
    platform = serializers.CharField(max_length=50)
    problem_id = serializers.CharField(max_length=50)
    user_code = serializers.CharField()
    language = serializers.CharField(max_length=50)
    test_results = serializers.ListField(child=serializers.DictField())


class AccountStatsSerializer(serializers.Serializer):
    """Account statistics serializer"""
    total_executions = serializers.IntegerField()
    by_platform = serializers.DictField()
    by_language = serializers.DictField()
    total_problems = serializers.IntegerField()
    passed_executions = serializers.IntegerField()
    failed_executions = serializers.IntegerField()


class ExtractProblemInfoSerializer(serializers.Serializer):
    """Extract problem info serializer"""
    problem_url = serializers.URLField()
    samples = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True,
        help_text="List of sample test cases with 'input' and 'output' keys"
    )


class ProblemRegisterSerializer(serializers.Serializer):
    """Problem registration serializer"""
    platform = serializers.CharField(max_length=50)
    problem_id = serializers.CharField(max_length=50)
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    constraints = serializers.CharField(required=False, allow_blank=True)
    time_limit = serializers.CharField(required=False, allow_blank=True)
    memory_limit = serializers.CharField(required=False, allow_blank=True)


class ProblemSaveSerializer(serializers.Serializer):
    """Problem save serializer"""
    platform = serializers.CharField(max_length=50)
    problem_id = serializers.CharField(max_length=50)
    solution_code = serializers.CharField(required=False, allow_blank=True)
    language = serializers.CharField(max_length=50, required=False)


class ScriptGenerationJobSerializer(serializers.Serializer):
    """Script generation job serializer"""
    job_id = serializers.CharField()
    platform = serializers.CharField()
    problem_id = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.IntegerField()
    updated_at = serializers.IntegerField()
