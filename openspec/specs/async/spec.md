# Async Utilities and HTTP Client

## Purpose

Web applications frequently need to perform asynchronous operations: fetching data from APIs, loading resources, or running long computations. In a reactive system, these operations must integrate seamlessly — when an async operation completes, its result should flow into the reactive graph just like any synchronous state change, triggering UI updates automatically.

WebComPy provides `AsyncComputed` for reactive async values, `AsyncWrapper` for fire-and-forget async operations, and `HttpClient` for making HTTP requests from the browser. Together, these enable developers to work with asynchronous data using the same patterns as synchronous reactive state.

## Requirements

### Requirement: Async operations shall integrate with the reactive system
Developers SHALL be able to create a reactive value that starts unresolved and automatically updates when an async operation completes, triggering UI updates like any other reactive change.

#### Scenario: Loading data from an API on page load
- **WHEN** a developer creates `AsyncComputed(fetch_user_data())`
- **THEN** `value` SHALL initially be `None`
- **AND** any UI depending on this `AsyncComputed` SHALL reflect the loading state
- **WHEN** the coroutine resolves
- **THEN** `value` SHALL update to the result
- **AND** `done` SHALL become `True`
- **AND** the UI SHALL update automatically

#### Scenario: Handling an async operation failure
- **WHEN** the coroutine raises an exception
- **THEN** `error` SHALL contain the exception
- **AND** `done` SHALL be `False`

### Requirement: Fire-and-forget async operations shall be supported
Developers SHALL be able to wrap async functions so that calling them runs the coroutine in the background without blocking or requiring the caller to await the result.

#### Scenario: Triggering a background save
- **WHEN** a developer wraps an async save function with `AsyncWrapper()`
- **AND** calls the wrapped function from an event handler
- **THEN** the coroutine SHALL run in the background
- **AND** optional callbacks SHALL be invoked on success or failure

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