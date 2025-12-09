# Техническая спецификация (ТЗ)  
## Микросервис: **API Gateway**  
### Проект: Orion Soft Internal AI Assistant — *Visior*

---

# 1. Назначение сервиса

API Gateway является единым входным узлом для всех внешних запросов к платформе Visior.  
Он обеспечивает:
- маршрутизацию,
- аутентификацию и авторизацию,
- rate limiting,
- входной safety-контур,
- аудит и трассировку,
- унифицированный API для frontend'а и интеграций.

Gateway не содержит бизнес-логики ассистента — только функции edge layer.

---

# 2. Обязанности (Scope)

## 2.1 Основные обязанности
1. Приём всех HTTP-запросов клиентов/интеграций.  
2. Проверка аутентификации (JWT / OAuth2 / SSO).  
3. Верификация tenant context и прав пользователя.  
4. Генерация `trace_id` для всей цепочки вызовов.  
5. Rate limiting (per tenant / per user / per IP).  
6. Input Safety Filter (вызов safety service).  
7. Валидация структуры входных данных.  
8. Маршрутизация запросов по микросервисам:  
   - AI Orchestrator  
   - Ingestion Service  
   - Document Service  
9. Обёртка ошибок в единый формат (`error.code`, `trace_id`).  
10. Логирование запросов и ответов без PII.  

## 2.2 За пределами области ответственности
- RAG-инференс  
- LLM вызовы  
- чтение документов  
- обработка файлов  
- генерация ответов  
- chunking, ingestion, embeddings  

---

# 3. Обзор архитектуры

API Gateway — stateless HTTP сервис, разворачиваемый как NGINX+Lua, Envoy, или FastAPI proxy layer.  
Поддерживает горизонтальное масштабирование без сохранения внутреннего состояния.

```
Client
   ↓
API Gateway
   ↓  (auth + safety + routing)
Orchestrator / Ingestion / Documents / Safety
```

Сервис должен быть совместим с:
- Kubernetes Ingress  
- Istio / Linkerd сервис-меш  
- OPA / Rego policies (опционально)

---

# 4. API Endpoints (Public API)

## 4.1 Аутентификация

### `GET /api/v1/auth/me`
- Проверка токена  
- Возврат профиля пользователя + tenant_id

### `POST /api/v1/auth/refresh` (если используется refresh flow)
- Проверка refresh token  
- Выдача нового access token

---

## 4.2 Запрос к ассистенту

### `POST /api/v1/assistant/query`

**Последовательность:**
1. Аутентификация → OK  
2. Input Safety Check  
3. Маршрутизация в Orchestrator  
4. Получение ответа  
5. Форматирование output  

**Request**:
```json
{
  "query": "...",
  "language": "ru",
  "context": {
    "conversation_id": "conv_123",
    "channel": "web"
  }
}
```

**Response**:
```json
{
  "answer": "...",
  "sources": [...],
  "meta": {
    "trace_id": "abc",
    "latency_ms": 1234
  }
}
```

---

## 4.3 Загрузка и управление документами

### `POST /api/v1/documents/upload`
- multipart/form-data  
- file (PDF/Docx)
- поля метаданных (product, version, tags)

Внутренний маршрут: `/internal/ingestion/enqueue`

### `GET /api/v1/documents`
- Запрос списка документов для tenant'а  

Внутренний маршрут: `/internal/documents/list`

### `GET /api/v1/documents/{id}`
- Получение метаданных  

---

## 4.4 Healthchecks

### `GET /api/v1/health`
- Возвращает статический OK  

---

# 5. Внутренние зависимости

API Gateway вызывает следующие микросервисы:

| Сервис             | Endpoint                                  | Назначение |
|--------------------|-------------------------------------------|------------|
| Safety Service     | `/internal/safety/input-check`            | Проверка запроса |
| AI Orchestrator    | `/internal/ai/query`                      | Основной AI pipeline |
| Ingestion Service  | `/internal/ingestion/enqueue`             | Ingestion документов |
| Document Service   | `/internal/docs/...`                      | Получение метаданных |
| Auth Provider      | `/oauth/introspect` / JWKS                | Проверка JWT/SSO |

Все вызовы должны содержать:
- `X-Request-ID` (trace_id)  
- `X-Tenant-ID`  

---

# 6. Примечания по реализации

Скелет микросервиса расположен в `services/api_gateway` и разворачивается как FastAPI-приложение.

- точка входа: `api_gateway.main:app`  
- конфигурация через `API_GATEWAY_*` переменные (`config.py`)
- внешние вызовы оформлены в клиентах (`api_gateway/clients/*`) и автоматически добавляют `X-Request-ID`, `X-Tenant-ID`, `X-User-ID`
- включён базовый rate limiting per tenant/user и mock-режим (`API_GATEWAY_MOCK_MODE=true`) для локальной разработки без доступных backend'ов

---

# 7. Аутентификация и авторизация

## 7.1 Поддерживаемые режимы
- **JWT Access Tokens** (предпочтительно)
- **OIDC / OAuth2**
- **SAML (опционально)**

## 7.2 Проверка JWT
- Проверка подписи через JWKS  
- Проверка истечения  
- Проверка `issuer`, `audience`  

## 7.3 Изоляция Tenant
Каждый запрос содержит:
- `tenant_id` в JWT claim  
или  
- подменяется gateway согласно domain mapping  

Нельзя допустить:
- межтенантный доступ  
- утечку данных другого клиента  

---

# 8. Rate Limiting

## 8.1 Уровни
1. per IP  
2. per user  
3. per tenant  
4. per endpoint  

## 8.2 Требования
- Burst limit: 10 req/sec  
- Sustained limit: 2 req/sec per user  
- Тяжёлые endpoint'ы (`upload`) — отдельные лимиты  

## 8.3 Реализация
- FastAPI  
- Envoy rate-limit-service  
- Redis-based limiter  

---

# 9. Интеграция Input Safety

Каждый запрос к `/assistant/query` проходит safety-проверку.

## 9.1 Последовательность
1. Gateway получает запрос  
2. Извлекает текст `query`  
3. Формирует payload:
```json
{
  "user": {...},
  "query": "...",
  "trace_id": "abc"
}
```
4. Отправляет в Safety Service  
5. Поведение:
   - `allowed` → пропускаем  
   - `transformed` → заменяем запрос  
   - `blocked` → возвращаем ошибку  

## 9.2 Формат ошибки (при блокировке)
```json
{
  "error": {
    "code": "INPUT_BLOCKED",
    "message": "Query violates safety policy."
  },
  "trace_id": "abc"
}
```

---

# 10. Логирование и аудит

## 10.1 Обязательные поля лога
- timestamp  
- service: "gateway"  
- trace_id  
- user_id  
- tenant_id  
- endpoint  
- HTTP status  
- response latency  

## 10.2 Ограничения по PII
В логах нельзя хранить:
- исходный текст query  
- документы  
- файлы  
- токены  

Вместо текста query логируем только intent tags (из safety).

---

# 11. Обработка ошибок

Все ошибки должны быть приведены к единому формату:

```json
{
  "error": {
    "code": "BAD_REQUEST",
    "message": "Invalid payload",
    "details": {}
  },
  "trace_id": "abc"
}
```

## 11.1 Коды ошибок
- `UNAUTHORIZED`  
- `FORBIDDEN`  
- `RATE_LIMITED`  
- `INPUT_BLOCKED`  
- `INVALID_PAYLOAD`  
- `SERVICE_UNAVAILABLE`  
- `INTERNAL_ERROR`

---

# 12. Требования к производительности

| Операция                | Целевая задержка |
|-------------------------|------------------|
| Проверка auth           | ≤ 20 ms          |
| Вызов input safety      | ≤ 50 ms          |
| Маршрутизация в orchestrator | ≤ 10 ms     |
| Upload → enqueue        | ≤ 100 ms         |

---

# 13. Развёртывание и масштабирование

## 13.1 Горизонтальное масштабирование
Gateway должен быть stateless → масштабируется независимо.

## 13.2 Рекомендуемые инстансы
- минимум 3 pod'а  
- autoscale от CPU 60%  

## 13.3 Протоколы
- HTTP/1.1  
- HTTP/2 опционально  
- gRPC passthrough опционально  

---

# 14. Конфигурация

### 14.1 Переменные окружения
- `JWT_ISSUER`  
- `JWKS_URL`  
- `SAFETY_URL`  
- `ORCHESTRATOR_URL`  
- `INGESTION_URL`  
- `RATE_LIMIT_CONFIG`  
- `LOG_LEVEL`  
- `TRUSTED_PROXIES`  

### 14.2 Секреты
- TLS сертификаты  
- Ключи подписи  
- OAuth client secrets  

---

# 15. Healthchecks

## Liveness
`/internal/health/live`  
Всегда возвращает OK, если не упал.

## Readiness
`/internal/health/ready`  
Проверяет:
- доступность JWKS  
- доступность safety service  
- доступность orchestrator  

---

# 16. Открытые вопросы

1. Нужна ли поддержка GraphQL?  
2. Нужна ли загрузка файлов через resumable upload?  
3. Нужны ли индивидуальные policies на уровне tenant?  
4. Должны ли интеграции использовать API keys?  

---

# КОНЕЦ ДОКУМЕНТА