# Plugin System

## Purpose

The plugin system provides a formal extension mechanism for WebComPy applications. Third-party Python packages can hook into the application lifecycle, register DI services, and declare conditional JavaScript scripts — all through a structured `WebComPyPlugin` API. This enables use cases like debug toolbars, authentication guards, analytics tracking, and custom integrations without modifying the framework core.

## Requirements

### Requirement: WebComPyPlugin shall provide a base class for framework extensions

A `WebComPyPlugin` class SHALL be provided in the `webcompy.plugin` module. Plugins SHALL extend this base class to declare lifecycle hooks, DI providers, and conditional scripts.

#### Scenario: Creating a minimal plugin
- **WHEN** a developer creates `class MyPlugin(WebComPyPlugin): pass`
- **THEN** `name` SHALL default to `""` (empty string)
- **AND** `version` SHALL default to `"0.1.0"`
- **AND** all lifecycle hooks SHALL be no-ops by default

#### Scenario: Declaring plugin scripts
- **WHEN** a plugin overrides `get_scripts()` to return `[PluginScript(attrs={"src": "..."})]`
- **THEN** the returned `PluginScript` instances SHALL be collected by `PluginManager.scripts`

#### Scenario: Declaring DI providers
- **WHEN** a plugin overrides `get_providers()` to return `{my_key: lambda: MyService()}`
- **THEN** the returned keys and factories SHALL be registered in the app's DI scope during `PluginManager.init_all()`

### Requirement: PluginManager shall manage plugin lifecycle and discovery

A `PluginManager` class SHALL be provided that discovers plugins from import paths, collects their declarations, registers DI providers, and initializes lifecycle hooks.

#### Scenario: Discovering plugins from AppConfig
- **WHEN** `AppConfig.plugins` contains `["myapp.plugins:ErudaPlugin"]`
- **AND** `PluginManager.discover(["myapp.plugins:ErudaPlugin"])` is called
- **THEN** the `myapp.plugins` module SHALL be imported
- **AND** `ErudaPlugin` SHALL be validated as a `WebComPyPlugin` subclass
- **AND** the plugin SHALL be stored in the manager's internal list

#### Scenario: Invalid plugin path format
- **WHEN** `AppConfig.plugins` contains `["invalid_path"]` (no `:` separator)
- **THEN** `PluginManager.discover()` SHALL raise `WebComPyPluginException` with a descriptive error

#### Scenario: Plugin path points to non-plugin class
- **WHEN** `AppConfig.plugins` contains `["myapp:SomeClass"]`
- **AND** `SomeClass` is not a subclass of `WebComPyPlugin`
- **THEN** `PluginManager.discover()` SHALL raise `WebComPyPluginException` with a descriptive error

#### Scenario: Initializing all plugins
- **WHEN** `PluginManager.init_all()` is called
- **THEN** providers from all discovered plugins SHALL be registered in the app's DI scope
- **AND** `on_app_init(app)` SHALL be called on each plugin instance
- **AND** plugins SHALL be initialized in declaration order

#### Scenario: Collecting plugin scripts
- **WHEN** `PluginManager.scripts` is accessed after discovery
- **THEN** all `PluginScript` instances from all plugins' `get_scripts()` SHALL be returned as a flat list

#### Scenario: Empty plugins list
- **WHEN** `AppConfig.plugins` is empty or default `[]`
- **THEN** `PluginManager.discover()` SHALL be a no-op
- **AND** `PluginManager.scripts` SHALL return an empty list
- **AND** no error SHALL be raised

### Requirement: Plugin initialization shall be integrated into the application bootstrap

`WebComPyApp` SHALL create a `PluginManager` and initialize plugins during its startup sequence, before the root component is created.

#### Scenario: Plugin initialization during app bootstrap
- **WHEN** `WebComPyApp.__init__()` is called with `config=AppConfig(plugins=[...])`
- **THEN** a `PluginManager` SHALL be created
- **AND** `PluginManager.discover()` SHALL be called with the plugin paths
- **AND** `PluginManager.init_all()` SHALL be called after DI scope setup and before `AppDocumentRoot` creation

#### Scenario: Plugin scripts in generated HTML
- **WHEN** `generate_html()` is called on an app with plugins
- **THEN** `PluginManager.scripts` SHALL be collected and included in `scripts_head` (for `in_head=True`) and `scripts_body` (for `in_head=False`)
- **AND** conditional scripts SHALL be rendered as wrapper `<script>` tags

### Requirement: Plugin lifecycle shall support on_app_ready hook

`WebComPyPlugin` SHALL provide an `on_app_ready(self, app)` hook, called from `app.run()` before the first render. This gives plugins access to the DOM mount point and browser APIs.

#### Scenario: Debug toolbar initialization
- **WHEN** a plugin defines `on_app_ready(self, app)`
- **AND** `app.run()` is called in the browser
- **THEN** `on_app_ready` SHALL be called with the `app` instance
- **AND** the hook SHALL have access to `browser.document` for DOM manipulation

### Requirement: PluginManager and WebComPyPlugin shall be exported in the public API

`PluginManager` and `WebComPyPlugin` SHALL be exported from `webcompy.plugin` and accessible via `webcompy.app`.

#### Scenario: Importing plugin classes
- **WHEN** a developer writes `from webcompy.app import WebComPyPlugin`
- **THEN** the import SHALL succeed
- **WHEN** a developer writes `from webcompy.app import PluginManager`
- **THEN** the import SHALL succeed
