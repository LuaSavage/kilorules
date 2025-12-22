#!/usr/bin/env python3
"""
API cache generator for taskflow OpenAPI schema and boilerplate.gen.go

Python version: 3.9.6+

The generator builds:
- path index for each operation (paths in taskflow.yaml)
- schema index for components/schemas in taskflow.yaml
- boilerplate index for entities in boilerplate.gen.go
- per-operation cache files with:
  * path fragment of YAML
  * all directly referenced schemas
  * snippets of generated Go code related to the operation
"""

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class FileRange:
    start_line: int
    end_line: int

    def to_dict(self) -> dict:
        return {"start_line": self.start_line, "end_line": self.end_line}


@dataclass
class PathEntry:
    operation_id: str
    method: str
    path: str
    range: FileRange

    def to_dict(self) -> dict:
        return {
            "operation_id": self.operation_id,
            "method": self.method,
            "path": self.path,
            "range": self.range.to_dict(),
        }


@dataclass
class SchemaEntry:
    name: str
    range: FileRange

    def to_dict(self) -> dict:
        return {"name": self.name, "range": self.range.to_dict()}


@dataclass
class BoilerplateEntity:
    type: str  # struct, func, const, var, type
    name: str
    file: str
    range: FileRange
    code: str

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "name": self.name,
            "file": self.file,
            "range": self.range.to_dict(),
            "code": self.code,
        }


class ApiCacheGenerator:
    """
    Generator for API cache (taskflow.yaml + boilerplate.gen.go).
    Configuration is read from api_cache_config.json in this directory.
    """

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.config = self._load_config(config_path)

        config_dir = config_path.parent.resolve()
        base_path_cfg = self.config["base_path"]
        if Path(base_path_cfg).is_absolute():
            self.base_path = Path(base_path_cfg).resolve()
        else:
            self.base_path = (config_dir / base_path_cfg).resolve()

        self.cache_dir = self.base_path / self.config.get("cache_dir", "cache_data")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.spec_file = self.base_path / self.config["spec_file"]
        self.boilerplate_file = self.base_path / self.config["boilerplate_file"]

        self.hashes_file = self.cache_dir / "hashes_api.json"
        self.hashes = self._load_hashes()

    # ------------------------------------------------------------------ #
    # Hashing helpers
    # ------------------------------------------------------------------ #
    def _load_config(self, path: Path) -> dict:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _load_hashes(self) -> dict:
        if self.hashes_file.exists():
            with self.hashes_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_hashes(self) -> None:
        with self.hashes_file.open("w", encoding="utf-8") as f:
            json.dump(self.hashes, f, indent=2, ensure_ascii=False)

    def _file_hash(self, path: Path) -> str:
        try:
            with path.open("rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as exc:  # pragma: no cover - defensive
            print(f"[api-cache] Error hashing {path}: {exc}")
            return ""

    def _should_reindex(self, rel_key: str, path: Path) -> bool:
        if not path.exists():
            print(f"[api-cache] Warning: file not found: {path}")
            return False
        current = self._file_hash(path)
        stored = self.hashes.get(rel_key)
        if stored != current:
            self.hashes[rel_key] = current
            return True
        return False

    # ------------------------------------------------------------------ #
    # Low-level file helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _read_all_lines(path: Path) -> List[str]:
        with path.open("r", encoding="utf-8") as f:
            return f.readlines()

    @staticmethod
    def _read_range(path: Path, fr: FileRange) -> str:
        lines = ApiCacheGenerator._read_all_lines(path)
        start = max(fr.start_line, 1) - 1
        end = min(fr.end_line, len(lines))
        return "".join(lines[start:end])

    # ------------------------------------------------------------------ #
    # Indexing taskflow.yaml
    # ------------------------------------------------------------------ #
    def index_paths(self) -> Dict[str, PathEntry]:
        """
        Build index for each operationId in taskflow.yaml under `paths:`.
        Key: operationId.
        """
        rel_key = "taskflow.yaml"
        if not self._should_reindex(rel_key, self.spec_file):
            print("[api-cache] taskflow.yaml not changed, loading existing path index if any")
            index_file = self.cache_dir / "taskflow.paths.index.json"
            if index_file.exists():
                with index_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                paths: Dict[str, PathEntry] = {}
                for op_id, info in data.get("paths", {}).items():
                    r = info["range"]
                    paths[op_id] = PathEntry(
                        operation_id=op_id,
                        method=info["method"],
                        path=info["path"],
                        range=FileRange(r["start_line"], r["end_line"]),
                    )
                return paths

        print("[api-cache] Indexing paths in taskflow.yaml ...")
        lines = self._read_all_lines(self.spec_file)
        total_lines = len(lines)

        paths_section_started = False
        paths: Dict[str, PathEntry] = {}

        i = 0
        current_path_line = None
        current_path = None
        current_method = None

        method_re = re.compile(r"^\s{4}(get|post|put|delete|patch|options|head):\s*$", re.IGNORECASE)
        path_re = re.compile(r"^\s{2}(/.+):\s*$")

        while i < total_lines:
            line = lines[i]
            stripped = line.strip()
            lineno = i + 1

            if not paths_section_started and stripped == "paths:":
                paths_section_started = True
                i += 1
                continue

            if not paths_section_started:
                i += 1
                continue

            # End of paths section: components:
            if stripped.startswith("components:"):
                break

            # New path
            m_path = path_re.match(line)
            if m_path:
                current_path = m_path.group(1)
                current_path_line = lineno
                current_method = None
                i += 1
                continue

            # HTTP method under current path
            m_method = method_re.match(line)
            if m_method and current_path:
                current_method = m_method.group(1).upper()
                i += 1

                # scan forward for operationId within this method block
                j = i
                op_id = None
                op_start = lineno  # default start at method line
                while j < total_lines:
                    l2 = lines[j]
                    s2 = l2.strip()
                    lineno2 = j + 1

                    # new path or components: means current operation ended
                    if path_re.match(l2) or s2.startswith("components:"):
                        break

                    if s2.startswith("operationId:"):
                        # operationId: GetFoo
                        parts = s2.split("operationId:", 1)[1].strip()
                        op_id = parts
                        op_start = current_path_line

                        # now extend until before next path/next at same level
                        k = j + 1
                        end_line = lineno2
                        while k < total_lines:
                            s3 = lines[k].strip()
                            if path_re.match(lines[k]) or s3.startswith("components:"):
                                break
                            end_line = k + 1
                            k += 1

                        if op_id:
                            paths[op_id] = PathEntry(
                                operation_id=op_id,
                                method=current_method,
                                path=current_path,
                                range=FileRange(op_start, end_line),
                            )
                        break

                    j += 1

                continue

            i += 1

        index_data = {
            "file_path": str(self.spec_file.relative_to(self.base_path)),
            "total_lines": total_lines,
            "paths": {op: entry.to_dict() for op, entry in paths.items()},
        }
        index_path = self.cache_dir / "taskflow.paths.index.json"
        with index_path.open("w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)
        print(f"[api-cache] Saved path index -> {index_path}")
        return paths

    def index_schemas(self) -> Dict[str, SchemaEntry]:
        """
        Build index for components/schemas in taskflow.yaml.
        Key: schema name.
        """
        rel_key = "taskflow.yaml.schemas"
        if not self._should_reindex(rel_key, self.spec_file):
            print("[api-cache] taskflow.yaml (schemas) not changed, loading schema index if any")
            index_file = self.cache_dir / "taskflow.schemas.index.json"
            if index_file.exists():
                with index_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                schemas: Dict[str, SchemaEntry] = {}
                for name, info in data.get("schemas", {}).items():
                    r = info["range"]
                    schemas[name] = SchemaEntry(name=name, range=FileRange(r["start_line"], r["end_line"]))
                return schemas

        print("[api-cache] Indexing schemas in taskflow.yaml ...")
        lines = self._read_all_lines(self.spec_file)
        total_lines = len(lines)

        schemas_started = False
        schemas: Dict[str, SchemaEntry] = {}

        schema_header_re = re.compile(r"^\s{4}(\w+):\s*$")

        i = 0
        while i < total_lines:
            line = lines[i]
            stripped = line.strip()
            lineno = i + 1

            if not schemas_started and stripped == "schemas:":
                schemas_started = True
                i += 1
                continue

            if not schemas_started:
                i += 1
                continue

            # End of schemas block when indentation goes back or file ends.
            # In practice, schemas go until the end, so we don't need extra checks.

            m_schema = schema_header_re.match(line)
            if m_schema:
                name = m_schema.group(1)
                start = lineno
                j = i + 1
                end = start
                while j < total_lines:
                    l2 = lines[j]
                    s2 = l2.rstrip("\n")
                    if schema_header_re.match(l2):
                        break
                    # end of schemas: probably outdented more than 4 spaces and new root key
                    if s2.strip() and not s2.startswith(" " * 6) and not s2.startswith(" " * 4):
                        # very conservative break
                        break
                    end = j + 1
                    j += 1

                schemas[name] = SchemaEntry(name=name, range=FileRange(start, end))
                i = j
                continue

            i += 1

        index_data = {
            "file_path": str(self.spec_file.relative_to(self.base_path)),
            "total_lines": total_lines,
            "schemas": {name: entry.to_dict() for name, entry in schemas.items()},
        }
        index_path = self.cache_dir / "taskflow.schemas.index.json"
        with index_path.open("w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)
        print(f"[api-cache] Saved schema index -> {index_path}")
        return schemas

    # ------------------------------------------------------------------ #
    # Indexing boilerplate.gen.go
    # ------------------------------------------------------------------ #
    def index_boilerplate(self) -> Dict[str, BoilerplateEntity]:
        """
        Very lightweight index of entities in boilerplate.gen.go.
        Key: entity name (struct / func / const / var / type).
        """
        rel_key = "boilerplate.gen.go"
        if not self._should_reindex(rel_key, self.boilerplate_file):
            print("[api-cache] boilerplate.gen.go not changed, loading existing index if any")
            index_file = self.cache_dir / "boilerplate.gen.go.index.json"
            if index_file.exists():
                with index_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                entities: Dict[str, BoilerplateEntity] = {}
                for name, info in data.get("entities", {}).items():
                    r = info["range"]
                    entities[name] = BoilerplateEntity(
                        type=info["type"],
                        name=name,
                        file=info["file"],
                        range=FileRange(r["start_line"], r["end_line"]),
                        code=info.get("code", ""),
                    )
                return entities

        print("[api-cache] Indexing boilerplate.gen.go ...")
        lines = self._read_all_lines(self.boilerplate_file)
        total_lines = len(lines)

        struct_re = re.compile(r"^type\s+(\w+)\s+struct\b")
        func_re = re.compile(r"^func\s+\(siw \*ServerInterfaceWrapper\)\s+(\w+)\s*\(")
        const_var_re = re.compile(r"^(const|var)\s+(\w+)\b")
        type_re = re.compile(r"^type\s+(\w+)\s+[^\s]+")

        entities: Dict[str, BoilerplateEntity] = {}

        i = 0
        current_name: Optional[str] = None
        current_type: Optional[str] = None
        current_start = 0
        brace_count = 0

        while i < total_lines:
            line = lines[i]
            stripped = line.strip()
            lineno = i + 1

            # Track braces to approximate end of blocks
            brace_count += line.count("{") - line.count("}")

            m_struct = struct_re.match(line)
            m_func = func_re.match(line)
            m_const = const_var_re.match(line)
            m_type = type_re.match(line)

            if m_func:
                # close previous entity
                if current_name and current_type:
                    end_line = lineno - 1 if lineno > current_start else current_start
                    fr = FileRange(current_start, end_line)
                    code = self._read_range(self.boilerplate_file, fr)
                    entities[current_name] = BoilerplateEntity(
                        type=current_type,
                        name=current_name,
                        file=str(self.boilerplate_file.relative_to(self.base_path)),
                        range=fr,
                        code=code,
                    )
                current_name = m_func.group(1)
                current_type = "func"
                current_start = lineno
                brace_count = line.count("{") - line.count("}")
                i += 1
                continue

            if m_struct:
                if current_name and current_type and brace_count == 0:
                    end_line = lineno - 1 if lineno > current_start else current_start
                    fr = FileRange(current_start, end_line)
                    code = self._read_range(self.boilerplate_file, fr)
                    entities[current_name] = BoilerplateEntity(
                        type=current_type,
                        name=current_name,
                        file=str(self.boilerplate_file.relative_to(self.base_path)),
                        range=fr,
                        code=code,
                    )
                current_name = m_struct.group(1)
                current_type = "struct"
                current_start = lineno
                brace_count = line.count("{") - line.count("}")
                i += 1
                continue

            if m_const:
                if current_name and current_type and brace_count == 0:
                    end_line = lineno - 1 if lineno > current_start else current_start
                    fr = FileRange(current_start, end_line)
                    code = self._read_range(self.boilerplate_file, fr)
                    entities[current_name] = BoilerplateEntity(
                        type=current_type,
                        name=current_name,
                        file=str(self.boilerplate_file.relative_to(self.base_path)),
                        range=fr,
                        code=code,
                    )
                current_name = m_const.group(2)
                current_type = m_const.group(1)  # const or var
                current_start = lineno
                i += 1
                continue

            if m_type and not struct_re.match(line):
                if current_name and current_type and brace_count == 0:
                    end_line = lineno - 1 if lineno > current_start else current_start
                    fr = FileRange(current_start, end_line)
                    code = self._read_range(self.boilerplate_file, fr)
                    entities[current_name] = BoilerplateEntity(
                        type=current_type,
                        name=current_name,
                        file=str(self.boilerplate_file.relative_to(self.base_path)),
                        range=fr,
                        code=code,
                    )
                current_name = m_type.group(1)
                current_type = "type"
                current_start = lineno
                i += 1
                continue

            # entity ends when braces closed and next non-empty, non-comment line appears
            if current_name and current_type and brace_count == 0 and stripped and not stripped.startswith("//"):
                end_line = lineno - 1 if lineno > current_start else current_start
                fr = FileRange(current_start, end_line)
                code = self._read_range(self.boilerplate_file, fr)
                entities[current_name] = BoilerplateEntity(
                    type=current_type,
                    name=current_name,
                    file=str(self.boilerplate_file.relative_to(self.base_path)),
                    range=fr,
                    code=code,
                )
                current_name = None
                current_type = None

            i += 1

        # flush last
        if current_name and current_type:
            fr = FileRange(current_start, total_lines)
            code = self._read_range(self.boilerplate_file, fr)
            entities[current_name] = BoilerplateEntity(
                type=current_type,
                name=current_name,
                file=str(self.boilerplate_file.relative_to(self.base_path)),
                range=fr,
                code=code,
            )

        index_data = {
            "file_path": str(self.boilerplate_file.relative_to(self.base_path)),
            "total_lines": total_lines,
            "entities": {name: ent.to_dict() for name, ent in entities.items()},
        }
        index_path = self.cache_dir / "boilerplate.gen.go.index.json"
        with index_path.open("w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)
        print(f"[api-cache] Saved boilerplate index -> {index_path}")
        return entities

    # ------------------------------------------------------------------ #
    # Operation-level cache generation
    # ------------------------------------------------------------------ #
    def _extract_schema_dependencies(
        self,
        op_block: str,
        schema_index: Dict[str, SchemaEntry],
    ) -> List[dict]:
        """
        Find all directly referenced components/schemas in operation YAML block.
        """
        deps: List[dict] = []
        seen = set()
        for match in re.findall(r"#/components/schemas/([A-Za-z0-9_]+)", op_block):
            if match in seen:
                continue
            seen.add(match)
            entry = schema_index.get(match)
            if not entry:
                continue
            schema_yaml = self._read_range(self.spec_file, entry.range)
            deps.append(
                {
                    "name": match,
                    "range": entry.range.to_dict(),
                    "file": str(self.spec_file.relative_to(self.base_path)),
                    "schema_yaml": schema_yaml,
                }
            )
        return deps

    def _extract_boilerplate_entities_for_op(
        self,
        op_id: str,
        boilerplate_index: Dict[str, BoilerplateEntity],
    ) -> List[dict]:
        """
        Collect boilerplate entities related to an operation:
        - structs and other entities whose name contains operationId
        - operation middleware func with exact name == operationId
        - Params struct: <OpId>Params
        - response item structs: <OpId>Response, <OpId>ResponseItem, etc.
        """
        related: List[dict] = []
        for name, ent in boilerplate_index.items():
            if name == op_id or name.startswith(op_id) or op_id in name:
                related.append(ent.to_dict())
        return related

    def generate_operation_cache(
        self,
        op: PathEntry,
        schema_index: Dict[str, SchemaEntry],
        boilerplate_index: Dict[str, BoilerplateEntity],
    ) -> None:
        """
        Generate cache JSON for single operationId.
        """
        op_block = self._read_range(self.spec_file, op.range)
        schemas = self._extract_schema_dependencies(op_block, schema_index)
        boilerplate_entities = self._extract_boilerplate_entities_for_op(op.operation_id, boilerplate_index)

        cache_obj = {
            "operation_id": op.operation_id,
            "path": op.path,
            "method": op.method,
            "spec_file": str(self.spec_file.relative_to(self.base_path)),
            "path_range": op.range.to_dict(),
            "path_yaml": op_block,
            "schemas": schemas,
            "boilerplate": {
                "file": str(self.boilerplate_file.relative_to(self.base_path)),
                "entities": boilerplate_entities,
            },
        }

        cache_file = self.cache_dir / f"{op.operation_id}.api.cache.json"
        with cache_file.open("w", encoding="utf-8") as f:
            json.dump(cache_obj, f, indent=2, ensure_ascii=False)
        print(f"[api-cache] Saved op cache -> {cache_file.name}")

    # ------------------------------------------------------------------ #
    # Public entrypoint
    # ------------------------------------------------------------------ #
    def generate(self) -> None:
        print("=" * 60)
        print("[api-cache] Starting API cache generation")
        print(f"[api-cache] Base path: {self.base_path}")
        print(f"[api-cache] Cache dir: {self.cache_dir}")
        print("=" * 60)

        paths_index = self.index_paths()
        schemas_index = self.index_schemas()
        boilerplate_index = self.index_boilerplate()

        # generate per-operation cache
        print(f"[api-cache] Generating cache for {len(paths_index)} operations ...")
        for op_id, entry in paths_index.items():
            try:
                self.generate_operation_cache(entry, schemas_index, boilerplate_index)
            except Exception as exc:  # pragma: no cover - defensive
                print(f"[api-cache] Error generating cache for {op_id}: {exc}")

        self._save_hashes()
        print("=" * 60)
        print("[api-cache] Done")
        print("=" * 60)


def main() -> None:
    import sys

    script_dir = Path(__file__).parent
    if len(sys.argv) > 1:
        config_path = Path(sys.argv[1])
    else:
        config_path = script_dir / "api_cache_config.json"

    if not config_path.exists():
        print(f"[api-cache] Config not found: {config_path}")
        sys.exit(1)

    generator = ApiCacheGenerator(config_path)
    generator.generate()


if __name__ == "__main__":
    main()


