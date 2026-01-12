# Foodgram Project

## Описание

**Foodgram** — это веб-приложение для любителей кулинарии. Оно позволяет пользователям:
- Публиковать рецепты.
- Просматривать рецепты других пользователей.
- Добавлять рецепты в избранное.
- Формировать список покупок на основе выбранных рецептов.

Проект разработан с использованием **Django** и **Django REST Framework**. Фронтенд приложения работает на **React**.

## Стек технологий

- **Backend**: Python 3, Django, Django REST Framework, PostgreSQL
- **Frontend**: React
- **API**: REST API
- **Контейнеризация**: Docker, Docker Compose
- **Web-сервер**: Nginx

## Установка и запуск

### 1. Клонирование репозитория
```bash
git clone https://github.com/grestedjesko/foodgram-st.git
cd foodgram-st
git checkout -b develop
git pull origin develop
```
### 2. Запуск контейнеров

Перейдите в папку **infra** и запустите контейнеры с помощью Docker Compose:
```bash
cd infra
docker-compose up -d
```
Это развернет проект с базой данных **PostgreSQL**, бекендом на **Django** и веб-сервером **Nginx**.

### 3. Создание суперпользователя

```bash
docker compose exec backend python manage.py loaddata fixtures/users.json
```
Для доступа к админ панели используйте суперпользователя
admin@example.com
12345678
или создайте своего:
```bash
docker-compose exec backend python manage.py createsuperuser
```

### 4. Загрузка ингредиентов

Приложение использует список ингредиентов, который можно загрузить из файла:
```bash
docker-compose exec backend python manage.py load_ingredients data/ingredients.json
```


### 4.1. Загрузка рецептов

Приложение использует список ингредиентов, который можно загрузить из файла:
```bash
docker compose exec backend python manage.py loaddata fixtures/recipes.json
docker compose exec backend python manage.py loaddata fixtures/ingredientinrecipe.json
```

### 5. Доступ к проекту

* Главная страница: http://localhost
* Админ-панель Django: http://localhost/admin или http://127.0.0.1:8000/admin
* API документация: http://localhost/api/docs/

### 6. Остановка сервисов
Для остановки контейнеров выполните:
```bash
docker-compose down
```

## Переменные окружения (ENV)

Для корректной работы проекта требуется настроить переменные окружения в файле .env. Создайте его в папке backend:
```bash
cd infra
touch .env
```
Добавьте в него:
```ini

DB_ENGINE=django.db.backends.postgresql
DB_NAME=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
SECRET_KEY=your-secret-key
DEBUG=0
ALLOWED_HOSTS=127.0.0.1,localhost
```
После этого перезапустите контейнеры:
```bash
docker-compose down
docker-compose up -d
```

## Полная спецификация API
Откройте по адресу localhost/api/docs

## Автор
Разработано студентом ИТИС Мироновым Максимом Олеговичем в рамках итогового проекта
