#!/usr/bin/env python3
"""
Генератор кеша для репозитория
Генерирует индексные файлы и файлы кеша для запросов на основе schema.sql, query.sql и сгенерированных Go файлов
"""

import json
import hashlib
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class EntityType(Enum):
    """Типы сущностей в Go коде"""
    FUNCTION = "function"
    STRUCT = "struct"
    INTERFACE = "interface"
    CONST = "const"
    VAR = "var"
    TYPE = "type"


@dataclass
class FileRange:
    """Диапазон строк в файле"""
    start_line: int
    end_line: int


@dataclass
class FileIndex:
    """Индекс файла с информацией о диапазонах строк"""
    file_path: str
    total_lines: int
    ranges: Dict[str, FileRange]

    def to_dict(self):
        return {
            "file_path": self.file_path,
            "total_lines": self.total_lines,
            "ranges": {
                name: {"start_line": r.start_line, "end_line": r.end_line}
                for name, r in self.ranges.items()
            }
        }


@dataclass
class TableDependency:
    """Зависимость от таблицы"""
    table_name: str
    range: FileRange
    file: str
    table_sql: str = ""

    def to_dict(self):
        return {
            "table_name": self.table_name,
            "range": {"start_line": self.range.start_line, "end_line": self.range.end_line},
            "file": self.file,
            "table_sql": self.table_sql
        }


@dataclass
class GeneratedCode:
    """Сгенерированный код"""
    type: str
    name: str
    code: str
    range: FileRange
    file: str

    def to_dict(self):
        return {
            "type": self.type,
            "name": self.name,
            "code": self.code,
            "range": {"start_line": self.range.start_line, "end_line": self.range.end_line},
            "file": self.file
        }


@dataclass
class QueryCache:
    """Кеш для одного запроса"""
    query_name: str
    query_sql: str
    query_range: FileRange
    query_file: str
    tables: List[TableDependency]
    generated_code: List[GeneratedCode]

    def to_dict(self):
        return {
            "query_name": self.query_name,
            "query_sql": self.query_sql,
            "query_range": {"start_line": self.query_range.start_line, "end_line": self.query_range.end_line},
            "query_file": self.query_file,
            "tables": [t.to_dict() for t in self.tables],
            "generated_code": [gc.to_dict() for gc in self.generated_code]
        }


class CacheGenerator:
    """Генератор кеша для репозитория"""

    def __init__(self, config_path: str):
        """Инициализация генератора с конфигурацией"""
        self.config = self._load_config(config_path)
        # base_path может быть абсолютным или относительным к директории config.json
        config_dir = Path(config_path).parent.resolve()
        base_path_config = self.config["base_path"]
        if Path(base_path_config).is_absolute():
            self.base_path = Path(base_path_config).resolve()
        else:
            self.base_path = (config_dir / base_path_config).resolve()
        self.cache_dir = self.base_path / self.config["cache_dir"]
        self.hashes_file = self.cache_dir / "hashes.json"
        self.hashes = self._load_hashes()

    def _load_config(self, config_path: str) -> dict:
        """Загрузка конфигурации"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _load_hashes(self) -> dict:
        """Загрузка хешей файлов"""
        if self.hashes_file.exists():
            with open(self.hashes_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_hashes(self):
        """Сохранение хешей файлов"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        with open(self.hashes_file, 'w', encoding='utf-8') as f:
            json.dump(self.hashes, f, indent=2, ensure_ascii=False)

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Вычисление SHA256 хеша файла"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            print(f"Ошибка при вычислении хеша файла {file_path}: {e}")
            return ""

    def _should_update_file(self, file_path: Path, relative_path: str) -> bool:
        """Проверка необходимости обновления файла"""
        if not file_path.exists():
            print(f"Предупреждение: файл {file_path} не существует")
            return False

        current_hash = self._calculate_file_hash(file_path)
        stored_hash = self.hashes.get(relative_path)

        if stored_hash != current_hash:
            self.hashes[relative_path] = current_hash
            return True
        return False

    def _read_file_lines(self, file_path: Path, start_line: int, end_line: int) -> List[str]:
        """Чтение диапазона строк из файла"""
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            return [lines[i].rstrip('\n') for i in range(start_line - 1, min(end_line, len(lines)))]

    def _read_file_range_content(self, file_path: Path, file_range: FileRange) -> str:
        """Чтение содержимого диапазона строк"""
        lines = self._read_file_lines(file_path, file_range.start_line, file_range.end_line)
        return '\n'.join(lines)

    def index_schema_file(self) -> Optional[FileIndex]:
        """Индексация schema.sql файла"""
        schema_path = self.base_path / self.config["schema_file"]
        relative_path = str(schema_path.relative_to(self.base_path))

        if not self._should_update_file(schema_path, relative_path):
            print(f"Schema file {relative_path} не изменился, пропускаем индексацию")
            return None

        print(f"Индексируем {relative_path}...")
        index = FileIndex(
            file_path=str(schema_path.relative_to(self.base_path)),
            total_lines=0,
            ranges={}
        )

        with open(schema_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            index.total_lines = len(lines)

        line_num = 0
        current_entity_name = None
        current_entity_start = 0
        in_definition = False

        # Паттерны для поиска сущностей
        create_table_pattern = re.compile(r'(?i)^\s*create\s+table\s+(?:if\s+not\s+exists\s+)?(\w+)')
        create_type_pattern = re.compile(r'(?i)^\s*create\s+type\s+(\w+)')
        create_function_pattern = re.compile(r'(?i)^\s*create\s+function\s+(\w+)')

        with open(schema_path, 'r', encoding='utf-8') as f:
            for line in f:
                line_num += 1
                stripped = line.strip()

                # Проверяем создание таблицы
                match = create_table_pattern.match(line)
                if match:
                    if current_entity_name and in_definition:
                        index.ranges[current_entity_name] = FileRange(
                            start_line=current_entity_start,
                            end_line=line_num - 1
                        )
                    current_entity_name = match.group(1)
                    current_entity_start = line_num
                    in_definition = True
                    continue

                # Проверяем создание типа
                match = create_type_pattern.match(line)
                if match:
                    if current_entity_name and in_definition:
                        index.ranges[current_entity_name] = FileRange(
                            start_line=current_entity_start,
                            end_line=line_num - 1
                        )
                    current_entity_name = match.group(1)
                    current_entity_start = line_num
                    in_definition = True
                    continue

                # Проверяем создание функции
                match = create_function_pattern.match(line)
                if match:
                    if current_entity_name and in_definition:
                        index.ranges[current_entity_name] = FileRange(
                            start_line=current_entity_start,
                            end_line=line_num - 1
                        )
                    current_entity_name = match.group(1)
                    current_entity_start = line_num
                    in_definition = True
                    continue

                # Проверяем окончание определения (точка с запятой в начале строки)
                if in_definition and stripped.startswith(';'):
                    if current_entity_name:
                        index.ranges[current_entity_name] = FileRange(
                            start_line=current_entity_start,
                            end_line=line_num
                        )
                    current_entity_name = None
                    in_definition = False

        # Сохраняем последнюю сущность
        if current_entity_name and in_definition:
            index.ranges[current_entity_name] = FileRange(
                start_line=current_entity_start,
                end_line=line_num
            )

        return index

    def index_query_file(self) -> Optional[FileIndex]:
        """Индексация query.sql файла"""
        query_path = self.base_path / self.config["query_file"]
        relative_path = str(query_path.relative_to(self.base_path))

        if not self._should_update_file(query_path, relative_path):
            print(f"Query file {relative_path} не изменился, пропускаем индексацию")
            return None

        print(f"Индексируем {relative_path}...")
        index = FileIndex(
            file_path=str(query_path.relative_to(self.base_path)),
            total_lines=0,
            ranges={}
        )

        query_pattern = re.compile(r'^--\s*name:\s*(\w+)\s*:(\w+)')

        with open(query_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            index.total_lines = len(lines)

        line_num = 0
        current_query_name = None
        current_query_start = 0

        with open(query_path, 'r', encoding='utf-8') as f:
            for line in f:
                line_num += 1
                match = query_pattern.match(line)
                if match:
                    if current_query_name:
                        index.ranges[current_query_name] = FileRange(
                            start_line=current_query_start,
                            end_line=line_num - 1
                        )
                    current_query_name = match.group(1)
                    current_query_start = line_num

        # Сохраняем последний запрос
        if current_query_name:
            index.ranges[current_query_name] = FileRange(
                start_line=current_query_start,
                end_line=line_num
            )

        return index

    def index_generated_file(self, file_path: Path) -> Optional[FileIndex]:
        """Индексация сгенерированного Go файла"""
        relative_path = str(file_path.relative_to(self.base_path))

        if not self._should_update_file(file_path, relative_path):
            print(f"Generated file {relative_path} не изменился, пропускаем индексацию")
            return None

        print(f"Индексируем {relative_path}...")
        index = FileIndex(
            file_path=relative_path,
            total_lines=0,
            ranges={}
        )

        # Паттерны для поиска сущностей в Go
        func_pattern = re.compile(r'^func\s+(?:\([^)]+\)\s+)?(\w+)')
        struct_pattern = re.compile(r'^type\s+(\w+)\s+struct')
        interface_pattern = re.compile(r'^type\s+(\w+)\s+interface')
        const_pattern = re.compile(r'^(?:const|var)\s+(\w+)')
        type_pattern = re.compile(r'^type\s+(\w+)\s+')

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            index.total_lines = len(lines)

        line_num = 0
        current_entity_name = None
        current_entity_start = 0
        brace_count = 0
        in_entity = False

        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line_num += 1
                trimmed = line.strip()

                # Подсчитываем фигурные скобки
                brace_count += line.count('{') - line.count('}')

                # Проверяем начало функции
                match = func_pattern.match(trimmed)
                if match:
                    if current_entity_name and in_entity:
                        index.ranges[current_entity_name] = FileRange(
                            start_line=current_entity_start,
                            end_line=line_num - 1
                        )
                    current_entity_name = match.group(1)
                    current_entity_start = line_num
                    in_entity = True
                    brace_count = line.count('{') - line.count('}')
                    continue

                # Проверяем начало структуры
                match = struct_pattern.match(trimmed)
                if match:
                    if current_entity_name and in_entity and brace_count == 0:
                        index.ranges[current_entity_name] = FileRange(
                            start_line=current_entity_start,
                            end_line=line_num - 1
                        )
                    current_entity_name = match.group(1)
                    current_entity_start = line_num
                    in_entity = True
                    brace_count = line.count('{') - line.count('}')
                    continue

                # Проверяем начало интерфейса
                match = interface_pattern.match(trimmed)
                if match:
                    if current_entity_name and in_entity and brace_count == 0:
                        index.ranges[current_entity_name] = FileRange(
                            start_line=current_entity_start,
                            end_line=line_num - 1
                        )
                    current_entity_name = match.group(1)
                    current_entity_start = line_num
                    in_entity = True
                    brace_count = line.count('{') - line.count('}')
                    continue

                # Проверяем тип (общий паттерн) - только если это не struct и не interface
                match = type_pattern.match(trimmed)
                if match and 'struct' not in trimmed and 'interface' not in trimmed:
                    if current_entity_name and in_entity and brace_count == 0:
                        index.ranges[current_entity_name] = FileRange(
                            start_line=current_entity_start,
                            end_line=line_num - 1
                        )
                    current_entity_name = match.group(1)
                    current_entity_start = line_num
                    in_entity = True
                    continue

                # Если все скобки закрыты, сущность закончилась
                if in_entity and brace_count == 0 and trimmed and not trimmed.startswith('//'):
                    if current_entity_name:
                        index.ranges[current_entity_name] = FileRange(
                            start_line=current_entity_start,
                            end_line=line_num
                        )
                    current_entity_name = None
                    in_entity = False

        # Сохраняем последнюю сущность
        if current_entity_name and in_entity:
            index.ranges[current_entity_name] = FileRange(
                start_line=current_entity_start,
                end_line=line_num
            )

        return index

    def extract_table_dependencies(self, query_sql: str, schema_index: FileIndex) -> List[TableDependency]:
        """Извлечение зависимостей от таблиц из SQL запроса"""
        tables = set()

        # Паттерны для поиска таблиц
        patterns = [
            re.compile(r'(?i)\bFROM\s+(\w+)'),
            re.compile(r'(?i)\bJOIN\s+(\w+)'),
            re.compile(r'(?i)\bINTO\s+(\w+)'),
            re.compile(r'(?i)\bUPDATE\s+(\w+)'),
            re.compile(r'(?i)\bDELETE\s+FROM\s+(\w+)'),
            re.compile(r'(?i)\bINSERT\s+INTO\s+(\w+)'),
        ]

        sql_keywords = {
            'SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'FULL',
            'OUTER', 'ON', 'AS', 'AND', 'OR', 'NOT', 'IN', 'EXISTS', 'UNION',
            'INSERT', 'UPDATE', 'DELETE', 'INTO', 'SET', 'VALUES', 'WITH',
            'GROUP', 'ORDER', 'BY', 'HAVING', 'LIMIT', 'OFFSET', 'DISTINCT',
            'ALL', 'ANY', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'CAST',
            'COALESCE', 'NULL', 'TRUE', 'FALSE', 'IS', 'LIKE', 'ILIKE',
            'BETWEEN', 'ASC', 'DESC'
        }

        for pattern in patterns:
            matches = pattern.findall(query_sql)
            for match in matches:
                table_name = match.strip()
                if table_name.upper() not in sql_keywords:
                    tables.add(table_name)

        dependencies = []
        schema_path = self.base_path / self.config["schema_file"]

        for table_name in tables:
            if table_name in schema_index.ranges:
                table_range = schema_index.ranges[table_name]
                table_sql = self._read_file_range_content(schema_path, table_range)
                dependencies.append(TableDependency(
                    table_name=table_name,
                    range=table_range,
                    file=str(schema_path.relative_to(self.base_path)),
                    table_sql=table_sql
                ))

        return dependencies

    def extract_generated_code(self, query_name: str, generated_indices: Dict[str, FileIndex]) -> List[GeneratedCode]:
        """Извлечение сгенерированного кода для запроса"""
        generated_code = []

        # Ищем в query.sql.go
        query_go_path = self.base_path / self.config["generated"]["query_sql_go"]
        if query_go_path.exists():
            query_go_index = None
            query_go_relative = str(query_go_path.relative_to(self.base_path))
            for idx in generated_indices.values():
                if idx.file_path == query_go_relative:
                    query_go_index = idx
                    break

            if query_go_index and query_name in query_go_index.ranges:
                code_range = query_go_index.ranges[query_name]
                code_content = self._read_file_range_content(query_go_path, code_range)
                generated_code.append(GeneratedCode(
                    type=EntityType.FUNCTION.value,
                    name=query_name,
                    code=code_content,
                    range=code_range,
                    file=query_go_relative
                ))

        # Ищем структуры в models.sql.go
        models_go_path = self.base_path / self.config["generated"]["models_sql_go"]
        if models_go_path.exists():
            models_go_index = None
            models_go_relative = str(models_go_path.relative_to(self.base_path))
            for idx in generated_indices.values():
                if idx.file_path == models_go_relative:
                    models_go_index = idx
                    break

            if models_go_index:
                # Ищем структуры, которые могут быть связаны с запросом
                # (упрощенная логика - можно улучшить)
                for entity_name, entity_range in models_go_index.ranges.items():
                    if query_name.lower() in entity_name.lower() or entity_name.lower() in query_name.lower():
                        code_content = self._read_file_range_content(models_go_path, entity_range)
                        generated_code.append(GeneratedCode(
                            type=EntityType.STRUCT.value,
                            name=entity_name,
                            code=code_content,
                            range=entity_range,
                            file=models_go_relative
                        ))

        return generated_code

    def generate_query_cache(self, query_name: str, query_range: FileRange,
                            query_index: FileIndex, schema_index: FileIndex,
                            generated_indices: Dict[str, FileIndex]) -> QueryCache:
        """Генерация кеша для одного запроса"""
        query_path = self.base_path / self.config["query_file"]
        query_sql = self._read_file_range_content(query_path, query_range)

        # Извлекаем зависимости от таблиц
        tables = self.extract_table_dependencies(query_sql, schema_index)

        # Извлекаем сгенерированный код
        generated_code = self.extract_generated_code(query_name, generated_indices)

        return QueryCache(
            query_name=query_name,
            query_sql=query_sql,
            query_range=query_range,
            query_file=str(query_path.relative_to(self.base_path)),
            tables=tables,
            generated_code=generated_code
        )

    def save_index(self, index: FileIndex, filename: str):
        """Сохранение индексного файла"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        index_file = self.cache_dir / filename
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"Сохранен индекс: {index_file}")

    def save_query_cache(self, cache: QueryCache):
        """Сохранение кеша запроса"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self.cache_dir / f"{cache.query_name}.cache.json"
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"Сохранен кеш: {cache_file}")

    def generate(self):
        """Основной метод генерации кеша"""
        print("=" * 60)
        print("Начинаем генерацию кеша...")
        print(f"Базовый путь: {self.base_path}")
        print(f"Директория кеша: {self.cache_dir}")
        print("=" * 60)

        # Индексируем schema.sql
        schema_index = self.index_schema_file()
        if schema_index:
            self.save_index(schema_index, "schema.sql.index.json")

        # Индексируем query.sql
        query_index = self.index_query_file()
        if query_index:
            self.save_index(query_index, "query.sql.index.json")

        # Индексируем сгенерированные файлы
        generated_indices = {}
        for gen_file_key, gen_file_path in self.config["generated"].items():
            gen_path = self.base_path / gen_file_path
            if gen_path.exists():
                gen_index = self.index_generated_file(gen_path)
                if gen_index:
                    filename = f"{Path(gen_file_path).stem}.index.json"
                    self.save_index(gen_index, filename)
                    generated_indices[gen_file_key] = gen_index

        # Загружаем индексы если они не были обновлены
        if not schema_index:
            index_file = self.cache_dir / "schema.sql.index.json"
            if index_file.exists():
                with open(index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    schema_index = FileIndex(
                        file_path=data["file_path"],
                        total_lines=data["total_lines"],
                        ranges={
                            name: FileRange(start_line=r["start_line"], end_line=r["end_line"])
                            for name, r in data["ranges"].items()
                        }
                    )

        if not query_index:
            index_file = self.cache_dir / "query.sql.index.json"
            if index_file.exists():
                with open(index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    query_index = FileIndex(
                        file_path=data["file_path"],
                        total_lines=data["total_lines"],
                        ranges={
                            name: FileRange(start_line=r["start_line"], end_line=r["end_line"])
                            for name, r in data["ranges"].items()
                        }
                    )

        # Загружаем индексы сгенерированных файлов если они не были обновлены
        for gen_file_key, gen_file_path in self.config["generated"].items():
            if gen_file_key not in generated_indices:
                gen_path = self.base_path / gen_file_path
                index_file = self.cache_dir / f"{Path(gen_file_path).stem}.index.json"
                if index_file.exists():
                    with open(index_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        gen_index = FileIndex(
                            file_path=data["file_path"],
                            total_lines=data["total_lines"],
                            ranges={
                                name: FileRange(start_line=r["start_line"], end_line=r["end_line"])
                                for name, r in data["ranges"].items()
                            }
                        )
                        generated_indices[gen_file_key] = gen_index

        # Генерируем кеш для каждого запроса
        if query_index and schema_index:
            print(f"\nГенерируем кеш для {len(query_index.ranges)} запросов...")
            for query_name, query_range in query_index.ranges.items():
                try:
                    cache = self.generate_query_cache(
                        query_name, query_range, query_index, schema_index, generated_indices
                    )
                    self.save_query_cache(cache)
                except Exception as e:
                    print(f"Ошибка при генерации кеша для {query_name}: {e}")
                    continue

        # Сохраняем хеши
        self._save_hashes()
        print("\n" + "=" * 60)
        print("Генерация кеша завершена!")
        print("=" * 60)


def main():
    """Точка входа"""
    import sys

    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        # По умолчанию ищем config.json в директории скрипта
        script_dir = Path(__file__).parent
        config_path = script_dir / "config.json"

    if not Path(config_path).exists():
        print(f"Ошибка: файл конфигурации {config_path} не найден")
        sys.exit(1)

    generator = CacheGenerator(config_path)
    generator.generate()


if __name__ == "__main__":
    main()

