from __future__ import annotations

from types import SimpleNamespace

import e2e.core.conftest as core_conftest
import e2e.docs.conftest as docs_conftest
from e2e.conftest import sanitize_console_log_name
from webcompy_cli._console_types import ConsoleMessage

_ARTIFACT_FORBIDDEN_CHARS = set('":<>|*?/\r\n\\')


def test_sanitize_console_log_name_strips_artifact_forbidden_chars() -> None:
    raw = (
        "test_server_tooling_page_renders_with_toc_and_code[static-chromium-/documents/server/testing"
        '-Testing-Recipe: testing a component that fetches data]::case "1" <a|b>*?\r\n\\end'
    )
    sanitized = sanitize_console_log_name(raw)
    assert not _ARTIFACT_FORBIDDEN_CHARS.intersection(sanitized)
    assert " " not in sanitized
    assert "__case" in sanitized


def test_write_console_log_uses_sanitized_filename(tmp_path, monkeypatch) -> None:
    node_name = (
        "test_server_tooling_page_renders_with_toc_and_code"
        "[static-chromium-/documents/server/testing-Testing-Recipe: testing a component that fetches data]"
    )
    fake_request = SimpleNamespace(node=SimpleNamespace(name=node_name))
    messages = [ConsoleMessage(type="warning", text="hello", location="http://localhost/:1:1")]

    for label, mod in (("docs", docs_conftest), ("core", core_conftest)):
        out_dir = tmp_path / label
        monkeypatch.setattr(mod, "CONSOLE_LOG_DIR", str(out_dir))
        mod._write_console_log(fake_request, messages)
        written = list(out_dir.iterdir())
        assert len(written) == 1
        assert not _ARTIFACT_FORBIDDEN_CHARS.intersection(written[0].name)
        assert written[0].name == f"console-{sanitize_console_log_name(node_name)}.log"
