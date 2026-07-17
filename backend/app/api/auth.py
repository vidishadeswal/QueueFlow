from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_business
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import rate_limiter
from app.core.redis import redis_client
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.core.token_denylist import revoke_token
from app.models.business import Business
from app.schemas.business import BusinessCreate, BusinessOut, BusinessUpdate, Token

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@router.post(
    "/signup",
    response_model=BusinessOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limiter("signup", settings.rate_limit_signup_per_hour, 3600))],
)
async def signup(payload: BusinessCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(Business).where(Business.email == payload.email))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    business = Business(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(business)
    await db.commit()
    await db.refresh(business)
    return business


@router.post(
    "/login",
    response_model=Token,
    dependencies=[Depends(rate_limiter("login", settings.rate_limit_login_per_minute, 60))],
)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    business = await db.scalar(select(Business).where(Business.email == form_data.username))
    if business is None or not verify_password(form_data.password, business.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject=str(business.id))
    return Token(access_token=access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if payload is None:
        return

    jti = payload.get("jti")
    exp = payload.get("exp")
    if jti and exp:
        ttl_seconds = int(exp - datetime.now(timezone.utc).timestamp())
        await revoke_token(redis_client, jti, ttl_seconds)


@router.get("/me", response_model=BusinessOut)
async def me(current_business: Business = Depends(get_current_business)):
    return current_business


@router.patch("/me", response_model=BusinessOut)
async def update_me(
    payload: BusinessUpdate,
    db: AsyncSession = Depends(get_db),
    current_business: Business = Depends(get_current_business),
):
    if payload.webhook_url and not payload.webhook_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="webhook_url must start with http:// or https://")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current_business, field, value)
    await db.commit()
    await db.refresh(current_business)
    return current_business
