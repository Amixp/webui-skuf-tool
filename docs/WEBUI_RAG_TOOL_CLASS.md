# Документация: Инструмент RAG для WebUI (класс Tools)

## Оглавление

- Описание
- Возможности
- Требования
- Настройка
- Импорт исходных файлов в Open WebUI (document/document_chunk)
- Использование в WebUI
- Методы и примеры использования
- Примеры сценариев использования
- Обработка ошибок
- Логирование
- Производительность
- Расширение функциональности
- Устранение неполадок
- Дополнительные ресурсы

## Описание

`scripts/webui_rag_tool_class.py` — инструмент для WebUI в формате класса `Tools`, предоставляющий методы для работы с RAG-системой и извлечения embedding данных из таблиц Open WebUI `document` и `document_chunk` в PostgreSQL с расширением pgvector.

## Возможности

- **Векторный поиск документов** по семантическому сходству
- **Извлечение документов по ID** с полной информацией
- **Поиск по метаданным** (JSONB поле)
- **Получение эмбеддингов** для текста через Ollama
- **Автоматическое управление пулом соединений** с БД

## Требования

- Python 3.11+
- PostgreSQL с расширением pgvector
- Ollama с моделью для эмбеддингов (например, `bge-m3`)
- Таблицы Open WebUI:
  - `document` (id, collection_name, name, title, filename, content, user_id, timestamp)
  - `document_chunk` (id, vector, collection_name, text, vmetadata)

## Настройка

### 1. Переменные окружения

**Где создать файл `.env`:**

Создайте файл `.env` в **корне проекта** (там же, где находится `env.example`):

```bash
# Из корня проекта
cp env.example .env
# Затем отредактируйте .env и заполните значения
```

**Важно:** Скрипт автоматически ищет `.env` в корне проекта (директория на уровень выше `scripts/`). Если файл находится в другом месте, скрипт попытается загрузить его из текущей рабочей директории.

**Как скрипт загружает переменные:**

Скрипт использует библиотеку `python-dotenv` для автоматической загрузки переменных из `.env` файла при инициализации класса `Tools`. Переменные загружаются в следующем порядке:

1. Сначала ищется `.env` в корне проекта (`/path/to/project/.env`)
2. Если не найден, загружается из текущей рабочей директории
3. Если и там нет, используются переменные из системного окружения

**Заполните следующие переменные в `.env`:**

```bash
# Обязательные переменные для подключения к БД
POSTGRES_HOST=postgres          # или localhost для локального запуска
POSTGRES_PORT=5432
POSTGRES_DB=rag_db              # Основная БД
POSTGRES_USER=rag_user
POSTGRES_PASSWORD=rag_password
POSTGRES_SSLMODE=disable        # или require для продакшена

# Конфигурация Ollama
OLLAMA_BASE_URL=http://localhost:11434  # или http://ollama:11434 для Docker
EMBEDDING_MODEL=bge-m3          # Модель для эмбеддингов

# Опционально: отдельная БД для знаний
KNOWLEDGE_DB=knowledge_db       # Если таблица documents в другой БД
```

### Настройка в Open WebUI (Docker, удаленный сервер)

Если Open WebUI запущен в Docker на удаленном сервере (например, `http://10.148.14.12:8080`), переменные нужно передать **в контейнер WebUI**. Есть два типовых способа:

**A. Через `docker-compose.yml` (рекомендуется):**

```yaml
services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:latest
    ports:
      - "8080:8080"
    environment:
      - POSTGRES_HOST=172.17.0.1
      - POSTGRES_PORT=5432
      - POSTGRES_DB=rag_db
      - POSTGRES_USER=rag_user
      - POSTGRES_PASSWORD=rag_password
      - POSTGRES_SSLMODE=disable
      - OLLAMA_BASE_URL=http://172.17.0.1:11434
      - EMBEDDING_MODEL=qllama/bge-m3:f16
      - KNOWLEDGE_DB=rag_db
    volumes:
      - ./scripts:/app/scripts
```

После изменения `docker-compose.yml` перезапусти контейнер:

```bash
docker-compose up -d --force-recreate
```

**B. Через `docker run`:**

```bash
docker run -d --name open-webui \
  -p 8080:8080 \
  -e POSTGRES_HOST=172.17.0.1 \
  -e POSTGRES_PORT=5432 \
  -e POSTGRES_DB=rag_db \
  -e POSTGRES_USER=rag_user \
  -e POSTGRES_PASSWORD=rag_password \
  -e POSTGRES_SSLMODE=disable \
  -e OLLAMA_BASE_URL=http://172.17.0.1:11434 \
  -e EMBEDDING_MODEL=qllama/bge-m3:f16 \
  -e KNOWLEDGE_DB=rag_db \
  -v $(pwd)/scripts:/app/scripts \
  ghcr.io/open-webui/open-webui:latest
```

**Важно:**

- `POSTGRES_HOST=172.17.0.1` и `OLLAMA_BASE_URL=http://172.17.0.1:11434` актуальны, если БД и Ollama живут на хосте Docker той же машины.
- Если БД/Ollama на другом хосте — подставь их IP/hostname.
- Файл `scripts/webui_rag_tool_class.py` должен быть доступен внутри контейнера (`/app/scripts`).
- После изменения переменных **обязательно** перезапусти контейнер WebUI.

### 2. Установка зависимостей

**Важно:** Убедитесь, что установлена библиотека `python-dotenv` для автоматической загрузки `.env` файла.

```bash
pip install psycopg2-binary requests loguru pydantic python-dotenv
```

Или используйте `requirements.txt` (включает все необходимые зависимости):

```bash
pip install -r requirements.txt
```

**Проверка установки:**

```bash
python -c "from dotenv import load_dotenv; print('python-dotenv установлен')"
```

**Проверка загрузки `.env`:**

После создания `.env` файла можно проверить, что переменные загружаются правильно:

```bash
# Из корня проекта
python -c "from dotenv import load_dotenv; from pathlib import Path; load_dotenv(Path('.env')); import os; print('POSTGRES_HOST:', os.getenv('POSTGRES_HOST'))"
```

Или просто запустите скрипт — в логах будет сообщение о загрузке `.env`:

```bash
# При инициализации Tools() в логах будет:
# INFO: Загружен .env файл: /path/to/project/.env
```

### 3. Подготовка базы данных

Убедитесь, что:

1. Расширение `pgvector` установлено:

   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

2. Таблицы Open WebUI существуют:

   ```sql
   SELECT COUNT(*) FROM document;
   SELECT COUNT(*) FROM document_chunk;
   ```

3. Индекс для векторного поиска по `document_chunk.vector` создан:

   ```sql
   CREATE INDEX IF NOT EXISTS idx_document_chunk_vector
   ON document_chunk USING ivfflat (vector vector_cosine_ops) WITH (lists = 100);
   ```

### 4. Проверка Ollama

Убедитесь, что Ollama запущен и модель эмбеддингов доступна:

```bash
# Проверка доступности Ollama
curl http://localhost:11434/api/tags

# Проверка модели эмбеддингов
curl http://localhost:11434/api/show -d '{"name": "bge-m3"}'
```

## Импорт исходных файлов в Open WebUI (document/document_chunk)

Этот раздел описывает скрипт `scripts/import_webui_documents.py`, который:

- импортирует исходные файлы в `document`
- режет текст на чанки и записывает их в `document_chunk`
- векторизует чанки через Ollama

### Переменные окружения для импорта

Скрипт `import_webui_documents.py` автоматически загружает `.env` из корня проекта (на уровень выше `scripts/`). Если файла нет — использует текущее окружение.

```bash
# Подключение к БД
POSTGRES_HOST=pgvector
POSTGRES_PORT=5432
POSTGRES_DB=openwebui
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_SSLMODE=disable

# Ollama (должна быть доступна из контейнера)
OLLAMA_BASE_URL=http://ollama:11434
EMBEDDING_MODEL=qllama/bge-m3:f16

# Источник файлов
WEBUI_SOURCE_DIR=data/webui_source
FILE_EXTENSIONS=.txt,.md,.csv,.json

# Чанкирование
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
CHUNKING_MODE=simple
STRUCTURAL_OVERLAP=0
STRUCTURAL_OVERLAP_MODE=auto

# Векторизация
EMBEDDING_BATCH_SIZE=32
WEBUI_VECTOR_DIM=1536
EMBEDDING_DIMENSION=1536

# Прочее
WEBUI_USER_ID=system
COLLECTION_PREFIX=webui
LIMIT_FILES=0
REPLACE_CHUNKS=true
SKIP_EXISTING=false
UPDATE_BY_ID=false
SKIP_SAME_HASH=true
SKIP_SAME_HASH_IN_DB=false
SKIP_SAME_HASH_IN_DB_MAX_BYTES=2000000
DOCUMENT_TABLE=document
CHUNK_TABLE=document_chunk
AUTO_CREATE_TABLES=false
```

### Как запускать

```bash
python scripts/import_webui_documents.py
```

### Как работает

1) Для каждого файла создаётся `document` (upsert по `collection_name`)
2) Текст режется на чанки в зависимости от режима:
   - `CHUNKING_MODE=simple` — по фиксированному размеру с overlap (текущий)
   - `CHUNKING_MODE=structural` — с учётом структуры документа (параграфы, заголовки, строки CSV, объекты JSON)
3) Каждая часть векторизуется через Ollama
4) Чанки пишутся в `document_chunk` с `vmetadata` (source_file, chunk_index, total_chunks + метаданные структуры)

### Режимы чанкирования

**`CHUNKING_MODE=simple` (по умолчанию):**

- Разбивка текста по фиксированному размеру символов с overlap
- Использует `CHUNK_OVERLAP` для перекрытия чанков
- Быстро и просто
- Подходит для однородных текстов

**`CHUNKING_MODE=structural`:**

- **TXT/MD файлы:** разбивка по параграфам (`\n\n`) и заголовкам Markdown (`#`, `##`, `###`). Сохраняет заголовок раздела в метаданные.
- **CSV файлы:** каждая строка или группа строк — отдельный чанк. Заголовки сохраняются в метаданные.
- **JSON файлы:** разбивка по top-level ключам или элементам массива. Путь в JSON сохраняется в метаданные.
- Лучше сохраняет семантическую целостность и контекст
- Использует `STRUCTURAL_OVERLAP` и `STRUCTURAL_OVERLAP_MODE` для перекрытия

**Рекомендации:**

- Используйте `structural` для структурированных документов (документация, CSV с инцидентами, JSON логов)
- Используйте `simple` для простых текстов без явной структуры

### Перекрытие чанков (Overlap) в структурном режиме

**`STRUCTURAL_OVERLAP`** — размер перекрытия между чанками:

- Для режимов `char` — количество символов
- Для режимов `paragraph`, `row`, `section`, `object` — количество структурных элементов
- По умолчанию `0` (без перекрытия)
- Рекомендуемые значения:
  - `char`: 100-300 символов
  - `paragraph`: 1-2 параграфа
  - `row` (CSV): 1-3 строки
  - `section` (MD): 1 раздел
  - `object` (JSON): 1 объект

**`STRUCTURAL_OVERLAP_MODE`** — режим перекрытия:

- `auto` (по умолчанию) — автоматический выбор оптимального режима:
  - `.md` → `section` (по разделам)
  - `.csv` → `row` (по строкам)
  - `.json` → `object` (по объектам)
  - `.txt` → `paragraph` (по параграфам)
- `char` — универсальный режим по символам (работает для всех форматов)
- `paragraph` — по параграфам (TXT, MD)
- `section` — по разделам Markdown (MD)
- `row` — по строкам CSV (CSV)
- `object` — по объектам JSON (JSON)

**Примеры использования:**

```bash
# Автоматический режим с перекрытием в 1 структурный элемент
export CHUNKING_MODE=structural
export STRUCTURAL_OVERLAP=1
export STRUCTURAL_OVERLAP_MODE=auto

# Markdown: перекрытие по разделам
export CHUNKING_MODE=structural
export STRUCTURAL_OVERLAP=1
export STRUCTURAL_OVERLAP_MODE=section

# CSV: перекрытие по строкам (дублирование последних 2 строк в следующем чанке)
export CHUNKING_MODE=structural
export STRUCTURAL_OVERLAP=2
export STRUCTURAL_OVERLAP_MODE=row

# JSON: перекрытие по объектам
export CHUNKING_MODE=structural
export STRUCTURAL_OVERLAP=1
export STRUCTURAL_OVERLAP_MODE=object

# Универсальное перекрытие по символам (300 символов)
export CHUNKING_MODE=structural
export STRUCTURAL_OVERLAP=300
export STRUCTURAL_OVERLAP_MODE=char
```

**Преимущества overlap:**

- Сохраняет контекст между соседними чанками
- Улучшает качество поиска на границах чанков
- Особенно полезно для CSV (не теряется связь между строками) и MD (сохраняется контекст раздела)

**Примеры метаданных в `vmetadata` при `structural` режиме:**

```json
// Для Markdown (с overlap)
{
  "source_file": "docs/setup.md",
  "chunk_index": 3,
  "total_chunks": 12,
  "chunking_mode": "structural",
  "structural_overlap": 1,
  "overlap_mode": "section",
  "heading": "Настройка pgvector",
  "heading_level": 2,
  "paragraph_indices": [5, 6, 7]
}

// Для CSV (с overlap по строкам)
{
  "source_file": "skuf/INC.csv",
  "chunk_index": 2,
  "total_chunks": 8,
  "chunking_mode": "structural",
  "structural_overlap": 2,
  "overlap_mode": "row",
  "csv_rows": 10,
  "csv_header": "Номер,Статус,Описание,Решение"
}

// Для JSON (с overlap по объектам)
{
  "source_file": "data/logs.json",
  "chunk_index": 5,
  "total_chunks": 20,
  "chunking_mode": "structural",
  "structural_overlap": 1,
  "overlap_mode": "object",
  "json_key": "incidents",
  "json_array_index": 42
}

// Для TXT (с overlap по параграфам)
{
  "source_file": "readme.txt",
  "chunk_index": 1,
  "total_chunks": 5,
  "chunking_mode": "structural",
  "structural_overlap": 1,
  "overlap_mode": "paragraph",
  "paragraph_indices": [3, 4, 5]
}
```

### Политика обработки существующих данных

- `SKIP_EXISTING=true` — пропускает файл, если документ уже найден по `collection_name` или `filename`.
- `UPDATE_BY_ID=true` — если документ найден, обновляет его по `id` (вместо upsert).
- `SKIP_SAME_HASH=true` — пропуск дубликатов по hash в рамках одного запуска.
- `SKIP_SAME_HASH_IN_DB=true` — пропуск, если в БД уже есть документ с таким же содержимым (сравнение через md5 для маленьких файлов).
- `SKIP_SAME_HASH_IN_DB_MAX_BYTES` — лимит размера текста для md5‑проверки в БД (по умолчанию 2MB). Если файл больше — проверка пропускается.
- `AUTO_CREATE_TABLES=true` — создаёт таблицы `DOCUMENT_TABLE`/`CHUNK_TABLE` и индексы, если их нет. Размерность берётся из `WEBUI_VECTOR_DIM` или `EMBEDDING_DIMENSION` (иначе 1536).

### Проверка результата

```sql
SELECT COUNT(*) FROM document;
SELECT COUNT(*) FROM document_chunk;
SELECT COUNT(*) FROM document_chunk WHERE vector IS NOT NULL;
```

## Использование в WebUI

### Интеграция с WebUI

1. Скопируйте файл `scripts/webui_rag_tool_class.py` в директорию инструментов WebUI
2. Импортируйте класс `Tools` в конфигурации WebUI
3. WebUI автоматически обнаружит методы класса как доступные инструменты

### Пример конфигурации для WebUI

```python
# В конфигурации WebUI
from scripts.webui_rag_tool_class import Tools

# Инициализация инструментов
tools = Tools()
```

WebUI автоматически создаст инструменты из методов класса с описаниями из docstrings и Field.

## Методы и примеры использования

### 1. `search_documents_by_query` — Векторный поиск документов

**Описание:** Поиск документов по семантическому сходству с запросом.

**Параметры:**

- `query` (str, обязательный) — Текст запроса для поиска
- `limit` (int, по умолчанию 5) — Количество документов для возврата (top-K)
- `min_score` (float, по умолчанию 0.0) — Минимальный порог релевантности (0.0-1.0)

**Пример использования в WebUI:**

```text
Пользователь: "Найди документы про ошибки подключения к базе данных"
```

WebUI вызовет:

```python
tools.search_documents_by_query(
    query="ошибки подключения к базе данных",
    limit=5,
    min_score=0.15
)
```

**Пример ответа:**

```text
Найдено документов: 3

[Документ #42, релевантность: 0.856] | Метаданные: {"type": "incident", "category": "database"}
Ошибка подключения к PostgreSQL возникает при неправильных учетных данных...

---

[Документ #78, релевантность: 0.743] | Метаданные: {"type": "incident", "category": "database"}
Проблема с пулом соединений: превышен лимит подключений...

---

[Документ #91, релевантность: 0.692] | Метаданные: {"type": "incident", "category": "database"}
Решение проблемы timeout при подключении к БД...
```

### 2. `get_document_by_id` — Извлечение документа по ID

**Описание:** Получение полной информации о конкретном документе.

**Параметры:**

- `document_id` (int, обязательный) — ID документа для извлечения

**Пример использования:**

```text
Пользователь: "Покажи мне документ номер 42"
```

WebUI вызовет:

```python
tools.get_document_by_id(document_id=42)
```

**Пример ответа:**

```text
Документ #42
Создан: 2024-01-15 10:30:00
Обновлён: 2024-01-15 10:30:00
Источник: incidents / INC-2024-001 (ID: 1001)
Метаданные: {"type": "incident", "category": "database", "priority": "high"}

Содержимое:
Ошибка подключения к PostgreSQL возникает при неправильных учетных данных.
Проверьте переменные окружения POSTGRES_USER и POSTGRES_PASSWORD.
Убедитесь, что пользователь имеет права на доступ к базе данных.
```

### 3. `get_embedding_for_text` — Получение эмбеддинга текста

**Описание:** Получение векторного представления текста (для отладки и проверки).

**Параметры:**

- `text` (str, обязательный) — Текст для получения эмбеддинга

**Пример использования:**

```text
Пользователь: "Получи эмбеддинг для текста 'ошибка базы данных'"
```

WebUI вызовет:

```python
tools.get_embedding_for_text(text="ошибка базы данных")
```

**Пример ответа:**

```text
Эмбеддинг получен успешно.
Размерность: 768
Модель: bge-m3
Первые 10 значений: [0.0234, -0.0156, 0.0891, 0.0023, -0.0456, 0.1234, -0.0078, 0.0345, -0.0123, 0.0567]
(Всего значений: 768)
```

### 4. `search_documents_by_metadata` — Поиск по метаданным

**Описание:** Поиск документов по значению в JSONB поле `metadata`.

**Параметры:**

- `metadata_key` (str, обязательный) — Ключ в JSONB metadata для поиска
- `metadata_value` (str, обязательный) — Значение для поиска
- `limit` (int, по умолчанию 20) — Максимальное количество документов

**Пример использования:**

```text
Пользователь: "Найди все инциденты типа 'database'"
```

WebUI вызовет:

```python
tools.search_documents_by_metadata(
    metadata_key="category",
    metadata_value="database",
    limit=20
)
```

**Пример ответа:**

```text
Найдено документов: 5

[Документ #42]
Метаданные: {"type": "incident", "category": "database", "priority": "high"}
Содержимое: Ошибка подключения к PostgreSQL возникает при неправильных учетных данных...

---

[Документ #78]
Метаданные: {"type": "incident", "category": "database", "priority": "medium"}
Содержимое: Проблема с пулом соединений: превышен лимит подключений...
```

## Примеры сценариев использования

### Сценарий 1: Поиск решения проблемы

**Запрос пользователя:**

```text
"У меня ошибка подключения к базе данных. Найди похожие случаи и решения."
```

**Действия WebUI:**

1. Вызывает `search_documents_by_query` с запросом "ошибка подключения к базе данных"
2. Получает топ-5 релевантных документов
3. Формирует ответ на основе найденных решений

### Сценарий 2: Получение детальной информации

**Запрос пользователя:**

```text
"Покажи подробности документа 42"
```

**Действия WebUI:**

1. Вызывает `get_document_by_id(document_id=42)`
2. Получает полную информацию о документе
3. Отображает содержимое, метаданные и источник

### Сценарий 3: Фильтрация по категории

**Запрос пользователя:**

```text
"Покажи все инциденты с приоритетом 'high'"
```

**Действия WebUI:**

1. Вызывает `search_documents_by_metadata(metadata_key="priority", metadata_value="high")`
2. Получает список документов с высоким приоритетом
3. Отображает результаты

### Сценарий 4: Комбинированный поиск

**Запрос пользователя:**

```text
"Найди документы про базу данных, но только с релевантностью выше 0.7"
```

**Действия WebUI:**

1. Вызывает `search_documents_by_query(query="база данных", limit=10, min_score=0.7)`
2. Получает только высокорелевантные документы
3. Отображает результаты с указанием релевантности

## Обработка ошибок

Инструмент обрабатывает следующие ошибки:

1. **Отсутствие подключения к БД:**

   ```text
   "Ошибка: пул соединений с БД не инициализирован. Проверьте переменные окружения."
   ```

2. **Ошибка получения эмбеддинга:**

   ```text
   "Ошибка: не удалось получить эмбеддинг запроса через Ollama."
   ```

   Проверьте:

   - Запущен ли Ollama
   - Доступна ли модель эмбеддингов
   - Правильность `OLLAMA_BASE_URL`

3. **Документы не найдены:**

   ```text
   "По запросу '...' документы не найдены (порог: 0.15)."
   ```

   Попробуйте:

   - Уменьшить `min_score`
   - Увеличить `limit`
   - Изменить формулировку запроса

## Логирование

Инструмент логирует все операции в файл `webui_rag_tool.log`:

```bash
# Просмотр логов
tail -f webui_rag_tool.log

# Поиск ошибок
grep ERROR webui_rag_tool.log
```

## Производительность

- **Пул соединений:** Используется `SimpleConnectionPool` (1-10 соединений)
- **Таймауты:** 120 секунд для запросов к Ollama
- **Лимиты:** Рекомендуется `limit <= 20` для быстрого ответа

## Расширение функциональности

Для добавления новых методов:

1. Добавьте метод в класс `Tools`
2. Используйте `Field` с описанием для параметров
3. Добавьте docstring с описанием метода
4. WebUI автоматически обнаружит новый инструмент

**Пример:**

```python
def my_custom_search(
    self,
    keyword: str = Field(..., description="Ключевое слово для поиска"),
) -> str:
    """
    Описание вашего метода.
    """
    # Ваша логика
    return "Результат"
```

## Устранение неполадок

### Проблема: "Пул соединений не инициализирован"

**Решение:**

1. Проверьте переменные окружения: `echo $POSTGRES_HOST`
2. Убедитесь, что `.env` загружен: `source .env`
3. Проверьте доступность БД: `psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB`

### Проблема: "Не удалось получить эмбеддинг"

**Решение:**

1. Проверьте Ollama: `curl http://localhost:11434/api/tags`
2. Убедитесь, что модель загружена: `ollama pull bge-m3`
3. Проверьте `OLLAMA_BASE_URL` в `.env`

### Проблема: "Документы не найдены"

**Решение:**

1. Проверьте наличие эмбеддингов: `SELECT COUNT(*) FROM documents WHERE embedding IS NOT NULL;`
2. Уменьшите `min_score` (например, до 0.0)
3. Проверьте размерность эмбеддингов в таблице

## Дополнительные ресурсы

- [Документация pgvector](https://github.com/pgvector/pgvector)
- [Документация Ollama](https://ollama.ai/docs)
- [WEBUI_RAG_TOOL.md](./WEBUI_RAG_TOOL.md) — документация CLI-версии инструмента
