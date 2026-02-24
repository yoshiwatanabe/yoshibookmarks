"""Recall service for natural-language bookmark retrieval."""

from __future__ import annotations

import asyncio
import math
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from ..models.bookmark import Bookmark
from ..models.config import AppConfig, EnvSettings
from .storage_manager import StorageManager


@dataclass
class _EmbeddingEntry:
    stamp: str
    vector: List[float]


class RecallService:
    """Hybrid keyword + semantic recall over bookmark storage."""

    def __init__(
        self,
        config: AppConfig,
        storage_manager: StorageManager,
        env_settings: EnvSettings,
    ):
        self.config = config
        self.storage_manager = storage_manager
        self.env_settings = env_settings
        self._embedding_cache: Dict[str, _EmbeddingEntry] = {}
        self._token_pattern = re.compile(r"[a-z0-9]{2,}")

    async def query(
        self,
        query_text: str,
        limit: Optional[int] = None,
        scope: str = "all",
        current_storage: Optional[str] = None,
    ) -> dict:
        """Run recall query and return ranked results."""
        effective_limit = min(limit or self.config.recall_default_limit, self.config.recall_max_limit)
        storage_name = current_storage if scope == "current" else None
        bookmarks = self.storage_manager.get_bookmarks(storage_name=storage_name, include_deleted=False)

        keyword_scores: Dict[str, float] = {}
        query_tokens = self._tokenize(query_text)
        for bookmark in bookmarks:
            keyword_scores[bookmark.id] = self._keyword_score(query_tokens, bookmark)

        semantic_available = False
        fallback_reason = None
        semantic_scores: Dict[str, float] = {}

        if self.config.enable_semantic_search:
            try:
                semantic_scores = await self._semantic_scores(query_text, bookmarks)
                semantic_available = True
            except Exception as exc:
                fallback_reason = f"semantic_unavailable: {exc}"
        else:
            fallback_reason = "semantic_search_disabled"

        w_semantic = self.config.recall_semantic_weight
        w_keyword = self.config.recall_keyword_weight
        if (w_semantic + w_keyword) <= 0:
            w_semantic, w_keyword = 0.55, 0.45

        scored: List[Tuple[float, Bookmark, float, float, str, List[str]]] = []
        for bookmark in bookmarks:
            k_score = keyword_scores.get(bookmark.id, 0.0)
            s_score = semantic_scores.get(bookmark.id, 0.0) if semantic_available else 0.0
            if semantic_available:
                final_score = (w_keyword * k_score) + (w_semantic * s_score)
            else:
                final_score = k_score

            if final_score <= 0:
                continue

            snippet, highlights = self._build_snippet(bookmark, query_tokens)
            scored.append((final_score, bookmark, k_score, s_score, snippet, highlights))

        scored.sort(key=lambda item: item[0], reverse=True)
        top = scored[:effective_limit]

        return {
            "query": query_text,
            "mode": "hybrid" if semantic_available else "keyword_only",
            "semantic_available": semantic_available,
            "fallback_reason": fallback_reason,
            "results": [
                {
                    "bookmark": item[1].model_dump(mode="json"),
                    "score": round(item[0], 6),
                    "score_breakdown": {
                        "keyword": round(item[2], 6),
                        "semantic": round(item[3], 6),
                    },
                    "snippet": item[4],
                    "highlights": item[5],
                }
                for item in top
            ],
            "total_returned": len(top),
            "searched_storage_names": self._searched_storages(scope, current_storage),
        }

    def _searched_storages(self, scope: str, current_storage: Optional[str]) -> List[str]:
        if scope == "current" and current_storage:
            return [current_storage]
        return self.storage_manager.get_all_storage_names()

    def _tokenize(self, text: str) -> List[str]:
        lowered = text.lower()
        return list(dict.fromkeys(self._token_pattern.findall(lowered)))

    def _keyword_score(self, query_tokens: List[str], bookmark: Bookmark) -> float:
        if not query_tokens:
            return 0.0

        fields = {
            "title": (bookmark.title or "", 4.0),
            "keywords": (" ".join(bookmark.keywords or []), 3.0),
            "tags": (" ".join(bookmark.tags or []), 2.0),
            "description": (bookmark.description or "", 1.5),
            "url": (str(bookmark.url), 1.0),
        }
        total_weight = sum(weight for _, weight in fields.values())
        total_score = 0.0

        for token in query_tokens:
            token_score = 0.0
            for field_text, weight in fields.values():
                lowered = field_text.lower()
                if token in lowered:
                    token_score += weight
            total_score += min(token_score / total_weight, 1.0)

        return min(total_score / len(query_tokens), 1.0)

    def _build_snippet(self, bookmark: Bookmark, query_tokens: List[str]) -> Tuple[str, List[str]]:
        candidates = [
            ("title", bookmark.title or ""),
            ("description", bookmark.description or ""),
            ("keywords", ", ".join(bookmark.keywords or [])),
            ("url", str(bookmark.url)),
        ]

        best_text = bookmark.title
        best_matches = -1
        highlights: List[str] = []
        for _, text in candidates:
            lowered = text.lower()
            matched = [token for token in query_tokens if token in lowered]
            if len(matched) > best_matches:
                best_matches = len(matched)
                best_text = text
                highlights = matched

        snippet = (best_text or "").strip()
        if len(snippet) > 180:
            snippet = snippet[:177] + "..."
        return snippet, highlights[:8]

    async def _semantic_scores(
        self,
        query_text: str,
        bookmarks: List[Bookmark],
    ) -> Dict[str, float]:
        query_vector = await self._embed_text(query_text)
        raw_scores: Dict[str, float] = {}

        for bookmark in bookmarks:
            vector = await self._bookmark_vector(bookmark)
            raw_scores[bookmark.id] = self._cosine_similarity(query_vector, vector)

        if not raw_scores:
            return {}

        min_score = min(raw_scores.values())
        max_score = max(raw_scores.values())
        if math.isclose(max_score, min_score):
            return {key: 0.5 for key in raw_scores.keys()}

        return {
            key: (value - min_score) / (max_score - min_score)
            for key, value in raw_scores.items()
        }

    async def _bookmark_vector(self, bookmark: Bookmark) -> List[float]:
        stamp_dt = bookmark.last_modified or bookmark.created_at
        if isinstance(stamp_dt, datetime):
            stamp = stamp_dt.isoformat()
        else:
            stamp = ""

        cache = self._embedding_cache.get(bookmark.id)
        if cache and cache.stamp == stamp:
            return cache.vector

        text = self._bookmark_text(bookmark)
        vector = await self._embed_text(text)
        self._embedding_cache[bookmark.id] = _EmbeddingEntry(stamp=stamp, vector=vector)
        return vector

    def _bookmark_text(self, bookmark: Bookmark) -> str:
        return "\n".join(
            [
                bookmark.title or "",
                str(bookmark.url),
                bookmark.description or "",
                " ".join(bookmark.keywords or []),
                " ".join(bookmark.tags or []),
            ]
        )

    async def _embed_text(self, text: str) -> List[float]:
        if not self.env_settings.openai_api_key:
            raise RuntimeError("missing_openai_api_key")

        timeout_s = max(0.1, self.config.recall_query_timeout_ms / 1000.0)
        model_name = self.config.embedding_model
        api_key = self.env_settings.openai_api_key
        base_url = self.env_settings.openai_api_base

        def _embed() -> List[float]:
            from openai import OpenAI

            client_kwargs = {"api_key": api_key, "timeout": timeout_s}
            if base_url:
                client_kwargs["base_url"] = base_url
            client = OpenAI(**client_kwargs)
            response = client.embeddings.create(model=model_name, input=text)
            return response.data[0].embedding

        return await asyncio.to_thread(_embed)

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        n1 = math.sqrt(sum(a * a for a in v1))
        n2 = math.sqrt(sum(b * b for b in v2))
        if n1 <= 0 or n2 <= 0:
            return 0.0
        return dot / (n1 * n2)
