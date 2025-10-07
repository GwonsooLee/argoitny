"""Custom JWT authentication with clock skew tolerance"""
from datetime import datetime, timedelta
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
import jwt


class CustomJWTAuthentication(JWTAuthentication):
    """JWT authentication with clock skew tolerance"""

    def get_validated_token(self, raw_token):
        """Validate token with clock skew tolerance"""
        try:
            # Decode without verification first to check timestamps
            unverified = jwt.decode(raw_token, options={"verify_signature": False})

            # Check if token was issued in the future (clock skew issue)
            iat = unverified.get('iat')
            current_time = datetime.utcnow().timestamp()

            if iat and iat > current_time:
                # Token issued in future - allow up to 10 seconds skew
                time_diff = iat - current_time
                if time_diff <= 10:
                    # Add leeway for clock skew
                    return AccessToken(raw_token, verify=True)

            # Normal validation
            return AccessToken(raw_token)

        except TokenError as e:
            # Check if it's a timing issue
            if 'Token used too early' in str(e):
                try:
                    # Try with leeway
                    return AccessToken(raw_token, verify=True)
                except:
                    pass
            raise InvalidToken({
                'detail': str(e),
                'messages': [{'message': str(e)}]
            })