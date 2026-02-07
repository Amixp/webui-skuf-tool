from __future__ import annotations

import re
from typing import Any, Dict, List


TOKEN_RE = re.compile(r"[\w\-]+", re.UNICODE)


def _tokenize(text: str) -> List[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def _score(query_tokens: List[str], doc_tokens: List[str]) -> float:
    if not query_tokens or not doc_tokens:
        return 0.0
    counts: Dict[str, int] = {}
    for token in doc_tokens:
        counts[token] = counts.get(token, 0) + 1
    return float(sum(counts.get(token, 0) for token in query_tokens))


class Tools:
    """Open WebUI tool for reranking search results."""

    def rerank(self, query: str, candidates: List[Dict[str, Any]], top_k: int = 5) -> Dict[str, Any]:
        """Rerank candidate documents based on token overlap."""
        query_tokens = _tokenize(query)
        scored: List[Dict[str, Any]] = []
        for candidate in candidates:
            text = str(candidate.get("text") or candidate.get("summary") or candidate)
            score = _score(query_tokens, _tokenize(text))
            scored.append({"score": score, "candidate": candidate})
        scored.sort(key=lambda item: item["score"], reverse=True)
        return {"query": query, "results": scored[:top_k]}
