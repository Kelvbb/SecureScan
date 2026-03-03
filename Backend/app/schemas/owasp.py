from pydantic import BaseModel, ConfigDict


class OwaspCategoryResponse(BaseModel):
    id: str
    name: str
    description: str | None

    model_config = ConfigDict(from_attributes=True)
