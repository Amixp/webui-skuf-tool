# SKUF: импорт CSV в Postgres (+ pgvector) для RAG

## Что есть в данных

В `skuf/*.csv` сейчас 3 источника:

- `CRQ.csv` (26 колонок)
- `PBI.csv` (22 колонки)
- `PKE.csv` (13 колонок)

Все три файла:

- `encoding`: `utf-8-sig`
- `delimiter`: `,`
- первая строка — заголовки

Пробник формата:

```bash
bash scripts/podman_csv_probe.sh
```

Результат сохраняется в `data/skuf_csv_probe.json`.

## Универсальная схема (raw + связь с RAG)

Схема создаётся SQL-файлом `init_skuf.sql`:

- `skuf_sources`: метаданные источника (имя файла, delimiter/encoding, список колонок)
- `skuf_rows`: сырой слой, одна строка CSV -> `data JSONB`
- `documents`: существующая таблица для RAG (не ломаем), добавляем только служебные колонки через `ALTER TABLE ... IF NOT EXISTS`

Важно: `init_skuf.sql` подключен в `podman-compose.yml` как init script Postgres (выполняется при первой инициализации volume).

## Импорт

Импорт CSV -> raw слой (через **postgres контейнер**, без сборки `chat-app`).

### Podman (тест): импорт

```bash
bash scripts/podman_import_skuf_psql.sh
```

### Docker (прод): импорт

```bash
docker compose -f docker-compose.yml -f docker-compose.import.yml up -d postgres
bash scripts/docker_import_skuf_psql.sh
```

Что делает:

- поднимает `postgres`
- запускает `psql + \copy` внутри контейнера `postgres` (через `bash -lc`)
- пишет данные в `skuf_sources` и `skuf_rows`

## Как использовать это ИИ-агенту

Минимальная универсальная стратегия:

- агент делает SQL-запросы в `skuf_rows` по JSONB (`data->>'Поле'`)
- фильтрует по `skuf_sources.source_name`

Пример (идея):

- поиск по статусу/приоритету
- выгрузка нескольких полей в контекст

Дальше поверх `skuf_rows` можно строить:

- материализованные представления под конкретные домены (CRQ/PBI/PKE)
- генерацию `documents.content` на основе `data` (без эмбеддингов на первом шаге)

## Подготовка `documents` из сырых данных

Сборка `documents` из `skuf_rows` (embedding остаётся NULL, зато агент уже может брать текстовый контекст):

### Podman (тест): сборка documents

```bash
bash scripts/podman_build_documents.sh
```

### Docker (прод): сборка documents

```bash
bash scripts/docker_build_documents.sh
```

## Пайплайн векторизации (`documents.embedding`)

### Предпосылки

- На хосте должен быть запущен **Ollama** и доступен из podman-контейнера по `host.containers.internal:11434`
- Должна быть скачана embedding-модель (по умолчанию `bge-m3`)

### Запуск

### Podman (тест): векторизация

```bash
# при необходимости можно переопределить модель/адрес
export OLLAMA_BASE_URL="http://host.containers.internal:11434"
export EMBEDDING_MODEL="bge-m3"
export BATCH_SIZE="64"

bash scripts/podman_vectorize.sh
```

### Docker (прод): векторизация

```bash
export OLLAMA_BASE_URL="http://host.docker.internal:11434"
export EMBEDDING_MODEL="bge-m3"
export BATCH_SIZE="64"

bash scripts/docker_vectorize.sh
```

Если будет ошибка размерности вектора — embedding-модель не совпадает с размером `VECTOR(768)` в таблице `documents`.
Для `bge-m3` обычно нужна размерность **1024** — тогда выполни миграцию и повтори векторизацию:

```bash
bash scripts/podman_set_embedding_dim_1024.sh
bash scripts/podman_vectorize.sh
```

Для docker:

```bash
bash scripts/docker_set_embedding_dim_1024.sh
bash scripts/docker_vectorize.sh
```
