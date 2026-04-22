# CLI — Delta: feat-hydration-partial

## Changes

### Updated: Loading screen shall be semi-transparent

The generated loading screen overlay (`#webcompy-loading`) SHALL use a semi-transparent dark background (e.g., `rgba(0, 0, 0, 0.5)`) instead of an opaque background. This allows pre-rendered content to be visible during the hydration phase, giving the user an immediate visual indication that content is loading and enabling developers to observe the hydration process.