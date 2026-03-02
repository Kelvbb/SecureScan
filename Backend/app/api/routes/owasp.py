from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.owasp_category import OwaspCategory
from app.schemas.owasp import OwaspCategoryResponse

router = APIRouter()


@router.get("", response_model=list[OwaspCategoryResponse])
def list_owasp_categories(db: Session = Depends(get_db)) -> list[OwaspCategoryResponse]:
    categories = db.query(OwaspCategory).order_by(OwaspCategory.id).all()
    return [OwaspCategoryResponse.model_validate(c) for c in categories]
