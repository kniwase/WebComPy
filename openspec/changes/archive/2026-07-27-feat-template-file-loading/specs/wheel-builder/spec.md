## REMOVED Requirements

### Requirement: Wheel builder assets parameter and `_assets_registry` generation

The `assets` parameter on `make_webcompy_app_package` and the `_generate_assets_registry` helper in `webcompy_cli._wheel_builder` SHALL be removed. The wheel builder SHALL NOT generate `{app_name}/_assets_registry.py` modules and SHALL NOT contain a `_REGISTRY` dict for runtime asset lookup. The `WebComPyBuildConfig.assets` field SHALL be removed.

This is superseded by the new `ResourcePort` mechanism (`resource-port/spec.md`) which serves resources through HTTP at runtime without bundling them into the wheel.

#### Scenario: assets parameter removed
- **WHEN** `make_webcompy_app_package(..., assets={"logo": "logo.png"})` is called
- **THEN** `TypeError` SHALL be raised due to the removed `assets` keyword argument

#### Scenario: No _assets_registry.py in the wheel
- **WHEN** the wheel builder builds an app wheel after this change
- **THEN** the wheel SHALL NOT contain `{app_name}/_assets_registry.py` for any app package name
- **AND** `import` of `{app_name}._assets_registry` SHALL raise `ModuleNotFoundError`

#### Scenario: assets field removed from BuildConfig
- **WHEN** `WebComPyBuildConfig(app_module, assets={...})` is constructed with the `assets` keyword
- **THEN** `TypeError` SHALL be raised due to the removed keyword

#### Scenario: load_asset API removed
- **WHEN** `from webcompy.assets import load_asset, AssetNotFoundError` is imported
- **THEN** `ImportError` SHALL be raised because `webcompy.assets` no longer exists

#### Scenario: No _assets_registry runtime injection
- **WHEN** the framework builds a project after this change
- **THEN** the project source tree SHALL NOT contain an `app/_assets_registry.py` or equivalent
- **AND** `importlib.import_module("app._assets_registry")` SHALL fail
