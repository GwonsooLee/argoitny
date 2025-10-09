"""Debug script to test authentication flow"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_test')
django.setup()

from api.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from api.dynamodb.repositories import UserRepository
from rest_framework.test import APIClient

# Create user in Django ORM
print("1. Creating user in Django ORM...")
user = User.objects.create_user(
    email='test@example.com',
    name='Test User',
    picture='test.jpg',
    google_id='test123'
)
print(f"   Created user: {user.email}, ID: {user.id}")

# Create user in DynamoDB
print("\n2. Creating user in DynamoDB...")
user_repo = UserRepository()
db_user = user_repo.create_user({
    'user_id': user.id,
    'email': user.email,
    'name': user.name,
    'picture': user.picture,
    'google_id': user.google_id
})
print(f"   Created DynamoDB user: {db_user.get('email')}")

# Verify we can fetch from DynamoDB
print("\n3. Verifying fetch from DynamoDB...")
fetched_user = user_repo.get_user_by_email(user.email)
print(f"   Fetched user: {fetched_user.get('email') if fetched_user else 'NOT FOUND'}")

# Generate JWT token
print("\n4. Generating JWT token...")
refresh = RefreshToken.for_user(user)
access_token = str(refresh.access_token)
print(f"   Access token (first 50 chars): {access_token[:50]}...")
print(f"   Token user_id claim: {refresh.access_token['user_id']}")

# Make authenticated request
print("\n5. Making authenticated API request...")
client = APIClient()
client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
response = client.get('/api/account/stats/')
print(f"   Response status: {response.status_code}")
print(f"   Response data: {response.data}")
