## MODIFIED Requirements

### Requirement: The framework shall operate in two environments from a single codebase
The same Python source code SHALL execute correctly both in the browser (via PyScript/Emscripten) and on the server (standard CPython). In the browser, the framework manipulates the DOM directly and responds to user interaction. On the server, it generates HTML strings for static site generation. No application code should need to change between environments.

#### Scenario: Rendering a component in the browser
- **WHEN** a component with `Signal`-based state and a template is rendered in the browser
- **THEN** the component SHALL create and manage real DOM nodes
- **AND** signal updates SHALL modify those DOM nodes directly

#### Scenario: Rendering the same component on the server
- **WHEN** the same component is rendered during static site generation
- **THEN** the component SHALL produce an HTML string
- **AND** no DOM manipulation SHALL be attempted