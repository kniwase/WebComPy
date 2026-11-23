---
title: Guides Overview
description: Build a complete six-step ToDo application with WebComPy, covering reactive state, components, routing, forms, remote data, and static deployment.
---

# Guides Overview

This tutorial builds one **ToDo application** from scratch across six sequential steps. By the end, you will have a working single-page app with reactive filtering, reusable components, hash-routed views, validated forms, async HTTP loading, error recovery, and a static production bundle.

Each step runs a live interactive PyScript demo and shows its full standalone `app.py` source at the bottom of the page, so you can read and test every milestone independently.

## Prerequisites

- Completed [Quickstart](/documents/getting-started/quickstart) and [Project Structure](/documents/getting-started/project-structure)
- A local project created with `webcompy init` and dependencies installed via `uv sync`

## Tutorial roadmap

| Step | Topic | What the app gains | Time |
|---|---|---|---|
| 1 | [Step 1: App Shell](/documents/guides/todo-app-shell) | Seeded tasks in a `ReactiveList`, filter state, `use_computed`, `repeat(..., key=...)` | ~10 min |
| 2 | [Step 2: Components](/documents/guides/todo-components) | Extracted `TodoItem` and `TodoToolbar` components using props and slots | ~10 min |
| 3 | [Step 3: Navigation](/documents/guides/todo-navigation) | Flat `Router` (`/`, `/active`, `/done`), `RouterLink` active styling, and `RouterView` | ~10 min |
| 4 | [Step 4: Forms](/documents/guides/todo-forms) | Add-task form with `use_field`, validators, `use_form`, `FormField`, `Input`, and `Checkbox` | ~15 min |
| 5 | [Step 5: Remote Data](/documents/guides/todo-remote-data) | Typed `HttpClient` requests, `use_async_result` loading/error UI, and an in-app `FetchMiddleware` mock | ~15 min |
| 6 | [Step 6: Deploy](/documents/guides/todo-deploy) | `ErrorBoundary` recovery and static build output with `webcompy generate` | ~10 min |

## How each step builds on the last

1. **Shell first, interactivity second**: Start by proving that reactive collections and derived counts render cleanly before adding child components or routes.
2. **Basic-tier APIs throughout**: Every step stays within core WebComPy primitives (`webcompy.signal`, `webcompy.components`, `webcompy.elements`, `webcompy.router`, `webcompy.forms`, `webcompy.ui`, and `webcompy.ajax`), except Step 5's compact client-side `FetchMiddleware` mock so remote requests work identically on static hosting.
3. **Self-contained demos**: Every step embeds a runnable iframe backed by its own `app.py` file and finishes with links to deeper reference pages.

## Next steps

- Start building the app shell in [Step 1: App Shell](/documents/guides/todo-app-shell).
