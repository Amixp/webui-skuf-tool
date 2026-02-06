# webui-skuf-tool

## Назначение

Набор инструментов для Open WebUI: поиск по базе знаний, генерация SQL и reranking результатов.

## Рекомендуемый формат базы знаний

Документы лучше хранить в markdown с заголовочной метадатой и разделителем `---`.
Подробная спецификация и пример: [docs/knowledge_base_format.md](docs/knowledge_base_format.md).

## Инструмент: контекстный агент (поиск + SQL)

Файл: `tools/context_agent_tool.py`

Основные методы:

- `search_kb(query, path="data/knowledge_base.md", top_k=5, filters=None)`
  - Поиск по документам.
  - `filters` — словарь фильтров по метаданным.
- `build_sql(table, columns, filters=None, limit=100, allowlist_json="data/sql_allowlist.json")`
  - Генерация параметризованного SQL только по allowlist.

## Инструмент: reranking

Файл: `tools/rerank_tool.py`

Основные методы:

- `rerank(query, candidates, top_k=5)`
  - Переупорядочивает кандидатов по релевантности.

## Пример: формат документа

```text
Problem ID: PBI000000183188
Сервис: Видеокомфорт
Приоритет: Medium
Статус: Closed
Дата создания: 2023-09-01 02:21:52

Описание: Потеря видеоархива у всех пользователей (INC000018102347).
Решение: Разнесение VIP IP, настройка failover.
---
Номер инцидента: INC000021013376
Имя услуги: Видеокомфорт
Статус инцидента: Закрыт

Описание: ТТ7 803129, нет трансляции по камере
```
