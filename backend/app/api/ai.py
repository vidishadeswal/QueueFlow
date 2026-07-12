from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.appointments import get_owned_appointment
from app.api.deps import get_current_business
from app.core.ai import AIDraftError, draft_reminder_message
from app.core.database import get_db
from app.models.business import Business
from app.models.contact import Contact
from app.schemas.ai import DraftReminderRequest, DraftReminderResponse

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/draft-reminder", response_model=DraftReminderResponse)
async def draft_reminder(
    payload: DraftReminderRequest,
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    appointment = await get_owned_appointment(payload.appointment_id, db, business)
    contact = await db.get(Contact, appointment.contact_id)

    try:
        message = await draft_reminder_message(
            business_name=business.name,
            appointment_title=appointment.title,
            contact_name=contact.name,
            tone=payload.tone,
            custom_prompt=payload.custom_prompt,
        )
    except AIDraftError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    return DraftReminderResponse(message=message)
