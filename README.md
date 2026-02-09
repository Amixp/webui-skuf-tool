# webui-skuf-tool

## Назначение

Набор инструментов для Open WebUI: поиск по базе знаний, генерация SQL и reranking результатов.

## Установка

```bash
pip install -r requirements.txt
```

Единственная зависимость — `requests`.

## Интеграция с Open WebUI

1. В админ-панели Open WebUI перейти в **Workspace → Tools**.
2. Создать новый инструмент и вставить содержимое нужного файла из `tools/`.
3. Параметры подключения:
   - `base_url` — адрес Open WebUI (по умолчанию `http://localhost:3000`).
   - `api_key` — API-ключ пользователя. Получить: **Settings → Account → API Keys**.
   - `endpoint` — путь эндпоинта поиска (по умолчанию `/api/knowledge/search`).

## Рекомендуемый формат базы знаний

Рекомендуемый формат метаданных для записей Knowledge описан в
[docs/knowledge_base_format.md](docs/knowledge_base_format.md).

## Инструмент: контекстный агент (поиск + SQL)

Файл: `tools/context_agent_tool.py`

### Методы

- `search_kb(query: str, top_k: int = 5, filters: Optional[Dict[str, str]] = None, base_url: str = "http://localhost:3000", api_key: Optional[str] = None, endpoint: str = "/api/knowledge/search") -> Dict[str, Any]`
  - Поиск по записям Knowledge через внутренний API Open WebUI.
  - `filters` — словарь фильтров по метаданным (ключи нормализуются автоматически).
  - `endpoint` — путь API-эндпоинта поиска.
  - Возвращает `{"query": ..., "results": [...], "total": N}`.

- `build_sql(table: str, columns: List[str], filters: Optional[Dict[str, Any]] = None, limit: int = 100, allowlist_json: str = "data/sql_allowlist.json") -> Dict[str, Any]`
  - Генерация параметризованного SQL только по allowlist.
  - `columns` — **обязательный** список колонок для SELECT.
  - Если таблица отсутствует в allowlist, возвращает `{"error": "Table '...' is not in the allowlist."}`.
  - При успехе возвращает `{"sql": "...", "params": {...}}`.

- `describe_format() -> Dict[str, Any]`
  - Возвращает рекомендуемую схему метаданных для записей базы знаний (обязательные и рекомендуемые поля).

## SQL Allowlist

Файл: `data/sql_allowlist.json`

Определяет разрешённые таблицы и колонки для генерации SQL. Формат — JSON-объект, где ключ — имя таблицы, значение — массив допустимых колонок:

```json
{
  "incidents": ["incident_id", "service", "priority", "status", ...],
  "problems": ["problem_id", "service", ...]
}
```

Чтобы разрешить новую таблицу или колонку — добавить запись в этот файл. Колонки и фильтры, отсутствующие в allowlist, молча отбрасываются.

## Инструмент: reranking

Файл: `tools/rerank_tool.py`

### Методы

- `rerank(query: str, candidates: List[Dict[str, Any]], top_k: int = 5) -> Dict[str, Any]`
  - Переупорядочивает кандидатов по релевантности на основе **token overlap scoring** (подсчёт совпадающих токенов между запросом и текстом кандидата). Это лёгкий эвристический ранжировщик, не ML-модель.
  - Текст кандидата берётся из полей `text`, `summary` или строкового представления объекта.
  - Возвращает `{"query": ..., "results": [{"score": N, "candidate": {...}}, ...]}`.

## Пример: формат записи Knowledge

```text
id: PBI000000183188
service: Видеокомфорт
priority: Medium
status: Closed
created_at: 2023-09-01 02:21:52
summary: Потеря видеоархива у всех пользователей (INC000018102347).
resolution: Разнесение VIP IP, настройка failover.
```

## Документация

- [Формат базы знаний](docs/knowledge_base_format.md)
- [Подход к RAG по инцидентам](docs/INCIDENT_RAG_APPROACH.md)
- [Реализация RAG по инцидентам](docs/INCIDENT_RAG_IMPLEMENTATION.md)
- [Поиск по JSONB в PostgreSQL](docs/POSTGRES_JSONB_SEARCH.md)
- [Настройка релевантности](docs/RELEVANCE_TUNING.md)
- [Импорт данных в SKUF](docs/SKUF_IMPORT.md)
- [RAG-инструмент для WebUI](docs/WEBUI_RAG_TOOL.md)
- [Класс RAG-инструмента для WebUI](docs/WEBUI_RAG_TOOL_CLASS.md)
