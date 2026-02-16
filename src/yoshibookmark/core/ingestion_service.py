"""Browser-extension oriented ingestion service."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..models.bookmark import Bookmark
from ..models.config import AppConfig
from .ai_inference import MultiProviderInferenceService, ProviderAttemptDiagnostics
from .bookmark_manager import BookmarkManager
from .content_analyzer import ContentAnalyzer
from .storage_manager import StorageManager

logger = logging.getLogger(__name__)


@dataclass
class PreviewRecord:
    preview_id: str
    created_at: datetime
    expires_at: datetime
    payload: Dict[str, Any]
    suggestion: Dict[str, Any]
    provider_trace: List[ProviderAttemptDiagnostics]


class IngestionError(Exception):
    """Ingestion operation error."""

    pass


class IngestionService:
    """Two-step ingestion flow: preview then commit."""

    def __init__(
        self,
        config: AppConfig,
        bookmark_manager: BookmarkManager,
        storage_manager: StorageManager,
        content_analyzer: ContentAnalyzer,
        inference_service: MultiProviderInferenceService,
    ):
        self.config = config
        self.bookmark_manager = bookmark_manager
        self.storage_manager = storage_manager
        self.content_analyzer = content_analyzer
        self.inference_service = inference_service
        self.previews: Dict[str, PreviewRecord] = {}

    async def create_preview(self, payload: Dict[str, Any], storage_location: str) -> Dict[str, Any]:
        """Generate ingest suggestions and return preview handle."""
        self._cleanup_expired_previews()

        url = payload["url"]
        page_title = payload.get("page_title") or ""
        selected_text = payload.get("selected_text") or ""
        page_excerpt = payload.get("page_excerpt") or ""
        user_note = payload.get("user_note") or ""

        analysis = await self.content_analyzer.analyze_url(url)
        ai_suggestion, provider_trace = await self.inference_service.generate_structured_metadata(
            url=url,
            page_title=page_title or analysis.get("title", ""),
            page_excerpt=page_excerpt,
            selected_text=selected_text,
            user_note=user_note,
        )

        base_keywords = analysis.get("keywords", [])
        inferred_keywords = (ai_suggestion or {}).get("keywords") or []
        merged_keywords = self._merge_keywords(inferred_keywords, base_keywords)

        suggested_title = (
            (ai_suggestion or {}).get("title")
            or page_title
            or analysis.get("title")
            or url
        )
        suggested_tags = self._normalize_list((ai_suggestion or {}).get("tags"), 6)
        summary = (ai_suggestion or {}).get("summary") or user_note
        confidence = float((ai_suggestion or {}).get("confidence") or 0.5)
        dedupe_candidates = self._find_dedupe_candidates(url, limit=5)

        preview_id = str(uuid4())
        now = datetime.now(timezone.utc)
        ttl = timedelta(seconds=self.config.ingest_preview_ttl_seconds)
        suggestion = {
            "suggested_title": suggested_title,
            "suggested_keywords": merged_keywords,
            "suggested_tags": suggested_tags,
            "summary": summary,
            "confidence": max(0.0, min(1.0, confidence)),
            "dedupe_candidates": dedupe_candidates,
            "storage_location": storage_location,
        }

        self.previews[preview_id] = PreviewRecord(
            preview_id=preview_id,
            created_at=now,
            expires_at=now + ttl,
            payload=payload,
            suggestion=suggestion,
            provider_trace=provider_trace,
        )

        return {
            "preview_id": preview_id,
            "created_at": now,
            "expires_at": now + ttl,
            **suggestion,
            "provider_trace": [vars(a) for a in provider_trace],
        }

    async def commit_preview(self, preview_id: str, final_data: Dict[str, Any]) -> Bookmark:
        """Persist bookmark based on preview and user edits."""
        self._cleanup_expired_previews()
        record = self.previews.get(preview_id)
        if record is None:
            raise IngestionError(f"Preview not found or expired: {preview_id}")

        suggestion = record.suggestion
        payload = record.payload
        storage_location = suggestion["storage_location"]

        title = final_data.get("title") or suggestion["suggested_title"]
        description = final_data.get("description") or suggestion["summary"] or payload.get("user_note")
        keywords = self._merge_keywords(
            final_data.get("keywords") or [],
            suggestion["suggested_keywords"],
        )
        tags = self._normalize_list(final_data.get("tags") or suggestion["suggested_tags"], 10)
        folder_path = final_data.get("folder_path")

        bookmark = await self.bookmark_manager.create_bookmark(
            url=payload["url"],
            title=title,
            storage_location=storage_location,
            keywords=keywords,
            description=description,
            tags=tags,
            folder_path=folder_path,
        )

        self.previews.pop(preview_id, None)
        return bookmark

    async def quick_save(self, payload: Dict[str, Any], storage_location: str) -> Bookmark:
        """Fast path create with minimal interactive review."""
        preview = await self.create_preview(payload, storage_location)
        return await self.commit_preview(preview["preview_id"], {})

    def get_provider_status(self) -> list[dict]:
        return self.inference_service.get_provider_status()

    def get_preview_trace(self, preview_id: str) -> List[dict]:
        self._cleanup_expired_previews()
        record = self.previews.get(preview_id)
        if record is None:
            raise IngestionError(f"Preview not found or expired: {preview_id}")
        return [vars(a) for a in record.provider_trace]

    def _cleanup_expired_previews(self) -> None:
        now = datetime.now(timezone.utc)
        expired_ids = [pid for pid, rec in self.previews.items() if rec.expires_at < now]
        for pid in expired_ids:
            self.previews.pop(pid, None)

    def _merge_keywords(self, first: List[str], second: List[str]) -> List[str]:
        merged: List[str] = []
        for source in [first or [], second or []]:
            for keyword in source:
                kw = (keyword or "").strip().lower()
                if kw and kw not in merged:
                    merged.append(kw)
        return merged[:4]

    def _normalize_list(self, values: Any, max_items: int) -> List[str]:
        if not isinstance(values, list):
            return []
        cleaned: List[str] = []
        for value in values:
            item = str(value).strip()
            if item and item not in cleaned:
                cleaned.append(item)
        return cleaned[:max_items]

    def _find_dedupe_candidates(self, url: str, limit: int = 5) -> List[dict]:
        all_items = self.storage_manager.get_bookmarks(include_deleted=False)
        url_text = url.strip().rstrip("/")
        matches = []
        for item in all_items:
            if str(item.url).rstrip("/") == url_text:
                matches.append(
                    {
                        "id": item.id,
                        "title": item.title,
                        "url": str(item.url),
                        "keywords": item.keywords,
                        "last_accessed": item.last_accessed,
                        "storage_location": item.storage_location,
                    }
                )
        return matches[:limit]
