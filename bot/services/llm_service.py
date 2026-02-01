import json
import random
from dataclasses import dataclass
from typing import List, Optional

from openai import AsyncOpenAI

from bot.config import settings


# Стили для разнообразия миксов
MIX_STYLES = [
    "классический и проверенный",
    "экспериментальный и смелый",
    "лёгкий и освежающий",
    "насыщенный и яркий",
    "сбалансированный и гармоничный",
    "сладкий и десертный",
    "тропический и экзотический",
    "мятно-холодный",
    "фруктово-ягодный",
    "необычный и креативный",
]


@dataclass
class MixComponent:
    """Компонент микса."""
    tobacco: str      # название табака
    portion: int      # процент (0-100)
    role: str         # "база", "дополнение", "акцент"


@dataclass
class MixRecommendation:
    """Рекомендация микса от LLM."""
    name: str                       # название микса
    components: List[MixComponent]  # список компонентов
    description: str                # описание вкуса
    tips: str                       # совет по забивке


class LLMService:
    """Сервис для генерации миксов через OpenAI-совместимый API."""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_api_url,
        )
        self.model = settings.llm_model

    def _get_system_prompt(self) -> str:
        """Возвращает системный промпт для AI."""
        return """Ты — эксперт по кальянным миксам с 10-летним опытом. Твоя задача — составлять идеальные миксы ТОЛЬКО из табаков, которые есть у пользователя.

ПРАВИЛА СОСТАВЛЕНИЯ МИКСОВ:
• 2-4 компонента в миксе
• Сумма пропорций ВСЕГДА = 100%
• Роли компонентов:
  - "база" (40-50%) — основной вкус микса
  - "дополнение" (25-35%) — поддерживает и обогащает базу
  - "акцент" (10-25%) — добавляет изюминку
• Объясняй почему выбранные вкусы хорошо сочетаются

ФОРМАТ ОТВЕТА — СТРОГО JSON без markdown-разметки:
{
  "name": "Название микса",
  "components": [
    {"tobacco": "точное название табака", "portion": 45, "role": "база"},
    {"tobacco": "точное название табака", "portion": 35, "role": "дополнение"},
    {"tobacco": "точное название табака", "portion": 20, "role": "акцент"}
  ],
  "description": "Описание вкусового профиля и ощущений",
  "tips": "Практический совет по забивке или подаче"
}

ВАЖНО: Используй ТОЛЬКО табаки из списка пользователя. Названия должны совпадать точно!"""

    def _format_collection(self, tobaccos: List[dict]) -> str:
        """Форматирует список табаков для промпта."""
        lines = []
        for t in tobaccos:
            parts = [f"- {t['name']}"]
            if t.get("brand"):
                parts.append(f"({t['brand']})")
            if t.get("category"):
                parts.append(f"[{t['category']}]")
            lines.append(" ".join(parts))
        return "\n".join(lines)

    async def generate_mix(
        self,
        tobaccos: List[dict],
        request_type: str,
        base_tobacco: Optional[str] = None,
        taste_profile: Optional[str] = None,
        liked_mixes: Optional[List[str]] = None,
        disliked_mixes: Optional[List[str]] = None,
        previous_mixes: Optional[List[str]] = None,
    ) -> MixRecommendation:
        """Генерирует микс через LLM API."""
        try:
            # Форматируем коллекцию
            collection_text = self._format_collection(tobaccos)

            # Формируем запрос пользователя
            if request_type == "base":
                user_request = f"Составь микс на основе табака '{base_tobacco}'"
            elif request_type == "profile":
                user_request = f"Составь {taste_profile} микс"
            else:  # surprise
                # Выбираем случайный стиль для разнообразия
                style = random.choice(MIX_STYLES)
                user_request = f"Удиви меня! Предложи {style} микс. Будь креативным!"

            # Добавляем информацию о предпочтениях
            preferences = []
            if liked_mixes:
                preferences.append(f"Мне нравились миксы: {', '.join(liked_mixes)}")
            if disliked_mixes:
                preferences.append(f"Мне не понравились миксы: {', '.join(disliked_mixes)}")
            
            # Исключаем ранее предложенные миксы
            if previous_mixes:
                preferences.append(f"НЕ предлагай эти миксы (уже были): {', '.join(previous_mixes[-5:])}")

            user_prompt = f"""Моя коллекция табаков:
{collection_text}

{user_request}"""

            if preferences:
                user_prompt += f"\n\nМои предпочтения:\n" + "\n".join(preferences)

            # Для surprise используем более высокую температуру
            temperature = 1.0 if request_type == "surprise" else settings.llm_temperature

            # Запрос к API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=settings.llm_max_tokens,
                temperature=temperature,
            )

            # Извлекаем ответ
            content = response.choices[0].message.content

            # Убираем markdown-разметку если есть
            if content.startswith("```"):
                content = content.strip("```").strip()
                if content.startswith("json"):
                    content = content[4:].strip()

            # Парсим JSON
            data = json.loads(content)

            # Создаём объект рекомендации
            components = [
                MixComponent(
                    tobacco=c["tobacco"],
                    portion=c["portion"],
                    role=c["role"],
                )
                for c in data["components"]
            ]

            return MixRecommendation(
                name=data["name"],
                components=components,
                description=data["description"],
                tips=data["tips"],
            )

        except json.JSONDecodeError as e:
            raise Exception(f"Ошибка парсинга ответа LLM: {e}")
        except KeyError as e:
            raise Exception(f"Неполный ответ от LLM, отсутствует поле: {e}")
        except Exception as e:
            raise Exception(f"Ошибка генерации микса: {e}")


llm_service = LLMService()
