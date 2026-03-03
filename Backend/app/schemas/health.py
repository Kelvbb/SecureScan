from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    status: str = "ok"

    model_config = ConfigDict()
