"""Regression tests for the pypdf security pin in requirements.txt.

The repository pins ``pypdf==6.21.4`` to close CVE-2026-119203
(GHSA-5849-834g-hvw5): an infinite loop in the standard xref-table trailer
search when opening an incomplete/truncated PDF that has no ``trailer``
keyword. On versions <= 6.21.2 the parser rewinds to the same offset forever;
since 6.21.3 it detects the repeated read and raises ``PdfReadError``.

The truncated PDF below is the minimal reproducer from the upstream fix
(py-pdf/pypdf#4289).
"""

import io
import threading

from pypdf import PdfReader
from pypdf.errors import PdfReadError

TRUNCATED_XREF_PDF = b"%PDF-1.4\nstartxref\n28\n%%EOF\nxref\n1 0\naaa"


def _parse_with_timeout(payload, timeout=5.0):
    """Run ``PdfReader`` on a daemon thread, reporting hangs vs results."""
    outcome = {}

    def run():
        try:
            PdfReader(io.BytesIO(payload))
            outcome["result"] = "returned"
        except PdfReadError as exc:
            outcome["result"] = "PdfReadError: %s" % exc
        except Exception as exc:  # any parse failure is acceptable here
            outcome["result"] = "%s: %s" % (type(exc).__name__, exc)

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    worker.join(timeout)
    if worker.is_alive():
        outcome["hang"] = True
    return outcome


def test_truncated_xref_trailer_search_terminates():
    """CVE-2026-119203: opening a truncated PDF must terminate quickly."""
    outcome = _parse_with_timeout(TRUNCATED_XREF_PDF)
    assert not outcome.get("hang"), (
        "pypdf hung while searching for the trailer in a truncated xref "
        "table (CVE-2026-119203 infinite loop)"
    )
    # With the fix, pypdf raises PdfReadError instead of looping forever.
    assert outcome["result"].startswith("PdfReadError"), outcome
