from __future__ import annotations

import hashlib
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

SPEC_URL = "https://raw.githubusercontent.com/github/cmark-gfm/499789b49373bfa045d0e7547e5ee63444c77bca/test/spec.txt"
SPEC_SHA256 = "7d8e5814befec287ac116786d81ff14e0adc9b13295b4494649e995408fd871c"
SPEC_EXAMPLE_COUNT = 672

CACHE_DIR = Path(__file__).parent / ".tmp"
CACHE_PATH = CACHE_DIR / "gfm_spec.txt"
XFAIL_PATH = Path(__file__).parent / "xfail.txt"

FENCE = "`" * 32
EXAMPLE_START = FENCE + " example"
EXAMPLE_START_WITH_INFO = re.compile(r"^\`{32} example(?P<info>.*)$")
HEADING_RE = re.compile(r"^#{1,6}\s+(?P<title>.*?)\s*$")
SLUG_RE = re.compile(r"[^a-z0-9]+")
_TAB_MARKER = "\u2192"


@dataclass(frozen=True)
class SpecExample:
    number: int
    section: str
    markdown: str
    expected_html: str


def _download_spec(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def _verify_hash(data: bytes, expected_sha256: str) -> None:
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected_sha256:
        msg = (
            f"sha256 mismatch for GFM spec.txt: expected {expected_sha256}, got {actual}. "
            "The pinned revision may have been tampered with or the URL is wrong."
        )
        raise FetchError(msg)


def ensure_spec_file() -> Path:
    override = os.environ.get("WEBCOMPY_GFM_SPEC_TXT")
    if override:
        return Path(override)

    if CACHE_PATH.is_file():
        data = CACHE_PATH.read_bytes()
        _verify_hash(data, SPEC_SHA256)
        return CACHE_PATH

    try:
        data = _download_spec(SPEC_URL)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        msg = (
            "GFM spec.txt is not cached and the harness could not download it. "
            f"To populate the cache, run: curl -fsSL {SPEC_URL} -o {CACHE_PATH}\n"
            f"Underlying error: {exc}"
        )
        raise FetchError(msg) from exc

    _verify_hash(data, SPEC_SHA256)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = CACHE_PATH.with_suffix(CACHE_PATH.suffix + ".tmp")
    tmp_path.write_bytes(data)
    tmp_path.replace(CACHE_PATH)
    return CACHE_PATH


class FetchError(RuntimeError):
    pass


def extract_examples(path: Path | None = None) -> list[SpecExample]:
    if path is None:
        path = ensure_spec_file()

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    examples: list[SpecExample] = []
    section = ""
    state: str = "outside"
    buffer: list[str] = []

    def emit() -> None:
        joined = "\n".join(buffer)
        markdown, _, expected_html = joined.partition("\n.\n")
        examples.append(
            SpecExample(
                number=len(examples) + 1,
                section=section,
                markdown=markdown.replace(_TAB_MARKER, "\t"),
                expected_html=expected_html.replace(_TAB_MARKER, "\t"),
            )
        )

    for line in lines:
        if state == "outside":
            heading = HEADING_RE.match(line)
            if heading is not None:
                section = heading.group("title")
            if line.rstrip() == EXAMPLE_START or EXAMPLE_START_WITH_INFO.match(line.rstrip()):
                state = "html"
                buffer = []
                continue
        elif line.rstrip() == FENCE:
            emit()
            state = "outside"
            buffer = []
            continue
        buffer.append(line)

    return examples


def load_xfail_numbers(path: Path = XFAIL_PATH) -> set[int]:
    if not path.is_file():
        return set()
    numbers: set[int] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        numbers.add(int(stripped))
    return numbers


def slugify(section: str) -> str:
    return SLUG_RE.sub("-", section.lower()).strip("-") or "general"
