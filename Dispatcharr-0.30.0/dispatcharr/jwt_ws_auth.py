from urllib.parse import parse_qs
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import UntypedToken
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.authentication import JWTAuthentication
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

@database_sync_to_async
def get_user(validated_token):
    try:
        jwt_auth = JWTAuthentication()
        user = jwt_auth.get_user(validated_token)
        return user
    except User.DoesNotExist:
        logger.warning(f"User from token does not exist. User ID: {validated_token.get('user_id', 'unknown')}")
        return AnonymousUser()
    except Exception as e:
        logger.error(f"Error getting user from token: {str(e)}")
        return AnonymousUser()

class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        try:
            # Extract the token from the query string
            query_string = parse_qs(scope["query_string"].decode())
            token = query_string.get("token", [None])[0]

            if token is not None:
                try:
                    validated_token = JWTAuthentication().get_validated_token(token)
                    scope["user"] = await get_user(validated_token)
                except (InvalidToken, TokenError) as e:
                    logger.warning(f"Invalid token: {str(e)}")
                    scope["user"] = AnonymousUser()
            else:
                scope["user"] = AnonymousUser()
        except Exception as e:
            logger.error(f"Error in JWT authentication: {str(e)}")
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)
