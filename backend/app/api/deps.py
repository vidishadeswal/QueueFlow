import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import redis_client
from app.core.security import decode_access_token
from app.core.token_denylist import is_token_revoked
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

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_error

    subject = payload.get("sub")
    jti = payload.get("jti")
    if subject is None or jti is None:
        raise credentials_error

    if await is_token_revoked(redis_client, jti):
        raise credentials_error

    try:
        business_id = uuid.UUID(subject)
    except ValueError:
        raise credentials_error

    business = await db.get(Business, business_id)
    if business is None:
        raise credentials_error

    return business
