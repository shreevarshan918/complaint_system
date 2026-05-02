from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Department(Base):
    __tablename__ = "department"

    department_id = Column(Integer, primary_key=True, index=True)
    dept_name     = Column(String(100), nullable=False, unique=True)
    dept_head     = Column(String(100), nullable=False)

    students    = relationship("Student", back_populates="department")
    staff       = relationship("Staff", back_populates="department")
    complaints  = relationship("Complaint", back_populates="department")


class Student(Base):
    __tablename__ = "student"

    student_id    = Column(Integer, primary_key=True, index=True)
    name          = Column(String(100), nullable=False)
    email         = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    phone         = Column(String(15))
    dept_id       = Column(Integer, ForeignKey("department.department_id"), nullable=False)

    department = relationship("Department", back_populates="students")
    complaints = relationship("Complaint", back_populates="student")


class Staff(Base):
    __tablename__ = "staff"

    staff_id      = Column(Integer, primary_key=True, index=True)
    name          = Column(String(100), nullable=False)
    email         = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    role          = Column(String(50))
    dept_id       = Column(Integer, ForeignKey("department.department_id"), nullable=False)

    department        = relationship("Department", back_populates="staff")
    assigned_complaints = relationship("Complaint", back_populates="assigned_staff")
    status_updates    = relationship("ComplaintStatus", back_populates="staff")


class Complaint(Base):
    __tablename__ = "complaint"

    complaint_id   = Column(Integer, primary_key=True, index=True)
    title          = Column(String(200), nullable=False)
    description    = Column(Text, nullable=False)
    category       = Column(String(50))
    priority       = Column(String(20))
    current_status = Column(String(20), default="Open")
    created_at     = Column(DateTime, server_default=func.now())
    student_id     = Column(Integer, ForeignKey("student.student_id"), nullable=False)
    dept_id        = Column(Integer, ForeignKey("department.department_id"), nullable=False)
    assigned_to    = Column(Integer, ForeignKey("staff.staff_id"), nullable=True)

    student        = relationship("Student", back_populates="complaints")
    department     = relationship("Department", back_populates="complaints")
    assigned_staff = relationship("Staff", back_populates="assigned_complaints")
    proofs         = relationship("ComplaintProof", back_populates="complaint")
    statuses       = relationship("ComplaintStatus", back_populates="complaint")


class ComplaintProof(Base):
    __tablename__ = "complaint_proof"

    proof_id     = Column(Integer, primary_key=True, index=True)
    file_path    = Column(String(500), nullable=False)
    file_type    = Column(String(10))
    uploaded_at  = Column(DateTime, server_default=func.now())
    complaint_id = Column(Integer, ForeignKey("complaint.complaint_id"), nullable=False)

    complaint = relationship("Complaint", back_populates="proofs")


class ComplaintStatus(Base):
    __tablename__ = "complaint_status"

    status_id    = Column(Integer, primary_key=True, index=True)
    week_number  = Column(Integer, nullable=False)
    status_label = Column(String(50))
    remarks      = Column(Text)
    updated_at   = Column(DateTime, server_default=func.now())
    complaint_id = Column(Integer, ForeignKey("complaint.complaint_id"), nullable=False)
    updated_by   = Column(Integer, ForeignKey("staff.staff_id"), nullable=False)

    complaint = relationship("Complaint", back_populates="statuses")
    staff     = relationship("Staff", back_populates="status_updates")  