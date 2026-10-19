
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import decode_access_token
from shared.models import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        subject = payload.get("sub")

        if not isinstance(subject, str) or not subject.isdigit():
            raise credentials_exception

        user_id = int(subject)
    except (jwt.InvalidTokenError, ValueError):
        raise credentials_exception from None

    user = db.get(User, user_id)
    if user is None:
        # If the user does not exist, treat as invalid credentials
        raise credentials_exception

    return user
