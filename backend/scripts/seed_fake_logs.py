"""Seed local DB with fake analysis logs + quota consumption.

This is for UI verification only (Admin sorting/time ranges/tokens; Quota consumption list/summary).
Safe to re-run: it deletes previously seeded rows (filename/description prefix) before inserting.

Run:
  python scripts/seed_fake_logs.py
"""

from __future__ import annotations

import random
import os
import sys
from datetime import datetime, timedelta

# Ensure `backend/` is on sys.path so `import app...` works when running this script directly.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.core.security import generate_referral_code, get_password_hash
from app.models.user import AnalysisLog, QuotaTransaction, User


NOW = datetime.utcnow()

SEED_USERS = [
    "u_ref_1",
    "u_ref_2",
    "u_other",
]


def get_or_create_user(db, username: str, *, referred_by: int | None) -> User:
    user = db.query(User).filter(User.username == username).first()
    if user:
        return user

    user = User(
        username=username,
        email=None,
        hashed_password=get_password_hash("Test12345!"),
        referral_code=generate_referral_code(),
        quota_balance=200,
        quota_used=0,
        is_admin=False,
        is_active=True,
        is_vip=False,
        referred_by=referred_by,
    )
    db.add(user)
    db.flush()
    return user


def delete_previous_seed(db) -> None:
    # Delete previously seeded logs/transactions by marker prefix.
    db.query(AnalysisLog).filter(AnalysisLog.filename.like("fake_%")).delete(synchronize_session=False)
    db.query(QuotaTransaction).filter(QuotaTransaction.description.like("Fake analysis cost%") ).delete(
        synchronize_session=False
    )


def ensure_balance(user: User, minimum: int = 200) -> None:
    if user.quota_balance is None:
        user.quota_balance = 0
    if user.quota_balance < minimum:
        user.quota_balance = minimum


def reset_user_quota(user: User, *, balance: int = 200) -> None:
    user.quota_balance = int(balance)
    user.quota_used = 0


def add_analysis(
    db,
    user: User,
    *,
    created_at: datetime,
    quota_cost: int,
    prompt_tokens: int,
    completion_tokens: int,
    status: str = "success",
) -> None:
    log = AnalysisLog(
        user_id=user.id,
        filename=f"fake_{user.username}_{created_at.strftime('%Y%m%d_%H%M%S')}.xlsx",
        file_type="xlsx",
        student_count=max(1, quota_cost),
        status=status,
        error_message=None if status == "success" else "simulated failure",
        quota_cost=quota_cost if status == "success" else 0,
        prompt_tokens=prompt_tokens if status == "success" else 0,
        completion_tokens=completion_tokens if status == "success" else 0,
        processing_time=round(random.uniform(1.2, 6.8), 3),
        created_at=created_at,
    )
    db.add(log)

    if status != "success":
        return

    before = int(user.quota_balance or 0)
    after = before - int(quota_cost)
    user.quota_balance = after
    user.quota_used = int(user.quota_used or 0) + int(quota_cost)

    tx = QuotaTransaction(
        user_id=user.id,
        transaction_type="analysis_cost",
        amount=-int(quota_cost),
        balance_after=after,
        description=f"Fake analysis cost ({quota_cost})",
        created_at=created_at,
    )
    db.add(tx)


def main() -> None:
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "aristo7298local").first()
        if not admin:
            raise RuntimeError("Expected local admin 'aristo7298local' to exist")

        delete_previous_seed(db)

        u1 = get_or_create_user(db, "u_ref_1", referred_by=admin.id)
        u2 = get_or_create_user(db, "u_ref_2", referred_by=admin.id)
        u3 = get_or_create_user(db, "u_other", referred_by=None)

        # Control created_at for referral-range tests
        u1.created_at = NOW - timedelta(days=2)
        u2.created_at = NOW - timedelta(hours=20)
        u3.created_at = NOW - timedelta(days=40)

        # Keep re-runs deterministic: reset quotas for the users involved in seeding.
        for u in (admin, u1, u2, u3):
            reset_user_quota(u, balance=200)
            ensure_balance(u)

        # Admin logs across windows: within 1d, within 7d, within 30d
        add_analysis(db, admin, created_at=NOW - timedelta(hours=6), quota_cost=5, prompt_tokens=1200, completion_tokens=300)
        add_analysis(db, admin, created_at=NOW - timedelta(days=3), quota_cost=12, prompt_tokens=2200, completion_tokens=900)
        add_analysis(db, admin, created_at=NOW - timedelta(days=18), quota_cost=25, prompt_tokens=5200, completion_tokens=1800)
        # Failed log should NOT be included in admin range aggregations
        add_analysis(db, admin, created_at=NOW - timedelta(days=1, hours=2), quota_cost=9, prompt_tokens=999, completion_tokens=999, status="failed")

        # u1: two logs within 7d
        add_analysis(db, u1, created_at=NOW - timedelta(days=1, hours=1), quota_cost=8, prompt_tokens=1800, completion_tokens=700)
        add_analysis(db, u1, created_at=NOW - timedelta(days=6, hours=5), quota_cost=3, prompt_tokens=600, completion_tokens=250)

        # u2: one log within 1d
        add_analysis(db, u2, created_at=NOW - timedelta(hours=2), quota_cost=15, prompt_tokens=3500, completion_tokens=1200)

        # u3: outside 30d
        add_analysis(db, u3, created_at=NOW - timedelta(days=45), quota_cost=7, prompt_tokens=900, completion_tokens=400)

        db.commit()

        print("Seed complete.")
        print("Users:")
        print(f"- admin: {admin.username} (id={admin.id})")
        print(f"- u_ref_1: {u1.username} (id={u1.id}) referred_by={u1.referred_by}")
        print(f"- u_ref_2: {u2.username} (id={u2.id}) referred_by={u2.referred_by}")
        print(f"- u_other: {u3.username} (id={u3.id}) referred_by={u3.referred_by}")
        print("New users password: Test12345!")

    finally:
        db.close()


if __name__ == "__main__":
    main()
