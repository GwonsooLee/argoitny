"""Serializers for API"""
from rest_framework import serializers
from .models import User, Problem, TestCase, SearchHistory, ScriptGenerationJob


class UserSerializer(serializers.ModelSerializer):
    """User serializer"""
    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'picture', 'created_at']
        read_only_fields = ['id', 'created_at']


class TestCaseSerializer(serializers.ModelSerializer):
    """TestCase serializer"""
    class Meta:
        model = TestCase
        fields = ['id', 'input', 'output']
        read_only_fields = ['id']


class ProblemSerializer(serializers.ModelSerializer):
    """Problem serializer"""
    test_cases = TestCaseSerializer(many=True, read_only=True)

    class Meta:
        model = Problem
        fields = ['id', 'platform', 'problem_id', 'title', 'problem_url', 'tags', 'solution_code', 'language', 'constraints', 'created_at', 'test_cases']
        read_only_fields = ['id', 'created_at']


class ProblemListSerializer(serializers.ModelSerializer):
    """Problem list serializer (without test cases)"""
    test_case_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Problem
        fields = ['id', 'platform', 'problem_id', 'title', 'problem_url', 'tags', 'language', 'created_at', 'test_case_count']
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
            'total_count', 'is_code_public', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'user_email']


class SearchHistoryListSerializer(serializers.ModelSerializer):
    """SearchHistory list serializer (code only if public)"""
    user_email = serializers.EmailField(source='user.email', read_only=True, allow_null=True)

    class Meta:
        model = SearchHistory
        fields = [
            'id', 'user_email', 'user_identifier', 'platform',
            'problem_number', 'problem_title', 'language',
            'passed_count', 'failed_count', 'total_count',
            'is_code_public', 'created_at', 'code'
        ]
        read_only_fields = ['id', 'created_at', 'user_email']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Hide code if not public
        if not instance.is_code_public:
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
        fields = ['id', 'platform', 'problem_id', 'title', 'problem_url', 'tags', 'solution_code', 'language', 'constraints']
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
