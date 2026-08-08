"""Authentication utilities for JWT and password handling."""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Request, HTTPException, status
from passlib.context import CryptContext
from jose import JWTError, jwt

from app.config import settings
from app import database as db


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def authenticate_user(email: str, password: str) -> dict | None:
    """Authenticate a user by email and password."""
    with db.get_db() as conn:
        user = db.get_user_by_email(conn, email)
        if not user:
            return None
        if not verify_password(password, user["password_hash"]):
            return None
        return user


def get_current_user(request: Request) -> dict:
    """
    Get the current authenticated user from the request.
    Raises HTTPException if not authenticated.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Try to get token from cookie first
    token = request.cookies.get("access_token")
    
    # If not in cookie, try Authorization header
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split("Bearer ")[1]
        else:
            raise credentials_exception

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        if email is None or user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    with db.get_db() as conn:
        user = db.get_user_by_id(conn, user_id)
        if user is None:
            raise credentials_exception
        return user


def verify_token_for_page(request: Request) -> bool:
    """
    Verify if the request has a valid token for page access.
    Returns True if valid, False otherwise.
    """
    token = request.cookies.get("access_token")
    if not token:
        return False
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        exp = payload.get("exp")
        if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
            return False
        return True
    except JWTError:
        return False
