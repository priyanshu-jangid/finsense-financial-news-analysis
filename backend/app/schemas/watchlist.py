from pydantic import BaseModel, ConfigDict


class WatchlistCreate(BaseModel):
    company_id: int


class WatchlistResponse(BaseModel):
    id: int
    user_id: int
    company_id: int

    model_config = ConfigDict(from_attributes=True)
