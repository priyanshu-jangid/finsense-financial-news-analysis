from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.schemas.company import CompanyCreate, CompanyResponse
from backend.app.services.company_service import (
    create_company,
    get_companies,
    get_company,
)


router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
)


@router.post(
    "",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_company_endpoint(
    company_data: CompanyCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_company(db, company_data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

@router.get(
    "",
    response_model=list[CompanyResponse],
)
def list_companies(
    db: Session = Depends(get_db),
):
    return get_companies(db)


@router.get(
    "/{company_id}",
    response_model=CompanyResponse,
)
def get_company_endpoint(
    company_id: int,
    db: Session = Depends(get_db),
):
    company = get_company(db, company_id)

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    return company
