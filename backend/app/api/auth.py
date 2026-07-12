from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_business
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.business import Business
from app.schemas.business import BusinessCreate, BusinessOut, Token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=BusinessOut, status_code=status.HTTP_201_CREATED)
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


@router.post("/login", response_model=Token)
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


@router.get("/me", response_model=BusinessOut)
async def me(current_business: Business = Depends(get_current_business)):
    return current_business
