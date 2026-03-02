from pydantic import BaseModel


class OwaspCategoryResponse(BaseModel):
    id: str
    name: str
    description: str | None

    class Config:
        from_attributes = True
