# Delta: docs-site-documents

## ADDED Requirements

### Requirement: The Examples category shall present explanation plus live demo plus source

The manifest SHALL contain an `Examples` category at `/documents/examples/`, with pages (in order): `hello-world`, `todo`, `forms`, `routing`, `storage-sync`, `transition`, `teleport`, `i18n-playground`, `matplotlib`, `http-fetch`, `fetch-middleware`, `rpc-middleware`. Each page SHALL combine a Markdown narrative, a live demo iframe of the showcase app, and the demo's full source; any page whose demo needs a backend SHALL satisfy it with an in-app `FetchMiddleware`/`RpcMiddleware` mock so it works identically on the dev server and the static export, and SHALL include a "real server wiring" section with server-side code and links to the corresponding Advanced pages. The legacy `/sample/*` routes and the Navbar "Demos" dropdown SHALL be removed without redirects; `fizzbuzz` SHALL be retired entirely.

#### Scenario: Mocked networking works on static export

- **WHEN** the fetch-middleware or rpc-middleware example runs from the generated static site
- **THEN** its demo interactions complete successfully with no failed network requests in the console

#### Scenario: Sample routes removed

- **WHEN** `/sample/todo` is requested
- **THEN** the 404 page renders and the Navbar no longer exposes a Demos dropdown

#### Scenario: Example page trio present

- **WHEN** any Examples page is opened
- **THEN** it shows narrative, an embedded live demo, and the complete demo source
