from pydantic import BaseModel, ConfigDict, Field, field_validator


PLACEHOLDER_VALUES = {
    "string",
    "test",
    "example",
    "none",
    "null",
    "undefined",
    "unknown",
    "n/a",
    "na",
    "your company",
    "company name",
}


class CompanyCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=200)
    sector: str | None = Field(default=None, max_length=100)

    @field_validator("ticker", "name", "sector", mode="before")
    @classmethod
    def strip_whitespace(cls, value):
        if isinstance(value, str):
            value = value.strip()
        return value

    @field_validator("ticker", "name")
    @classmethod
    def reject_placeholder_values(cls, value):
        if value.casefold() in PLACEHOLDER_VALUES:
            raise ValueError("A valid company name and ticker are required")
        return value


class CompanyResponse(BaseModel):
    id: int
    ticker: str
    name: str
    sector: str | None
    is_sp500: bool

    model_config = ConfigDict(from_attributes=True)