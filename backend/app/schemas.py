from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RequestCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=8, max_length=20)
    email: str = ""
    city: str = "Bengaluru"
    call_mode: str = "web"
    consent: bool

    @field_validator("phone")
    @classmethod
    def e164ish(cls, v: str) -> str:
        v = v.replace(" ", "").replace("-", "")
        if not v.startswith("+"):
            v = "+91" + v.lstrip("0")
        if not v[1:].isdigit():
            raise ValueError("Phone number should contain digits only, e.g. +919876543210")
        return v

    @field_validator("consent")
    @classmethod
    def must_consent(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Consent is required before we can call you")
        return v

    @field_validator("call_mode")
    @classmethod
    def valid_mode(cls, v: str) -> str:
        if v not in {"phone", "web"}:
            raise ValueError("call_mode must be 'phone' or 'web'")
        return v


class PropertyPublic(BaseModel):
    """What a renter sees before selecting: no owner contact."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    city: str
    locality: str
    rent: int
    deposit: int
    bhk: int
    property_type: str
    furnishing: str
    area_sqft: int
    amenities: list[str]
    pets_allowed: bool
    available_from: date
    description: str
    last_verified_at: datetime


class PropertyFull(PropertyPublic):
    address: str
    lat: float
    lng: float
    owner_name: str
    owner_phone: str
    is_active: bool


class PropertyIn(BaseModel):
    title: str
    city: str = "Bengaluru"
    locality: str
    address: str = ""
    lat: float
    lng: float
    rent: int = Field(gt=0)
    deposit: int = 0
    bhk: int = Field(ge=0, le=6)
    property_type: str = "apartment"
    furnishing: str = "semi"
    area_sqft: int = 0
    amenities: list[str] = []
    pets_allowed: bool = False
    available_from: date | None = None
    description: str = ""
    owner_name: str
    owner_phone: str


class MatchOut(BaseModel):
    rank: int
    score: float
    reasons: list[str]
    property: PropertyPublic


class RequestOut(BaseModel):
    id: str
    name: str
    city: str
    call_mode: str
    status: str
    preferences: dict
    relaxation_note: str
    call_summary: str
    chat_token: str
    matches: list[MatchOut]
    created_at: datetime


class ChatIn(BaseModel):
    content: str = Field(min_length=1, max_length=1000)


class SelectIn(BaseModel):
    property_id: int


class AttachCallIn(BaseModel):
    call_id: str
