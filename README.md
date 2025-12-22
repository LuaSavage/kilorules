# Шаблоны файлов кеша для репозитория

Эта папка содержит примеры (шаблоны) файлов кеша для системы кеширования больших файлов репозитория.

## Структура

### Индексные файлы

Индексные файлы хранят информацию о диапазонах строк в больших файлах без самого кода:

- `schema.sql.index.json` - индекс для schema.sql
- `query.sql.index.json` - индекс для query.sql  
- `models.sql.go.index.json` - индекс для generated/models.sql.go
- `query.sql.go.index.json` - индекс для generated/query.sql.go

**Формат индексного файла:**
```json
{
  "file_path": "путь/к/файлу",
  "total_lines": 492,
  "ranges": {
    "имя_сущности": {
      "start_line": 1,
      "end_line": 10
    }
  }
}
```

### Файлы кеша запросов

Каждый файл кеша соответствует одному SQL запросу и содержит:
- Сам SQL запрос
- Информацию о диапазоне строк в query.sql
- Зависимые таблицы из schema.sql с их диапазонами строк и SQL кодом
- Сгенерированный Go код с диапазонами строк

**Формат файла кеша:**
```json
{
  "query_name": "GetItemInfo",
  "query_sql": "...",
  "query_range": { "start_line": 1, "end_line": 5 },
  "query_file": "src/pkg/repository/query.sql",
  "tables": [
    {
      "table_name": "items",
      "range": { "start_line": 226, "end_line": 244 },
      "file": "src/pkg/repository/schema.sql",
      "table_sql": "..."
    }
  ],
  "generated_code": [
    {
      "type": "function",
      "name": "GetItemInfo",
      "code": "...",
      "range": { "start_line": 1, "end_line": 50 },
      "file": "src/pkg/repository/generated/query.sql.go"
    }
  ]
}
```

## Примеры

- `GetItemInfo.cache.json` - пример кеша для простого запроса с одной таблицей
- `GetItemInfoByAssignmentID.cache.json` - пример кеша для запроса с JOIN и несколькими таблицами

## Использование

Эти шаблоны служат примером структуры файлов кеша. Реальные файлы кеша будут генерироваться автоматически инструментами индексации и кеширования.

