from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shared.models import Company
from backend.app.schemas.company import CompanyCreate


def create_company(
    db: Session,
    company_data: CompanyCreate,
) -> Company:
    company = Company(
        ticker=company_data.ticker.upper(),
        name=company_data.name,
        sector=company_data.sector,
    )

    db.add(company)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("A company with this ticker already exists")

    db.refresh(company)

    return company


def get_companies(db: Session) -> list[Company]:
    return db.query(Company).order_by(Company.ticker).all()


def get_company(
    db: Session,
    company_id: int,
) -> Company | None:
    return db.query(Company).filter(
        Company.id == company_id
    ).first()
