"""Append-only JSONL research ledger with a hash chain and exclusive writer lock.

The chain detects accidental edits; it does not authenticate users or establish
scientific truth.  Ledger files are local research material, never release source.
"""
from __future__ import annotations
import contextlib
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

PROTOCOL = "ledger-json-v1"
EVENT_ACTORS = {
    "project.init": {("tool", "T0")}, "search.result": {("tool", "T0")},
    "project.update": {("user", "T1")},
    "paper.resolve": {("tool", "T0")}, "source.fetch": {("tool", "T0")},
    "evidence.anchor": {("tool", "T0")}, "source.identity.confirm": {("user", "T1")},
    "candidate.upsert": {("model", "T2")}, "claim.add": {("model", "T2")},
    "claim.link": {("model", "T2")}, "review.record": {("model", "T2")},
    "decision.record": {("user", "T1")}, "decision.revoke": {("user", "T1")},
    "reading.confirm": {("model", "T2"), ("user", "T1")},
}

class LedgerError(ValueError):
    pass

def canonical_json(value: Any) -> str:
    def check(item: Any) -> None:
        if isinstance(item, float):
            raise LedgerError("ledger-json-v1 forbids floating point values; encode them as decimal strings")
        if isinstance(item, dict):
            if any(not isinstance(key, str) for key in item):
                raise LedgerError("ledger keys must be strings")
            for child in item.values():
                check(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                check(child)
        elif item is not None and not isinstance(item, (str, bool, int)):
            raise LedgerError("unsupported ledger value")
    check(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)

def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def ensure_private_path(path: Path) -> None:
    """Reject projects inside the published skill tree or tracked Git paths."""
    path = path.resolve()
    skill_root = Path(__file__).resolve().parents[2]
    try:
        path.relative_to(skill_root)
    except ValueError:
        pass
    else:
        raise LedgerError("project outputs cannot be written inside the published skill tree")
    # A repository ancestor marks a public source tree; ignored paths are safe
    # only when git can confirm it, never just because a folder has a familiar name.
    for parent in [path, *path.parents]:
        if (parent / ".git").exists():
            import subprocess
            try:
                check = subprocess.run(["git", "check-ignore", "--quiet", str(path)], cwd=parent, capture_output=True, timeout=5)
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise LedgerError("cannot verify that project path is ignored by Git") from exc
            if check.returncode != 0:
                raise LedgerError("project outputs inside a Git working tree must be ignored by Git")
            return

class Ledger:
    def __init__(self, project: str | Path, *, clock=utc_now) -> None:
        self.project = Path(project).expanduser().resolve()
        ensure_private_path(self.project)
        self.path = self.project / "ledger.jsonl"
        self.clock = clock

    @contextlib.contextmanager
    def _lock(self):
        self.project.mkdir(parents=True, exist_ok=True)
        lock = self.project / "ledger.lock"
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise LedgerError("ledger writer lock already exists; verify the other writer stopped before removing a stale lock") from exc
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(canonical_json({"pid": os.getpid(), "created": self.clock()}))
                stream.flush()
                os.fsync(stream.fileno())
            yield
        finally:
            lock.unlink(missing_ok=True)

    def read(self) -> list[dict[str, Any]]:
        try:
            self.path.resolve().relative_to(self.project)
        except ValueError as exc:
            raise LedgerError("ledger path escapes project through a symbolic link") from exc
        if not self.path.exists():
            return []
        raw = self.path.read_bytes()
        if raw and not raw.endswith(b"\n"):
            raise LedgerError("ledger has an incomplete final line; do not silently truncate research history")
        events = []
        for number, line in enumerate(raw.splitlines(), 1):
            if not line:
                raise LedgerError(f"blank ledger line at {number}")
            try:
                event = json.loads(line.decode("utf-8"))
            except (ValueError, UnicodeError) as exc:
                raise LedgerError(f"invalid ledger JSON at line {number}") from exc
            if not isinstance(event, dict):
                raise LedgerError(f"ledger line {number} must be an object")
            events.append(event)
        return events

    def verify(self) -> dict[str, Any]:
        try:
            events = self.read()
        except LedgerError as exc:
            return {"valid": False, "errors": [str(exc)], "event_count": 0, "protocol": PROTOCOL}
        previous = None
        errors = []
        for seq, event in enumerate(events, 1):
            required = {"seq", "id", "ts", "type", "actor", "trust", "data", "prev", "protocol", "sha256"}
            if set(event) != required:
                errors.append(f"event fields mismatch at line {seq}")
            if type(event.get("seq")) is not int or event.get("seq") != seq or event.get("id") != f"EV-{seq:06d}":
                errors.append(f"event sequence mismatch at line {seq}")
            if not isinstance(event.get("data"), dict) or not isinstance(event.get("type"), str) or not event.get("type") or event.get("protocol") != PROTOCOL:
                errors.append(f"event contract mismatch at line {seq}")
            actor_valid = isinstance(event.get("actor"), str) and isinstance(event.get("trust"), str)
            if not actor_valid or (event.get("actor"), event.get("trust")) not in {("tool", "T0"), ("user", "T1"), ("model", "T2"), ("tool", "TL")}:
                errors.append(f"actor/trust mismatch at line {seq}")
            if actor_valid and isinstance(event.get("type"), str) and event["type"] in EVENT_ACTORS and (event.get("actor"), event.get("trust")) not in EVENT_ACTORS[event["type"]]:
                errors.append(f"event actor mismatch at line {seq}")
            try:
                timestamp = event.get("ts")
                if not isinstance(timestamp, str):
                    raise ValueError("timestamp must be text")
                observed_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                if observed_time.tzinfo is None:
                    raise ValueError("timestamp needs timezone")
            except ValueError:
                errors.append(f"invalid event timestamp at line {seq}")
            if event.get("prev") != previous:
                errors.append(f"hash chain mismatch at line {seq}")
            payload = {key: value for key, value in event.items() if key != "sha256"}
            try:
                actual = digest(payload)
            except LedgerError as exc:
                errors.append(f"invalid payload at line {seq}: {exc}")
                actual = None
            if event.get("sha256") != actual:
                errors.append(f"event hash mismatch at line {seq}")
            previous = event.get("sha256")
        return {"valid": not errors, "errors": errors, "event_count": len(events), "protocol": PROTOCOL}

    def append(self, event_type: str, data: dict[str, Any], *, actor: str = "tool", trust: str = "T0", expected_head: str | None = None) -> dict[str, Any]:
        if not event_type or not isinstance(data, dict):
            raise LedgerError("event type and object data are required")
        if not isinstance(actor, str) or not isinstance(trust, str) or actor not in {"tool", "model", "user"} or trust not in {"T0", "T1", "T2", "TL"}:
            raise LedgerError("invalid actor/trust classification")
        if (actor, trust) not in {("tool", "T0"), ("user", "T1"), ("model", "T2"), ("tool", "TL")}:
            raise LedgerError("actor and trust must agree")
        if event_type in EVENT_ACTORS and (actor, trust) not in EVENT_ACTORS[event_type]:
            raise LedgerError("event type requires its declared tool/model/user actor")
        with self._lock():
            verification = self.verify()
            if not verification["valid"]:
                raise LedgerError("refusing append to invalid ledger: " + "; ".join(verification["errors"]))
            events = self.read()
            if expected_head is not None and expected_head != (events[-1]["sha256"] if events else ""):
                raise LedgerError("ledger changed during the operation; retry against the current snapshot")
            seq = len(events) + 1
            event = {"seq": seq, "id": f"EV-{seq:06d}", "ts": self.clock(), "type": event_type,
                     "actor": actor, "trust": trust, "data": data, "prev": events[-1]["sha256"] if events else None,
                     "protocol": PROTOCOL}
            event["sha256"] = digest(event)
            with self.path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(canonical_json(event) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            return event

    def get(self, event_id: str) -> dict[str, Any]:
        verification = self.verify()
        if not verification["valid"]:
            raise LedgerError("cannot use an invalid ledger")
        for event in self.read():
            if event["id"] == event_id:
                return event
        raise LedgerError(f"unknown event ID: {event_id}")
