"""Session memory manager maintaining the 3-turn window and user preferences."""

import threading
from datetime import UTC, datetime

from pydantic import BaseModel, Field


class TurnRecord(BaseModel):
    """Immutable record of a single conversation turn."""

    turn_id: str
    user_transcript: str
    assistant_response: str
    tool_used: str | None = None
    tool_output: str | None = None
    latencies: dict[str, float] = Field(default_factory=dict)
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )


class SessionData(BaseModel):
    """Session container with 3-turn memory window and user preferences."""

    session_id: str
    created_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    preferences: dict[str, str] = Field(default_factory=dict)
    turns: list[TurnRecord] = Field(default_factory=list)

    def get_recent_turns(self, max_turns: int = 3) -> list[TurnRecord]:
        """Return the most recent N turns for active context memory."""
        return self.turns[-max_turns:] if self.turns else []

    def format_history_prompt(self, max_turns: int = 3) -> str:
        """Format the active turns and preferences into conversational context."""
        recent = self.get_recent_turns(max_turns)
        lines = []
        if self.preferences:
            pref_strs = [f"{k}: {v}" for k, v in self.preferences.items()]
            lines.append(f"User Preferences: {', '.join(pref_strs)}")

        if not recent:
            return "\n".join(lines)

        lines.append("Recent Conversation History:")
        for turn in recent:
            lines.append(f"User: {turn.user_transcript}")
            if turn.tool_used:
                lines.append(f"[Tool {turn.tool_used}]: {turn.tool_output}")
            lines.append(f"Assistant: {turn.assistant_response}")
        return "\n".join(lines)


class SessionStore:
    """Thread-safe in-memory session store."""

    def __init__(self, max_turns: int = 3):
        self.max_turns = max_turns
        self._sessions: dict[str, SessionData] = {}
        self._lock = threading.Lock()

    def create_session(self, session_id: str | None = None) -> SessionData:
        with self._lock:
            import uuid
            sid = session_id or f"sess_{uuid.uuid4().hex[:12]}"
            session = SessionData(session_id=sid)
            self._sessions[sid] = session
            return session

    def get_session(self, session_id: str) -> SessionData | None:
        with self._lock:
            return self._sessions.get(session_id)

    def get_or_create_session(self, session_id: str) -> SessionData:
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionData(session_id=session_id)
            return self._sessions[session_id]

    def add_turn(self, session_id: str, turn: TurnRecord) -> SessionData:
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionData(session_id=session_id)
            sess = self._sessions[session_id]
            sess.turns.append(turn)
            sess.updated_at = datetime.now(UTC).isoformat()
            return sess

    def set_preference(self, session_id: str, key: str, value: str) -> None:
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionData(session_id=session_id)
            self._sessions[session_id].preferences[key] = value
            self._sessions[session_id].updated_at = datetime.now(UTC).isoformat()

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()

    def seed_demo_fixtures(self) -> str:
        """Seed a clean demo session with the canonical Kirana scenario turns."""
        with self._lock:
            demo_sid = "demo-session-kirana"
            sess = SessionData(
                session_id=demo_sid,
                preferences={"preferred_language": "Hinglish"},
            )
            # Turn 1: Price lookup
            sess.turns.append(
                TurnRecord(
                    turn_id="turn_demo_01",
                    user_transcript="Bhaiya, 2 kilo atta kitne ka hai?",
                    assistant_response=(
                        "Atta — ₹55 per kilo (2 kilo ka ₹110), stock mein hai (25 kilo available hai). "
                        "Aur kuch chahiye?"
                    ),
                    tool_used="catalog_lookup",
                    tool_output="Atta — ₹55 per kilo (2 kilo ka ₹110), stock mein hai (25 kilo available hai).",
                    latencies={"stt": 82.0, "agent": 120.0, "tts": 35.0, "total": 237.0},
                )
            )
            # Turn 2: Order & total confirmation
            sess.turns.append(
                TurnRecord(
                    turn_id="turn_demo_02",
                    user_transcript="2 kilo atta aur 1 litre tel le lo, total kitna hua?",
                    assistant_response=(
                        "Aapka order: 2 kilo atta ₹110 + 1 litre tel ₹145 = kul ₹255. Confirm karun?"
                    ),
                    tool_used="catalog_order",
                    tool_output="2 kilo atta @ ₹55 = ₹110; 1 litre tel @ ₹145 = ₹145|255",
                    latencies={"stt": 75.0, "agent": 110.0, "tts": 40.0, "total": 225.0},
                )
            )
            # Turn 3: Stock lookup
            sess.turns.append(
                TurnRecord(
                    turn_id="turn_demo_03",
                    user_transcript="Doodh hai kya stock mein?",
                    assistant_response=(
                        "Doodh — ₹56 per litre, stock mein hai (10 litre available hai). "
                        "Aur kuch chahiye?"
                    ),
                    tool_used="catalog_lookup",
                    tool_output="Doodh — ₹56 per litre, stock mein hai (10 litre available hai).",
                    latencies={"stt": 60.0, "agent": 80.0, "tts": 30.0, "total": 170.0},
                )
            )
            self._sessions[demo_sid] = sess
            return demo_sid


_global_session_store = SessionStore()


def get_session_store() -> SessionStore:
    return _global_session_store
