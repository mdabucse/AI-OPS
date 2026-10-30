from __future__ import annotations

import json
import re
from pathlib import Path


KNOWLEDGE_PATH = Path(__file__).parent / "knowledge" / "runbooks.json"


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.lower()))


def retrieve_context(query: str, top_k: int = 3) -> list[dict]:
    """Retrieve explainable local runbook matches using token overlap."""
    if top_k <= 0:
        return []
    query_tokens = _tokens(query)
    if not query_tokens:
        return []

    documents = json.loads(KNOWLEDGE_PATH.read_text(encoding="utf-8"))
    matches = []
    for document in documents:
        searchable = set(document["keywords"]) | _tokens(document["title"])
        overlap = query_tokens & searchable
        if overlap:
            matches.append(
                {
                    "document_id": document["document_id"],
                    "title": document["title"],
                    "content": document["content"],
                    "score": round(len(overlap) / len(query_tokens), 4),
                }
            )
    matches.sort(key=lambda item: (-item["score"], item["document_id"]))
    return matches[:top_k]
