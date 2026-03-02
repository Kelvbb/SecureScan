"""Schémas Pydantic pour l'API."""

from app.schemas.user import UserCreate, UserResponse
from app.schemas.scan import ScanCreate, ScanResponse, ScanList
from app.schemas.vulnerability import VulnerabilityResponse, VulnerabilityList
from app.schemas.owasp import OwaspCategoryResponse
from app.schemas.health import HealthResponse

__all__ = [
    "UserCreate",
    "UserResponse",
    "ScanCreate",
    "ScanResponse",
    "ScanList",
    "VulnerabilityResponse",
    "VulnerabilityList",
    "OwaspCategoryResponse",
    "HealthResponse",
]
