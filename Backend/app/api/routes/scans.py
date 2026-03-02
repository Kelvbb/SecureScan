from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.scan import Scan
from app.schemas.scan import ScanCreate, ScanResponse, ScanList

router = APIRouter()


@router.post("", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
def create_scan(payload: ScanCreate, db: Session = Depends(get_db)) -> ScanResponse:
    scan = Scan(
        user_id=payload.user_id,
        repository_url=payload.repository_url,
        upload_path=payload.upload_path,
        status="pending",
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return ScanResponse.model_validate(scan)


@router.get("/{scan_id}", response_model=ScanResponse)
def get_scan(scan_id: UUID, db: Session = Depends(get_db)) -> ScanResponse:
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return ScanResponse.model_validate(scan)


@router.get("", response_model=list[ScanList])
def list_scans(
    user_id: UUID | None = None,
    db: Session = Depends(get_db),
) -> list[ScanList]:
    q = db.query(Scan)
    if user_id is not None:
        q = q.filter(Scan.user_id == user_id)
    scans = q.order_by(Scan.created_at.desc()).all()
    return [ScanList.model_validate(s) for s in scans]
