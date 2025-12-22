# Repository Cache Usage Rules for Kilocode and DeepSeek

## Overview

The repository implements a caching system for large files (`schema.sql`, `query.sql`, and generated Go files). Instead of reading large files entirely, use the cache to retrieve only the necessary context.

## Cache Structure

The cache is located in the `src/pkg/repository/cache/cache_data/` directory and contains:

### Index Files (metadata only, no code)
- `schema.sql.index.json` - index of tables, types, and functions from schema.sql
- `query.sql.index.json` - index of SQL queries from query.sql
- `models.sql.go.index.json` - index of structures and types from generated/models.sql.go
- `query.sql.go.index.json` - index of functions from generated/query.sql.go

### Query Cache Files (contain code + metadata)
- `{QueryName}.cache.json` - complete cache for each SQL query

## Usage Rules

### 1. When Working with SQL Queries

**INSTEAD OF:**
- Reading the entire `query.sql` file (3049 lines)
- Manually searching for the needed query

**USE:**
1. Find the needed query in `cache/cache_data/query.sql.index.json`
2. Read the corresponding cache file `{QueryName}.cache.json`
3. The cache file contains:
   - SQL query code
   - Dependent tables with their SQL definitions
   - Generated Go code (functions, structures)

**Example:**
```json
// cache/cache_data/GetItemInfo.cache.json contains:
{
  "query_name": "GetItemInfo",
  "query_sql": "...",  // SQL query
  "tables": [          // All dependent tables with their definitions
    {
      "table_name": "items",
      "table_sql": "create table ..."
    }
  ],
  "generated_code": [  // All related Go code
    {
      "type": "function",
      "name": "GetItemInfo",
      "code": "..."
    }
  ]
}
```

### 2. When Working with Database Schema

**INSTEAD OF:**
- Reading the entire `schema.sql` file (492 lines)
- Manually searching for table definition

**USE:**
1. Find the table in `cache/cache_data/schema.sql.index.json`
2. Use the line range from the index to read only the needed part:
   ```json
   {
     "ranges": {
       "items": {
         "start_line": 226,
         "end_line": 244
       }
     }
   }
   ```
3. Or use a query cache file that already contains the needed tables

### 3. When Working with Generated Go Code

**INSTEAD OF:**
- Reading the entire `generated/query.sql.go` file (10378 lines)
- Reading the entire `generated/models.sql.go` file (698 lines)

**USE:**
1. Find the needed function/structure in the corresponding index file:
   - `cache/cache_data/query.sql.go.index.json` for functions
   - `cache/cache_data/models.sql.go.index.json` for structures
2. Use the line range to read only the needed part
3. Or use a query cache file that already contains the related code

## Workflow Algorithm

### When User Asks About an SQL Query:

1. **Check for Cache:**
   - Look for file `cache/cache_data/{QueryName}.cache.json`
   - If the file exists, use it - it contains EVERYTHING needed

2. **If Cache Doesn't Exist, Use Index:**
   - Open `cache/cache_data/query.sql.index.json`
   - Find the query by name
   - Use the line range to read only the needed part of `query.sql`

3. **For Dependencies:**
   - If using a cache file - dependencies are already included
   - If using an index - find tables in `schema.sql.index.json` and read their definitions

### When User Asks About a Table:

1. **Check Index:**
   - Open `cache/cache_data/schema.sql.index.json`
   - Find the table by name
   - Use the line range to read only the needed part of `schema.sql`

2. **Or Find in Query Cache:**
   - Search for cache files that use this table
   - They already contain the table definition

### When User Asks About a Go Function/Structure:

1. **Check Index:**
   - Open the corresponding index file
   - Find the function/structure by name
   - Use the line range to read only the needed part

2. **Or Use Query Cache:**
   - If the function is related to an SQL query, use the query cache file

## Usage Examples

### Example 1: User Asks About Query GetItemInfo

```python
# ✅ CORRECT:
# 1. Read cache file
cache_file = "cache/cache_data/GetItemInfo.cache.json"
# File contains: SQL query, tables, Go code - EVERYTHING needed

# ❌ INCORRECT:
# Read entire query.sql (3049 lines) and search for query
```

### Example 2: User Asks About Table items

```python
# ✅ CORRECT:
# 1. Read index
index = read_json("cache/cache_data/schema.sql.index.json")
range = index["ranges"]["items"]  # start_line: 226, end_line: 244
# 2. Read only needed lines from schema.sql
table_def = read_lines("schema.sql", 226, 244)

# ❌ INCORRECT:
# Read entire schema.sql (492 lines) and search for table
```

### Example 3: User Asks About Function GetItemInfo in Go

```python
# ✅ CORRECT:
# 1. Use query cache (if available)
cache = read_json("cache/cache_data/GetItemInfo.cache.json")
go_code = cache["generated_code"][0]["code"]

# OR
# 2. Use index
index = read_json("cache/cache_data/query.sql.go.index.json")
range = index["ranges"]["GetItemInfo"]
go_code = read_lines("generated/query.sql.go", range["start_line"], range["end_line"])

# ❌ INCORRECT:
# Read entire generated/query.sql.go (10378 lines)
```

## Important Notes

1. **Always check for cache before reading large files**
2. **Cache files contain full context** - use them when possible
3. **Index files are lightweight** - they can be read entirely for searching
4. **Line ranges in indexes** allow reading only needed parts of large files
5. **Cache updates automatically** when source files change (via Python script)

## File Paths

- Base path: `src/pkg/repository/`
- Cache: `src/pkg/repository/cache/cache_data/`
- Source files:
  - `src/pkg/repository/schema.sql`
  - `src/pkg/repository/query.sql`
  - `src/pkg/repository/generated/models.sql.go`
  - `src/pkg/repository/generated/query.sql.go`

## Cache Update

Cache is generated by Python script `cache_generator.py`. The script automatically:
- Calculates file hashes
- Updates only changed indexes
- Generates cache for all queries

Run: `python cache_generator.py` from `src/pkg/repository/cache/` directory
