from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from uuid import uuid4

import duckdb
import pandas as pd


@dataclass
class Session:
    session_id: str
    tables: dict[str, pd.DataFrame] = field(default_factory=dict)
    history: list[dict[str, str]] = field(default_factory=list)

    def connection(self) -> duckdb.DuckDBPyConnection:
        conn = duckdb.connect(":memory:")
        for name, frame in self.tables.items():
            conn.register(name, frame)
        return conn


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = Lock()

    def create(self) -> Session:
        session = Session(session_id=str(uuid4()))
        with self._lock:
            self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> Session:
        with self._lock:
            session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(session_id)
        return session

    def get_or_create(self, session_id: str | None) -> Session:
        if session_id:
            try:
                return self.get(session_id)
            except KeyError:
                pass
        return self.create()


store = SessionStore()
