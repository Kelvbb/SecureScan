import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SuggestedFix(Base):
    __tablename__ = "suggested_fixes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    vulnerability_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vulnerabilities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Type de fix (ex : "sql_injection") — clé dans OWASP_CATEGORY_BY_FIX_TYPE
    fix_type: Mapped[str] = mapped_column(Text, nullable=False)
    # Explication pédagogique générée par le template
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Diff unified pour l'affichage côte-à-côte et la reconstruction de fixed_line
    patch_diff: Mapped[str | None] = mapped_column(Text, nullable=True)
    # True si applicable sans intervention manuelle
    auto_applicable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    vulnerability = relationship(
        "Vulnerability",
        back_populates="suggested_fixes",
        lazy="select",
    )
