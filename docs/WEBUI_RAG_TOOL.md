# Инструмент RAG для WebUI

Мини-скрипт `scripts/webui_rag_tool.py` ищет по таблице `documents` (pgvector) и формирует промпт для WebUI. Работает на той же инстанции Postgres, что и WebUI; таблица может быть в отдельной БД, но проще скопировать её в БД WebUI.

## Предварительно

- Скопируйте `.env` из `env.example` и заполните `POSTGRES_*`, `OLLAMA_BASE_URL`, `EMBEDDING_MODEL`.
- Таблица `documents` должна быть импортирована и иметь эмбеддинги.
- Шаблон промпта по умолчанию: `prompts/qwen_rag_prompt_webui.txt`.

## Быстрый запуск

```bash
source .env
python scripts/webui_rag_tool.py --query "как настроить pgvector?" --limit 5 --threshold 0.15
```

Опции:

- `--knowledge-db` — другое имя БД с таблицей `documents` (если не совпадает с `POSTGRES_DB`).
- `--simple-prompt` — использовать упрощённый промпт вместо файла.
- `--json` — вывести результат в JSON (удобно для интеграции в WebUI/инструменты).

## Формат ответа

- Подбор top-K документов с полем `score = 1 - distance`.
- Собранный промпт (по шаблону или упрощённый) для передачи модели.

## Копирование таблицы в БД WebUI

Если знания лежат в другой БД того же Postgres:

```bash
source .env
SRC_DB=knowledge_db DST_DB=${POSTGRES_DB} RESET_TARGET=true \
  bash scripts/copy_documents_to_webui_db.sh
```

- `RESET_TARGET=true` очистит цель перед заливкой (иначе данные добавятся).
- Скрипт использует `init.sql` для гарантии расширения `vector`.

## Интеграция с WebUI

- Используйте `--json` и подайте `prompt` в WebUI как исходный текст для модели.
- При желании можно обернуть запуск в HTTP-эндпоинт или tool-код WebUI, вызывая `webui_rag_tool.py`.

## Проверка

- Перед использованием убедитесь, что `pgvector` установлен: `psql ... -c "CREATE EXTENSION IF NOT EXISTS vector;"`.
- Прогоните тестовый запрос (пример выше) и убедитесь, что возвращаются документы со значениями score.
