"""
author: Khudoley.Artem
title: Context agent
version: 0.1.0
description: Open WebUI tools for knowledge-base search, SQL generation and aggregation.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

# ---------------------------------------------------------------------------
# Допустимые SQL-операторы для фильтров
# ---------------------------------------------------------------------------
_ALLOWED_OPS = frozenset({"=", "!=", ">", "<", ">=", "<=", "LIKE", "ILIKE", "IN"})


def _normalize_key(raw_key: str) -> str:
    return raw_key.strip().replace(" ", "_").replace("/", "_").lower()


def _load_allowlist(path: str = "data/sql_allowlist.json") -> Dict[str, List[str]]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _apply_allowlist(
    table: str, columns: Iterable[str], filters: Dict[str, Any], allowlist: Dict[str, List[str]]
) -> Tuple[List[str], Dict[str, Any]]:
    allowed_columns = allowlist.get(table, [])
    safe_columns = [col for col in columns if col in allowed_columns]
    safe_filters = {key: value for key, value in filters.items() if key in allowed_columns}
    return safe_columns, safe_filters


def _build_where(filters: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """Build a WHERE clause from *filters*.

    Each value can be:
      - a plain scalar  → ``column = :param``
      - a dict ``{"op": "<operator>", "value": <val>}``
        where operator is one of ``=, !=, >, <, >=, <=, LIKE, ILIKE, IN``.
        For ``IN`` the value must be a list.
    """
    clauses: List[str] = []
    params: Dict[str, Any] = {}
    for idx, (key, value) in enumerate(filters.items()):
        p = f"p{idx}"
        if isinstance(value, dict) and "op" in value:
            op = str(value["op"]).upper()
            if op not in _ALLOWED_OPS:
                continue
            val = value["value"]
            if op == "IN" and isinstance(val, list):
                placeholders = ", ".join(f":{p}_{i}" for i in range(len(val)))
                clauses.append(f"{key} IN ({placeholders})")
                for i, v in enumerate(val):
                    params[f"{p}_{i}"] = v
            else:
                clauses.append(f"{key} {op} :{p}")
                params[p] = val
        else:
            clauses.append(f"{key} = :{p}")
            params[p] = value
    if not clauses:
        return "", params
    return " WHERE " + " AND ".join(clauses), params


class Tools:
    """Open WebUI tools for knowledge-base search, SQL generation and aggregation."""

    # ------------------------------------------------------------------
    # search_kb — семантический поиск по базе знаний
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # build_sql — генерация SELECT-запросов
    # ------------------------------------------------------------------
    def build_sql(
        self,
        table: str,
        columns: List[str],
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        allowlist_json: str = "data/sql_allowlist.json",
    ) -> Dict[str, Any]:
        """Generate a parameterized SELECT query with a strict allowlist.

        Filters support comparison operators — see ``_build_where`` docstring.
        """
        allowlist = _load_allowlist(allowlist_json)
        if table not in allowlist:
            return {"error": f"Table '{table}' is not in the allowlist."}
        safe_filters = filters or {}
        safe_columns, safe_filters = _apply_allowlist(table, columns, safe_filters, allowlist)
        select_columns = ", ".join(safe_columns) if safe_columns else "*"
        where_clause, params = _build_where(safe_filters)
        sql = f"SELECT {select_columns} FROM {table}{where_clause} LIMIT {limit};"
        return {"sql": sql, "params": params}

    # ------------------------------------------------------------------
    # count_records — подсчёт записей (COUNT / GROUP BY)
    # ------------------------------------------------------------------
    def count_records(
        self,
        table: str,
        filters: Optional[Dict[str, Any]] = None,
        date_column: str = "created_at",
        year: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        group_by: Optional[List[str]] = None,
        allowlist_json: str = "data/sql_allowlist.json",
    ) -> Dict[str, Any]:
        """Build a COUNT(*) query with equality/operator filters, date range and optional GROUP BY.

        Parameters
        ----------
        table : str
            Target table (must be in allowlist).
        filters : dict, optional
            Equality or operator filters, e.g.
            ``{"status": "Closed"}`` or ``{"priority": {"op": "IN", "value": ["High", "Critical"]}}``.
        date_column : str
            Column used for year / date_from / date_to filtering (default ``created_at``).
        year : int, optional
            Filter by year extracted from *date_column*.
        date_from / date_to : str, optional
            ISO-date bounds (``YYYY-MM-DD``).  Inclusive on both ends.
        group_by : list[str], optional
            Columns to GROUP BY (e.g. ``["status"]``, ``["service", "priority"]``).
        """
        allowlist = _load_allowlist(allowlist_json)
        if table not in allowlist:
            return {"error": f"Table '{table}' is not in the allowlist."}
        allowed = allowlist[table]

        # --- Валидация date_column ---
        if date_column not in allowed:
            return {"error": f"Column '{date_column}' is not in the allowlist for '{table}'."}

        # --- Собираем WHERE ---
        clauses: List[str] = []
        params: Dict[str, Any] = {}

        # equality / operator filters
        if filters:
            safe_filters = {k: v for k, v in filters.items() if k in allowed}
            if safe_filters:
                where_fragment, where_params = _build_where(safe_filters)
                if where_fragment:
                    # отрезаем " WHERE " — склеим позже
                    clauses.append(where_fragment.lstrip(" WHERE "))
                    params.update(where_params)

        # date constraints
        if year is not None:
            clauses.append(f"EXTRACT(YEAR FROM {date_column}) = :_year")
            params["_year"] = year
        if date_from is not None:
            clauses.append(f"{date_column} >= :_date_from")
            params["_date_from"] = date_from
        if date_to is not None:
            clauses.append(f"{date_column} <= :_date_to")
            params["_date_to"] = date_to

        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""

        # --- GROUP BY ---
        if group_by:
            safe_group = [col for col in group_by if col in allowed]
            if not safe_group:
                return {"error": "None of the group_by columns are in the allowlist."}
            group_cols = ", ".join(safe_group)
            sql = (
                f"SELECT {group_cols}, COUNT(*) AS cnt "
                f"FROM {table}{where} "
                f"GROUP BY {group_cols} ORDER BY cnt DESC;"
            )
        else:
            sql = f"SELECT COUNT(*) AS cnt FROM {table}{where};"

        return {"sql": sql, "params": params}

    # ------------------------------------------------------------------
    # execute_sql — выполнение read-only SQL
    # ------------------------------------------------------------------
    def execute_sql(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
        db_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a **read-only** parameterized SQL query and return rows.

        The query is validated to start with SELECT (no INSERT/UPDATE/DELETE).

        Parameters
        ----------
        sql : str
            SQL query (must begin with SELECT).
        params : dict, optional
            Named bind-parameters for the query.
        db_url : str, optional
            SQLAlchemy connection string.
            Falls back to env var ``DATABASE_URL`` or
            ``postgresql://localhost:5432/webui``.
        """
        normalized = sql.strip().upper()
        if not normalized.startswith("SELECT"):
            return {"error": "Only SELECT queries are allowed."}
        for forbidden in ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE"):
            if forbidden in normalized:
                return {"error": f"Forbidden keyword '{forbidden}' detected in query."}

        try:
            from sqlalchemy import create_engine, text  # noqa: late import — optional dep

            url = db_url or os.getenv("DATABASE_URL", "postgresql://localhost:5432/webui")
            engine = create_engine(url)
            with engine.connect() as conn:
                result = conn.execute(text(sql), params or {})
                rows = [dict(row._mapping) for row in result]
            return {"rows": rows, "total": len(rows)}
        except ImportError:
            return {"error": "sqlalchemy is not installed. Add it to requirements."}
        except Exception as exc:  # noqa: broad-except — return error to the model
            return {"error": str(exc)}

    # ------------------------------------------------------------------
    # describe_format — схема метаданных
    # ------------------------------------------------------------------
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
                "sla_violated",
                "sla_deadline",
                "coordinator",
                "assignee",
            ],
            "notes": "Store metadata as key/value pairs in the WebUI knowledge entry.",
        }
