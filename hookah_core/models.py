from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, Text, JSON, String, UniqueConstraint, CheckConstraint, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, validates


from .schemas import normalized_name


class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""
    pass


class User(Base):
    """Пользователь приложения."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    tobaccos: Mapped[list["Tobacco"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    mixes: Mapped[list["Mix"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Category(Base):
    """Категория вкусов табака."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    emoji: Mapped[str]
    taste_profile: Mapped[str]  # сладкий/кислый/свежий/терпкий/нейтральный


class Tobacco(Base):
    """Табак пользователя."""

    __tablename__ = "tobaccos"
    __table_args__ = (UniqueConstraint("user_id", "normalized_name", "normalized_brand", name="uq_tobacco_owner_brand_name"), Index("ix_tobaccos_user_id", "user_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str]
    normalized_name: Mapped[str] = mapped_column(String(300))
    normalized_brand: Mapped[str] = mapped_column(String(300), default='', server_default='')
    brand: Mapped[Optional[str]] = mapped_column(nullable=True)
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id"), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    @validates('brand')
    def validate_brand(self, key, value):
        value = (value or '').strip()
        self.normalized_brand = normalized_name(value)
        return value or None

    @validates('name')
    def validate_name(self, key, value):
        value = value.strip()
        if not 2 <= len(value) <= 100:
            raise ValueError('Invalid tobacco name length')
        self.normalized_name = normalized_name(value)
        return value

    # Relationships
    user: Mapped["User"] = relationship(back_populates="tobaccos")
    category: Mapped[Optional["Category"]] = relationship()


class Mix(Base):
    """Сгенерированный микс."""

    __tablename__ = "mixes"
    __table_args__ = (CheckConstraint("rating IN (-1, 0, 1)", name="ck_mix_rating"), Index("ix_mixes_user_created", "user_id", "created_at"))

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str]
    components: Mapped[dict] = mapped_column(JSON)  # {"табак": {"portion": %, "role": str}, ...}
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tips: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rating: Mapped[Optional[int]] = mapped_column(nullable=True)  # -1, 0, 1
    is_favorite: Mapped[bool] = mapped_column(default=False)
    request_type: Mapped[str]  # base/profile/surprise
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="mixes")
