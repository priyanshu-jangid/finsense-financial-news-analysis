
from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.models import User
from backend.app.core.security import hash_password
from backend.app.schemas.auth import UserRegister


def get_user_by_email(db: Session, email: str) -> User | None:
    normalized_email = email.strip().lower()

    return db.scalar(
        select(User).where(User.email == normalized_email)
    )


def register_user(db: Session, user_data: UserRegister) -> User:
    email = str(user_data.email).strip().lower()

    existing_user = get_user_by_email(db, email)
    if existing_user:
        raise ValueError("An account with this email already exists")

    user = User(
        email=email,
        password_hash=hash_password(user_data.password),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user
