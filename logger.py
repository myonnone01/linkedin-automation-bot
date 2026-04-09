"""Thread-safe log bus.

The automation worker pushes log events to a single `LogBus` instance; the
Flask SSE endpoint subscribes a per-client queue and drains events as they
arrive. Events are also printed to stdout so they show up in the terminal
that launched `start.bat`.
"""
import json
import queue
import threading
import time
from datetime import datetime
from typing import Iterator


class LogBus:
    def __init__(self) -> None:
        self._subscribers: list[queue.Queue] = []
        self._lock = threading.Lock()
        self._history: list[dict] = []
        self._history_cap = 500

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=1000)
        with self._lock:
            # Replay recent history so a new SSE client sees context
            for event in self._history[-50:]:
                try:
                    q.put_nowait(event)
                except queue.Full:
                    break
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def publish(self, level: str, message: str, **extra) -> None:
        event = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "message": message,
            **extra,
        }
        print(f"[{event['ts']}] [{level.upper()}] {message}", flush=True)
        with self._lock:
            self._history.append(event)
            if len(self._history) > self._history_cap:
                self._history = self._history[-self._history_cap:]
            dead = []
            for q in self._subscribers:
                try:
                    q.put_nowait(event)
                except queue.Full:
                    dead.append(q)
            for q in dead:
                self._subscribers.remove(q)

    # Convenience wrappers
    def info(self, message: str, **extra) -> None:
        self.publish("info", message, **extra)

    def warn(self, message: str, **extra) -> None:
        self.publish("warn", message, **extra)

    def error(self, message: str, **extra) -> None:
        self.publish("error", message, **extra)

    def success(self, message: str, **extra) -> None:
        self.publish("success", message, **extra)


# Module-level singleton
bus = LogBus()


def sse_stream(q: queue.Queue) -> Iterator[str]:
    """Yield text/event-stream payloads from a subscriber queue."""
    try:
        # Initial comment so browser considers the stream open
        yield ": connected\n\n"
        while True:
            try:
                event = q.get(timeout=15)
                yield f"data: {json.dumps(event)}\n\n"
            except queue.Empty:
                # Heartbeat to keep the connection alive
                yield ": keepalive\n\n"
    finally:
        bus.unsubscribe(q)
