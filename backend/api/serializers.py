"""Serializers for API"""
from rest_framework import serializers
from .models import User, Problem, TestCase, SearchHistory


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
        fields = ['id', 'platform', 'problem_id', 'title', 'created_at', 'test_cases']
        read_only_fields = ['id', 'created_at']


class ProblemListSerializer(serializers.ModelSerializer):
    """Problem list serializer (without test cases)"""
    class Meta:
        model = Problem
        fields = ['id', 'platform', 'problem_id', 'title', 'created_at']
        read_only_fields = ['id', 'created_at']


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
    platform = serializers.CharField(max_length=50)
    problem_id = serializers.CharField(max_length=50)
    title = serializers.CharField(max_length=255)
    solution_code = serializers.CharField()
    language = serializers.CharField(max_length=50)
    constraints = serializers.CharField()


class GenerateTestCasesSerializer(serializers.Serializer):
    """Generate test cases serializer"""
    platform = serializers.CharField(max_length=50)
    problem_id = serializers.CharField(max_length=50)
    title = serializers.CharField(max_length=255)
    solution_code = serializers.CharField()
    language = serializers.CharField(max_length=50)
    constraints = serializers.CharField()


class ExecuteCodeSerializer(serializers.Serializer):
    """Execute code serializer"""
    code = serializers.CharField()
    language = serializers.CharField(max_length=50)
    problem_id = serializers.IntegerField()
    user_identifier = serializers.CharField(max_length=100, required=False, default='anonymous')
    is_code_public = serializers.BooleanField(default=False)
