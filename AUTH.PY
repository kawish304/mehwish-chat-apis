from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from typing import Optional
import sqlite3
import secrets
import string

# JWT settings
SECRET_KEY = "mehwish-chat-api-secret-key-2023"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Database connection
def get_db_connection():
    conn = sqlite3.connect('mehwish.db')
    conn.row_factory = sqlite3.Row
    return conn

# User model
class User:
    def __init__(self, username: str, email: str, password: str):
        self.username = username
        self.email = email
        self.password = password

# Token model
class Token:
    def __init__(self, access_token: str, token_type: str):
        self.access_token = access_token
        self.token_type = token_type

# Token data model
class TokenData:
    def __init__(self, username: Optional[str] = None):
        self.username = username

# Password utilities
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

# API Key Generation
def generate_api_key(length=32):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# JWT Token Creation
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# JWT Token Verification
def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return TokenData(username=username)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

# Get current user from token
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    token_data = verify_token(token)
    
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (token_data.username,)).fetchone()
    conn.close()
    
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user

# API Key Authentication
async def get_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    api_key = credentials.credentials
    
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE api_key = ?", (api_key,)).fetchone()
    conn.close()
    
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return user

# User registration
def register_user(username: str, email: str, password: str):
    conn = get_db_connection()
    
    # Check if user already exists
    existing_user = conn.execute(
        "SELECT * FROM users WHERE username = ? OR email = ?", 
        (username, email)
    ).fetchone()
    
    if existing_user:
        conn.close()
        raise HTTPException(status_code=400, detail="Username or email already registered")
    
    # Create new user
    hashed_password = get_password_hash(password)
    api_key = f"mehwish_{generate_api_key()}"
    
    conn.execute(
        "INSERT INTO users (username, email, hashed_password, api_key) VALUES (?, ?, ?, ?)",
        (username, email, hashed_password, api_key)
    )
    conn.commit()
    conn.close()
    
    return {"message": "User created successfully", "api_key": api_key}

# User login
def login_user(username: str, password: str):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    
    if not user or not verify_password(password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    access_token = create_access_token(data={"sub": user["username"]})
    return Token(access_token=access_token, token_type="bearer")

# Verify API key
def verify_api_key(api_key: str):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE api_key = ?", (api_key,)).fetchone()
    conn.close()
    
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return user

# Get user by API key
def get_user_by_api_key(api_key: str):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE api_key = ?", (api_key,)).fetchone()
    conn.close()
    
    return user
