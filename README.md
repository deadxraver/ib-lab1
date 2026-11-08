# Python Rest backend

## Описание проекта

Веб-приложение для создания постов.

## API

Все защищенные эндпоинты требуют заголовок:

```
Authorization: Bearer <access_token>
```

### POST /api/auth/register - Регистрация

```bash
curl -X POST http://127.0.0.1:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"<username>","password":"<password>"}'
```

### POST /auth/login - Аутентификация

```bash
curl -X POST http://127.0.0.1:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"<username>","password":"<password>"}'
```
В ответ должны получить токен при успешной авторизации.

### GET /api/data - Защищенные данные

```bash
curl -i http://127.0.0.1:5000/api/data \
  -H "Authorization: Bearer <token>"
```

### POST /api/posts - Создание поста

```bash
curl -X POST http://127.0.0.1:5000/api/posts \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"title":"<title>","content":"<content>"}'
```

## Реализованные меры защиты

### Защита от SQLi

Используется SQLAlchemy ORM (Flask-SQLAlchemy),
который генерирует параметризованные запросы.
Пользовательские данные передаются как связанные параметры, а не как часть SQL-строки.

### Защита от XSS

Чтобы браузер не выполнял пользовательский код,
который возвращается в ответе,
используем `markupsafe.escape()` при отправке ответа.

### Защита от Broken Authentication

#### Хэширование паролей

Пароли не хранятся в открытом виде.
Используется bcrypt с уникальной солью.

Регистрация:

```python
bcrypt.hashpw(
    password.encode("utf-8"),
    bcrypt.gensalt()
).decode("utf-8")
```

Логин:

```python
bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8"))
```

#### JWT-аутентификация

При успешном логине выдается подписанный JWT с user_id в sub:

```python
token = create_access_token(identity=str(user.id))
```

Токен подписан JWT_SECRET_KEY (алгоритм HS256), срок жизни 1 час.
Секрет вынесен в переменные окружения, не хранится в коде.

#### Middleware для проверки токена

Каждый защищенный эндпоинт помечен декоратором `jwt_required()`, который перехватывает
запрос до контроллера и проверяет:

1. Наличие заголовка Authorization: Bearer <token>
1. Корректность подписи
1. Срок действия
1. Формат JWT

При любой ошибке возвращается 401 Unauthorized, до кода контроллера запрос не доходит.

#### Обработка ошибок без утечек

Кастомные обработчики 404, 405, 500 возвращают JSON без трейсбеков -
это предотвращает утечку внутренней структуры приложения.

### Дополнительные меры
- Stateless: JWT не хранится на сервере, нет серверных сессий, нет Session Fixation
- Валидация входа: `request.get_json(silent=True)` не падает на битом JSON
- Ограничения длины: username не короче 3, password не короче 8, проверяется на сервере
- Разделение ответственности: модели в models.py, эндпоинты в app.py

## Примеры взаимодействия

```bash
$ curl -i -X POST http://127.0.0.1:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"StrongPass123"}'
HTTP/1.1 201 CREATED
Server: Werkzeug/3.1.9 Python/3.13.5
Date: Sun, 08 Nov 2026 17:17:21 GMT
Content-Type: application/json
Content-Length: 41
Connection: close

{"id":1,"msg":"Registration successful"}
$ curl -i -X POST http://127.0.0.1:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"StrongPass123"}'
HTTP/1.1 200 OK
Server: Werkzeug/3.1.9 Python/3.13.5
Date: Sun, 08 Nov 2026 17:17:36 GMT
Content-Type: application/json
Content-Length: 367
Connection: close

{"access_token":"eyJ...","token_type":"Bearer"}
$ curl -i http://127.0.0.1:5000/api/data
HTTP/1.1 401 UNAUTHORIZED
Server: Werkzeug/3.1.9 Python/3.13.5
Date: Sun, 08 Nov 2026 17:17:59 GMT
Content-Type: application/json
Content-Length: 39
Connection: close

{"msg":"Missing Authorization Header"}
$ export TOKEN='eyJ...'
$ curl -i http://127.0.0.1:5000/api/data \
  -H "Authorization: Bearer $TOKEN"
HTTP/1.1 200 OK
Server: Werkzeug/3.1.9 Python/3.13.5
Date: Sun, 08 Nov 2026 17:18:43 GMT
Content-Type: application/json
Content-Length: 24
Connection: close

{"data":[],"user_id":1}
$ curl -i -X POST http://127.0.0.1:5000/api/posts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Post 1","content":"Hellooooo"}'
HTTP/1.1 201 CREATED
Server: Werkzeug/3.1.9 Python/3.13.5
Date: Sun, 08 Nov 2026 17:19:14 GMT
Content-Type: application/json
Content-Length: 30
Connection: close

{"id":1,"msg":"Post created"}
$ curl http://127.0.0.1:5000/api/data -H "Authorization: Bearer $TOKEN"
{"data":[{"content":"Hellooooo","id":1,"title":"Post 1"}],"user_id":1}
$ curl -X POST http://127.0.0.1:5000/api/posts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"<script>alert(1)</script>","content":"xss"}'
{"id":2,"msg":"Post created"}
$ curl http://127.0.0.1:5000/api/data -H "Authorization: Bearer $TOKEN"
{"data":[{"content":"Hellooooo","id":1,"title":"Post 1"},{"content":"xss","id":2,"title":"&amp;lt;script&amp;gt;alert(1)&amp;lt;/script&amp;gt;"}],"user_id":1}

```
