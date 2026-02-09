# Поиск в JSONB полях PostgreSQL

Документация по различным способам поиска данных в JSONB полях PostgreSQL, включая поиск по полю "Номер инцидента" и другим метаданным.

## Содержание

1. [Базовые операторы JSONB](#базовые-операторы-jsonb)
2. [Точный поиск](#точный-поиск)
3. [Частичный поиск](#частичный-поиск)
4. [Поиск с использованием индексов](#поиск-с-использованием-индексов)
5. [Поиск во вложенных структурах](#поиск-во-вложенных-структурах)
6. [Поиск в массивах](#поиск-в-массивах)
7. [Комплексные запросы](#комплексные-запросы)
8. [Примеры для таблицы incidents](#примеры-для-таблицы-incidents)
9. [Примеры для таблицы documents](#примеры-для-таблицы-documents)

## Базовые операторы JSONB

### Операторы доступа к JSONB

- `->` - возвращает JSON объект (для вложенных объектов)
- `->>` - возвращает текст (для получения значения как строки)
- `#>` - доступ по пути (массив ключей)
- `#>>` - доступ по пути с возвратом текста
- `@>` - проверка содержания (contains)
- `?` - проверка существования ключа
- `?|` - проверка существования любого из ключей
- `?&` - проверка существования всех ключей

## Точный поиск

### 1. Поиск по точному значению (оператор `->>`)

```sql
-- Поиск по точному значению в таблице incidents
SELECT * FROM incidents
WHERE metadata->>'Номер инцидента' = 'INC000001234';

-- Поиск в таблице documents
SELECT * FROM documents
WHERE metadata->>'Номер инцидента' = 'INC000001234';

-- С выборкой конкретных полей
SELECT
    id,
    number,
    metadata->>'Номер инцидента' as incident_number_from_metadata,
    description,
    status
FROM incidents
WHERE metadata->>'Номер инцидента' = 'INC000001234';
```

### 2. Поиск с использованием оператора `@>` (рекомендуется для индексов)

```sql
-- Использует GIN индекс (быстрее)
SELECT * FROM incidents
WHERE metadata @> '{"Номер инцидента": "INC000001234"}'::jsonb;

-- Для documents
SELECT * FROM documents
WHERE metadata @> '{"Номер инцидента": "INC000001234"}'::jsonb;
```

## Частичный поиск

### 3. Поиск по части значения (LIKE)

```sql
-- Поиск по части номера в incidents
SELECT * FROM incidents
WHERE metadata->>'Номер инцидента' LIKE '%INC000001%';

-- Поиск в documents
SELECT * FROM documents
WHERE metadata->>'Номер инцидента' LIKE '%INC000001%';

-- Поиск с начала строки
SELECT * FROM incidents
WHERE metadata->>'Номер инцидента' LIKE 'INC000001%';
```

### 4. Поиск без учета регистра (ILIKE)

```sql
-- Без учета регистра
SELECT * FROM incidents
WHERE metadata->>'Номер инцидента' ILIKE '%inc000001%';

-- Поиск в documents
SELECT * FROM documents
WHERE metadata->>'Номер инцидента' ILIKE '%inc000001%';
```

### 5. Поиск с регулярными выражениями

```sql
-- Использование регулярных выражений
SELECT * FROM incidents
WHERE metadata->>'Номер инцидента' ~ '^INC\d{9}$';

-- Без учета регистра
SELECT * FROM incidents
WHERE metadata->>'Номер инцидента' ~* '^inc\d{9}$';
```

## Поиск с использованием индексов

### 6. Оптимизированный поиск с GIN индексом

```sql
-- Использует индекс incidents_metadata_gin_idx (самый быстрый)
SELECT * FROM incidents
WHERE metadata @> '{"Номер инцидента": "INC000001234"}'::jsonb;

-- Поиск по нескольким полям одновременно
SELECT * FROM incidents
WHERE metadata @> '{"Номер инцидента": "INC000001234", "Статус": "Закрыт"}'::jsonb;
```

### 7. Проверка существования ключа

```sql
-- Проверка наличия ключа
SELECT * FROM incidents
WHERE metadata ? 'Номер инцидента';

-- Проверка наличия любого из ключей
SELECT * FROM incidents
WHERE metadata ?| array['Номер инцидента', 'номер_инцидента'];

-- Проверка наличия всех ключей
SELECT * FROM incidents
WHERE metadata ?& array['Номер инцидента', 'Статус'];
```

## Поиск во вложенных структурах

### 8. Поиск в вложенных объектах

```sql
-- Если номер находится в вложенном объекте
SELECT * FROM incidents
WHERE metadata->'incident'->>'Номер инцидента' = 'INC000001234';

-- Или через путь (массив ключей)
SELECT * FROM incidents
WHERE metadata#>>'{incident,Номер инцидента}' = 'INC000001234';

-- Более глубокий путь
SELECT * FROM incidents
WHERE metadata#>>'{data,incident,number}' = 'INC000001234';
```

### 9. Поиск с использованием jsonb_path_exists (PostgreSQL 12+)

```sql
-- Поиск через JSONPath
SELECT * FROM incidents
WHERE jsonb_path_exists(metadata, '$.Номер инцидента ? (@ == "INC000001234")');

-- Поиск с условием
SELECT * FROM incidents
WHERE jsonb_path_exists(metadata, '$.Номер инцидента ? (@ like_regex "INC.*")');
```

## Поиск в массивах

### 10. Поиск значения в массиве

```sql
-- Если номер хранится в массиве
SELECT * FROM incidents
WHERE metadata @> '{"Номер инцидента": ["INC000001234", "INC000001235"]}'::jsonb;

-- Поиск любого элемента массива
SELECT * FROM incidents
WHERE metadata->'Номер инцидента' @> '"INC000001234"'::jsonb;
```

### 11. Поиск через jsonb_array_elements

```sql
-- Развертывание массива и поиск
SELECT DISTINCT i.*
FROM incidents i,
     jsonb_array_elements(i.metadata->'Номер инцидента') AS elem
WHERE elem::text = '"INC000001234"';
```

## Комплексные запросы

### 12. Поиск по нескольким вариантам названия поля

```sql
-- Если поле может называться по-разному
SELECT * FROM incidents
WHERE metadata->>'Номер инцидента' = 'INC000001234'
   OR metadata->>'номер_инцидента' = 'INC000001234'
   OR metadata->>'IncidentNumber' = 'INC000001234'
   OR metadata->>'incident_number' = 'INC000001234';
```

### 13. Поиск с использованием COALESCE

```sql
-- Поиск с fallback на разные варианты названий
SELECT * FROM incidents
WHERE COALESCE(
    metadata->>'Номер инцидента',
    metadata->>'номер_инцидента',
    metadata->>'IncidentNumber'
) = 'INC000001234';
```

### 14. Комбинированный поиск (JSONB + обычные поля)

```sql
-- Поиск в JSONB и обычном поле number
SELECT * FROM incidents
WHERE number = 'INC000001234'
   OR metadata->>'Номер инцидента' = 'INC000001234';

-- С приоритетом обычного поля
SELECT * FROM incidents
WHERE number = 'INC000001234'
   OR (number IS NULL AND metadata->>'Номер инцидента' = 'INC000001234');
```

### 15. Поиск с сортировкой и лимитом

```sql
-- Поиск с сортировкой по дате
SELECT * FROM incidents
WHERE metadata->>'Номер инцидента' = 'INC000001234'
ORDER BY creation_date DESC
LIMIT 10;
```

### 16. Поиск с агрегацией

```sql
-- Подсчет количества инцидентов по статусу из metadata
SELECT
    metadata->>'Статус инцидента' as status,
    COUNT(*) as count
FROM incidents
WHERE metadata ? 'Статус инцидента'
GROUP BY metadata->>'Статус инцидента';
```

## Примеры для таблицы incidents

### 17. Полный пример с выборкой всех полей

```sql
SELECT
    id,
    number,
    creation_date,
    status,
    description,
    metadata->>'Номер инцидента' as metadata_number,
    metadata->>'Приоритет инцидента' as priority,
    metadata->>'Имя услуги' as service_name,
    metadata
FROM incidents
WHERE metadata->>'Номер инцидента' = 'INC000001234';
```

### 18. Поиск по диапазону дат и номеру из metadata

```sql
SELECT * FROM incidents
WHERE metadata->>'Номер инцидента' LIKE 'INC%'
  AND creation_date BETWEEN '2023-01-01' AND '2023-12-31'
ORDER BY creation_date DESC;
```

### 19. Поиск с JOIN (если нужно связать с другими таблицами)

```sql
-- Пример с documents (если есть связь)
SELECT
    i.id,
    i.number,
    i.metadata->>'Номер инцидента' as metadata_number,
    d.content
FROM incidents i
LEFT JOIN documents d ON d.metadata->>'Номер инцидента' = i.number
WHERE i.metadata->>'Номер инцидента' = 'INC000001234';
```

## Примеры для таблицы documents

### 20. Поиск документов по номеру инцидента

```sql
-- Поиск документов, связанных с инцидентом
SELECT
    id,
    content,
    metadata->>'Номер инцидента' as incident_number,
    metadata->>'source_type' as source_type,
    created_at
FROM documents
WHERE metadata->>'Номер инцидента' = 'INC000001234';
```

### 21. Поиск документов с фильтрацией по нескольким полям metadata

```sql
SELECT * FROM documents
WHERE metadata @> '{
    "Номер инцидента": "INC000001234",
    "source_type": "csv"
}'::jsonb;
```

### 22. Поиск документов с извлечением вложенных данных

```sql
-- Если структура metadata сложнее
SELECT
    id,
    content,
    metadata->'incident'->>'Номер инцидента' as incident_number,
    metadata->'incident'->>'Статус' as status
FROM documents
WHERE metadata->'incident'->>'Номер инцидента' = 'INC000001234';
```

## Производительность и оптимизация

### Рекомендации по использованию индексов

1. **GIN индекс** - используйте для оператора `@>`:
   ```sql
   CREATE INDEX incidents_metadata_gin_idx ON incidents USING GIN (metadata);
   ```

2. **GIN индекс с jsonb_path_ops** - для более быстрого поиска по путям:
   ```sql
   CREATE INDEX incidents_metadata_path_ops_idx
   ON incidents USING GIN (metadata jsonb_path_ops);
   ```

3. **Выраженный индекс** - для часто используемых полей:
   ```sql
   CREATE INDEX incidents_metadata_number_idx
   ON incidents ((metadata->>'Номер инцидента'));
   ```

### Сравнение производительности операторов

| Оператор            | Использует индекс | Скорость | Рекомендация                            |
| ------------------- | ----------------- | -------- | --------------------------------------- |
| `@>`                | Да (GIN)          | ⭐⭐⭐⭐⭐    | Используйте для точного поиска          |
| `->>` + `=`         | Нет               | ⭐⭐⭐      | Для простых случаев                     |
| `->>` + `LIKE`      | Нет               | ⭐⭐       | Медленно, избегайте на больших таблицах |
| `jsonb_path_exists` | Зависит           | ⭐⭐⭐⭐     | Для сложных путей                       |

## Примеры использования в Python (psycopg2)

```python
# Точный поиск
cursor.execute("""
    SELECT * FROM incidents
    WHERE metadata->>'Номер инцидента' = %s
""", ('INC000001234',))

# Поиск с использованием индекса
cursor.execute("""
    SELECT * FROM incidents
    WHERE metadata @> %s::jsonb
""", (json.dumps({'Номер инцидента': 'INC000001234'}),))

# Частичный поиск
cursor.execute("""
    SELECT * FROM incidents
    WHERE metadata->>'Номер инцидента' LIKE %s
""", ('%INC000001%',))
```

## Примечания

1. **В таблице `incidents`** номер обычно хранится в поле `number` (TEXT), а не в `metadata`. Для поиска по полю `number` используйте:
   ```sql
   SELECT * FROM incidents WHERE number = 'INC000001234';
   ```

2. **Экранирование специальных символов**: При использовании оператора `->>` значения автоматически экранируются, но при использовании `LIKE` или регулярных выражений нужно быть осторожным с спецсимволами.

3. **NULL значения**: Оператор `->>` возвращает NULL, если ключ не существует. Используйте `COALESCE` или проверку `?` для обработки отсутствующих ключей.

4. **Типы данных**: JSONB автоматически преобразует типы, но для сравнения чисел используйте правильные операторы:
   ```sql
   -- Для чисел
   WHERE (metadata->>'priority')::int > 3
   ```

## Дополнительные ресурсы

- [PostgreSQL JSONB документация](https://www.postgresql.org/docs/current/datatype-json.html)
- [JSONB операторы и функции](https://www.postgresql.org/docs/current/functions-json.html)
- [GIN индексы для JSONB](https://www.postgresql.org/docs/current/gin.html)
