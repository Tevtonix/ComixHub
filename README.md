# ComixHub

## Описание проекта

Проект "ComixHub - Сервис, где пользователи могут: Публиковать свои комиксы, мангу и истории. Читать работы других авторов. Обсуждать главу и комиксы в комментариях. О производит закладки и отслеживание любимых серий. Оценивать и писать понравившиеся работы."

---

## Основные возможности

### Для читателей:
- Просмотр каталога комиксов с поиском
- Детальная страница комикса
- Чтение глав с постраничным просмотром
- Система комментариев и рейтинга глав (1–5 звёзд)
- Добавление комиксов в закладки («Мои закладки»)
- Авторизация и персональный профиль

### Для авторов:
- Регистрация в режиме «Автор»
- Публикация нового комикса (с обложкой)
- Добавление глав (загрузка нескольких изображений одновременно)
- Управление своими комиксами

### Общее:
- Красивый ретро-футуристический интерфейс в стиле тактического HUD
- Полноценная система аутентификации через JWT (cookie)
- Защита маршрутов (только авторы могут создавать контент)

---

## Стек технологий

- **Backend**: FastAPI
- **База данных**: SQLite + SQLModel (SQLAlchemy)
- **Шаблоны**: Jinja2
- **Аутентификация**: JWT (python-jose) + bcrypt
- **Frontend**: HTML + CSS (собственный дизайн в стиле CRT / tactical UI)
- **Загрузка файлов**: Multipart + сохранение в `static/uploads/`
- **ORM**: SQLModel
- **Валидация**: Pydantic
- **Сервер**: Uvicorn (с режимом reload)

---

## Структура проекта

comixhub/
├── app/
│   ├── main.py                 # Запуск приложения и главная страница
│   ├── database.py             # Настройка БД
│   ├── models.py               # Все SQLModel модели (User, Comic, Chapter, Comment, Favorite)
│   ├── schemas.py              # Pydantic схемы
│   ├── config.py               # Настройки (Pydantic Settings)
│   ├── routers/
│   │   ├── auth.py             # Авторизация и регистрация
│   │   └── comics.py           # Все маршруты комиксов
│   └── templates/              # Jinja2 шаблоны (все .html файлы)
│       ├── base.html
│       ├── index.html
│       ├── comic_detail.html
│       ├── chapter_read.html
│       ├── comic_form.html
│       ├── chapter_form.html
│       ├── login.html
│       ├── register.html
│       └── favorites.html
├── static/
│   ├── css/
│   │   └── style.css           # Основной стиль (более 18кб ретро-дизайна)
│   └── uploads/                # Сюда сохраняются обложки и страницы глав
├── run.py                      # Запуск через uvicorn
├── README.md
├── .gitignore
├── comixhub.db                 # Файл базы данных SQLite
└── config.py

Как запустить проект
1. Клонирование репозитория
Bashgit clone <ваш-репозиторий>
cd comixhub
2. Установка зависимостей
Bashpip install fastapi uvicorn sqlmodel python-jose[cryptography] passlib[bcrypt] python-multipart pydantic-settings jinja2
3. Запуск проекта
Bashpython run.py
Или напрямую:
Bashuvicorn app.main:app --host 127.0.0.1 --port 8000 --reload