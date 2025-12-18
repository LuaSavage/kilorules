# SQL Query Style Guide for sqlc (TagMe TaskFlow)

This document defines the conventions and rules for writing SQL queries in the `query.sql` file for use with sqlc. The goal is to maintain consistency, readability, and correctness across all generated queries.

## 1. Naming Conventions

### Query Names
- Use **PascalCase** (e.g., `GetItemInfo`, `InsertTaskInSkills`).
- Prefix indicates the operation:
  - `Get` – SELECT returning rows.
  - `Insert` – INSERT statements.
  - `Update` – UPDATE statements.
  - `Delete` / `Del` – DELETE statements (short form `Del` is allowed).
  - `Lock` – SELECT … FOR UPDATE (row‑level locking).
  - `Check` – EXISTS subqueries that return a boolean.
  - `Set` – UPDATE that sets a specific state (e.g., `SetStatusStop`).
  - `Upsert` – INSERT … ON CONFLICT.
  - `Add` – adding relations (e.g., `AddMarkersToTaskAccess`).
  - `Remove` – removing relations.
  - `Increment` – incrementing counters.
  - `Expire` – expiring assignments.
  - `Archive` / `Unarchive` – moving data to/from archive.
  - `Fill` – filling missing data.
  - `Drop` – dropping a status flag.
  - `Mark` – marking a record (e.g., `InsertMarkedTask`).
  - `Recalculate` – recalculating statistics.
  - `Enable` / `Disable` – enabling/disabling records.
  - `Post` – posting an assignment result.
  - `Skip` – skipping an assignment.
  - `Reject` – rejecting assignments.
  - `Assign` – assigning an assignment to a marker.
  - `Activate` – activating an assignment.
  - `Unassign` – unassigning an assignment.
  - `Release` – releasing a job lock.
  - `Put` – updating a single field (e.g., `PutItemOverlap`).

### Suffixes (sqlc command types)
- `:one` – query returns exactly one row.
- `:many` – query returns zero or more rows.
- `:exec` – query does not return rows (INSERT/UPDATE/DELETE without RETURNING).
- `:copyfrom` – batch insert operation (used with `sqlc.copyfrom`).

### Additional Name Parts
- Use `ByID`, `ByIDs`, `ByTaskID`, `ByMarkerID`, etc. to indicate filtering criteria.
- For queries that return a single row **without** locking, add `WithoutLock` (e.g., `TaskByIDWithoutLock`).
- For queries that return aggregated statistics, include `Stat` (e.g., `GetTaskAssignmentStatuses`).

## 2. Formatting

### Case
- SQL keywords **UPPERCASE** (SELECT, FROM, WHERE, JOIN, etc.).
- Table and column names **lowercase_snake_case**.

### Table and CTE Aliases
- Aliases are formed by taking the **first letter of each word** in the table or CTE name, written in **uppercase**.
  - Single‑word table: `tasks` → `T`
  - Multi‑word table: `project_markers` → `PM`
  - CTE: `updated_rows` → `UR`, `task_assignments` → `TA`
- If the alias would conflict with another alias in the same query, adjust by adding a numeric suffix (e.g., `PM2`).
- Always use the alias to qualify column references in joins and where clauses.

### Indentation
- Use **2 spaces** per indentation level.
- Do not use tabs.

### Line Breaks
- Each major clause starts on a new line:
  ```sql
  SELECT ...
  FROM ...
  WHERE ...
  ORDER BY ...
  ```
- Subqueries are indented one level more.
- When a clause has multiple items (e.g., column list, JOIN conditions), each item may be placed on a separate line if it improves readability.

### Common Templates

#### CTE (WITH)
```sql
WITH cte_name AS (
    SELECT ...
        FROM ...
        WHERE ...
)
SELECT ...
FROM cte_name
WHERE ...
```

#### INSERT with multiple rows
```sql
INSERT INTO table_name (col1, col2, col3)
VALUES
    (val1, val2, val3),
    (val4, val5, val6)
ON CONFLICT (col1) DO UPDATE
    SET col2 = excluded.col2,
        col3 = excluded.col3;
```

#### UPDATE with multiple SET columns
```sql
UPDATE table_name
SET col1 = value1,
    col2 = value2,
    col3 = value3
WHERE condition;
```

#### SELECT with JOIN
```sql
SELECT T.*,
       P.column
FROM tasks T
INNER JOIN projects P ON T.project_id = P.project_id
WHERE T.status = 'ACTIVE'
ORDER BY T.created DESC;
```

## 3. Parameter Usage

### Named Parameters
- Always use **named parameters** (`@param_name`). Do not use positional parameters (`$1`, `$2`).
- Every parameter **must** be explicitly cast with `::type`.

### Common Casts
- UUID: `@task_id::uuid`
- Timestamp: `@time_now::timestamp`
- Array of UUIDs: `@ids::uuid[]`
- Boolean: `@enabled_is::boolean`
- Integer: `@count::integer`
- Bigint: `@overlap::bigint`
- Text: `@name::text`
- JSONB: `@data::jsonb`
- Numeric: `@price::numeric`

### Using Arrays
- For `IN`‑style conditions: `WHERE column = ANY(@ids::uuid[])`
- For expanding arrays in `VALUES`: `VALUES (UNNEST(@ids::uuid[]))`
- For multiple parallel arrays (e.g., in a CTE) use `UNNEST` with the same ordering:
  ```sql
  WITH UPD AS (
      SELECT
          UNNEST(@ids::uuid[]) AS id,
          UNNEST(@names::text[]) AS name
  )
  ```

## 4. SQL Constructs

### SELECT
- Prefer `SELECT *` unless specific columns are required for performance or clarity.
- When joining several tables, use `sqlc.embed(table_alias)` to embed all columns of that table:
  ```sql
  SELECT sqlc.embed(T), sqlc.embed(P)
  FROM tasks T
  JOIN projects P ON T.project_id = P.project_id
  ```

### Locking
- Use `FOR UPDATE` when you need to lock selected rows for update.
- Use `FOR UPDATE SKIP LOCKED` for queue‑like patterns to avoid blocking.

### Upserts
- Always specify the conflict target and the columns to update:
  ```sql
  ON CONFLICT (id) DO UPDATE
      SET column1 = excluded.column1,
          column2 = excluded.column2
  ```

### Returning Data
- Use `RETURNING *` (or specific columns) for INSERT/UPDATE/DELETE that need to return the affected rows.

### CTEs
- Use CTEs to break down complex logic, especially when a subquery is used more than once.
- Name CTEs descriptively (e.g., `task_assignments`, `updated_rows`).

### Distinct
- Use `DISTINCT ON (columns)` when you need a single row per group, together with an `ORDER BY` that defines which row to pick.

### Ordering
- Specify nulls order explicitly: `ORDER BY column NULLS FIRST` (or `NULLS LAST`).

### Conditional Logic
- Use `CASE` for inline conditional expressions.
- Use `COALESCE` to provide default values for nullable columns.

### Existence Checks
- Use `EXISTS (SELECT 1 FROM ... WHERE ...)` rather than `COUNT(*) > 0`.

### Joins
- Use explicit `JOIN` syntax (never comma‑separated tables).
- Use `LEFT JOIN` when the relationship is optional.
- Use `INNER JOIN` when the relationship is mandatory.
- Always qualify column names with table aliases in joins.

## 5. Comments

### Query Header
- Each query must be preceded by a `-- name: QueryName :type` line.
- Optionally add a description (in Russian or English) above the name line, starting with `--`.
- Example:
  ```sql
  -- Returns all tasks that are currently running and accessible to the given marker.
  -- name: GetRunningProjectsStatsByIDs :many
  WITH task_assignments AS (...)
  ```

### Inline Comments
- Add brief comments for non‑obvious business logic or complex conditions.
- Use `--` for single‑line comments inside the SQL.

## 6. File Organization

- Group queries by the main entity they operate on (items, skills, tasks, assignments, etc.).
- Separate groups with a blank line.
- Within a group, order queries logically (e.g., CRUD order: Create, Read, Update, Delete).

## 7. Additional Conventions

### UPDATE SET
- List each `column = value` on a separate line, aligned under `SET`.
- Example:
  ```sql
  UPDATE tasks
  SET status = 'STOP',
      stopped = @stopped_at::timestamp,
      updated_at = @updated_at::timestamp
  WHERE id = @id;
  ```

### INSERT Column List
- If the column list is long (more than ~4 columns), split it across multiple lines:
  ```sql
  INSERT INTO tasks (
      id,
      item_timeout_seconds,
      name,
      description,
      ...
  ) VALUES (...);
  ```

### WHERE Conditions
- Place each condition on a new line, indented, with the logical operator (`AND`, `OR`) at the beginning of the line.
- Example:
  ```sql
  WHERE T.status = 'RUN'
    AND T.project_id = ANY(@ids::uuid[])
    AND (T.max_items_per_day IS NULL OR MTS.marked_today < T.max_items_per_day)
  ```

### Order of Clauses
- Follow the standard SQL order:
  1. `WITH`
  2. `SELECT`
  3. `FROM`
  4. `JOIN`
  5. `WHERE`
  6. `GROUP BY`
  7. `HAVING`
  8. `ORDER BY`
  9. `LIMIT`
  10. `OFFSET`
  11. `FOR UPDATE`

## 8. Examples

### Simple Get by ID
```sql
-- name: GetTaskByID :one
SELECT *
FROM tasks T
WHERE T.id = @id::uuid;
```

### Insert with Returning
```sql
-- name: InsertProject :exec
INSERT INTO projects (project_id, project_name, description, method_id)
VALUES (@project_id::uuid, @project_name::text, @description::text, @method_id::uuid)
ON CONFLICT (project_id) DO UPDATE
    SET project_name = excluded.project_name,
        description = excluded.description,
        method_id = excluded.method_id;
```

### Complex Join with Locking
```sql
-- name: LockAssignedAssignment :one
SELECT *
FROM assignments AS A
WHERE A.task_id = @task_id::uuid
  AND A.status = 'ASSIGNED'
  AND A.marker_id = @marker_id::uuid
ORDER BY A.expired_after ASC,
         CASE WHEN (@is_straight_order::boolean) THEN A.index ELSE RANDOM() END
LIMIT 1
    FOR UPDATE SKIP LOCKED;
```

### Batch Insert (copyfrom)
```sql
-- name: InsertAssignments :copyfrom
INSERT INTO assignments (id, task_id, suite_id, started, status, marker_id, item_ids, price, index, updated_at, expired_after, original_assignment_id, item_meta_version_ids, assigned_at)
VALUES (@id, @task_id, @suite_id, @started, @status, @marker_id, @item_ids, @price, @index, @updated_at, @expired_after, @original_assignment_id, @item_meta_version_ids, @assigned_at);
```

---

*This guide is based on the existing `src/pkg/repository/query.sql` file and the associated sqlc configuration.*
