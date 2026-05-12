"""Heart wallet service — atomic grant and spend operations.

All writes are wrapped in a single transaction (wallet update + event insert).
Idempotency keys prevent duplicate rewards on retry.
PRD §10.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.services.db.models import HeartRewardEvent, HeartWallet
from app.services.utils import make_id, get_now

logger = logging.getLogger(__name__)

_DAILY_EARN_CAP = 200  # soft guard; individual event caps enforced per reward type


def _get_or_create_wallet(db: Session, user_id: str) -> HeartWallet:
    wallet = db.scalar(select(HeartWallet).where(HeartWallet.user_id == user_id))
    if wallet is None:
        wallet = HeartWallet(user_id=user_id)
        db.add(wallet)
        db.flush()
    return wallet


def get_balance(db: Session, user_id: str) -> int:
    wallet = db.scalar(select(HeartWallet).where(HeartWallet.user_id == user_id))
    return wallet.balance if wallet else 0


def grant_hearts(
    db: Session,
    *,
    user_id: str,
    amount: int,
    event_type: str,
    source_tab: str,
    idempotency_key: str,
    metadata: dict[str, Any] | None = None,
    background_tasks: Any | None = None,
) -> dict[str, Any]:
    """Grant hearts to user wallet. Idempotent — duplicate key returns already-claimed result.

    Returns dict with: granted (bool), amount, new_balance, event_id.
    """
    existing = db.scalar(
        select(HeartRewardEvent).where(HeartRewardEvent.idempotency_key == idempotency_key)
    )
    if existing:
        wallet = db.scalar(select(HeartWallet).where(HeartWallet.user_id == user_id))
        return {
            "granted": False,
            "reason": "already_claimed",
            "amount": 0,
            "new_balance": wallet.balance if wallet else 0,
            "event_id": existing.event_id,
        }

    wallet = _get_or_create_wallet(db, user_id)
    today: date = get_now().date()
    if wallet.daily_earned_date != today:
        wallet.daily_earned_today = 0
        wallet.daily_earned_date = today

    event = HeartRewardEvent(
        event_id=make_id("hre"),
        user_id=user_id,
        event_type=event_type,
        amount=amount,
        source_tab=source_tab,
        idempotency_key=idempotency_key,
        status="granted",
        metadata_json=metadata or {},
    )
    db.add(event)

    wallet.balance += amount
    wallet.lifetime_earned += amount
    wallet.daily_earned_today += amount
    wallet.updated_at = get_now().replace(tzinfo=None)

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(HeartRewardEvent).where(HeartRewardEvent.idempotency_key == idempotency_key)
        )
        wallet = db.scalar(select(HeartWallet).where(HeartWallet.user_id == user_id))
        return {
            "granted": False,
            "reason": "already_claimed",
            "amount": 0,
            "new_balance": wallet.balance if wallet else 0,
            "event_id": existing.event_id if existing else None,
        }

    logger.info(
        "[HeartService] grant user=%s event_type=%s amount=%d key=%s",
        user_id, event_type, amount, idempotency_key,
    )
    
    # Push real-time notification
    try:
        from app.services.notification_service import send_instant_notification
        send_instant_notification(
            db, 
            user_id=user_id, 
            event_type="reward.earned", 
            payload={
                "amount": amount,
                "reward_type": event_type,
                "message": f"Bạn vừa nhận được {amount} Tim!"
            },
            background_tasks=background_tasks
        )
    except Exception as e:
        logger.warning(f"Failed to send reward notification: {e}")

    return {
        "granted": True,
        "amount": amount,
        "new_balance": wallet.balance,
        "event_id": event.event_id,
    }

