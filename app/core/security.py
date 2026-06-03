"""
Security utilities for the application.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, ValidationError

settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    subject: Union[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
    return encoded_jwt


def create_refresh_token(
    subject: Union[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT refresh token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.refresh_token_expire_days
        )
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        
        # Check token type
        if payload.get("type") != token_type:
            raise AuthenticationError("Invalid token type")
        
        # Check expiration
        exp = payload.get("exp")
        if exp is None or datetime.fromtimestamp(exp, timezone.utc) < datetime.now(timezone.utc):
            raise AuthenticationError("Token has expired")
        
        return payload
    
    except JWTError as e:
        raise AuthenticationError(f"Invalid token: {e}")


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def generate_password_reset_token(email: str) -> str:
    """Generate a password reset token."""
    delta = timedelta(hours=1)  # Token valid for 1 hour
    now = datetime.now(timezone.utc)
    expires = now + delta
    exp = expires.timestamp()
    encoded_jwt = jwt.encode(
        {"exp": exp, "nbf": now, "sub": email, "type": "password_reset"},
        settings.secret_key,
        algorithm="HS256",
    )
    return encoded_jwt


def verify_password_reset_token(token: str) -> Optional[str]:
    """Verify a password reset token and return the email."""
    try:
        payload = verify_token(token, "password_reset")
        return payload.get("sub")
    except AuthenticationError:
        return None


def generate_api_key() -> str:
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)


def validate_password_strength(password: str) -> None:
    """Validate password strength according to security requirements."""
    if len(password) < settings.password_min_length:
        raise ValidationError(
            f"Password must be at least {settings.password_min_length} characters long"
        )
    
    # Check for at least one uppercase letter
    if not any(c.isupper() for c in password):
        raise ValidationError("Password must contain at least one uppercase letter")
    
    # Check for at least one lowercase letter
    if not any(c.islower() for c in password):
        raise ValidationError("Password must contain at least one lowercase letter")
    
    # Check for at least one digit
    if not any(c.isdigit() for c in password):
        raise ValidationError("Password must contain at least one digit")
    
    # Check for at least one special character
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        raise ValidationError("Password must contain at least one special character")


def generate_secure_filename(original_filename: str) -> str:
    """Generate a secure filename to prevent path traversal attacks."""
    import os
    from pathlib import Path
    
    # Get the file extension
    extension = Path(original_filename).suffix
    
    # Generate a secure random name
    secure_name = secrets.token_hex(16)
    
    # Combine with extension
    return f"{secure_name}{extension}"


def sanitize_input(input_string: str) -> str:
    """Sanitize user input to prevent injection attacks."""
    import re
    
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>"\'&]', '', input_string)
    
    # Strip whitespace
    sanitized = sanitized.strip()
    
    return sanitized


def is_safe_url(url: str, allowed_hosts: Optional[list[str]] = None) -> bool:
    """Check if a URL is safe for redirects."""
    from urllib.parse import urlparse
    
    if allowed_hosts is None:
        allowed_hosts = ["localhost", "127.0.0.1"]
    
    try:
        parsed_url = urlparse(url)
        
        # Only allow http and https schemes
        if parsed_url.scheme not in ["http", "https"]:
            return False
        
        # Check if the host is in allowed hosts
        if parsed_url.netloc not in allowed_hosts:
            return False
        
        return True
    
    except Exception:
        return False


class RateLimiter:
    """Simple in-memory rate limiter for API endpoints."""
    
    def __init__(self):
        self.requests: Dict[str, list[datetime]] = {}
    
    def is_allowed(
        self, 
        key: str, 
        limit: int, 
        window: timedelta
    ) -> bool:
        """Check if a request is allowed based on rate limit."""
        now = datetime.now(timezone.utc)
        
        # Clean old requests
        if key in self.requests:
            self.requests[key] = [
                req_time for req_time in self.requests[key]
                if now - req_time < window
            ]
        else:
            self.requests[key] = []
        
        # Check if under limit
        if len(self.requests[key]) < limit:
            self.requests[key].append(now)
            return True
        
        return False


# Global rate limiter instance
rate_limiter = RateLimiter()
