"""Health Check Views"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
from django.core.cache import cache
import redis


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Simple health check endpoint for load balancers

    Returns:
        200 OK if service is healthy
    """
    return Response({
        'status': 'healthy',
        'service': 'algoitny-backend'
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def readiness_check(request):
    """
    Readiness check endpoint

    Checks:
    - Database connection
    - Redis connection

    Returns:
        200 OK if all dependencies are ready
        503 Service Unavailable if any dependency is not ready
    """
    checks = {
        'database': False,
        'redis': False,
    }

    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks['database'] = True
    except Exception as e:
        checks['database'] = False
        checks['database_error'] = str(e)

    # Check Redis
    try:
        cache.set('health_check', 'ok', 1)
        result = cache.get('health_check')
        checks['redis'] = (result == 'ok')
    except Exception as e:
        checks['redis'] = False
        checks['redis_error'] = str(e)

    # All checks must pass
    is_ready = all([
        checks['database'],
        checks['redis'],
    ])

    if is_ready:
        return Response({
            'status': 'ready',
            'checks': checks
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'status': 'not_ready',
            'checks': checks
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(['GET'])
@permission_classes([AllowAny])
def liveness_check(request):
    """
    Liveness check endpoint

    Simple check that the application is running

    Returns:
        200 OK if application is alive
    """
    return Response({
        'status': 'alive',
        'service': 'algoitny-backend'
    }, status=status.HTTP_200_OK)
