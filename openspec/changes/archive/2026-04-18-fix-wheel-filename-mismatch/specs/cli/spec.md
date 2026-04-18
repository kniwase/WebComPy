## MODIFIED Requirements

### Requirement: Generated HTML shall include PyScript bootstrapping

Every generated HTML page SHALL include PyScript v2026.3.1 CSS and JS, a loading screen, the app div (either pre-rendered or hidden), and a PyScript configuration specifying all required Python packages. The configuration SHALL reference a single bundled wheel (not separate framework and application wheels) and SHALL NOT include `typing_extensions` as a dependency. The bundled wheel URL SHALL be computed using `get_wheel_filename` from the wheel builder module, using the actual app package name — not a hardcoded `"app"` prefix.

#### Scenario: Inspecting generated HTML

- **WHEN** a generated `index.html` is examined for an app package named `myapp`
- **THEN** it SHALL contain a `<script type="module">` tag loading PyScript
- **AND** a `<script type="py">` tag with the bootstrap code
- **AND** a `<style>` tag with scoped component CSS
- **AND** a loading screen div with `id="webcompy-loading"`
- **AND** the PyScript packages list SHALL reference a single bundled wheel URL using `get_wheel_filename("myapp", version)`
- **AND** `typing_extensions` SHALL NOT appear in the packages list

### Requirement: The dev server shall serve application packages

The dev server SHALL build a single bundled Python wheel containing both the webcompy framework and the application, and serve it at the `/_webcompy-app-package/` endpoint so that PyScript can load it in the browser. The wheel filename SHALL be computed using `get_wheel_filename` from the wheel builder module and SHALL match the URL referenced in the generated HTML.

#### Scenario: Starting the dev server

- **WHEN** a developer runs `python -m webcompy start --dev`
- **THEN** the server SHALL build a single bundled wheel containing both webcompy and the application code
- **AND** serve it at `/_webcompy-app-package/{filename}` where `{filename}` matches the wheel URL in the generated HTML
- **AND** the browser SHALL be able to import both `webcompy` and the application package