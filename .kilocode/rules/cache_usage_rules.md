# Cache Usage Guide for AI Assistants

## Quick Start

### For Working with SQL Query:

```bash
# 1. Check for cache
ls cache/cache_data/{QueryName}.cache.json

# 2. If file exists - use it
# It contains EVERYTHING needed: SQL, tables, Go code

# 3. If file doesn't exist - use index
cat cache/cache_data/query.sql.index.json | jq '.ranges."{QueryName}"'
```

### For Working with Table:

```bash
# 1. Find in index
cat cache/cache_data/schema.sql.index.json | jq '.ranges."{TableName}"'

# 2. Use line range to read only needed part
sed -n '226,244p' schema.sql
```

## Cache File Structure

### Index File (example: `schema.sql.index.json`):
```json
{
  "file_path": "src/pkg/repository/schema.sql",
  "total_lines": 492,
  "ranges": {
    "items": {
      "start_line": 226,
      "end_line": 244
    }
  }
}
```

### Query Cache File (example: `GetItemInfo.cache.json`):
```json
{
  "query_name": "GetItemInfo",
  "query_sql": "-- name: GetItemInfo :one\nSELECT *\nFROM items\nWHERE...",
  "query_range": {"start_line": 1, "end_line": 5},
  "query_file": "src/pkg/repository/query.sql",
  "tables": [
    {
      "table_name": "items",
      "range": {"start_line": 226, "end_line": 244},
      "file": "src/pkg/repository/schema.sql",
      "table_sql": "create table if not exists items\n(...)"
    }
  ],
  "generated_code": [
    {
      "type": "function",
      "name": "GetItemInfo",
      "code": "func (q *Queries) GetItemInfo(...) {...}",
      "range": {"start_line": 1, "end_line": 50},
      "file": "src/pkg/repository/generated/query.sql.go"
    }
  ]
}
```

## Checklist for AI Assistant

When user asks about:

### SQL Query:
- [ ] Check `cache/cache_data/{QueryName}.cache.json`
- [ ] If exists - use cache file (contains everything)
- [ ] If not - use `query.sql.index.json` to find line range

### Table:
- [ ] Check `cache/cache_data/schema.sql.index.json`
- [ ] Find table line range
- [ ] Read only needed range from `schema.sql`
- [ ] Or find table in query cache files

### Go Function/Structure:
- [ ] Check corresponding index file
- [ ] Find line range
- [ ] Read only needed range
- [ ] Or use query cache file

## Benefits of Using Cache

1. **Token savings** - no need to read thousands of lines
2. **Fast access** - all information in one place
3. **Full context** - cache files contain dependencies
4. **Accuracy** - only current code parts are used

## Cache Update

Cache is updated automatically when files change via:
```bash
python cache_generator.py
```

The script checks file hashes and updates only changed parts.
