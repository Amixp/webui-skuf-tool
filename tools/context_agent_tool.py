from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests


def _normalize_key(raw_key: str) -> str:
    return raw_key.strip().replace(" ", "_").replace("/", "_").lower()


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
        top_k: int = 5,
        filters: Optional[Dict[str, str]] = None,
        base_url: str = "http://localhost:3000",
        api_key: Optional[str] = None,
        endpoint: str = "/api/knowledge/search",
    ) -> Dict[str, Any]:
        """Search Open WebUI knowledge entries via the internal API."""
        normalized_filters = {_normalize_key(key): value for key, value in (filters or {}).items()}
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        payload = {"query": query, "top_k": top_k, "filters": normalized_filters}
        response = requests.post(f"{base_url}{endpoint}", headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", data)
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
        """Return recommended metadata schema for knowledge entries."""
        return {
            "format": "knowledge-entry",
            "required_fields": ["id", "service"],
            "recommended_fields": [
                "priority",
                "status",
                "category",
                "class",
                "created_at",
                "resolved_at",
                "closed_at",
                "coordinator",
                "assignee",
            ],
            "notes": "Store metadata as key/value pairs in the WebUI knowledge entry.",
        }
