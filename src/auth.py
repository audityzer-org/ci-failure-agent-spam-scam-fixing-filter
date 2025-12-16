"""Authentication & Authorization Module - JWT-based authentication with RBAC."""
import os
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from passlib.context import CryptContext
from pydantic import BaseModel

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Models
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    roles: list
    expires_in: int

class TokenPayload(BaseModel):
    sub: str
    roles: list
    exp: datetime

class User(BaseModel):
    user_id: str
    username: str
    roles: list
    permissions: list

# Mock user database (replace with real DB in production)
MOCK_USERS = {
    "admin": {
        "username": "admin",
        "hashed_password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5YmMxSUFRj7P6",  # password: "admin"
        "user_id": "user-001",
        "roles": ["admin", "operator"],
        "permissions": ["read:all", "write:all", "delete:all", "manage:users"]
    },
    "operator": {
        "username": "operator",
        "hashed_password": "$2b$12$N0Wz1VEVrx0uHvt4VQB.K.K.K.K.K.K.K.K.K.K.K.K.K.K.K",  # password: "operator"
        "user_id": "user-002",
        "roles": ["operator"],
        "permissions": ["read:all", "write:cases"]
    },
    "viewer": {
        "username": "viewer",
        "hashed_password": "$2b$12$V9W8V8V8V8V8V8V8V8V8V8V8V8V8V8V8V8V8V8V8V8V8V8V8V8",  # password: "viewer"
        "user_id": "user-003",
        "roles": ["viewer"],
        "permissions": ["read:all"]
    }
}

class AuthManager:
    """Manages authentication, authorization, and JWT token lifecycle."""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Generate password hash."""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(user_id: str, username: str, roles: list, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode = {
            "sub": user_id,
            "username": username,
            "roles": roles,
            "exp": expire
        }
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Dict:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str = payload.get("sub")
            if user_id is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    @staticmethod
    def authenticate_user(username: str, password: str) -> Optional[Dict]:
        """Authenticate user credentials."""
        user = MOCK_USERS.get(username)
        if not user:
            return None
        if not AuthManager.verify_password(password, user["hashed_password"]):
            return None
        return user

# Dependency functions
async def get_current_user(credentials: HTTPAuthCredentials = Depends(security)) -> User:
    """Extract and validate current user from JWT token."""
    token = credentials.credentials
    payload = AuthManager.verify_token(token)
    user_id = payload.get("sub")
    username = payload.get("username")
    roles = payload.get("roles", [])
    return User(user_id=user_id, username=username, roles=roles, permissions=[])

async def verify_role(required_role: str):
    """Dependency to verify user has required role."""
    async def verify(user: User = Depends(get_current_user)):
        if required_role not in user.roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user
    return verify

# Public functions for API endpoints
def login(username: str, password: str) -> LoginResponse:
    """Authenticate user and return JWT token."""
    user = AuthManager.authenticate_user(username, password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    access_token = AuthManager.create_access_token(
        user_id=user["user_id"],
        username=user["username"],
        roles=user["roles"]
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user["user_id"],
        roles=user["roles"],
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

def logout(user: User) -> Dict:
    """Logout user (client should discard token)."""
    return {"message": f"User {user.username} logged out successfully"}

def get_current_user_info(user: User = Depends(get_current_user)) -> Dict:
    """Get current user information."""
    return {
        "user_id": user.user_id,
        "username": user.username,
        "roles": user.roles,
        "permissions": user.permissions
    }
