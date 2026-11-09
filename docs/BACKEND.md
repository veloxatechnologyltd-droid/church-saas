# BACKEND.md — FastAPI Backend Conventions

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## `requirements.txt`
```txt
fastapi
uvicorn[standard]
sqlalchemy
alembic
psycopg2-binary
pydantic-settings
python-jose[cryptography]
passlib[bcrypt]
python-multipart
cloudinary
sendgrid
httpx
httpx
pandas
openpyxl
python-dotenv
```

---

## `app/main.py` Pattern

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import auth, members, attendance, donations, groups, events, communication, reports

app = FastAPI(title="Living Spring CMS API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://your-vercel-app.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(members.router, prefix="/api/v1/members", tags=["Members"])
app.include_router(attendance.router, prefix="/api/v1/attendance", tags=["Attendance"])
app.include_router(donations.router, prefix="/api/v1/donations", tags=["Finance"])
app.include_router(groups.router, prefix="/api/v1/groups", tags=["Groups"])
app.include_router(events.router, prefix="/api/v1/events", tags=["Events"])
app.include_router(communication.router, prefix="/api/v1/communication", tags=["Communication"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])

@app.get("/")
def root():
    return {"message": "Living Spring CMS API is running"}
```

---

## File Patterns

### Model (`app/models/member.py`)
```python
from sqlalchemy import Column, String, Boolean, Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.db.database import Base

class Member(Base):
    __tablename__ = "members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    # ... other fields
```

### Schema (`app/schemas/member.py`)
```python
from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import date

class MemberBase(BaseModel):
    first_name: str
    last_name: str
    phone: Optional[str] = None
    email: Optional[str] = None

class MemberCreate(MemberBase):
    pass

class MemberUpdate(MemberBase):
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class MemberResponse(MemberBase):
    id: UUID
    membership_status: str
    created_at: date

    class Config:
        from_attributes = True
```

### CRUD (`app/crud/member.py`)
```python
from sqlalchemy.orm import Session
from app.models.member import Member
from app.schemas.member import MemberCreate, MemberUpdate

def get_member(db: Session, member_id: str):
    return db.query(Member).filter(Member.id == member_id).first()

def get_members(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Member).offset(skip).limit(limit).all()

def create_member(db: Session, member: MemberCreate):
    db_member = Member(**member.model_dump())
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member

def update_member(db: Session, member_id: str, member: MemberUpdate):
    db_member = get_member(db, member_id)
    for key, value in member.model_dump(exclude_unset=True).items():
        setattr(db_member, key, value)
    db.commit()
    db.refresh(db_member)
    return db_member

def delete_member(db: Session, member_id: str):
    db_member = get_member(db, member_id)
    db.delete(db_member)
    db.commit()
```

### Route (`app/api/v1/members.py`)
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.crud import member as crud
from app.schemas.member import MemberCreate, MemberUpdate, MemberResponse
from typing import List

router = APIRouter()

@router.get("/", response_model=List[MemberResponse])
def list_members(skip: int = 0, limit: int = 100, db: Session = Depends(get_db),
                 current_user=Depends(get_current_user)):
    return crud.get_members(db, skip=skip, limit=limit)

@router.post("/", response_model=MemberResponse, status_code=201)
def create_member(member: MemberCreate, db: Session = Depends(get_db),
                  current_user=Depends(require_roles("church_admin", "secretary"))):
    return crud.create_member(db, member)

@router.get("/{member_id}", response_model=MemberResponse)
def get_member(member_id: str, db: Session = Depends(get_db),
               current_user=Depends(get_current_user)):
    member = crud.get_member(db, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return member

@router.put("/{member_id}", response_model=MemberResponse)
def update_member(member_id: str, member: MemberUpdate, db: Session = Depends(get_db),
                  current_user=Depends(require_roles("church_admin", "secretary"))):
    return crud.update_member(db, member_id, member)

@router.delete("/{member_id}", status_code=204)
def delete_member(member_id: str, db: Session = Depends(get_db),
                  current_user=Depends(require_roles("church_admin"))):
    crud.delete_member(db, member_id)
```

---

## Response Format

Always return consistent shapes:
```python
# Success
{"status": "success", "data": {...}}

# List
{"status": "success", "data": [...], "total": 100, "page": 1}

# Error (use HTTPException)
raise HTTPException(status_code=404, detail="Member not found")
```

---

## File Upload (Cloudinary)

```python
import cloudinary
import cloudinary.uploader
from app.core.config import settings

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)

def upload_photo(file_bytes: bytes, public_id: str) -> str:
    result = cloudinary.uploader.upload(file_bytes, public_id=public_id, folder="church-cms/members")
    return result["secure_url"]
```
