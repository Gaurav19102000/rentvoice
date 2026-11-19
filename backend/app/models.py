import secrets
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    city: Mapped[str] = mapped_column(String(80), index=True)
    locality: Mapped[str] = mapped_column(String(120), index=True)
    address: Mapped[str] = mapped_column(String(300), default="")
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    rent: Mapped[int] = mapped_column(Integer, index=True)          # monthly, INR
    deposit: Mapped[int] = mapped_column(Integer, default=0)
    bhk: Mapped[int] = mapped_column(Integer, index=True)           # 0 = studio / PG room
    property_type: Mapped[str] = mapped_column(String(40))          # apartment | independent_house | villa | pg | studio
    furnishing: Mapped[str] = mapped_column(String(20))             # unfurnished | semi | fully
    area_sqft: Mapped[int] = mapped_column(Integer, default=0)
    amenities: Mapped[list] = mapped_column(JSON, default=list)
    pets_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    available_from: Mapped[date] = mapped_column(Date, default=date.today)
    description: Mapped[str] = mapped_column(Text, default="")
    owner_name: Mapped[str] = mapped_column(String(120))
    owner_phone: Mapped[str] = mapped_column(String(30))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_verified_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class RentalRequest(Base):
    __tablename__ = "rental_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(30))
    email: Mapped[str] = mapped_column(String(200), default="")
    city: Mapped[str] = mapped_column(String(80))
    call_mode: Mapped[str] = mapped_column(String(10), default="web")   # phone | web
    consent: Mapped[bool] = mapped_column(Boolean, default=False)
    # submitted -> calling -> in_call -> matched | no_match -> completed ; call_failed
    status: Mapped[str] = mapped_column(String(20), default="submitted", index=True)
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    relaxation_note: Mapped[str] = mapped_column(String(300), default="")
    call_id: Mapped[str] = mapped_column(String(80), default="", index=True)
    call_summary: Mapped[str] = mapped_column(Text, default="")
    transcript: Mapped[str] = mapped_column(Text, default="")
    chat_token: Mapped[str] = mapped_column(String(40), default=lambda: secrets.token_urlsafe(16), unique=True)
    selected_property_id: Mapped[int | None] = mapped_column(ForeignKey("properties.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    matches: Mapped[list["Match"]] = relationship(
        back_populates="request", cascade="all, delete-orphan", order_by="Match.rank"
    )


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[str] = mapped_column(ForeignKey("rental_requests.id"), index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"))
    rank: Mapped[int] = mapped_column(Integer)
    score: Mapped[float] = mapped_column(Float)
    reasons: Mapped[list] = mapped_column(JSON, default=list)

    request: Mapped[RentalRequest] = relationship(back_populates="matches")
    property: Mapped[Property] = relationship()


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[str] = mapped_column(ForeignKey("rental_requests.id"), index=True)
    role: Mapped[str] = mapped_column(String(12))   # user | assistant
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
