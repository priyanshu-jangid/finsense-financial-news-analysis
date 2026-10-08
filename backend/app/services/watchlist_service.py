from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shared.models import Company, User, Watchlist
from backend.app.schemas.watchlist import WatchlistCreate


def add_to_watchlist(
    db: Session,
    user_id: int,
    watchlist_data: WatchlistCreate,
) -> Watchlist:

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise ValueError("User not found")

    company = (
        db.query(Company)
        .filter(Company.id == watchlist_data.company_id)
        .first()
    )

    if company is None:
        raise ValueError("Company not found")

    watchlist = Watchlist(
        user_id=user_id,
        company_id=watchlist_data.company_id,
    )

    db.add(watchlist)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Company is already in the user's watchlist")

    db.refresh(watchlist)

    return watchlist


def get_user_watchlist(
    db: Session,
    user_id: int,
) -> list[Watchlist]:

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise ValueError("User not found")

    return (
        db.query(Watchlist)
        .filter(Watchlist.user_id == user_id)
        .order_by(Watchlist.id)
        .all()
    )


def remove_from_watchlist(
    db: Session,
    user_id: int,
    company_id: int,
) -> bool:

    watchlist = (
        db.query(Watchlist)
        .filter(
            Watchlist.user_id == user_id,
            Watchlist.company_id == company_id,
        )
        .first()
    )

    if watchlist is None:
        return False

    db.delete(watchlist)
    db.commit()

    return True
