# webui-skuf-tool

## Назначение

Набор инструментов для Open WebUI: поиск по базе знаний, генерация SQL и reranking результатов.

## Рекомендуемый формат базы знаний

Рекомендуемый формат метаданных для записей Knowledge описан в
[docs/knowledge_base_format.md](docs/knowledge_base_format.md).

## Инструмент: контекстный агент (поиск + SQL)

Файл: `tools/context_agent_tool.py`

Основные методы:

- `search_kb(query, top_k=5, filters=None, base_url="http://localhost:3000", api_key=None)`
  - Поиск по записям Knowledge через внутренний API Open WebUI.
  - `filters` — словарь фильтров по метаданным.
- `build_sql(table, columns, filters=None, limit=100, allowlist_json="data/sql_allowlist.json")`
  - Генерация параметризованного SQL только по allowlist.

## Инструмент: reranking

Файл: `tools/rerank_tool.py`

Основные методы:

- `rerank(query, candidates, top_k=5)`
  - Переупорядочивает кандидатов по релевантности.

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
