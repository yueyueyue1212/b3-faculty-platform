from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

TITLES = ["教授", "副教授", "讲师", "助教"]
DEGREES = ["博士", "硕士", "学士", "其他"]
TEACHER_STATUSES = ["active", "on_leave", "retired"]
OUTPUT_TYPES = ["paper", "patent", "book", "report"]
SERVICE_TYPES = ["award", "academic_post", "social_service"]


def _email_ok(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    if "@" not in value or "." not in value.split("@")[-1]:
        raise ValueError("邮箱格式不正确")
    return value


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=100)


class TeacherBase(BaseModel):
    teacher_no: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=50)
    gender: Optional[str] = None
    birth_year: Optional[int] = Field(default=None, ge=1900, le=2010)
    college: str = Field(min_length=1, max_length=80)
    department: Optional[str] = None
    discipline: str = Field(min_length=1, max_length=80)
    degree: Optional[str] = None
    title: str = Field(min_length=1, max_length=20)
    position: Optional[str] = None
    hire_date: Optional[date] = None
    research_direction: Optional[str] = None
    bio: Optional[str] = None
    skills: Optional[str] = None
    research_keywords: Optional[str] = None
    status: str = "active"
    advisor_qualified: bool = False
    enrollment_status: str = "closed"
    capacity: int = Field(default=0, ge=0, le=100)
    current_students: int = Field(default=0, ge=0, le=100)
    phone: Optional[str] = None
    email: Optional[str] = None
    data_source: Optional[str] = "手动录入"
    verification_status: str = "verified"

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        return _email_ok(value)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value):
        if value not in TITLES:
            raise ValueError(f"职称必须是：{'/'.join(TITLES)}")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value):
        if value not in TEACHER_STATUSES:
            raise ValueError("教师状态不合法")
        return value

    @field_validator("enrollment_status")
    @classmethod
    def validate_enrollment(cls, value):
        if value not in ("open", "full", "closed"):
            raise ValueError("招生状态不合法")
        return value


class TeacherCreate(TeacherBase):
    pass


class TeacherUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    teacher_no: Optional[str] = Field(default=None, min_length=1, max_length=30)
    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    gender: Optional[str] = None
    birth_year: Optional[int] = Field(default=None, ge=1900, le=2010)
    college: Optional[str] = None
    department: Optional[str] = None
    discipline: Optional[str] = None
    degree: Optional[str] = None
    title: Optional[str] = None
    position: Optional[str] = None
    hire_date: Optional[date] = None
    research_direction: Optional[str] = None
    bio: Optional[str] = None
    skills: Optional[str] = None
    research_keywords: Optional[str] = None
    status: Optional[str] = None
    advisor_qualified: Optional[bool] = None
    enrollment_status: Optional[str] = None
    capacity: Optional[int] = Field(default=None, ge=0, le=100)
    current_students: Optional[int] = Field(default=None, ge=0, le=100)
    phone: Optional[str] = None
    email: Optional[str] = None
    data_source: Optional[str] = None
    verification_status: Optional[str] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        return _email_ok(value)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value):
        if value is not None and value not in TITLES:
            raise ValueError(f"职称必须是：{'/'.join(TITLES)}")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value):
        if value is not None and value not in TEACHER_STATUSES:
            raise ValueError("教师状态不合法")
        return value


class ResearchOutputCreate(BaseModel):
    teacher_id: int
    output_type: str
    title: str = Field(min_length=1, max_length=300)
    venue: Optional[str] = None
    publish_date: Optional[date] = None
    level: Optional[str] = None
    authors: Optional[str] = None
    doi: Optional[str] = None
    data_source: Optional[str] = "手动录入"

    @field_validator("output_type")
    @classmethod
    def validate_type(cls, value):
        if value not in OUTPUT_TYPES:
            raise ValueError(f"成果类型必须是：{'/'.join(OUTPUT_TYPES)}")
        return value


class ResearchOutputUpdate(BaseModel):
    output_type: Optional[str] = None
    title: Optional[str] = None
    venue: Optional[str] = None
    publish_date: Optional[date] = None
    level: Optional[str] = None
    authors: Optional[str] = None
    doi: Optional[str] = None
    data_source: Optional[str] = None


class ProjectCreate(BaseModel):
    project_no: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=300)
    level: Optional[str] = None
    funding: float = Field(default=0, ge=0)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    principal_teacher_id: int
    status: str = "ongoing"
    member_ids: list[int] = []
    data_source: Optional[str] = "手动录入"


class ProjectUpdate(BaseModel):
    project_no: Optional[str] = None
    name: Optional[str] = None
    level: Optional[str] = None
    funding: Optional[float] = Field(default=None, ge=0)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    principal_teacher_id: Optional[int] = None
    status: Optional[str] = None
    member_ids: Optional[list[int]] = None
    data_source: Optional[str] = None


class TeachingCreate(BaseModel):
    teacher_id: int
    course_name: str = Field(min_length=1, max_length=200)
    academic_year: str = Field(min_length=4, max_length=20)
    semester: Optional[str] = None
    hours: float = Field(default=0, ge=0)
    student_count: int = Field(default=0, ge=0)
    teaching_level: Optional[str] = None
    evaluation_score: Optional[float] = Field(default=None, ge=0, le=100)
    achievement: Optional[str] = None
    data_source: Optional[str] = "手动录入"


class TeachingUpdate(BaseModel):
    course_name: Optional[str] = None
    academic_year: Optional[str] = None
    semester: Optional[str] = None
    hours: Optional[float] = Field(default=None, ge=0)
    student_count: Optional[int] = Field(default=None, ge=0)
    teaching_level: Optional[str] = None
    evaluation_score: Optional[float] = Field(default=None, ge=0, le=100)
    achievement: Optional[str] = None
    data_source: Optional[str] = None


class ServiceCreate(BaseModel):
    teacher_id: int
    service_type: str
    name: str = Field(min_length=1, max_length=300)
    organization: Optional[str] = None
    role: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = None
    data_source: Optional[str] = "手动录入"

    @field_validator("service_type")
    @classmethod
    def validate_type(cls, value):
        if value not in SERVICE_TYPES:
            raise ValueError(f"服务类型必须是：{'/'.join(SERVICE_TYPES)}")
        return value


class ServiceUpdate(BaseModel):
    service_type: Optional[str] = None
    name: Optional[str] = None
    organization: Optional[str] = None
    role: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = None
    data_source: Optional[str] = None


class StudentCreate(BaseModel):
    student_no: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=50)
    major: str = Field(min_length=1, max_length=80)
    discipline: str = Field(min_length=1, max_length=80)
    research_interest: Optional[str] = None
    keywords: Optional[str] = None
    desired_direction: Optional[str] = None
    training_needs: Optional[str] = None
    degree_goal: Optional[str] = None
    other_conditions: Optional[str] = None


class StudentUpdate(BaseModel):
    name: Optional[str] = None
    major: Optional[str] = None
    discipline: Optional[str] = None
    research_interest: Optional[str] = None
    keywords: Optional[str] = None
    desired_direction: Optional[str] = None
    training_needs: Optional[str] = None
    degree_goal: Optional[str] = None
    other_conditions: Optional[str] = None


class MatchTaskCreate(BaseModel):
    student_id: int
    name: Optional[str] = None
    weights: Optional[dict[str, float]] = None


class MatchScoreRequest(BaseModel):
    student_id: int
    teacher_id: Optional[int] = None
    weights: Optional[dict[str, float]] = None


class MaterialUpdate(BaseModel):
    status: Optional[str] = None
    note: Optional[str] = None


class BatchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    year: int = Field(ge=2000, le=2100)
    title_type: str = Field(min_length=1, max_length=30)
    college: Optional[str] = None
    deadline: Optional[date] = None
    status: str = "draft"


class BatchUpdate(BaseModel):
    name: Optional[str] = None
    year: Optional[int] = None
    title_type: Optional[str] = None
    college: Optional[str] = None
    deadline: Optional[date] = None
    status: Optional[str] = None


class RequirementCreate(BaseModel):
    category: str
    name: str = Field(min_length=1, max_length=200)
    requirement_desc: Optional[str] = None
    min_count: int = Field(default=1, ge=1, le=100)
    mandatory: bool = True
    keywords: Optional[str] = None
    window_years: int = Field(default=5, ge=1, le=30)
    principal_only: bool = False


class RequirementUpdate(BaseModel):
    category: Optional[str] = None
    name: Optional[str] = None
    requirement_desc: Optional[str] = None
    min_count: Optional[int] = Field(default=None, ge=1, le=100)
    mandatory: Optional[bool] = None
    keywords: Optional[str] = None
    window_years: Optional[int] = Field(default=None, ge=1, le=30)
    principal_only: Optional[bool] = None


class PositionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    college: str = Field(min_length=1, max_length=80)
    discipline: str = Field(min_length=1, max_length=80)
    research_direction: Optional[str] = None
    required_degree: str = "博士"
    min_outputs: int = Field(default=0, ge=0, le=100)
    research_topics: Optional[str] = None
    requirements_desc: Optional[str] = None
    weights: Optional[dict[str, float]] = None
    status: str = "open"


class PositionUpdate(BaseModel):
    name: Optional[str] = None
    college: Optional[str] = None
    discipline: Optional[str] = None
    research_direction: Optional[str] = None
    required_degree: Optional[str] = None
    min_outputs: Optional[int] = Field(default=None, ge=0, le=100)
    research_topics: Optional[str] = None
    requirements_desc: Optional[str] = None
    weights: Optional[dict[str, float]] = None
    status: Optional[str] = None


class CandidateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    position_id: int
    degree: Optional[str] = None
    graduate_school: Optional[str] = None
    major: Optional[str] = None
    research_direction: Optional[str] = None
    keywords: Optional[str] = None
    outputs_count: int = Field(default=0, ge=0, le=1000)
    projects_count: int = Field(default=0, ge=0, le=1000)
    teaching_years: float = Field(default=0, ge=0, le=80)
    output_evidence: Optional[str] = None
    project_evidence: Optional[str] = None
    teaching_evidence: Optional[str] = None
    source: Optional[str] = "手动录入"
    unverified_fields: Optional[str] = None


class CandidateUpdate(BaseModel):
    name: Optional[str] = None
    degree: Optional[str] = None
    graduate_school: Optional[str] = None
    major: Optional[str] = None
    research_direction: Optional[str] = None
    keywords: Optional[str] = None
    outputs_count: Optional[int] = Field(default=None, ge=0, le=1000)
    projects_count: Optional[int] = Field(default=None, ge=0, le=1000)
    teaching_years: Optional[float] = Field(default=None, ge=0, le=80)
    output_evidence: Optional[str] = None
    project_evidence: Optional[str] = None
    teaching_evidence: Optional[str] = None
    source: Optional[str] = None
    unverified_fields: Optional[str] = None


class EvaluationReview(BaseModel):
    review_status: str
    review_note: Optional[str] = None

    @field_validator("review_status")
    @classmethod
    def validate_status(cls, value):
        if value not in ("pending", "reviewed", "shortlisted", "rejected"):
            raise ValueError("评审状态不合法")
        return value


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=100)
    display_name: Optional[str] = None
    role: str = "viewer"

    @field_validator("role")
    @classmethod
    def validate_role(cls, value):
        if value not in ("admin", "manager", "viewer"):
            raise ValueError("角色不合法")
        return value


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=6, max_length=100)


class WeightSettings(BaseModel):
    advisor_weights: Optional[dict[str, float]] = None
    candidate_weights: Optional[dict[str, float]] = None
