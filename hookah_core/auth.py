import hashlib
import hmac
import json
import re
import time
from urllib.parse import parse_qsl

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class TelegramUser(BaseModel):
    model_config = ConfigDict(strict=True)
    id: int = Field(gt=0, le=2**52 - 1)
    first_name: str = Field(max_length=256)
    username: str | None = Field(None, max_length=64)


class InvalidInitData(ValueError):
    pass


def validate_init_data(raw: str, bot_token: str, max_age: int, now: int | None = None) -> TelegramUser:
    """Telegram's bot-token HMAC scheme; verify before trusting any user fields."""
    try:
        if not bot_token or not raw or len(raw) > 8192:
            raise ValueError()
        pairs = parse_qsl(raw, keep_blank_values=True, strict_parsing=True, max_num_fields=32, errors='strict')
        fields = dict(pairs)
        if len(fields) != len(pairs):
            raise ValueError()
        signature = fields.pop('hash')
        if not re.fullmatch('[0-9a-f]{64}', signature):
            raise ValueError()
        check = '\n'.join(f'{key}={value}' for key, value in sorted(fields.items()))
        secret = hmac.new(b'WebAppData', bot_token.encode(), hashlib.sha256).digest()
        expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise ValueError()
        issued = int(fields['auth_date'])
        age = (int(time.time()) if now is None else now) - issued
        if age < -30 or age > max_age:
            raise ValueError()
        return TelegramUser.model_validate(json.loads(fields['user']))
    except (ValueError, KeyError, TypeError, ValidationError, UnicodeError) as exc:
        raise InvalidInitData('Invalid or expired Telegram session') from exc
