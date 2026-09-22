"""
User repository — infrastructure-level database operations for User persistence.

Security:
- Passwords are hashed before storage using get_password_hash().
- Email is normalized to lowercase for consistent lookup.
- No plaintext passwords are ever stored or returned.
- No JWT logic belongs here.
"""
from typing import Optional
from uuid import UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as SQLAlchemySession

from backend.app.core.security import get_password_hash
from backend.app.models.user import User


class UserRepository:

    @staticmethod
    def _normalize_email(email: str) -> str:
        """Normalize email to lowercase and strip whitespace for consistent lookups."""
        return email.strip().lower()

    def get_by_id(self, db: SQLAlchemySession, user_id: UUID) -> Optional[User]:
        """Retrieve a user by primary key UUID."""
        return db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, db: SQLAlchemySession, email: str) -> Optional[User]:
        """Retrieve a user by normalized email address."""
        return db.query(User).filter(
            User.email == self._normalize_email(email)
        ).first()

    def exists_by_email(self, db: SQLAlchemySession, email: str) -> bool:
        """Check whether a user with the given email already exists."""
        return self.get_by_email(db, email) is not None

    def create(
        self,
        db: SQLAlchemySession,
        email: str,
        password: str,
    ) -> User:
        """
        Create and persist a new user with a hashed password.
        The plaintext password is never stored.

        Raises:
            ValueError: If a user with the given email already exists.
        """
        normalized_email = self._normalize_email(email)
        if self.exists_by_email(db, normalized_email):
            raise ValueError("A user with this email already exists")

        db_user = User(
            email=normalized_email,
            hashed_password=get_password_hash(password),
        )
        try:
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            return db_user
        except IntegrityError:
            db.rollback()
            raise ValueError("A user with this email already exists")
