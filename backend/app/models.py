from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship

from .database import Base
from .utils import utcnow


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(50))
    role = Column(String(20), nullable=False, default="viewer")  # admin / manager / viewer
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=utcnow)


class SystemSetting(Base):
    __tablename__ = "system_settings"
    id = Column(Integer, primary_key=True)
    key = Column(String(80), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False, default="")
    description = Column(String(255))
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class Teacher(Base):
    __tablename__ = "teachers"
    id = Column(Integer, primary_key=True)
    teacher_no = Column(String(30), unique=True, nullable=False, index=True)
    name = Column(String(50), nullable=False, index=True)
    gender = Column(String(10))
    birth_year = Column(Integer)
    college = Column(String(80), nullable=False, index=True)
    department = Column(String(80))
    discipline = Column(String(80), nullable=False, index=True)
    degree = Column(String(20))
    title = Column(String(20), nullable=False, index=True)
    position = Column(String(50))
    hire_date = Column(Date)
    research_direction = Column(Text)
    bio = Column(Text)
    skills = Column(Text)
    research_keywords = Column(Text)
    status = Column(String(20), nullable=False, default="active", index=True)
    advisor_qualified = Column(Boolean, nullable=False, default=False)
    enrollment_status = Column(String(20), nullable=False, default="closed")  # open/full/closed
    capacity = Column(Integer, nullable=False, default=0)
    current_students = Column(Integer, nullable=False, default=0)
    phone = Column(String(30))
    email = Column(String(120))
    data_source = Column(String(80), default="模拟数据")
    verification_status = Column(String(20), nullable=False, default="verified")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    outputs = relationship("ResearchOutput", back_populates="teacher")
    teaching_records = relationship("TeachingRecord", back_populates="teacher")
    service_records = relationship("ServiceRecord", back_populates="teacher")


class ResearchOutput(Base):
    __tablename__ = "research_outputs"
    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False, index=True)
    output_type = Column(String(30), nullable=False, index=True)  # paper/patent/book/report
    title = Column(String(300), nullable=False, index=True)
    venue = Column(String(200))
    publish_date = Column(Date, index=True)
    level = Column(String(30))
    authors = Column(String(300))
    doi = Column(String(120))
    data_source = Column(String(80), default="模拟数据")
    created_at = Column(DateTime, default=utcnow)
    teacher = relationship("Teacher", back_populates="outputs")

    __table_args__ = (Index("ix_output_teacher_title", "teacher_id", "title"),)


class ResearchProject(Base):
    __tablename__ = "research_projects"
    id = Column(Integer, primary_key=True)
    project_no = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(300), nullable=False, index=True)
    level = Column(String(50))
    funding = Column(Float, default=0)
    start_date = Column(Date)
    end_date = Column(Date)
    principal_teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False, index=True)
    status = Column(String(20), default="ongoing")
    data_source = Column(String(80), default="模拟数据")
    created_at = Column(DateTime, default=utcnow)
    principal = relationship("Teacher", foreign_keys=[principal_teacher_id])
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")


class ProjectMember(Base):
    __tablename__ = "project_members"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("research_projects.id"), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False, index=True)
    role = Column(String(50), default="参与人")
    contribution_pct = Column(Float, default=0)
    project = relationship("ResearchProject", back_populates="members")
    teacher = relationship("Teacher")

    __table_args__ = (UniqueConstraint("project_id", "teacher_id", name="uq_project_teacher"),)


class TeachingRecord(Base):
    __tablename__ = "teaching_records"
    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False, index=True)
    course_name = Column(String(200), nullable=False)
    academic_year = Column(String(20), index=True)
    semester = Column(String(20))
    hours = Column(Float, default=0)
    student_count = Column(Integer, default=0)
    teaching_level = Column(String(20))  # 本科/研究生
    evaluation_score = Column(Float)
    achievement = Column(Text)
    data_source = Column(String(80), default="模拟数据")
    created_at = Column(DateTime, default=utcnow)
    teacher = relationship("Teacher", back_populates="teaching_records")


class ServiceRecord(Base):
    __tablename__ = "service_records"
    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False, index=True)
    service_type = Column(String(30), nullable=False, index=True)  # award/academic_post/social_service
    name = Column(String(300), nullable=False)
    organization = Column(String(200))
    role = Column(String(100))
    start_date = Column(Date)
    end_date = Column(Date)
    description = Column(Text)
    data_source = Column(String(80), default="模拟数据")
    created_at = Column(DateTime, default=utcnow)
    teacher = relationship("Teacher", back_populates="service_records")


class StudentProfile(Base):
    __tablename__ = "student_profiles"
    id = Column(Integer, primary_key=True)
    student_no = Column(String(30), unique=True, nullable=False, index=True)
    name = Column(String(50), nullable=False)
    major = Column(String(80), nullable=False)
    discipline = Column(String(80), nullable=False)
    research_interest = Column(Text)
    keywords = Column(Text)
    desired_direction = Column(Text)
    training_needs = Column(Text)
    degree_goal = Column(String(30))
    other_conditions = Column(Text)
    created_at = Column(DateTime, default=utcnow)


class AdvisorMatchTask(Base):
    __tablename__ = "advisor_match_tasks"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("student_profiles.id"), nullable=False, index=True)
    name = Column(String(120))
    weights = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    created_by = Column(String(50))
    error = Column(Text)
    created_at = Column(DateTime, default=utcnow)
    completed_at = Column(DateTime)
    student = relationship("StudentProfile")
    results = relationship("AdvisorMatchResult", back_populates="task", cascade="all, delete-orphan")


class AdvisorMatchResult(Base):
    __tablename__ = "advisor_match_results"
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("advisor_match_tasks.id"), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False, index=True)
    total_score = Column(Float, default=0)
    direction_score = Column(Float, default=0)
    topic_score = Column(Float, default=0)
    need_score = Column(Float, default=0)
    capacity_score = Column(Float, default=0)
    qualified = Column(Boolean, default=True)
    reasons = Column(Text)
    disqualifiers = Column(Text)
    rank = Column(Integer)
    human_confirmed = Column(Boolean, default=False)
    note = Column(Text)
    created_at = Column(DateTime, default=utcnow)
    task = relationship("AdvisorMatchTask", back_populates="results")
    teacher = relationship("Teacher")


class PromotionBatch(Base):
    __tablename__ = "promotion_batches"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    year = Column(Integer, nullable=False)
    title_type = Column(String(30), nullable=False)
    college = Column(String(80))
    deadline = Column(Date)
    status = Column(String(20), nullable=False, default="draft")  # draft/open/completed
    created_at = Column(DateTime, default=utcnow)
    requirements = relationship("PromotionRequirement", back_populates="batch", cascade="all, delete-orphan")
    materials = relationship("PromotionMaterial", back_populates="batch", cascade="all, delete-orphan")


class PromotionRequirement(Base):
    __tablename__ = "promotion_requirements"
    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey("promotion_batches.id"), nullable=False, index=True)
    category = Column(String(30), nullable=False)  # paper/project/award/teaching/service
    name = Column(String(200), nullable=False)
    requirement_desc = Column(Text)
    min_count = Column(Integer, nullable=False, default=1)
    mandatory = Column(Boolean, default=True)
    keywords = Column(String(300))
    window_years = Column(Integer, default=5)
    principal_only = Column(Boolean, default=False)
    batch = relationship("PromotionBatch", back_populates="requirements")


class PromotionMaterial(Base):
    __tablename__ = "promotion_materials"
    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey("promotion_batches.id"), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False, index=True)
    requirement_id = Column(Integer, ForeignKey("promotion_requirements.id"), nullable=False, index=True)
    category = Column(String(30), nullable=False)
    title = Column(String(300), nullable=False)
    output_type = Column(String(30))
    output_ref = Column(String(80))
    matched_count = Column(Integer, default=0)
    status = Column(String(30), nullable=False, default="matched")
    note = Column(Text)
    updated_by = Column(String(50))
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    batch = relationship("PromotionBatch", back_populates="materials")
    requirement = relationship("PromotionRequirement")


class JobPosition(Base):
    __tablename__ = "job_positions"
    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    college = Column(String(80), nullable=False)
    discipline = Column(String(80), nullable=False)
    research_direction = Column(Text)
    required_degree = Column(String(20), default="博士")
    min_outputs = Column(Integer, default=0)
    research_topics = Column(Text)
    requirements_desc = Column(Text)
    weights = Column(Text)
    status = Column(String(20), default="open")
    created_at = Column(DateTime, default=utcnow)


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    position_id = Column(Integer, ForeignKey("job_positions.id"), nullable=False, index=True)
    degree = Column(String(20))
    graduate_school = Column(String(120))
    major = Column(String(80))
    research_direction = Column(Text)
    keywords = Column(Text)
    outputs_count = Column(Integer, default=0)
    projects_count = Column(Integer, default=0)
    teaching_years = Column(Float, default=0)
    output_evidence = Column(Text)
    project_evidence = Column(Text)
    teaching_evidence = Column(Text)
    source = Column(String(120), default="模拟数据")
    unverified_fields = Column(String(300))
    created_at = Column(DateTime, default=utcnow)
    position = relationship("JobPosition")


class CandidateEvaluation(Base):
    __tablename__ = "candidate_evaluations"
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidate_profiles.id"), nullable=False, index=True)
    position_id = Column(Integer, ForeignKey("job_positions.id"), nullable=False, index=True)
    hard_pass = Column(Boolean, default=False)
    direction_score = Column(Float, default=0)
    outputs_score = Column(Float, default=0)
    projects_score = Column(Float, default=0)
    teaching_score = Column(Float, default=0)
    total_score = Column(Float, default=0)
    rank = Column(Integer)
    reasons = Column(Text)
    gaps = Column(Text)
    evidence = Column(Text)
    review_status = Column(String(20), default="pending")  # pending/reviewed/shortlisted/rejected
    reviewer = Column(String(50))
    review_note = Column(Text)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    candidate = relationship("CandidateProfile")
    position = relationship("JobPosition")

    __table_args__ = (UniqueConstraint("candidate_id", "position_id", name="uq_candidate_position"),)


class ImportBatch(Base):
    __tablename__ = "import_batches"
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    import_type = Column(String(30), nullable=False)
    total_rows = Column(Integer, default=0)
    success_rows = Column(Integer, default=0)
    failed_rows = Column(Integer, default=0)
    duplicate_rows = Column(Integer, default=0)
    status = Column(String(20), default="completed")
    created_by = Column(String(50))
    created_at = Column(DateTime, default=utcnow)
    errors = relationship("ImportRowError", back_populates="batch", cascade="all, delete-orphan")


class ImportRowError(Base):
    __tablename__ = "import_row_errors"
    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey("import_batches.id"), nullable=False, index=True)
    row_number = Column(Integer, nullable=False)
    column_name = Column(String(80))
    error_message = Column(String(400), nullable=False)
    raw_value = Column(String(300))
    batch = relationship("ImportBatch", back_populates="errors")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    username = Column(String(50))
    action = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    resource_id = Column(String(50))
    detail = Column(Text)
    ip = Column(String(50))
    created_at = Column(DateTime, default=utcnow, index=True)
