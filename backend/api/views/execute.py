"""Code Execution Views"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db import transaction
from ..models import Problem, SearchHistory
from ..services.code_executor import CodeExecutor
from ..serializers import ExecuteCodeSerializer


class ExecuteCodeView(APIView):
    """Execute code against test cases (async)"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Execute user code against problem test cases (async)

        Request body:
            {
                "code": "user code",
                "language": "python",
                "problem_id": 1,
                "user_identifier": "user@example.com",  # optional
                "is_code_public": false  # optional
            }

        Returns:
            {
                "message": "Code execution task started",
                "task_id": "abc123..."
            }
        """
        serializer = ExecuteCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        code = serializer.validated_data['code']
        language = serializer.validated_data['language']
        problem_id = serializer.validated_data['problem_id']
        user_identifier = serializer.validated_data.get('user_identifier', 'anonymous')
        is_code_public = serializer.validated_data.get('is_code_public', False)

        try:
            # Verify problem exists
            problem = Problem.objects.prefetch_related('test_cases').get(id=problem_id)

            if not problem.test_cases.exists():
                return Response(
                    {'error': 'No test cases found for this problem'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Start async task
            from api.tasks import execute_code_task
            user_id = request.user.id if request.user.is_authenticated else None
            task = execute_code_task.delay(
                code=code,
                language=language,
                problem_id=problem_id,
                user_id=user_id,
                user_identifier=user_identifier,
                is_code_public=is_code_public
            )

            return Response({
                'message': 'Code execution task started',
                'task_id': task.id
            }, status=status.HTTP_202_ACCEPTED)

        except Problem.DoesNotExist:
            return Response(
                {'error': 'Problem not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to start code execution: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
