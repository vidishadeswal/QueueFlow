import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.business import Business

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_business(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Business:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    subject = decode_access_token(token)
    if subject is None:
        raise credentials_error

    try:
        business_id = uuid.UUID(subject)
    except ValueError:
        raise credentials_error

    business = await db.get(Business, business_id)
    if business is None:
        raise credentials_error

    return business
