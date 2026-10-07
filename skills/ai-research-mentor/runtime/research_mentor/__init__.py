"""Python-first research evidence core.

The package is deliberately standard-library only.  It creates evidence receipts
from tool observations and keeps the append-only project ledger separate from the
published skill source tree.
"""
from .contracts import Envelope, PACKAGE_VERSION
from .ledger import Ledger
from .privacy import PrivacyError, check_outbound
from .anchors import AnchorError, quote_text
from .core import ResearchCore
from .judgment import Judgment

__all__ = ["Envelope", "Ledger", "PrivacyError", "check_outbound", "AnchorError", "quote_text", "ResearchCore", "Judgment"]
__version__ = PACKAGE_VERSION
