# Деплой Mini App на Render

## Шаг 1: Создать аккаунт на Render

1. Перейдите на https://render.com
2. Нажмите "Get Started for Free"
3. Зарегистрируйтесь через GitHub (рекомендуется)

## Шаг 2: Загрузить код на GitHub

Создайте новый репозиторий и загрузите код:

```bash
cd c:\Projects\hookah_bot

# Инициализировать git (если ещё нет)
git init

# Добавить файлы
git add mini-app-backend mini-app-frontend

# Создать коммит
git commit -m "Add Mini App"

# Создать репозиторий на GitHub и подключить
git remote add origin https://github.com/ВАШ_USERNAME/hookah-mini-app.git
git push -u origin main
```

## Шаг 3: Деплой Backend на Render

1. В Render Dashboard нажмите **New +** → **Web Service**
2. Подключите ваш GitHub репозиторий
3. Настройки:
   - **Name:** `hookah-mini-app-api`
   - **Root Directory:** `mini-app-backend`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`

4. Добавьте Environment Variables:
   - `LLM_API_URL` = `https://openrouter.ai/api/v1`
   - `LLM_API_KEY` = `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`
   - `LLM_MODEL` = `openai/gpt-3.5-turbo`
   - `DATABASE_URL` = `sqlite+aiosqlite:///./hookah_app.db`
   - `CORS_ORIGINS` = `*`

5. Нажмите **Create Web Service**
6. Дождитесь деплоя и скопируйте URL (например `https://hookah-mini-app-api.onrender.com`)

## Шаг 4: Деплой Frontend на Render

1. В Render Dashboard нажмите **New +** → **Static Site**
2. Подключите тот же репозиторий
3. Настройки:
   - **Name:** `hookah-mini-app`
   - **Root Directory:** `mini-app-frontend`
   - **Build Command:** `npm install && npm run build`
   - **Publish Directory:** `dist`

4. Добавьте Environment Variable:
   - `VITE_API_URL` = `https://hookah-mini-app-api.onrender.com/api`
   (замените на URL вашего backend из Шага 3)

5. Нажмите **Create Static Site**
6. Дождитесь деплоя и скопируйте URL (например `https://hookah-mini-app.onrender.com`)

## Шаг 5: Настроить Telegram бота

1. Откройте [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте `/mybots`
3. Выберите вашего бота
4. **Bot Settings** → **Menu Button** → **Configure Menu Button**
5. Введите URL вашего frontend: `https://hookah-mini-app.onrender.com`
6. Введите текст кнопки: `Открыть приложение`

## Готово!

Теперь при открытии бота в Telegram будет кнопка меню, которая открывает Mini App.

---

## Важные замечания

- Бесплатный план Render "засыпает" после 15 минут неактивности. Первый запрос после простоя занимает ~30 секунд.
- Для постоянной работы нужен платный план ($7/месяц за сервис).
- SQLite на Render не сохраняется между деплоями. Для production лучше использовать PostgreSQL (Render предоставляет бесплатно).
