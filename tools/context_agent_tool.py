from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


HEADER_LINE_RE = re.compile(r"^(?P<key>[^:]+):\s*(?P<value>.*)$")
TOKEN_RE = re.compile(r"[\w\-]+", re.UNICODE)


@dataclass(frozen=True)
class KnowledgeRecord:
    record_id: str
    record_type: str
    fields: Dict[str, str]
    body: str

    def to_index_text(self) -> str:
        field_text = " ".join(f"{key} {value}" for key, value in self.fields.items())
        return f"{self.record_id} {self.record_type} {field_text} {self.body}".strip()


def _normalize_key(raw_key: str) -> str:
    return raw_key.strip().replace(" ", "_").replace("/", "_").lower()


def _infer_record_type(fields: Dict[str, str]) -> Tuple[str, str]:
    if "problem_id" in fields:
        return fields["problem_id"], "problem"
    if "номер_инцидента" in fields:
        return fields["номер_инцидента"], "incident"
    if "номер_задачи" in fields:
        return fields["номер_задачи"], "task"
    if "номер_изменения" in fields:
        return fields["номер_изменения"], "change"
    return fields.get("id", "unknown"), "unknown"


def parse_markdown_records(text: str) -> List[KnowledgeRecord]:
    blocks = [block.strip() for block in text.split("---") if block.strip()]
    records: List[KnowledgeRecord] = []
    for block in blocks:
        lines = block.splitlines()
        fields: Dict[str, str] = {}
        body_lines: List[str] = []
        in_body = False
        for line in lines:
            if not in_body:
                if not line.strip():
                    in_body = True
                    continue
                match = HEADER_LINE_RE.match(line)
                if match:
                    key = _normalize_key(match.group("key"))
                    fields[key] = match.group("value").strip()
                    continue
                in_body = True
            body_lines.append(line)
        body = "\n".join(body_lines).strip()
        record_id, record_type = _infer_record_type(fields)
        records.append(
            KnowledgeRecord(
                record_id=record_id,
                record_type=record_type,
                fields=fields,
                body=body,
            )
        )
    return records


def _tokenize(text: str) -> List[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def _score_query(query_tokens: List[str], doc_tokens: List[str]) -> float:
    if not query_tokens or not doc_tokens:
        return 0.0
    doc_counts: Dict[str, int] = {}
    for token in doc_tokens:
        doc_counts[token] = doc_counts.get(token, 0) + 1
    score = 0.0
    for token in query_tokens:
        score += doc_counts.get(token, 0)
    return score


def _filter_record(record: KnowledgeRecord, filters: Optional[Dict[str, str]]) -> bool:
    if not filters:
        return True
    for key, expected in filters.items():
        normalized_key = _normalize_key(key)
        value = record.fields.get(normalized_key, "")
        if expected.lower() not in value.lower():
            return False
    return True


def _load_records(path: Path) -> List[KnowledgeRecord]:
    text = path.read_text(encoding="utf-8")
    return parse_markdown_records(text)


def _record_summary(record: KnowledgeRecord) -> Dict[str, Any]:
    return {
        "id": record.record_id,
        "type": record.record_type,
        "fields": record.fields,
        "summary": record.body[:400],
    }


def _apply_allowlist(
    table: str, columns: Iterable[str], filters: Dict[str, Any], allowlist: Dict[str, List[str]]
) -> Tuple[List[str], Dict[str, Any]]:
    allowed_columns = allowlist.get(table, [])
    safe_columns = [col for col in columns if col in allowed_columns]
    safe_filters = {key: value for key, value in filters.items() if key in allowed_columns}
    return safe_columns, safe_filters


def _build_where(filters: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    clauses = []
    params: Dict[str, Any] = {}
    for idx, (key, value) in enumerate(filters.items()):
        param_name = f"p{idx}"
        clauses.append(f"{key} = :{param_name}")
        params[param_name] = value
    if not clauses:
        return "", params
    return " WHERE " + " AND ".join(clauses), params


class Tools:
    """Open WebUI tools for knowledge-base search and SQL generation."""

    def search_kb(
        self,
        query: str,
        path: str = "data/knowledge_base.md",
        top_k: int = 5,
        filters: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Search knowledge base records in a markdown file."""
        records = _load_records(Path(path))
        query_tokens = _tokenize(query)
        scored: List[Tuple[KnowledgeRecord, float]] = []
        for record in records:
            if not _filter_record(record, filters):
                continue
            score = _score_query(query_tokens, _tokenize(record.to_index_text()))
            if score > 0:
                scored.append((record, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        results = [_record_summary(record) for record, _ in scored[:top_k]]
        return {"query": query, "results": results, "total": len(results)}

    def build_sql(
        self,
        table: str,
        columns: List[str],
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        allowlist_json: str = "data/sql_allowlist.json",
    ) -> Dict[str, Any]:
        """Generate a parameterized SQL query with a strict allowlist."""
        allowlist = json.loads(Path(allowlist_json).read_text(encoding="utf-8"))
        if table not in allowlist:
            return {"error": f"Table '{table}' is not in the allowlist."}
        safe_filters = filters or {}
        safe_columns, safe_filters = _apply_allowlist(table, columns, safe_filters, allowlist)
        select_columns = ", ".join(safe_columns) if safe_columns else "*"
        where_clause, params = _build_where(safe_filters)
        sql = f"SELECT {select_columns} FROM {table}{where_clause} LIMIT {limit};"
        return {"sql": sql, "params": params}

    def describe_format(self) -> Dict[str, Any]:
        """Return recommended knowledge base record format."""
        return {
            "format": "markdown-with-front-matter",
            "separator": "---",
            "required_fields": ["Problem ID/Номер инцидента/Номер задачи/Номер изменения", "Сервис"],
            "notes": "Metadata at top as key: value lines, blank line, then body." ,
        }
