from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
import os, shutil, uuid

import models, schemas
from database import engine, get_db
from auth import hash_password, verify_password, create_access_token, decode_token

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="College Complaint System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads",   StaticFiles(directory="uploads"),   name="uploads")
app.mount("/static",    StaticFiles(directory="static"),    name="static")
app.mount("/templates", StaticFiles(directory="templates"), name="templates")

# ── DEPARTMENTS ──────────────────────────────────────────
@app.get("/departments", response_model=list[schemas.DepartmentResponse])
def get_departments(db: Session = Depends(get_db)):
    return db.query(models.Department).all()

# ── REGISTER ─────────────────────────────────────────────
@app.post("/register/student", response_model=schemas.StudentResponse)
def register_student(data: schemas.StudentRegister, db: Session = Depends(get_db)):
    if not data.email.endswith("@bgscet.ac.in"):
        raise HTTPException(status_code=400, detail="Only @bgscet.ac.in email addresses are allowed")
    if db.query(models.Student).filter(models.Student.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    student = models.Student(
        name=data.name, email=data.email,
        password_hash=hash_password(data.password),
        phone=data.phone, dept_id=data.dept_id
    )
    db.add(student); db.commit(); db.refresh(student)
    return student

@app.post("/register/staff", response_model=schemas.StaffResponse)
def register_staff(data: schemas.StaffRegister, db: Session = Depends(get_db)):
    if not data.email.endswith("@bgscet.ac.in"):
        raise HTTPException(status_code=400, detail="Only @bgscet.ac.in email addresses are allowed")
    if db.query(models.Staff).filter(models.Staff.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    staff = models.Staff(
        name=data.name, email=data.email,
        password_hash=hash_password(data.password),
        role=data.role, dept_id=data.dept_id
    )
    db.add(staff); db.commit(); db.refresh(staff)
    return staff

# ── LOGIN ─────────────────────────────────────────────────
@app.post("/login", response_model=schemas.TokenResponse)
def login(data: schemas.LoginRequest, db: Session = Depends(get_db)):
    if data.role == "student":
        user = db.query(models.Student).filter(models.Student.email == data.email).first()
        if not user or not verify_password(data.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        token = create_access_token({"sub": user.email, "role": "student", "id": user.student_id})
        return {"access_token": token, "token_type": "bearer", "role": "student", "name": user.name}
    elif data.role == "staff":
        user = db.query(models.Staff).filter(models.Staff.email == data.email).first()
        if not user or not verify_password(data.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        token = create_access_token({"sub": user.email, "role": user.role, "id": user.staff_id})
        return {"access_token": token, "token_type": "bearer", "role": user.role, "name": user.name}
    raise HTTPException(status_code=400, detail="Invalid role")

# ── COMPLAINTS ────────────────────────────────────────────
@app.post("/complaints", response_model=schemas.ComplaintResponse)
def create_complaint(
    title:       str = Form(...),
    description: str = Form(...),
    category:    str = Form(...),
    priority:    str = Form(...),
    dept_id:     int = Form(...),
    files: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user: dict = Depends(decode_token)
):
    student = db.query(models.Student).filter(models.Student.email == current_user["email"]).first()
    if not student:
        raise HTTPException(status_code=403, detail="Only students can file complaints")

    complaint = models.Complaint(
        title=title, description=description, category=category,
        priority=priority, dept_id=dept_id,
        student_id=student.student_id, current_status="Open"
    )
    db.add(complaint); db.commit(); db.refresh(complaint)

    for file in files:
        if file.filename:
            ext       = file.filename.split(".")[-1].lower()
            file_type = "video" if ext in ["mp4","mov","avi"] else "image"
            fname     = f"{uuid.uuid4()}.{ext}"
            fpath     = f"uploads/{fname}"
            with open(fpath, "wb") as buf:
                shutil.copyfileobj(file.file, buf)
            db.add(models.ComplaintProof(
                file_path=fpath, file_type=file_type,
                complaint_id=complaint.complaint_id
            ))
    db.commit()
    return complaint

@app.get("/complaints")
def get_complaints(
    search:   Optional[str] = Query(None),
    status:   Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    page:     int = Query(1, ge=1),
    limit:    int = Query(20, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(decode_token)
):
    query = db.query(models.Complaint)

    if current_user["role"] == "student":
        student = db.query(models.Student).filter(models.Student.email == current_user["email"]).first()
        query   = query.filter(models.Complaint.student_id == student.student_id)

    if search:
        query = query.filter(or_(
            models.Complaint.title.ilike(f"%{search}%"),
            models.Complaint.description.ilike(f"%{search}%")
        ))
    if status:   query = query.filter(models.Complaint.current_status == status)
    if category: query = query.filter(models.Complaint.category == category)
    if priority: query = query.filter(models.Complaint.priority == priority)

    complaints = query.order_by(models.Complaint.created_at.desc()).offset((page-1)*limit).limit(limit).all()

    result = []
    for c in complaints:
        student = db.query(models.Student).filter(models.Student.student_id == c.student_id).first()
        result.append({
            "complaint_id":   c.complaint_id,
            "title":          c.title,
            "description":    c.description,
            "category":       c.category,
            "priority":       c.priority,
            "current_status": c.current_status,
            "created_at":     c.created_at,
            "student_id":     c.student_id,
            "student_name":   student.name if student else "Unknown",
            "dept_id":        c.dept_id,
            "assigned_to":    c.assigned_to
        })
    return result

@app.get("/complaints/{complaint_id}", response_model=schemas.ComplaintResponse)
def get_complaint(complaint_id: int, db: Session = Depends(get_db), current_user: dict = Depends(decode_token)):
    c = db.query(models.Complaint).filter(models.Complaint.complaint_id == complaint_id).first()
    if not c: raise HTTPException(status_code=404, detail="Not found")
    return c

@app.get("/complaints/{complaint_id}/detail")
def get_complaint_detail(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(decode_token)
):
    c = db.query(models.Complaint).filter(models.Complaint.complaint_id == complaint_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    student = db.query(models.Student).filter(models.Student.student_id == c.student_id).first()
    proofs  = db.query(models.ComplaintProof).filter(models.ComplaintProof.complaint_id == complaint_id).all()
    assigned_staff = None
    if c.assigned_to:
        s = db.query(models.Staff).filter(models.Staff.staff_id == c.assigned_to).first()
        assigned_staff = s.name if s else None
    return {
        "complaint_id":        c.complaint_id,
        "title":               c.title,
        "description":         c.description,
        "category":            c.category,
        "priority":            c.priority,
        "current_status":      c.current_status,
        "created_at":          c.created_at,
        "student_name":        student.name  if student else "Unknown",
        "student_email":       student.email if student else "Unknown",
        "dept_id":             c.dept_id,
        "assigned_to":         c.assigned_to,
        "assigned_staff_name": assigned_staff,
        "proofs": [{"proof_id": p.proof_id, "file_path": p.file_path, "file_type": p.file_type} for p in proofs]
    }

@app.put("/complaints/{complaint_id}/assign")
def assign_complaint(
    complaint_id: int,
    staff_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(decode_token)
):
    if current_user["role"] == "student":
        raise HTTPException(status_code=403, detail="Not authorized")
    c = db.query(models.Complaint).filter(models.Complaint.complaint_id == complaint_id).first()
    if not c: raise HTTPException(status_code=404, detail="Not found")
    c.assigned_to    = staff_id
    c.current_status = "In Progress"
    db.commit()
    return {"message": "Assigned successfully"}

@app.put("/complaints/{complaint_id}/status")
def update_status(
    complaint_id: int,
    data: schemas.StatusUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(decode_token)
):
    if current_user["role"] == "student":
        raise HTTPException(status_code=403, detail="Not authorized")
    staff = db.query(models.Staff).filter(models.Staff.email == current_user["email"]).first()
    c     = db.query(models.Complaint).filter(models.Complaint.complaint_id == complaint_id).first()
    if not c: raise HTTPException(status_code=404, detail="Not found")
    db.add(models.ComplaintStatus(
        week_number=data.week_number, status_label=data.status_label,
        remarks=data.remarks, complaint_id=complaint_id, updated_by=staff.staff_id
    ))
    c.current_status = "Resolved" if data.status_label == "Resolved" else "In Progress"
    db.commit()
    return {"message": "Status updated"}

@app.put("/complaints/{complaint_id}/reject")
def reject_complaint(
    complaint_id: int,
    reason: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(decode_token)
):
    if current_user["role"] == "student":
        raise HTTPException(status_code=403, detail="Not authorized")
    c = db.query(models.Complaint).filter(models.Complaint.complaint_id == complaint_id).first()
    if not c: raise HTTPException(status_code=404, detail="Not found")
    c.current_status = "Rejected"
    staff = db.query(models.Staff).filter(models.Staff.email == current_user["email"]).first()
    db.add(models.ComplaintStatus(
        week_number=0,
        status_label="Rejected",
        remarks=f"Rejected: {reason}",
        complaint_id=complaint_id,
        updated_by=staff.staff_id
    ))
    db.commit()
    return {"message": "Complaint rejected"}

@app.get("/complaints/{complaint_id}/status", response_model=list[schemas.StatusResponse])
def get_status_history(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(decode_token)
):
    return db.query(models.ComplaintStatus).filter(
        models.ComplaintStatus.complaint_id == complaint_id
    ).order_by(models.ComplaintStatus.week_number).all()

@app.get("/complaints/{complaint_id}/proofs")
def get_proofs(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(decode_token)
):
    proofs = db.query(models.ComplaintProof).filter(
        models.ComplaintProof.complaint_id == complaint_id
    ).all()
    return [{"proof_id": p.proof_id, "file_path": p.file_path, "file_type": p.file_type} for p in proofs]

@app.get("/staff/list")
def get_staff_list(
    db: Session = Depends(get_db),
    current_user: dict = Depends(decode_token)
):
    if current_user["role"] == "student":
        raise HTTPException(status_code=403, detail="Not authorized")
    staff = db.query(models.Staff).all()
    return [{"staff_id": s.staff_id, "name": s.name, "role": s.role, "dept_id": s.dept_id} for s in staff]

@app.put("/change-password")
def change_password(
    old_password: str,
    new_password: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(decode_token)
):
    if current_user["role"] == "student":
        user = db.query(models.Student).filter(models.Student.email == current_user["email"]).first()
    else:
        user = db.query(models.Staff).filter(models.Staff.email == current_user["email"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not verify_password(old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.password_hash = hash_password(new_password)
    db.commit()
    return {"message": "Password changed successfully"}

@app.get("/analytics/summary")
def get_summary(
    db: Session = Depends(get_db),
    current_user: dict = Depends(decode_token)
):
    all_c = db.query(models.Complaint).all()
    return {
        "total":       len(all_c),
        "open":        sum(1 for c in all_c if c.current_status == "Open"),
        "in_progress": sum(1 for c in all_c if c.current_status == "In Progress"),
        "resolved":    sum(1 for c in all_c if c.current_status == "Resolved"),
        "rejected":    sum(1 for c in all_c if c.current_status == "Rejected"),
        "by_category": {
            "Canteen":        sum(1 for c in all_c if c.category == "Canteen"),
            "Hostel":         sum(1 for c in all_c if c.category == "Hostel"),
            "Academic":       sum(1 for c in all_c if c.category == "Academic"),
            "Infrastructure": sum(1 for c in all_c if c.category == "Infrastructure"),
            "Library":        sum(1 for c in all_c if c.category == "Library"),
            "Harassment":     sum(1 for c in all_c if c.category == "Harassment"),
            "Transport":      sum(1 for c in all_c if c.category == "Transport"),
            "Administration": sum(1 for c in all_c if c.category == "Administration"),
        },
        "by_priority": {
            "High":   sum(1 for c in all_c if c.priority == "High"),
            "Medium": sum(1 for c in all_c if c.priority == "Medium"),
            "Low":    sum(1 for c in all_c if c.priority == "Low"),
        }
    }