"""Import every model so SQLAlchemy metadata (and Alembic) sees all tables."""

from app.models.audit_log import AuditLog
from app.models.base import Base
from app.models.education import Education
from app.models.experience import Experience
from app.models.job import Job, JobMatch, JobSource, SearchRun
from app.models.preferences import JobPreferences
from app.models.profile import ProfessionalProfile
from app.models.refresh_token import RefreshToken
from app.models.resume import Resume
from app.models.skill import Skill
from app.models.user import User

__all__ = [
    "AuditLog",
    "Base",
    "Education",
    "Experience",
    "Job",
    "JobMatch",
    "JobPreferences",
    "JobSource",
    "ProfessionalProfile",
    "RefreshToken",
    "Resume",
    "SearchRun",
    "Skill",
    "User",
]
