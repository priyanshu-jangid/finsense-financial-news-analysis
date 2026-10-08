from pydantic import BaseModel, ConfigDict, Field


class CompanyCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=200)
    sector: str | None = Field(default=None, max_length=100)


class CompanyResponse(BaseModel):
    id: int
    ticker: str
    name: str
    sector: str | None

    model_config = ConfigDict(from_attributes=True)
