from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.vulnerability import Vulnerability
from app.schemas.vulnerability import VulnerabilityList, VulnerabilityResponse

router = APIRouter()


@router.get("/scan/{scan_id}", response_model=VulnerabilityList)
def list_vulnerabilities_by_scan(
    scan_id: UUID,
    db: Session = Depends(get_db),
    severity: str | None = Query(None),
    owasp_category_id: str | None = Query(None),
) -> VulnerabilityList:
    q = db.query(Vulnerability).filter(Vulnerability.scan_id == scan_id)
    if severity:
        q = q.filter(Vulnerability.severity == severity)
    if owasp_category_id:
        q = q.filter(Vulnerability.owasp_category_id == owasp_category_id)
    items = q.all()
    return VulnerabilityList(
        items=[VulnerabilityResponse.model_validate(v) for v in items],
        total=len(items),
    )


@router.get("/{vuln_id}", response_model=VulnerabilityResponse)
def get_vulnerability(
    vuln_id: UUID,
    db: Session = Depends(get_db),
) -> VulnerabilityResponse:
    vuln = db.get(Vulnerability, vuln_id)
    if not vuln:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    return VulnerabilityResponse.model_validate(vuln)
