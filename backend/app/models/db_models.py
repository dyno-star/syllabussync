from sqlalchemy import Column, String, Float, Date, DateTime, Boolean, ForeignKey, Text, Uuid
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.db import Base


class Course(Base):
    __tablename__ = "courses"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    course_code = Column(String, nullable=True)
    course_name = Column(String, nullable=True)
    instructor = Column(String, nullable=True)
    term = Column(String, nullable=True)
    source_filename = Column(String, nullable=True)
    needs_review = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    assignments = relationship(
        "Assignment", back_populates="course", cascade="all, delete-orphan"
    )


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    course_id = Column(Uuid, ForeignKey("courses.id"), nullable=False)

    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    weight_pct = Column(Float, nullable=True)
    due_date = Column(Date, nullable=True)
    raw_source_text = Column(Text, nullable=True)
    confidence = Column(Float, default=0.5)

    # Tracks whether a human has corrected this field after extraction —
    # useful later for measuring real-world extraction accuracy beyond
    # the eval fixture set (how often do users actually fix things?)
    human_corrected = Column(Boolean, default=False)

    course = relationship("Course", back_populates="assignments")
