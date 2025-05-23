# Flashik Exchange

REST API биржа для торговли активами, разработанная на Django.

## Требования

- Python 3.10+
- Django
- Django REST Framework
- SQLite3

## Установка и запуск

### 1. Клонирование репозитория

```bash
git clone <url-репозитория>
cd tochka
```

### 2. Создание виртуального окружения

```bash
python -m venv venv
source venv/bin/activate  # для Linux/macOS
# или
venv\Scripts\activate     # для Windows
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Настройка базы данных

```bash
cd flashik_exchange
python manage.py migrate
```

### 5. Запуск сервера

```bash
python manage.py runserver
```

Сервер будет доступен по адресу: http://localhost:8000/

## API Endpoints

### Публичные эндпоинты

- `POST /api/v1/public/register/` - Регистрация нового пользователя
- `GET /api/v1/public/instrument/` - Получение списка торговых инструментов
- `GET /api/v1/public/orderbook/{ticker}/` - Получение стакана заявок по инструменту

### Приватные эндпоинты (требуют авторизации)

- `GET /api/v1/balance/` - Получение баланса пользователя
- `POST /api/v1/balance/deposit/` - Пополнение баланса
- `POST /api/v1/balance/withdraw/` - Вывод средств
- `POST /api/v1/order/` - Создание нового ордера
- `GET /api/v1/order/` - Получение списка ордеров пользователя

## Авторизация

Для доступа к приватным эндпоинтам необходимо передавать токен в заголовке запроса:

```
Authorization: Token <your_token>
```

Токен можно получить при регистрации пользователя.

## Разработка

Проект использует:
- Django 5.1
- Django REST Framework 3.14
- SQLite как базу данных
- Swagger/ReDoc для документации API

## Документация API

После запуска сервера документация доступна по адресам:
- Swagger UI: http://localhost:8000/swagger/
- ReDoc: http://localhost:8000/redoc/
