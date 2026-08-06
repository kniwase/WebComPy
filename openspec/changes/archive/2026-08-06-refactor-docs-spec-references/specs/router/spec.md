## ADDED Requirements

### Requirement: RouterView shall subscribe through its own holder Computed

Each `RouterView` SHALL subscribe to `router.current_match` through its OWN holder `Computed` (`self._level_match = Computed(lambda: router.current_match.value)`) rather than registering directly on the shared `router.current_match`. The holder SHALL keep the view's subscription local to the view's lifetime — destroying the view SHALL destroy only its holder edge — and SHALL preserve per-view notification semantics.

#### Scenario: View destruction removes only its own subscription

- **WHEN** a `RouterView` is destroyed while other views at other depths remain mounted
- **THEN** the destroyed view's holder `Computed` edge SHALL be removed from `router.current_match`
- **AND** the remaining views' subscriptions SHALL continue to receive notifications
