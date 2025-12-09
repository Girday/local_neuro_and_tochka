# Документация AI-пайплайна
## Orion Soft Internal AI Assistant — **Visior**
### Архитектура, поток данных и модель безопасности (Markdown-версия)

## 1. Обзор
AI-ассистент Orion Soft — это корпоративная система поиска и генерации ответов на основе внутренних документов компании.
Она использует:
- RAG (Retrieval-Augmented Generation)
- multi-stage retrieval (doc → section → chunk → reranking)
- MCP (Model Context Protocol) для запроса файлов по требованию
- двойной safety-контур (input / output filtering)
- OWASP-совместимый подход к безопасности и governance

## 2. Архитектура (высокий уровень)
Основные слои:
- Client Layer – UI, чат или интеграции
- Edge Layer – API Gateway, аутентификация
- Safety Layer (Input) – фильтрация вредоносных или запрещённых запросов
- AI Orchestrator – маршрутизация, выбор режима, orchestration
- Retrieval Layer – vector DB, hybrid search, rerankers
- LLM Layer – генерация ответа, RAG, tool-use, MCP
- Safety Layer (Output) – фильтрация вредных, рискованных или утечечных ответов
- Response Layer – форматирование, логирование
- Data Layer – хранилище документов, метаданные, политики

## 3. Полный пайплайн (пользователь → ответ)
### 3.1. Шаг 1 — Ввод пользователя
Пользователь отправляет вопрос через UI:
- Web-чат
- Telegram/Slack интеграция
- Корпоративный портал

### 3.2 Шаг 2 — API Gateway и аутентификация
Функции:
- Rate limiting
- JWT/OAuth2/SSO проверка
- Tenant isolation
- Basic request validation
После авторизации запрос передаётся в Input Safety.

## 4. Фильтр безопасности #1 — Input Guard
Первый слой защиты, предотвращающий вредоносные или неразрешённые запросы ещё до запуска дорогостоящего inference или RAG.

### 4.1 Задачи
- Content Safety (в соответствии с OWASP LLM-01)
- DLP: фильтрация PII, секретов, токенов
- Access Control и RBAC
- Tenant Isolation
- Bad prompt rejection (вред, взлом, политические ограничения)
- Optional: user-level throttling

### 4.2 Действия
- allow — запрос проходит далее
- transform — анонимизация, фильтрация PII
- block — безопасное сообщение пользователю

### 4.3 Технологии
- Компактная Safety-LLM / classifier
- Regex rulesets
- OWASP-совместимые политики (OPA/Rego по желанию)
- Keyword scoring

## 5. AI Orchestrator
Главный управляющий компонент.

### 5.1 Функции
- Выбор режима:
  - RAG
  - MCP tool-use
  - прямой inference
- Управление pipeline задачами
- Лимиты по времени (timeouts)
- Трейсинг и ID запросов
- Контроль token-budget

## 6. Retrieval Layer
Многоступенчатая система поиска:
- doc-level retrieval
- section-level retrieval
- chunk-level retrieval
- multi-stage reranking

### 6.1 Структура индекса
| Уровень   | Хранится                  | Применение             |
|-----------|---------------------------|------------------------|
| Document  | doc_embedding, metadata   | грубая фильтрация     |
| Section   | summary, summary_embedding| основная точка входа  |
| Chunk     | чанк текста, embedding    | точный поиск          |

### 6.2 Hybrid Search
Используется комбинация:
- Dense embeddings
- BM25 / keyword lookup
- Metadata-boosting (product, version)
- Cross-encoder reranking

### 6.3 Context Builder
Собирает оптимальный контекст по:
- токен-лимиту (например 4k токенов)
- важности чанков
- разнообразию документов
- необходимости включить хотя бы один чанк из каждого важного документа

## 7. RAG + MCP (LLM Inference Layer)
### 7.1 Основной пайплайн
LLM получает:
- инструкцию
- чанки контекста
- источники
- вопрос
LLM генерирует ответ.

### 7.2 MCP (Model Context Protocol)
Позволяет модели самостоятельно запрашивать сырой текст документа, если summary недостаточно.
LLM может вызвать:
- read_section(doc_id, page_start, page_end)
- read_file_range(doc_id, offset, length)
- search_index(...)
Это:
- снижает нагрузку на контекст
- позволяет уточнять данные из документа
- предотвращает ingestion больших файлов в prompt

## 8. Фильтр безопасности #2 — Output Guard
Второй safety-контур.
Он работает после LLM-ответа и перед отправкой пользователю.

### 8.1 Задачи
- Детекция вредного или опасного контента
- Предотвращение утечек данных (OWASP LLM-02)
- Защита внутренних секретов
- Контроль тональности и соблюдение корпоративного стиля
- Повторная проверка tenant isolation
- Переписывание ответа при нарушениях

### 8.2 Действия
- allow — отправить
- sanitize — переписать/обрезать
- block — вернуть безопасный отказ

## 9. Response Formatting Layer
Добавляет:
- ссылки на источники
- форматирование ответа
- локализацию (RU/EN)
- генерацию метаданных
- подготовку UI-payload

## 10. Логирование и мониторинг
Система ведёт:
- полный audit trail
- monitoring:
  - latency per component
  - RAG recall/precision
  - frequency MCP calls
  - safety blocks statistics
  - error tracking
  - red-team evaluation

## 11. Пайплайн обработки документов (Documents → Index)

### 11.1. Этап 1 — Загрузка
Документ помещается в object storage, создаётся запись doc_id.

### 11.2. Этап 2 — Парсинг
Извлечение:
- текста
- структуры (sections/headers/pages)
- табличных данных
- изображений (опционально)

### 11.3. Этап 3 — Chunking
Разделение на секции и чанки.

### 11.4. Этап 4 — Summaries
LLM генерирует section summary.

### 11.5. Этап 5 — Embeddings
Embeddings для:
- документов
- секций
- чанков

### 11.6. Этап 6 — Indexing
Вставка в Vector DB + метаданные + MCP-путь.

## 12. Безопасность данных и управление
### Соответствие OWASP (LLM Top 10)
| Категория | Реализация |
|-----------|------------|
| LLM01 – Prompt Injection | Safety-filters + context isolation + MCP restrictions |
| LLM02 – Data Leakage | Output Guard + tenant isolation |
| LLM03 – Data Poisoning | Sanitization ingestion pipeline |
| LLM04 – Misuse | RBAC + safety-input |
| LLM05 – Supply Chain | Verified dependency scanning |
| LLM06 – Model Theft | Local LLM execution |
| LLM07 – Privacy | PII filtering + DLP |
| LLM08 – Abuse | Rate limits |
| LLM09 – Insecure Tools | Sandboxed MCP |
| LLM10 – Logging Risks | No logging of secrets or PII |

## 13. Итог
Эта архитектура:
- устойчива к небезопасным запросам
- гибко расширяется
- использует best-practice retrieval и reranking
- использует безопасный доступ к большим документам через MCP
- обеспечивает высокое качество ответов
- полностью соответствует требованиям OWASP LLM Top-10