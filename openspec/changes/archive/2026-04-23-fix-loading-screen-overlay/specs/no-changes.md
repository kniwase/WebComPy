No new capabilities introduced and no existing spec requirements are changing.

This change is an internal implementation fix within the CLI HTML generation layer (`_Loadscreen`). It does not alter any developer-facing behavior described in existing spec documents. The loading screen overlay still appears during PyScript initialization and is still removed via the same `#webcompy-loading` ID. Only the internal DOM structure and CSS class names change.
