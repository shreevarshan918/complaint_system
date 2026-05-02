from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# ── DEPARTMENT ──────────────────────────
class DepartmentResponse(BaseModel):
    department_id: int
    dept_name: str
    dept_head: str
    class Config:
        from_attributes = True

# ── STUDENT ─────────────────────────────
class StudentRegister(BaseModel):
    name: str
    email: str
    password: str
    phone: Optional[str] = None
    dept_id: int

class StudentResponse(BaseModel):
    student_id: int
    name: str
    email: str
    phone: Optional[str]
    dept_id: int
    class Config:
        from_attributes = True

# ── STAFF ───────────────────────────────
class StaffRegister(BaseModel):
    name: str
    email: str
    password: str
    role: str
    dept_id: int

class StaffResponse(BaseModel):
    staff_id: int
    name: str
    email: str
    role: str
    dept_id: int
    class Config:
        from_attributes = True

# ── LOGIN ───────────────────────────────
class LoginRequest(BaseModel):
    email: str
    password: str
    role: str  # "student" or "staff"

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    name: str

# ── COMPLAINT ───────────────────────────
class ComplaintCreate(BaseModel):
    title: str
    description: str
    category: str
    priority: str
    dept_id: int

class ComplaintResponse(BaseModel):
    complaint_id: int
    title: str
    description: str
    category: str
    priority: str
    current_status: str
    created_at: datetime
    student_id: int
    dept_id: int
    assigned_to: Optional[int]
    class Config:
        from_attributes = True

# ── COMPLAINT STATUS ─────────────────────
class StatusUpdate(BaseModel):
    week_number: int
    status_label: str
    remarks: str
    complaint_id: int

class StatusResponse(BaseModel):
    status_id: int
    week_number: int
    status_label: str
    remarks: str
    updated_at: datetime
    complaint_id: int
    class Config:
        from_attributes = True