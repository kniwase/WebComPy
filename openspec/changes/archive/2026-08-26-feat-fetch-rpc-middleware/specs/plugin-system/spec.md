# Delta: plugin-system

## ADDED Requirements

### Requirement: Plugins may declare fetch and RPC middlewares

`WebComPyPlugin` SHALL expose optional `get_fetch_middlewares()` and `get_rpc_middlewares()` hooks returning lists of middlewares. `PluginManager` SHALL aggregate hook results across plugin classes in `AppConfig.plugins` declaration order and register them on the corresponding middleware registries during render-context initialization, before chain assembly. The hooks are additive sugar over the registries and SHALL NOT interfere with `get_providers`.

#### Scenario: Hook aggregation order matches declaration order

- **WHEN** `AppConfig.plugins = ["a:A", "b:B"]` and each declares one middleware
- **THEN** the registry contains A's middleware before B's middleware

#### Scenario: Default hooks are inert

- **WHEN** a plugin does not override the new hooks
- **THEN** no middleware is registered on its behalf
