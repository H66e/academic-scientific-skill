"""Outbound privacy policy.

Private research material must never be sent to a provider by accident.  Callers
must explicitly classify outbound material as public or de-identified.  The
heuristics only catch obvious local paths and credentials; they are not a DLP
system and are intentionally reported as a block rather than silently redacted.
"""
from __future__ import annotations
import re
from dataclasses import dataclass

class PrivacyError(ValueError):
    pass

@dataclass(frozen=True)
class OutboundCheck:
    sensitivity: str
    redacted: bool = False

def check_outbound(value: str, *, sensitivity: str = "private") -> OutboundCheck:
    if sensitivity not in {"public", "deidentified", "private"}:
        raise PrivacyError("sensitivity must be public, deidentified, or private")
    if sensitivity == "private":
        raise PrivacyError("private material is blocked from outbound requests; use local/offline mode or explicitly de-identify it")
    text = value or ""
    # Do not try to guess arbitrary research ideas.  Block credentials and local paths.
    patterns = [
        r"(?i)(?:api[_-]?key|secret|token|password)\s*[:=]\s*[^\s]+",
        r"(?i)bearer\s+[a-z0-9._-]{12,}",
        r"(?i)[a-z]:[\\/][^\s]+",
        r"(?:^|\s)\\\\[^\\\s]+\\[^\s]+",
        r"(?i)(?:^|\s)/(?:users|home|private|var|mnt)/[^\s]+",
        r"(?i)\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b",
    ]
    if any(re.search(pattern, text) for pattern in patterns):
        raise PrivacyError("outbound text appears to contain a credential, email address or local path")
    return OutboundCheck(sensitivity=sensitivity)
