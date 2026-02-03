from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ============ USER SCHEMAS ============

class UserBase(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None


class UserCreate(UserBase):
    pass


class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============ CATEGORY SCHEMAS ============

class CategoryResponse(BaseModel):
    id: int
    name: str
    emoji: str
    taste_profile: str

    class Config:
        from_attributes = True


# ============ TOBACCO SCHEMAS ============

class TobaccoBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    brand: Optional[str] = None
    category_id: Optional[int] = None
    notes: Optional[str] = None


class TobaccoCreate(TobaccoBase):
    pass


class TobaccoBulkCreate(BaseModel):
    tobaccos: List[TobaccoCreate]


class TobaccoUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    brand: Optional[str] = None
    category_id: Optional[int] = None
    notes: Optional[str] = None


class TobaccoResponse(TobaccoBase):
    id: int
    user_id: int
    created_at: datetime
    category: Optional[CategoryResponse] = None

    class Config:
        from_attributes = True


class TobaccoBulkResponse(BaseModel):
    added: List[str]
    skipped: List[str]
    errors: List[str]


# ============ MIX SCHEMAS ============

class MixComponent(BaseModel):
    tobacco: str
    portion: int
    role: str


class MixBase(BaseModel):
    name: str
    components: Dict[str, Any]  # {"tobacco_name": {"portion": int, "role": str}}
    description: Optional[str] = None
    tips: Optional[str] = None
    request_type: str


class MixCreate(MixBase):
    pass


class MixResponse(MixBase):
    id: int
    user_id: int
    rating: Optional[int] = None
    is_favorite: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class MixGenerateRequest(BaseModel):
    request_type: str = Field(..., pattern="^(base|profile|surprise)$")
    base_tobacco: Optional[str] = None
    taste_profile: Optional[str] = None


class MixGenerateResponse(BaseModel):
    id: int
    name: str
    components: List[MixComponent]
    description: str
    tips: str


class MixRateRequest(BaseModel):
    rating: int = Field(..., ge=-1, le=1)


class MixFavoriteRequest(BaseModel):
    is_favorite: bool


# ============ STATS SCHEMAS ============

class StatsResponse(BaseModel):
    tobaccos_count: int
    mixes_count: int
    favorites_count: int
