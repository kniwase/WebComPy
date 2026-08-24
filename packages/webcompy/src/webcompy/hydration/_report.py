"""Recording and reporting of hydration mismatches."""

from __future__ import annotations

from dataclasses import dataclass
from logging import getLogger
from typing import Any, Literal

MismatchKind = Literal["text", "attribute", "tag", "node-count", "raw_html"]

_logger = getLogger("webcompy.hydration")


@dataclass(frozen=True)
class HydrationMismatchRecord:
    """One server/client hydration mismatch observation.

    Args:
        kind: Kind of mismatch observed.
        expected: Server-rendered value the client expected.
        actual: Value actually found in the client DOM.
        component_id: Component the mismatch occurred in, when known.

    Attributes:
        kind: Kind of mismatch observed.
        expected: Server-rendered value the client expected.
        actual: Value actually found in the client DOM.
        component_id: Component the mismatch occurred in, when known.

    """

    kind: MismatchKind
    expected: Any
    actual: Any
    component_id: str = ""


class HydrationReporter:
    def __init__(self) -> None:
        self.records: list[HydrationMismatchRecord] = []


def emit_report_summary(ctx: Any) -> None:
    reporter = getattr(ctx, "_hydration_reporter", None)
    if reporter is None or not reporter.records:
        return
    records = reporter.records
    by_kind: dict[str, int] = {}
    by_cid: dict[str, int] = {}
    for record in records:
        by_kind[record.kind] = by_kind.get(record.kind, 0) + 1
        if record.component_id:
            by_cid[record.component_id] = by_cid.get(record.component_id, 0) + 1
    kind_summary = ", ".join(f"{kind}={count}" for kind, count in sorted(by_kind.items()))
    cid_summary = ", ".join(f"{cid}({count})" for cid, count in sorted(by_cid.items()))
    _logger.warning(
        "Hydration mismatches detected (%d): %s%s",
        len(records),
        kind_summary,
        f"; components: {cid_summary}" if cid_summary else "",
    )


def _active_hydration_window() -> Any:
    from webcompy.components._component import _active_app_context

    ctx = _active_app_context.get()
    if ctx is None or not getattr(ctx, "_hydration_in_progress", False):
        return None
    return ctx


def record_mismatch(
    kind: MismatchKind,
    expected: Any,
    actual: Any,
    component_id: str = "",
) -> None:
    """Record a hydration mismatch with the active reporter, if any.

    Mismatches observed outside an active hydration window are ignored.

    Args:
        kind: Kind of mismatch observed.
        expected: Server-rendered value the client expected.
        actual: Value actually found in the client DOM.
        component_id: Component the mismatch occurred in, when known.

    """
    ctx = _active_hydration_window()
    if ctx is None:
        return
    reporter = getattr(ctx, "_hydration_reporter", None)
    if reporter is None:
        return
    reporter.records.append(HydrationMismatchRecord(kind, expected, actual, component_id))
