"""Authentication and authorization utilities."""

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security schemes
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str
    exp: datetime
    iat: datetime
    type: str = "access"
    roles: list[str] = []


class UserContext(BaseModel):
    """Current user context extracted from token."""

    user_id: str
    email: str | None = None
    roles: list[str] = []

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles

    def has_any_role(self, roles: list[str]) -> bool:
        """Check if user has any of the specified roles."""
        return any(role in self.roles for role in roles)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(
    subject: str,
    roles: list[str] | None = None,
    expires_delta: timedelta | None = None,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    """Create a JWT access token.

    Args:
        subject: The subject (usually user ID) for the token.
        roles: List of roles for the user.
        expires_delta: Optional custom expiration time.
        additional_claims: Optional additional claims to include.

    Returns:
        Encoded JWT token string.
    """
    now = datetime.now(timezone.utc)

    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    payload = {
        "sub": subject,
        "exp": expire,
        "iat": now,
        "type": "access",
        "roles": roles or [],
    }

    if additional_claims:
        payload.update(additional_claims)

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> TokenPayload:
    """Decode and validate a JWT token.

    Args:
        token: The JWT token string.

    Returns:
        Decoded token payload.

    Raises:
        HTTPException: If token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return TokenPayload(**payload)
    except JWTError as e:
        logger.warning("JWT decode error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_api_key(api_key: str) -> bool:
    """Verify an API key.

    Args:
        api_key: The API key to verify.

    Returns:
        True if valid, False otherwise.
    """
    # In production, this should validate against a database of API keys
    # For MVP, we use a simple comparison with the configured secret
    return api_key == settings.api_key_secret


async def get_current_user(
    api_key: str | None = Security(api_key_header),
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> UserContext:
    """Get the current authenticated user from request.

    Supports both API key and JWT bearer token authentication.

    Args:
        api_key: Optional API key from header.
        credentials: Optional bearer token credentials.

    Returns:
        UserContext with user information.

    Raises:
        HTTPException: If authentication fails.
    """
    # Try API key authentication first
    if api_key:
        if verify_api_key(api_key):
            return UserContext(
                user_id="api-user",
                roles=["api"],
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    # Try bearer token authentication
    if credentials:
        token_payload = decode_token(credentials.credentials)
        return UserContext(
            user_id=token_payload.sub,
            roles=token_payload.roles,
        )

    # No authentication provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_roles(*required_roles: str):
    """Dependency to require specific roles.

    Args:
        required_roles: One or more roles that are required.

    Returns:
        Dependency function that validates roles.
    """

    async def role_checker(
        user: UserContext = Depends(get_current_user),
    ) -> UserContext:
        if not user.has_any_role(list(required_roles)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {', '.join(required_roles)}",
            )
        return user

    return role_checker


# Role constants
class Roles:
    """Available user roles."""

    VIEWER = "viewer"
    ANALYST = "analyst"
    APPROVER = "approver"
    CONTRACT_MANAGER = "contract_manager"
    ADMINISTRATOR = "admin"
    API = "api"
