"""Append-only JSONL research ledger with a hash chain and exclusive writer lock.

The chain detects accidental edits; it does not authenticate users or establish
scientific truth.  Ledger files are local research material, never release source.

A hash chain cannot see its own tail being cut off: every surviving event still
points at its predecessor, so a shorter chain verifies clean.  The anchor file
next to the ledger records the expected head and event count from outside the
chain, which turns a silently truncated ledger into a reported mismatch.  The
anchor shares the ledger's directory and threat model, so it does not defend
against a deliberate owner who rewrites both; it defends against accident, loss
and partial writes, which is what this module claims to detect.
"""
from __future__ import annotations
import contextlib
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

from .results import validate_result_payload

PROTOCOL = "ledger-json-v1"
ANCHOR_PROTOCOL = "ledger-anchor-v1"
EVENT_ACTORS = {
    "project.init": {("tool", "T0")}, "search.result": {("tool", "T0")},
    "project.update": {("user", "T1")},
    "paper.resolve": {("tool", "T0")}, "source.fetch": {("tool", "T0")},
    "evidence.anchor": {("tool", "T0")}, "source.identity.confirm": {("user", "T1")},
    "candidate.upsert": {("model", "T2")}, "claim.add": {("model", "T2")},
    "claim.link": {("model", "T2")}, "review.record": {("model", "T2")},
    "decision.record": {("user", "T1")}, "decision.revoke": {("user", "T1")},
    "reading.confirm": {("model", "T2"), ("user", "T1")},
    "result.record": {("model", "T2"), ("user", "T1")},
    "result.invalidate": {("user", "T1")},
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
        self.anchor_path = self.project / "ledger.anchor.json"
        self.clock = clock

    def _read_anchor(self) -> dict[str, Any] | None:
        """Return the recorded anchor, or None when the project has none yet."""
        if not self.anchor_path.exists():
            return None
        try:
            anchor = json.loads(self.anchor_path.read_text(encoding="utf-8"))
        except (ValueError, UnicodeError, OSError) as exc:
            raise LedgerError(f"unreadable ledger anchor: {exc}") from exc
        if (not isinstance(anchor, dict) or anchor.get("protocol") != ANCHOR_PROTOCOL
                or type(anchor.get("event_count")) is not int
                or not isinstance(anchor.get("head"), str)):
            raise LedgerError("malformed ledger anchor")
        return anchor

    def _write_anchor(self, head: str, count: int) -> None:
        # Replace, never append: a half-written anchor must not survive as a
        # valid-looking shorter one.  os.replace is atomic within a directory.
        temporary = self.anchor_path.with_name(self.anchor_path.name + ".tmp")
        anchor = {"protocol": ANCHOR_PROTOCOL, "event_count": count, "head": head}
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(canonical_json(anchor) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, self.anchor_path)

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

    def _compare_anchor(self, events: list[dict[str, Any]], errors: list[str]) -> str:
        try:
            anchor = self._read_anchor()
        except LedgerError as exc:
            errors.append(str(exc))
            return "mismatch"
        if anchor is None:
            # Projects created before anchoring, or whose anchor was deleted,
            # are reported as unanchored rather than silently passed as anchored.
            return "absent"
        if anchor["event_count"] != len(events):
            errors.append(f"anchor/ledger event count mismatch: anchor={anchor['event_count']} ledger={len(events)}; "
                          "events were removed from the end of the ledger or the anchor is stale")
            return "mismatch"
        if anchor["head"] != (events[-1]["sha256"] if events else ""):
            errors.append("anchor/ledger head mismatch: the last event does not match the recorded anchor")
            return "mismatch"
        return "matched"

    def verify(self, *, check_anchor: bool = True) -> dict[str, Any]:
        try:
            events = self.read()
        except LedgerError as exc:
            return {"valid": False, "errors": [str(exc)], "event_count": 0,
                    "protocol": PROTOCOL, "anchor": "unchecked"}
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
            if isinstance(event.get("type"), str) and event["type"] not in EVENT_ACTORS:
                errors.append(f"unregistered event type at line {seq}: {event['type']!r}")
            actor_valid = isinstance(event.get("actor"), str) and isinstance(event.get("trust"), str)
            if not actor_valid or (event.get("actor"), event.get("trust")) not in {("tool", "T0"), ("user", "T1"), ("model", "T2"), ("tool", "TL")}:
                errors.append(f"actor/trust mismatch at line {seq}")
            if actor_valid and isinstance(event.get("type"), str) and event["type"] in EVENT_ACTORS and (event.get("actor"), event.get("trust")) not in EVENT_ACTORS[event["type"]]:
                errors.append(f"event actor mismatch at line {seq}")
            if isinstance(event.get("type"), str) and event["type"] in {"result.record", "result.invalidate"}:
                try:
                    validate_result_payload(event["type"], event.get("data"))
                except ValueError as exc:
                    errors.append(f"invalid result payload at line {seq}: {exc}")
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
        anchor = self._compare_anchor(events, errors) if check_anchor else "unchecked"
        return {"valid": not errors, "errors": errors, "event_count": len(events),
                "protocol": PROTOCOL, "anchor": anchor}

    def anchor(self) -> dict[str, Any]:
        """Record the current head and count as the expected state.

        This adopts the ledger as it stands.  Running it on an already truncated
        ledger anchors the truncation, so it is only meaningful once a person has
        decided the current contents are the ones they mean to keep.
        """
        with self._lock():
            verification = self.verify(check_anchor=False)
            if not verification["valid"]:
                raise LedgerError("refusing to anchor an invalid ledger: " + "; ".join(verification["errors"]))
            events = self.read()
            head = events[-1]["sha256"] if events else ""
            self._write_anchor(head, len(events))
            return {"protocol": ANCHOR_PROTOCOL, "event_count": len(events), "head": head}

    def append(self, event_type: str, data: dict[str, Any], *, actor: str = "tool", trust: str = "T0", expected_head: str | None = None) -> dict[str, Any]:
        if not isinstance(event_type, str) or not event_type or not isinstance(data, dict):
            raise LedgerError("event type and object data are required")
        if event_type not in EVENT_ACTORS:
            raise LedgerError(f"unregistered event type: {event_type!r}")
        if not isinstance(actor, str) or not isinstance(trust, str) or actor not in {"tool", "model", "user"} or trust not in {"T0", "T1", "T2", "TL"}:
            raise LedgerError("invalid actor/trust classification")
        if (actor, trust) not in {("tool", "T0"), ("user", "T1"), ("model", "T2"), ("tool", "TL")}:
            raise LedgerError("actor and trust must agree")
        if (actor, trust) not in EVENT_ACTORS[event_type]:
            raise LedgerError("event type requires its declared tool/model/user actor")
        try:
            validate_result_payload(event_type, data)
        except ValueError as exc:
            raise LedgerError(str(exc)) from exc
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
            self._write_anchor(event["sha256"], seq)
            return event

    def get(self, event_id: str) -> dict[str, Any]:
        verification = self.verify()
        if not verification["valid"]:
            raise LedgerError("cannot use an invalid ledger")
        for event in self.read():
            if event["id"] == event_id:
                return event
        raise LedgerError(f"unknown event ID: {event_id}")
