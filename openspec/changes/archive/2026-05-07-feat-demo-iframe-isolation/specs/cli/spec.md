## ADDED Requirements

### Requirement: Static site generation SHALL copy _demos directory
When `webcompy generate` runs and `_demos/` exists in the static files directory, it SHALL copy the entire `_demos/` directory tree to `dist/_demos/` alongside other static files and generated HTML pages.

#### Scenario: _demos directory is copied to dist
- **WHEN** a developer runs `python -m webcompy generate` with `_demos/` in the static files directory
- **THEN** all files in `dist/_demos/` (app.py files and sample.json) SHALL exist
- **AND** the files SHALL be identical to the source files

#### Scenario: _demos app.py files reference local asset URLs
- **WHEN** `dist/_demos/helloworld/app.py` is examined after generation
- **THEN** its import statements SHALL reference `webcompy` packages available from the same origin
