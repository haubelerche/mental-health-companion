"""Nutrition meal check-in route.

POST /nutrition/meal-checkins
  → one reward per meal slot per local day (+5 Tim, capped at 15 Tim/day)
PRD §10.4
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import ensure_policy_acknowledged
from app.core.responses import ok
from app.hearts.service import grant_hearts
from app.services.db.models import HeartRewardEvent, NutritionMealCheckin, User
from app.services.db.session import get_db
from app.services.utils import local_date_utc7, make_id, get_now

router = APIRouter(prefix="/nutrition", tags=["nutrition"])

logger = logging.getLogger(__name__)

_MEAL_REWARD_HEARTS = 5
_MEAL_SLOTS = frozenset({"breakfast", "lunch", "dinner"})
_DAILY_NUTRITION_CAP = 15


class MealCheckinRequest(BaseModel):
    meal_slot: str = Field(..., pattern="^(breakfast|lunch|dinner)$")
    items_text: str = Field(..., min_length=1, max_length=2000)
    photo_url: str | None = None
    mood_before: str | None = None
    mood_after: str | None = None


@router.get("/meal-checkins")
def get_meal_history(
    limit: int = 50,
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    checkins = db.scalars(
        select(NutritionMealCheckin)
        .where(NutritionMealCheckin.user_id == current_user.user_id)
        .order_by(NutritionMealCheckin.meal_date.desc(), NutritionMealCheckin.created_at.desc())
        .limit(limit)
    ).all()

    return ok({
        "checkins": [
            {
                "meal_slot": c.meal_slot,
                "meal_date": c.meal_date.isoformat(),
                "items_text": c.items_text,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in checkins
        ]
    })


@router.get("/meal-checkins/today")
def get_today_checkins(
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    meal_date = local_date_utc7()
    checkins = db.scalars(
        select(NutritionMealCheckin).where(
            NutritionMealCheckin.user_id == current_user.user_id,
            NutritionMealCheckin.meal_date == meal_date,
        )
    ).all()

    return ok({
        "meal_date": meal_date.isoformat(),
        "claimed_slots": [c.meal_slot for c in checkins],
        "checkins": [
            {
                "meal_slot": c.meal_slot,
                "items_text": c.items_text,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in checkins
        ],
    })


@router.post("/meal-checkins")
def meal_checkin(
    payload: MealCheckinRequest,
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    meal_date = local_date_utc7()
    user_id = current_user.user_id

    existing = db.scalar(
        select(NutritionMealCheckin).where(
            NutritionMealCheckin.user_id == user_id,
            NutritionMealCheckin.meal_date == meal_date,
            NutritionMealCheckin.meal_slot == payload.meal_slot,
        )
    )
    if existing:
        return ok({
            "checkin_id": existing.checkin_id,
            "updated": False,
            "reward": {"granted": False, "reason": "already_claimed_today", "amount": 0},
        })

    daily_earned = (
        db.scalar(
            select(func.coalesce(func.sum(HeartRewardEvent.amount), 0)).where(
                HeartRewardEvent.user_id == user_id,
                HeartRewardEvent.source_tab == "nutrition",
                func.date(HeartRewardEvent.created_at) == meal_date,
            )
        )
        or 0
    )

    now = get_now()
    row = NutritionMealCheckin(
        checkin_id=make_id("nmc"),
        user_id=user_id,
        meal_date=meal_date,
        meal_slot=payload.meal_slot,
        items_text=payload.items_text[:2000],
        photo_url=payload.photo_url,
        mood_before=payload.mood_before,
        mood_after=payload.mood_after,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()

    reward: dict = {"granted": False, "amount": 0, "reason": "daily_cap_reached"}
    if daily_earned < _DAILY_NUTRITION_CAP:
        idem_key = f"nutrition_meal:{user_id}:{meal_date.isoformat()}:{payload.meal_slot}"
        result = grant_hearts(
            db,
            user_id=user_id,
            amount=_MEAL_REWARD_HEARTS,
            event_type="nutrition_meal_checkin_completed",
            source_tab="nutrition",
            idempotency_key=idem_key,
            metadata={"meal_slot": payload.meal_slot, "meal_date": meal_date.isoformat()},
        )
        if result["granted"]:
            row.reward_event_id = result["event_id"]
            reward = {"granted": True, "amount": _MEAL_REWARD_HEARTS, "balance": result["new_balance"]}

    db.commit()
    return ok({"checkin_id": row.checkin_id, "reward": reward}, status_code=201)
