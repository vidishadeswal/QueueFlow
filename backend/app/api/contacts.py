import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_business
from app.core.database import get_db
from app.models.business import Business
from app.models.contact import Contact
from app.schemas.contact import ContactCreate, ContactOut, ContactUpdate

router = APIRouter(prefix="/contacts", tags=["contacts"])


async def get_owned_contact(contact_id: uuid.UUID, db: AsyncSession, business: Business) -> Contact:
    contact = await db.get(Contact, contact_id)
    if contact is None or contact.business_id != business.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return contact


@router.post("", response_model=ContactOut, status_code=status.HTTP_201_CREATED)
async def create_contact(
    payload: ContactCreate,
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    contact = Contact(business_id=business.id, **payload.model_dump())
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact


@router.get("", response_model=list[ContactOut])
async def list_contacts(
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    result = await db.scalars(select(Contact).where(Contact.business_id == business.id).order_by(Contact.created_at.desc()))
    return list(result)


@router.get("/{contact_id}", response_model=ContactOut)
async def get_contact(
    contact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    return await get_owned_contact(contact_id, db, business)


@router.patch("/{contact_id}", response_model=ContactOut)
async def update_contact(
    contact_id: uuid.UUID,
    payload: ContactUpdate,
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    contact = await get_owned_contact(contact_id, db, business)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)
    await db.commit()
    await db.refresh(contact)
    return contact


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    contact = await get_owned_contact(contact_id, db, business)
    await db.delete(contact)
    await db.commit()
