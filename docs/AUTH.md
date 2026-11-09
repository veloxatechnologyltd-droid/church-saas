# AUTH.md — Authentication & Role-Based Access Control

## Overview

The system uses **JWT (JSON Web Tokens)** for authentication.
Passwords are hashed using **bcrypt** via `passlib`.
Every protected endpoint requires a valid Bearer token in the `Authorization` header.

---

## User Roles

| Role | Access Level |
|---|---|
| `superadmin` | Full access to everything |
| `secretary` | Members, attendance, events, communication |
| `finance` | Church finance operations: giving, funds, statements, reports, and future finance workflows |
| `group_leader` | Their own department members, attendance, department SMS, and pastoral care assigned to them |
| `member` | Their own profile and giving history only |

---

## Key Libraries

```txt
python-jose[cryptography]
passlib[bcrypt]
python-multipart
```

---

## Core Auth Files

### `app/core/config.py`
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    class Config:
        env_file = ".env"

settings = Settings()
```

### `app/core/security.py`
```python
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
```

### `app/core/dependencies.py`
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.security import decode_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user

def require_roles(*roles):
    def role_checker(current_user=Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker
```

---

## Auth Endpoints (`app/api/v1/auth.py`)

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/auth/login` | Login and get access token |
| POST | `/api/v1/auth/register` | Register a new user (superadmin only) |
| GET | `/api/v1/auth/me` | Get current logged-in user |
| POST | `/api/v1/auth/change-password` | Change own password |

---

## Usage in Route Files

```python
from app.core.dependencies import get_current_user, require_roles

# Any logged-in user
@router.get("/members")
def get_members(current_user=Depends(get_current_user), db=Depends(get_db)):
    ...

# Only superadmin or secretary
@router.post("/members")
def create_member(current_user=Depends(require_roles("superadmin", "secretary")), db=Depends(get_db)):
    ...

# Only finance role
@router.get("/donations/reports")
def get_reports(current_user=Depends(require_roles("superadmin", "finance")), db=Depends(get_db)):
    ...
```

---

## Frontend Auth Flow

1. User submits login form → POST `/api/v1/auth/login`
2. Store returned `access_token` in Zustand store (and optionally localStorage)
3. Attach token to every Axios request via interceptor:

```javascript
// src/services/api.js
import axios from 'axios';
import { useAuthStore } from '../store/authStore';

const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL });

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout();
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export default api;
```

4. On app load, call `/api/v1/auth/me` to verify token is still valid
5. Protect routes using a `ProtectedRoute` wrapper component that checks role
