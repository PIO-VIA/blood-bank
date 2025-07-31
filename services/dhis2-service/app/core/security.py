from datetime import datetime, timedelta
from typing import Any, Union, Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
import structlog

from .config import settings

logger = structlog.get_logger()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    subject: Union[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        subject: The subject (usually user ID) to encode in the token
        expires_delta: Token expiration time delta
        
    Returns:
        str: The encoded JWT token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": datetime.utcnow(),
        "type": "access"
    }
    
    try:
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.SECRET_KEY, 
            algorithm=settings.ALGORITHM
        )
        return encoded_jwt
    except Exception as e:
        logger.error("Failed to create access token", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create access token"
        )


def verify_token(token: str) -> dict:
    """
    Verify and decode a JWT token.
    
    Args:
        token: The JWT token to verify
        
    Returns:
        dict: The decoded token payload
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        # Check if token has expired
        exp = payload.get("exp")
        if exp is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing expiration"
            )
        
        if datetime.utcnow() > datetime.fromtimestamp(exp):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        
        return payload
        
    except JWTError as e:
        logger.error("JWT verification failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against its hash.
    
    Args:
        plain_password: The plain text password
        hashed_password: The hashed password to verify against
        
    Returns:
        bool: True if password matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error("Password verification failed", error=str(e))
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a plain text password.
    
    Args:
        password: The plain text password to hash
        
    Returns:
        str: The hashed password
    """
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error("Password hashing failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not hash password"
        )


def generate_api_key() -> str:
    """
    Generate a secure API key.
    
    Returns:
        str: A secure API key
    """
    import secrets
    import string
    
    alphabet = string.ascii_letters + string.digits
    api_key = ''.join(secrets.choice(alphabet) for _ in range(32))
    return f"bbas_{api_key}"  # Blood Bank API Service prefix


def validate_api_key(api_key: str) -> bool:
    """
    Validate an API key format.
    
    Args:
        api_key: The API key to validate
        
    Returns:
        bool: True if valid format, False otherwise
    """
    if not api_key:
        return False
    
    if not api_key.startswith("bbas_"):
        return False
    
    if len(api_key) != 37:  # 5 (prefix) + 32 (key)
        return False
    
    # Check if the key part contains only valid characters
    key_part = api_key[5:]
    valid_chars = set(string.ascii_letters + string.digits)
    return all(c in valid_chars for c in key_part)


class SecurityHeaders:
    """Security headers middleware configuration."""
    
    @staticmethod
    def get_security_headers() -> dict:
        """Get security headers for HTTP responses."""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY", 
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }


def sanitize_input(input_string: str, max_length: int = 1000) -> str:
    """
    Sanitize user input to prevent injection attacks.
    
    Args:
        input_string: The input string to sanitize
        max_length: Maximum allowed length
        
    Returns:
        str: Sanitized input string
    """
    if not input_string:
        return ""
    
    # Truncate if too long
    if len(input_string) > max_length:
        input_string = input_string[:max_length]
    
    # Remove potential dangerous characters
    dangerous_chars = ['<', '>', '"', "'", '&', '\x00', '\r', '\n']
    for char in dangerous_chars:
        input_string = input_string.replace(char, '')
    
    return input_string.strip()


def rate_limit_key(identifier: str, endpoint: str) -> str:
    """
    Generate a rate limit key for Redis.
    
    Args:
        identifier: User identifier (IP, user ID, etc.)
        endpoint: API endpoint
        
    Returns:
        str: Rate limit key
    """
    return f"rate_limit:{identifier}:{endpoint}"


def is_safe_redirect_url(url: str, allowed_hosts: list = None) -> bool:
    """
    Check if a redirect URL is safe to prevent open redirect vulnerabilities.
    
    Args:
        url: The URL to check
        allowed_hosts: List of allowed hosts for redirection
        
    Returns:
        bool: True if URL is safe, False otherwise
    """
    if not url:
        return False
    
    # Don't allow absolute URLs to different domains
    if url.startswith(('http://', 'https://')):
        if allowed_hosts:
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            return parsed_url.netloc in allowed_hosts
        return False
    
    # Allow relative URLs
    if url.startswith('/'):
        return True
    
    return False