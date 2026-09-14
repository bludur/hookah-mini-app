import unicodedata
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]
TobaccoReference = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=240)]
Brand = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)]
Notes = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
Role = Literal['база', 'дополнение', 'акцент']


def normalized_name(value: str) -> str:
    return unicodedata.normalize('NFKC', value).strip().casefold()


class InputModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class TobaccoCreate(InputModel):
    name: Name
    brand: Brand | None = None
    category_id: int | None = Field(None, gt=0)
    notes: Notes | None = None


class TobaccoUpdate(InputModel):
    name: Name | None = None
    brand: Brand | None = None
    category_id: int | None = Field(None, gt=0)
    notes: Notes | None = None

    @field_validator('name')
    @classmethod
    def non_null_name(cls, value: str | None) -> str:
        if value is None:
            raise ValueError('Название не может быть пустым')
        return value


class MixGenerateRequest(InputModel):
    request_type: Literal['base', 'profile', 'surprise']
    base_tobacco: TobaccoReference | None = None
    base_tobacco_id: int | None = Field(None, gt=0)
    taste_profile: Literal['сладкий', 'кислый', 'свежий'] | None = None

    @model_validator(mode='after')
    def matching_fields(self) -> Self:
        if self.base_tobacco and self.base_tobacco_id is not None:
            raise ValueError('Выберите один способ задания базы')
        if self.request_type == 'base' and not (self.base_tobacco or self.base_tobacco_id):
            raise ValueError('Выберите базовый табак')
        if self.request_type == 'profile' and not self.taste_profile:
            raise ValueError('Выберите вкусовой профиль')
        if self.request_type != 'base' and (self.base_tobacco is not None or self.base_tobacco_id is not None):
            raise ValueError('Базовый табак допустим только для режима base')
        if self.request_type != 'profile' and self.taste_profile is not None:
            raise ValueError('Профиль допустим только для режима profile')
        return self


class MixComponent(InputModel):
    tobacco: TobaccoReference
    portion: int = Field(strict=True, gt=0, le=100)
    role: Role

    @field_validator('role', mode='before')
    @classmethod
    def canonical_role(cls, value):
        # Free providers may translate these enum labels despite a Russian prompt.
        if isinstance(value, str):
            return {'base': 'база', 'addition': 'дополнение', 'accent': 'акцент'}.get(value, value)
        return value


class MixRecommendation(InputModel):
    name: Name
    components: list[MixComponent] = Field(min_length=2, max_length=4)
    description: str = Field(min_length=1, max_length=800)
    tips: str = Field(min_length=1, max_length=500)

    @model_validator(mode='after')
    def valid_proportions(self) -> Self:
        names = [normalized_name(c.tobacco) for c in self.components]
        if len(set(names)) != len(names):
            raise ValueError('Duplicate components')
        if sum(c.portion for c in self.components) != 100:
            raise ValueError('Portions must sum to 100')
        if sum(c.role == 'база' for c in self.components) != 1:
            raise ValueError('Exactly one base is required')
        return self

    def validate_collection(self, names: set[str], base: str | None = None) -> Self:
        if any(c.tobacco not in names for c in self.components):
            raise ValueError('Unknown tobacco')
        if base and not any(c.tobacco == base and c.role == 'база' for c in self.components):
            raise ValueError('Requested base is missing')
        return self
