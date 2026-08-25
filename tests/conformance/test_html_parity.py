from __future__ import annotations

from my_app.parity_fixtures import PARITY_TEMPLATES, compute_parity_results


def test_parity_results_structure():
    results = compute_parity_results()
    assert set(results) == set(PARITY_TEMPLATES)
    for kind, payload in results.values():
        assert kind in {"tree", "error"}
        assert isinstance(payload, str) and payload


# browser-dualrun: skip
