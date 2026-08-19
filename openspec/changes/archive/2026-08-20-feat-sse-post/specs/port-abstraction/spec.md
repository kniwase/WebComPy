# Port Abstraction (delta)

## ADDED Requirements

### Requirement: FetchPort shall provide a streaming request capability

`FetchPort` SHALL provide a `stream(url, *, method="GET", headers=None, body=None)` method returning a `FetchStream` object. `FetchStream` SHALL expose `status_code: int`, `headers: dict[str, str]`, and `ok: bool`, each available without consuming the response body. `FetchStream` SHALL be an `AsyncIterator[str]` of text chunks: the concatenation of all yielded chunks SHALL equal the complete response body text, and iteration SHALL finish with `StopAsyncIteration` when the body is exhausted. `FetchStream` SHALL provide a `close()` method (idempotent) that aborts the underlying request; after `close()`, in-flight iteration SHALL finish and no further chunks SHALL be yielded. The base class SHALL provide a default `stream()` implementation that performs the ordinary `fetch()` and yields the entire response body as a single chunk, so existing port implementations remain functional without modification; implementations MAY override it for real incremental streaming.

#### Scenario: Response metadata is available before body consumption

- **WHEN** `fetch_port.stream("/data")` returns a `FetchStream`
- **THEN** `status_code`, `headers`, and `ok` SHALL be readable before any `__anext__` call

#### Scenario: Chunks concatenate to the full body

- **WHEN** a `FetchStream` yields chunks `"hel"`, `"lo wor"`, `"ld"`
- **THEN** their concatenation SHALL equal `"hello world"`
- **AND** the iterator SHALL then raise `StopAsyncIteration`

#### Scenario: Default implementation degrades to a single chunk

- **WHEN** a `FetchPort` implementation does not override `stream()` and its `fetch()` returns body text `"abc"`
- **THEN** `stream()` SHALL yield exactly one chunk equal to `"abc"`

#### Scenario: close aborts and is idempotent

- **WHEN** `close()` is called on a `FetchStream` mid-iteration
- **THEN** the underlying request SHALL be aborted and the iterator SHALL finish
- **AND** calling `close()` again SHALL NOT raise

### Requirement: The browser FetchPort shall stream incrementally with abort support

The browser `FetchPort` implementation SHALL override `stream()` to read the response body incrementally from the browser `ReadableStream` API. It SHALL decode bytes incrementally with a streaming UTF-8 decoder so a multi-byte character split across read chunks SHALL be reconstructed correctly. `close()` SHALL abort the underlying fetch via an abort controller and cancel the body reader. The implementation SHALL pass the request method, headers, and body to the underlying fetch call unchanged.

#### Scenario: Multi-byte characters split across chunks are preserved

- **WHEN** the browser stream delivers the UTF-8 bytes of `"こんにちは"` split between two chunks such that a code point boundary falls between them
- **THEN** the decoded chunks SHALL reassemble the string without corruption

#### Scenario: close aborts the fetch and cancels the reader

- **WHEN** `close()` is called on a browser `FetchStream` while the body is still streaming
- **THEN** the fetch SHALL be aborted via its abort signal
- **AND** the body reader SHALL be cancelled
