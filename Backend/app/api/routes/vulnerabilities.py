"""Routes vulnerabilities — squelette."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db

router = APIRouter()


@router.get("/scan/{scan_id}")
def list_vulnerabilities_by_scan(
    scan_id: UUID,
    db: Session = Depends(get_db),
    severity: str | None = Query(None),
    owasp_category_id: str | None = Query(None),
):
    pass


@router.get("/{vuln_id}")
def get_vulnerability(vuln_id: UUID, db: Session = Depends(get_db)):
    pass
