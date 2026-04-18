# Async Utilities and HTTP Client

## Purpose

Web applications frequently need to perform asynchronous operations: fetching data from APIs, loading resources, or running long computations. In a reactive system, these operations must integrate seamlessly — when an async operation completes, its result should flow into the reactive graph just like any synchronous state change, triggering UI updates automatically.

WebComPy provides `useAsyncResult` for structured reactive async state with loading/error/success predicates, `useAsync` for fire-and-forget async operations, `AsyncResult` as a standalone async state container, and `HttpClient` for making HTTP requests from the browser. Together, these enable developers to work with asynchronous data using the same patterns as synchronous reactive state.

**What WebComPy does not yet provide:** `HttpClient` only works in the browser — there is no server-side request capability for SSG data fetching.

## Requirements

### Requirement: Async operations shall integrate with the reactive system
Developers SHALL be able to create a reactive async state container that starts unresolved and automatically updates when an async operation completes, triggering UI updates like any other reactive change. The `AsyncResult` class provides a structured state machine (`AsyncState.PENDING`, `LOADING`, `SUCCESS`, `ERROR`) with typed predicates for declarative UI rendering. The `useAsyncResult` composable integrates `AsyncResult` with the component lifecycle for automatic execution and cleanup.

#### Scenario: Loading data from an API on component mount with useAsyncResult
- **WHEN** a developer calls `useAsyncResult(fetch_func)` inside a component setup
- **THEN** `result.state` SHALL initially be `AsyncState.PENDING`
- **AND** after rendering, `result.state` SHALL transition to `AsyncState.LOADING`
- **WHEN** the async function resolves successfully
- **THEN** `result.data.value` SHALL contain the result
- **AND** `result.state.value` SHALL be `AsyncState.SUCCESS`
- **AND** `result.is_success.value` SHALL be `True`
- **AND** the UI SHALL update automatically

#### Scenario: Handling an async operation failure with structured error state
- **WHEN** the async function raises an exception
- **THEN** `result.state.value` SHALL be `AsyncState.ERROR`
- **AND** `result.is_error.value` SHALL be `True`
- **AND** `result.error.value` SHALL contain the exception
- **AND** `result.data.value` SHALL retain the last successful value (SWR pattern) or be the `default` value if no prior success

#### Scenario: Distinguishing async states with AsyncResult predicates
- **WHEN** a developer checks `result.is_pending`, `result.is_loading`, `result.is_success`, or `result.is_error`
- **THEN** each SHALL be a `Computed[bool]` reflecting the current `AsyncResult.state`
- **AND** they SHALL be suitable for use as `switch()` case conditions
- **AND** `result.is_loading` and `result.is_success` SHALL be mutually exclusive after the first execution

### Requirement: HTTP requests shall be made from the browser
`HttpClient` SHALL provide methods for all common HTTP verbs (GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS) that work in the browser environment using the Fetch API.

#### Scenario: Fetching JSON data
- **WHEN** a developer calls `await HttpClient.get(url)`
- **THEN** a `Response` object SHALL be returned with `text`, `headers`, `status_code`, and `ok` properties
- **AND** calling `response.json()` SHALL parse the response body as JSON

#### Scenario: Posting form data
- **WHEN** a developer calls `await HttpClient.post(url, form_data={"field": "value"})`
- **THEN** a `FormData` object SHALL be constructed in the browser
- **AND** the POST request SHALL be sent with the form data

#### Scenario: Making a request outside the browser
- **WHEN** `HttpClient.request()` is called on the server (where `browser` is `None`)
- **THEN** `WebComPyHttpClientException` SHALL be raised

### Requirement: HTTP responses shall provide convenient accessors
`HttpClient` requests SHALL return a `Response` object with properties for common response data and methods for error handling.

#### Scenario: Accessing response metadata
- **WHEN** a response is received
- **THEN** `response.status_code` SHALL contain the HTTP status code
- **AND** `response.ok` SHALL be `True` for 2xx status codes
- **AND** `response.headers` SHALL contain the response headers as a dict

#### Scenario: Handling error responses
- **WHEN** `response.raise_for_status()` is called on a response with a non-2xx status code
- **THEN** `WebComPyHttpClientException` SHALL be raised