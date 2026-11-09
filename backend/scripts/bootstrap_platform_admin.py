"""Create the first platform admin (the product owner's operator account).

    PLATFORM_ADMIN_EMAIL=you@yourcompany.com PLATFORM_ADMIN_PASSWORD='a long passphrase' \
        python scripts/bootstrap_platform_admin.py

Both variables are required: there is deliberately no default email or password.
If the user already exists they are promoted to platform admin and their password is
left untouched. Platform admins have no powers inside a church unless they also hold a
membership there.
"""
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session

from app.crud import auth as auth_crud
from app.db.database import SessionLocal

MIN_PASSWORD_LENGTH = 12


def bootstrap_platform_admin(db: Session, email: str, password: str | None) -> str:
    existing = auth_crud.get_user_by_email(db, email)
    if existing:
        if existing.is_platform_admin:
            return f"{existing.email} is already a platform admin"
        existing.is_platform_admin = True
        db.commit()
        return f"Promoted existing user {existing.email} to platform admin (password unchanged)"

    if not password or len(password) < MIN_PASSWORD_LENGTH:
        raise SystemExit(f"PLATFORM_ADMIN_PASSWORD must be at least {MIN_PASSWORD_LENGTH} characters")
    user = auth_crud.create_user(db, email=email, password=password, is_platform_admin=True)
    return f"Created platform admin {user.email}"


def main() -> None:
    email = os.getenv("PLATFORM_ADMIN_EMAIL", "").strip()
    if not email:
        raise SystemExit("Set PLATFORM_ADMIN_EMAIL (and PLATFORM_ADMIN_PASSWORD for a new account)")
    db = SessionLocal()
    try:
        print(bootstrap_platform_admin(db, email, os.getenv("PLATFORM_ADMIN_PASSWORD")))
    finally:
        db.close()


if __name__ == "__main__":
    main()
