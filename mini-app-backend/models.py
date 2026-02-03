from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, Text, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


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

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str]
    brand: Mapped[Optional[str]] = mapped_column(nullable=True)
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id"), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="tobaccos")
    category: Mapped[Optional["Category"]] = relationship()


class Mix(Base):
    """Сгенерированный микс."""
    
    __tablename__ = "mixes"

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
