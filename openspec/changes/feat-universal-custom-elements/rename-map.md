# Rename Map

Names that could not satisfy the naming-consistency rule
(`func.__name__ == kebab_to_pascal(custom_element_name)`), with their replacements.

## Single-word components (no hyphen in derived kebab name)

| Old name | New name | Custom element | Location |
|---|---|---|---|
| `App` | `HelloWorldApp` | `hello-world-app` | `docs_app/static/_demos/helloworld/app.py` |
| `App` | `FizzbuzzApp` | `fizzbuzz-app` | `docs_app/static/_demos/fizzbuzz/app.py` |
| `App` | `TodoApp` | `todo-app` | `docs_app/static/_demos/todo/app.py` |
| `App` | `FetchSampleApp` | `fetch-sample-app` | `docs_app/static/_demos/fetch_sample/app.py` |
| `App` | `MatplotlibSampleApp` | `matplotlib-sample-app` | `docs_app/static/_demos/matplotlib_sample/app.py` |
| `App` | `TeleportDemoApp` | `teleport-demo-app` | `docs_app/static/_demos/teleport/app.py` |
| `App` | `TransitionDemoApp` | `transition-demo-app` | `docs_app/static/_demos/transition/app.py` |
| `Button` | `DocsButton` | `docs-button` | `docs_app/components/ui.py` |
| `Card` | `DocsCard` | `docs-card` | `docs_app/components/ui.py` |
| `Link` | `DocsLink` | `docs-link` | `docs_app/components/ui.py` |
| `Section` | `DocsSection` | `docs-section` | `docs_app/components/ui.py` |
| `Navbar` | `DocsNavbar` | `docs-navbar` | `docs_app/components/navigation.py` |
| `Root` | `DocsRoot` | `docs-root` | `docs_app/layout/__init__.py` |
| `Home` | `HomeContent` | `home-content` | `docs_app/templates/home.py` |
| `Root` | `AppRoot` | `app-root` | `e2e/core/my_app/layout.py` |
| `Root` | `AppRoot` | `app-root` | `packages/webcompy-cli/src/webcompy_cli/template_data/app/components/root.py` |
| `Navigation` | `SiteNavigation` | `site-navigation` | `packages/webcompy-cli/src/webcompy_cli/template_data/app/components/navigation.py` |
| `Home` | `HomePage` | `home-page` | `packages/webcompy-cli/src/webcompy_cli/template_data/app/components/home.py` |
| `Fizzbuzz` | `FizzbuzzPage` | `fizzbuzz-page` | `packages/webcompy-cli/src/webcompy_cli/template_data/app/components/fizzbuzz.py` |
| `Root` | `TestRoot` | `test-root` | `tests/test_async_component_context.py`, `test_error_boundary.py`, `test_event_error_routing.py`, `test_rerender_lifecycle_error_routing.py`, `test_transition.py`, `test_custom_element_components.py` |
| `Child` | `TestChild` | `test-child` | `tests/test_transition.py` |
| `Page` | `TeleportPage` | `teleport-page` | `tests/test_teleport.py` |
| `Modal` | `TeleportModal` | `teleport-modal` | `tests/test_teleport.py` |
| `Page` | `EventSourcePage` | `event-source-page` | `tests/test_readonly_event_sources.py` |
| `Page` | `StoragePage` | `storage-page` | `tests/test_storage_composable.py` |
| `Page` | `TemplateExpressionPage` | `template-expression-page` | `tests/test_template_expressions.py` |
| `Bad` | `BadCard` | `bad-card` | `tests/test_custom_element_components.py` |
| `Plain` | `PlainCard` | `plain-card` | `tests/test_custom_element_components.py` |

## Acronym names (do not round-trip)

| Old name | New name | Custom element | Location |
|---|---|---|---|
| `MarkdownSSRPage` | `MarkdownSsrPage` | `markdown-ssr-page` | `tests/test_template_markdown_integration.py` |
| `MarkdownListForSSRPage` | `MarkdownListForSsrPage` | `markdown-list-for-ssr-page` | `tests/test_template_markdown_integration.py` |
| `E2ECard` | `E2eCard` | `e2e-card` (unchanged) | `e2e/core/my_app/pages/custom_element.py` |
| `PLMethod` | `PlMethod` | `pl-method` | `tests/test_lazy_routing.py` |
| `TestPage` (was `Page`) | `TestPage` | `test-page` | `tests/test_ssr_set_cookie.py`, `test_rpc_mount.py`, `test_asgi_embed.py`, `test_asgi_mount.py` |

## Leading-underscore test components (strip `_`, keep PascalCase)

All in `tests/`; each strips the leading underscore and keeps the rest of the name
(e.g. `_TestRoot` → `TestRoot`, `_FetchRoot` → `FetchRoot`,
`_RpcFetchRootNoTransfer` → `RpcFetchRootNoTransfer`). Files:
`test_app_di_scope_server_error.py`, `test_asgi_embed.py`, `test_asgi_mount.py`,
`test_build_artifacts.py`, `test_error_policy.py`, `test_framework_ui_html.py`,
`test_html_generation.py`, `test_plugin_render_context_init.py`,
`test_plugin_script.py`, `test_plugin_system.py`, `test_prerender_hidden.py`,
`test_render_context_dispose.py`, `test_render_context_isolation.py`,
`test_request_isolation.py`, `test_router_request_scoping.py`,
`test_rpc_integration.py`, `test_runtime_local_integration.py`,
`test_server_rendering.py`, `test_template_ssr.py`, `test_typed_transfer.py`.

## Module-scoped test roots in test files

`Root` (single-word) → `TestRoot` where the file had no other `Test*Root` name;
`_Root` → `ScopingRoot` and `_Page` → `ScopingPage` in `test_router_request_scoping.py`;
`_Root` → `BuildArtifactsRoot` in `test_build_artifacts.py`.

## Cross-file reference updates

- `docs_app/pages/home.py`: `Home` → `HomeContent` (import + call site).
- `docs_app/app.py`: `Root` → `DocsRoot`.
- `docs_app/layout/__init__.py`: `Navbar` → `DocsNavbar`.
- `docs_app/pages/demo/teleport.py`, `pages/demo/transition.py`, `pages/not_found.py`,
  `templates/home.py`: `Section` → `DocsSection`.
- `docs_app/pages/document/home.py`, `components/demo_display.py`: `Card` → `DocsCard`.
- `e2e/core/my_app/app.py`: `Root` → `AppRoot`.
- `packages/webcompy-cli/src/webcompy_cli/template_data/app/app.py`: `Root` → `AppRoot`.
- `packages/webcompy-cli/src/webcompy_cli/template_data/app/router.py`:
  `Home` → `HomePage`, `Fizzbuzz` → `FizzbuzzPage`.
- `tests/test_docs_demos.py`: demo component imports renamed (`HelloWorldApp` etc.),
  kept local alias `App` for call sites.
