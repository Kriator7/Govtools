"""Inbound webhooks. Verify secrets before trusting provider payloads."""

from fastapi import APIRouter, Header, HTTPException, Request

from app.config import get_settings
from app.dependencies import ActiveRealtor, DbSession
from app.models.enums import InvestorResponse
from app.models.opportunity import Opportunity
from app.services.sms.investor_notify import InvestorNotificationService
from app.services.telegram.realtor_agent import RealtorTelegramService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/telegram")
async def telegram_webhook(
    request: Request,
    db: DbSession,
    realtor: ActiveRealtor,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    settings = get_settings()
    if settings.telegram_mode == "live" and settings.telegram_webhook_secret:
        if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
            raise HTTPException(status_code=401, detail="Invalid Telegram webhook secret")
    payload = await request.json()
    callback = (payload.get("callback_query") or {}).get("data")
    if not callback:
        return {"ok": True, "ignored": True}
    result = RealtorTelegramService(db).handle_callback(realtor, callback)
    if result.get("action") == "approve" and result.get("ok"):
        opportunity = (
            db.query(Opportunity)
            .filter(Opportunity.public_id == callback.split(":", 1)[1])
            .one_or_none()
        )
        if opportunity:
            InvestorNotificationService(db).notify_approved(realtor, opportunity)
    db.commit()
    return result


@router.post("/twilio")
async def twilio_webhook(request: Request, db: DbSession, realtor: ActiveRealtor) -> dict:
    form = await request.form()
    body = str(form.get("Body") or "").strip().upper()
    from_number = str(form.get("From") or "")
    mapping = {"YES": InvestorResponse.YES, "NO": InvestorResponse.NO, "MORE INFO": InvestorResponse.MORE_INFO}
    if body not in mapping:
        return {"ok": True, "ignored": True, "from": from_number}
    opportunity = (
        db.query(Opportunity)
        .filter(Opportunity.realtor_id == realtor.id)
        .order_by(Opportunity.created_at.desc())
        .first()
    )
    if opportunity is None:
        return {"ok": False, "error": "no opportunity"}
    InvestorNotificationService(db).record_response(realtor, opportunity, mapping[body], body)
    db.commit()
    return {"ok": True, "opportunity_id": opportunity.public_id}
