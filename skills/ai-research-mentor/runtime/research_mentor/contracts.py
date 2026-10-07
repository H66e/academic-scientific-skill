"""Stable JSON output envelope used by the Python CLI and API."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

# Mirrors repository VERSION and Python package metadata; unreleased behavior is
# documented in CHANGELOG, not labeled as a second public release.
PACKAGE_VERSION = "0.3.0"

@dataclass
class Envelope:
    ok: bool
    status: str
    data: Any = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    ledger_events: list[str] = field(default_factory=list)
    next: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "status": self.status, "data": self.data,
                "warnings": list(self.warnings), "errors": list(self.errors),
                "ledger_events": list(self.ledger_events), "next": list(self.next)}

    @classmethod
    def success(cls, data: Any = None, *, status: str = "complete", **kwargs: Any) -> "Envelope":
        return cls(True, status, data, **kwargs)

    @classmethod
    def failure(cls, message: str, *, status: str = "failed", **kwargs: Any) -> "Envelope":
        return cls(False, status, None, errors=[message], **kwargs)
