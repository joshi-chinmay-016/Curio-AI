import json
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session as SQLAlchemySession

from backend.app.repositories.timeline_repository import TimelineRepository
from backend.app.repositories.session_repository import SessionRepository
from backend.app.schemas.timeline import TimelineEvent, TimelineListResponse, SUPPORTED_EVENT_TYPES


class TimelineService:
    def __init__(
        self,
        repo: Optional[TimelineRepository] = None,
        session_repo: Optional[SessionRepository] = None,
    ):
        self.repo = repo or TimelineRepository()
        self.session_repo = session_repo or SessionRepository()

    def _parse_event_types(self, event_types: Optional[str]) -> Optional[List[str]]:
        if not event_types or not event_types.strip():
            return None
        types = [et.strip() for et in event_types.split(",") if et.strip()]
        if not types:
            return None
        invalid = [et for et in types if et not in SUPPORTED_EVENT_TYPES]
        if invalid:
            raise ValueError(
                f"Invalid event types: {', '.join(invalid)}. Supported: {', '.join(SUPPORTED_EVENT_TYPES)}"
            )
        return types

    def _parse_datetime(self, dt_str: Optional[str], param_name: str = "datetime") -> Optional[datetime]:
        if not dt_str or not dt_str.strip():
            return None
        try:
            parsed = dt_str.strip()
            last_space = parsed.rfind(" ")
            if last_space > 0 and ":" in parsed[last_space:]:
                parsed = parsed[:last_space] + "+" + parsed[last_space+1:]
            if parsed.endswith("Z"):
                parsed = parsed[:-1] + "+00:00"
            parsed = parsed.replace("%2B", "+")
            dt = datetime.fromisoformat(parsed)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            raise ValueError(
                f"Invalid {param_name} format: {dt_str}. Use ISO 8601 (e.g., 2024-01-15T12:00:00Z or 2024-01-15T12:00:00+00:00)"
            )

    def get_timeline(
        self,
        db: SQLAlchemySession,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
        session_id: Optional[UUID] = None,
        event_types: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> Optional[TimelineListResponse]:
        # Anti-enumeration check: if session_id is provided, verify it exists and is owned by user
        if session_id is not None:
            session = self.session_repo.get_by_id_and_user(db, session_id, user_id)
            if not session:
                return None

        parsed_event_types = self._parse_event_types(event_types)
        parsed_start = self._parse_datetime(start, "start")
        parsed_end = self._parse_datetime(end, "end")

        effective_page_size = min(max(1, page_size), 100)
        page = max(1, page)

        items, total = self.repo.get_timeline(
            db=db,
            user_id=user_id,
            page=page,
            page_size=effective_page_size,
            session_id=session_id,
            event_types=parsed_event_types,
            start=parsed_start,
            end=parsed_end,
        )

        timeline_events = []
        for row in items:
            meta = row.metadata
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except Exception:
                    meta = {}
            elif meta is None:
                meta = {}

            event = TimelineEvent(
                event_type=row.event_type,
                timestamp=row.timestamp,
                session_id=row.session_id,
                message_id=row.message_id,
                entity_id=row.entity_id,
                metadata=meta,
            )
            timeline_events.append(event)

        pages = (total + effective_page_size - 1) // effective_page_size if total > 0 else 0

        return TimelineListResponse(
            items=timeline_events,
            total=total,
            page=page,
            page_size=effective_page_size,
            pages=pages,
        )