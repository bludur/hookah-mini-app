from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer
from hookah_core.schemas import TobaccoCreate, TobaccoUpdate, MixGenerateRequest, MixComponent, MixRecommendation, InputModel


class ResponseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    @field_serializer('created_at', check_fields=False)
    def utc_timestamp(self, value: datetime):
        return value.replace(tzinfo=timezone.utc).isoformat() if value.tzinfo is None else value.isoformat()


class UserResponse(ResponseModel):
    id: int
    telegram_id: int
    username: str | None
    first_name: str | None
    created_at: datetime


class CategoryResponse(ResponseModel):
    id: int
    name: str
    emoji: str
    taste_profile: str


class TobaccoResponse(ResponseModel):
    id: int
    user_id: int
    name: str
    brand: str | None
    category_id: int | None
    notes: str | None
    created_at: datetime
    category: CategoryResponse | None


class TobaccoBulkCreate(InputModel):
    tobaccos: list[dict[str, Any]] = Field(min_length=1, max_length=100)


class TobaccoBulkResponse(BaseModel):
    added: list[str]
    skipped: list[str]
    errors: list[str]


class MixResponse(ResponseModel):
    id: int
    user_id: int
    name: str
    components: dict[str, Any]
    description: str | None
    tips: str | None
    request_type: str
    rating: int | None
    is_favorite: bool
    created_at: datetime


class MixGenerateResponse(MixRecommendation):
    id: int


class MixRateRequest(InputModel):
    rating: int = Field(strict=True, ge=-1, le=1)


class MixFavoriteRequest(InputModel):
    is_favorite: bool = Field(strict=True)


class StatsResponse(BaseModel):
    tobaccos_count: int
    mixes_count: int
    favorites_count: int
