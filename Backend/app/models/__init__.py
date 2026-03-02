"""Modèles SQLAlchemy (alignés sur securescanbdd.sql)."""

from app.models.user import User
from app.models.scan import Scan
from app.models.security_tool import SecurityTool
from app.models.tool_execution import ToolExecution
from app.models.owasp_category import OwaspCategory
from app.models.vulnerability import Vulnerability
from app.models.suggested_fix import SuggestedFix
from app.models.scan_metrics import ScanMetrics

__all__ = [
    "User",
    "Scan",
    "SecurityTool",
    "ToolExecution",
    "OwaspCategory",
    "Vulnerability",
    "SuggestedFix",
    "ScanMetrics",
]
