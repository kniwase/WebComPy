from __future__ import annotations

import html as html_module
import json
from logging import getLogger
from typing import TYPE_CHECKING, TypeAlias, cast

from webcompy.app._config import _LOADING_DEFAULTS, PluginScript
from webcompy.components._component import Component, _active_app_context, _set_app_instance
from webcompy.di import inject
from webcompy.elements.typealias import ElementChildren
from webcompy.elements.types import Element
from webcompy.elements.types._base import ElementWithChildren
from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY, DOM_PORT_KEY

if TYPE_CHECKING:
    from webcompy.app._render_context import RenderContext

_logger = getLogger(__name__)

Scripts: TypeAlias = list[tuple[dict[str, str], str | None]]

PYSCRIPT_VERSION = "2026.3.1"
PYSCRIPT_BASE_URL = f"https://pyscript.net/releases/{PYSCRIPT_VERSION}"


class _DummyParent:
    def __init__(self, node) -> None:
        self._node = node

    def _get_node(self):
        return self._node

    def _get_belonging_component(self):
        return ""

    def _get_belonging_components(self):
        return ()

    def _re_index_children(self, recursive):
        pass


class _HtmlElement(Element):
    def __init__(
        self,
        tag_name: str,
        attrs: dict[str, str],
        *children: ElementChildren,
    ) -> None:
        super().__init__(
            tag_name,  # type: ignore
            attrs,  # type: ignore
            {},
            None,
            children,
        )

    async def render_html(self):
        port = inject(DOM_PORT_KEY)
        root_node = port.create_element("div")
        root_node.__webcompy_node__ = False
        root_node.__webcompy_prerendered_node__ = True
        self._parent = cast("ElementWithChildren", _DummyParent(root_node))
        self._node_idx = 0
        self._clear_node_cache()
        await self._render()
        root_child = root_node.childNodes[0] if root_node.childNodes.length > 0 else None
        if root_child is None:
            return ""
        return port.render_html(root_child)

    def _get_belonging_component(self):
        return ""

    def _get_belonging_components(self) -> tuple[Component, ...]:
        return tuple([])


class _Loadscreen(_HtmlElement):
    def __init__(self, loading: dict) -> None:
        delay_ms = loading["reveal_delay_ms"]
        fade_ms = loading["fade_out_ms"]
        children: list[ElementChildren] = [
            _HtmlElement("style", {}, _render_css_block(self._style)),
            _HtmlElement("div", {"class": "wc-loader"}),
        ]
        if loading["stages"]:
            children.append(
                _HtmlElement(
                    "div",
                    {"class": "wc-status"},
                    _HtmlElement("span", {"data-wc-status": ""}),
                    _HtmlElement("span", {"data-wc-substatus": "", "aria-hidden": "true"}),
                )
            )
        children.append(
            _HtmlElement(
                "div",
                {"class": "wc-timeout", "data-wc-timeout": "", "hidden": ""},
                _HtmlElement("span", {}, "Taking longer than usual… "),
                _HtmlElement("button", {"class": "wc-reload", "data-wc-reload": ""}, "Reload"),
            )
        )
        super().__init__(
            "div",
            {
                "id": "webcompy-loading",
                "role": "status",
                "data-wc-fade": str(fade_ms),
                "style": f"--wc-delay:{delay_ms}ms;--wc-fade:{fade_ms}ms",
            },
            *children,
        )

    @property
    def _style(self):
        return {
            "#webcompy-loading": {
                "position": "fixed",
                "inset": "0",
                "display": "flex",
                "flex-direction": "column",
                "align-items": "center",
                "justify-content": "center",
                "gap": "16px",
                "background": "var(--wc-backdrop, rgba(0, 0, 0, 0.15))",
                "z-index": "9999",
            },
            "#webcompy-loading [hidden]": {"display": "none"},
            ".wc-loader": {
                "opacity": "0",
                "width": "40px",
                "height": "40px",
                "border": "3px solid",
                "border-color": "light-dark(#d3d3d3, #4b5563)",
                "border-top-color": "light-dark(#87ceeb, #7dd3fc)",
                "border-radius": "50%",
                "animation": "wc-spin 0.8s linear infinite, wc-reveal 0.01s linear var(--wc-delay, 350ms) forwards",
            },
            ".wc-status": {
                "opacity": "0",
                "animation": "wc-reveal 0.01s linear var(--wc-delay, 350ms) forwards",
                "text-align": "center",
                "color": "light-dark(#333333, #cccccc)",
                "font-family": "system-ui, sans-serif",
                "font-size": "14px",
                "min-height": "1.5em",
            },
            ".wc-substatus": {
                "display": "block",
                "font-size": "12px",
                "opacity": "0.7",
            },
            ".wc-timeout": {
                "color": "light-dark(#333333, #cccccc)",
                "font-family": "system-ui, sans-serif",
                "font-size": "14px",
            },
            ".wc-reload": {
                "background": "none",
                "border": "none",
                "padding": "0",
                "color": "light-dark(#1d4ed8, #7dd3fc)",
                "text-decoration": "underline",
                "cursor": "pointer",
                "font": "inherit",
            },
            "html[data-theme='dark'] .wc-loader": {
                "--wc-ring": "#4b5563",
                "--wc-accent": "#7dd3fc",
            },
            "html[data-theme='dark'] #webcompy-loading": {
                "background": "rgba(0, 0, 0, 0.35)",
            },
            "@keyframes wc-spin": {
                "0%": {
                    "transform": "rotate(0deg)",
                },
                "100%": {
                    "transform": "rotate(360deg)",
                },
            },
            "@keyframes wc-reveal": {
                "to": {
                    "opacity": "1",
                },
            },
            "#webcompy-loading.wc-fading": {
                "opacity": "0 !important",
                "transition": "opacity var(--wc-fade, 250ms) ease",
            },
            "@media (prefers-reduced-motion: reduce)": {
                ".wc-loader": {
                    "animation": "wc-reveal 0.01s linear var(--wc-delay, 350ms) forwards",
                },
                ".wc-status": {
                    "animation": "wc-reveal 0.01s linear var(--wc-delay, 350ms) forwards",
                },
                "#webcompy-loading.wc-fading": {
                    "transition": "none",
                },
            },
        }


def _render_css_block(style: dict) -> str:
    return " ".join(
        f"{selector}{{"
        + "".join(
            name
            + (
                "{{{}}}".format("".join(f"{n}:{v};" for n, v in value.items()))
                if isinstance(value, dict)
                else f":{value};"
            )
            for name, value in props.items()
        )
        + "}"
        for selector, props in style.items()
    )


def _resolve_loading_config(config: dict | None) -> dict:
    merged = dict(_LOADING_DEFAULTS)
    if config:
        merged.update(config)
    return merged


_LOADING_DEFAULT_MESSAGES = {
    "runtime_prepare": "Preparing Python runtime…",
    "runtime_download": "Downloading Python runtime…",
    "packages": "Installing packages…",
    "runtime_ready": "Runtime ready…",
    "app_start": "Starting app…",
}

_LOADING_STAGE_CEILINGS = {
    "runtime_prepare": 35,
    "runtime_download": 60,
    "packages": 85,
    "runtime_ready": 93,
    "app_start": 97,
}

_LOADING_STAGE_EVENTS = [
    ("Loading Pyodide", "runtime_prepare"),
    ("Loading interpreter", "runtime_download"),
    ("Loaded interpreter", "packages"),
    ("Loaded Pyodide", "runtime_ready"),
]

_LOADING_CONTROLLER_TEMPLATE = """(function () {
  var root = document.getElementById("webcompy-loading");
  if (!root) return;
  var CONFIG = __WC_CONFIG__;
  var STAGES = __WC_STAGES__;
  var CEILINGS = __WC_CEILINGS__;
  var FIXED_CEILING = 97;
  var statusEl = root.querySelector("[data-wc-status]");
  var substatusEl = root.querySelector("[data-wc-substatus]");
  var barEl = root.querySelector("[data-wc-bar]");
  var timeoutEl = root.querySelector("[data-wc-timeout]");
  var reloadEl = root.querySelector("[data-wc-reload]");
  var stage = -1;
  var progress = 0;
  var start = Date.now();
  var watchdog = null;

  function setStatus(key) {
    stage = key;
    if (!CONFIG.stages) return;
    if (statusEl) statusEl.textContent = (CONFIG.messages && CONFIG.messages[key]) || key;
  }

  function setSub(text) {
    if (!CONFIG.stages || !substatusEl) return;
    substatusEl.textContent = text;
  }

  function setBar(value) {
    if (!barEl) return;
    if (value <= progress) return;
    progress = value;
    barEl.style.setProperty("--wc-progress", String(value / 100));
  }

  function resetWatchdog() {
    if (!CONFIG.timeoutSeconds) return;
    if (watchdog) clearTimeout(watchdog);
    watchdog = setTimeout(function () {
      if (timeoutEl && timeoutEl.hidden) timeoutEl.hidden = false;
    }, CONFIG.timeoutSeconds * 1000);
  }

  function onProgress(e) {
    var detail = e.detail;
    if (typeof detail !== "string") return;
    if (CONFIG.stages) {
      for (var i = 0; i < STAGES.length; i++) {
        if (STAGES[i][0] === detail) {
          setStatus(STAGES[i][1]);
          setBar(CEILINGS[STAGES[i][1]]);
          resetWatchdog();
          return;
        }
      }
      setSub(detail);
    }
    resetWatchdog();
  }

  function onReady() {
    setStatus("app_start");
    setBar(CEILINGS.app_start);
    resetWatchdog();
  }

  if (CONFIG.stages) {
    window.addEventListener("py:progress", onProgress);
    window.addEventListener("py:ready", onReady);
  } else {
    window.addEventListener("py:progress", resetWatchdog);
  }

  if (reloadEl) {
    reloadEl.addEventListener("click", function () {
      window.location.reload();
    });
  }

  function trickle() {
    if (root.hasAttribute("data-wc-complete")) return;
    var ceiling;
    if (CONFIG.stages) {
      ceiling = stage >= 0 ? CEILINGS[STAGES[stage][1]] : CEILINGS.runtime_prepare;
    } else {
      ceiling = FIXED_CEILING;
    }
    var elapsed = (Date.now() - start) / 1000;
    var target = ceiling * (2 / Math.PI) * Math.atan(elapsed / 6);
    setBar(target);
    requestAnimationFrame(trickle);
  }

  resetWatchdog();
  trickle();
})();"""


def _loading_controller_script(loading: dict) -> str:
    messages = dict(_LOADING_DEFAULT_MESSAGES)
    if loading["stages"]:
        messages.update(loading.get("messages") or {})
    config = {
        "stages": loading["stages"],
        "timeoutSeconds": loading["timeout_seconds"],
    }
    if loading["stages"]:
        config["messages"] = messages
    payload = json.dumps(config, ensure_ascii=False).replace("</", "<\\/")
    stages_payload = json.dumps(_LOADING_STAGE_EVENTS).replace("</", "<\\/")
    ceilings_payload = json.dumps(_LOADING_STAGE_CEILINGS).replace("</", "<\\/")
    return (
        _LOADING_CONTROLLER_TEMPLATE.replace("__WC_CONFIG__", payload)
        .replace("__WC_STAGES__", stages_payload)
        .replace("__WC_CEILINGS__", ceilings_payload)
    )


def _load_scripts(scripts: Scripts):
    return [
        _HtmlElement(
            "script",
            attrs,
            script,
        )
        for attrs, script in scripts
    ]


def _render_plugin_script(ps: PluginScript) -> _HtmlElement:
    if ps.condition is None:
        return _HtmlElement("script", ps.attrs, ps.script)
    target = "document.head" if ps.in_head else "document.body"
    if "src" in ps.attrs:
        js_parts: list[str] = [
            "(function(){",
            f"  if ({ps.condition}) {{",
            "    var __wc_s = document.createElement('script');",
        ]
        for key, value in ps.attrs.items():
            escaped = json.dumps(value)
            js_parts.append(f"    __wc_s.setAttribute({json.dumps(key)}, {escaped});")
        if ps.script:
            js_parts.append(f"    __wc_s.onload = function() {{ {ps.script} }};")
        js_parts.append(f"    {target}.appendChild(__wc_s);")
        js_parts.extend(["  }", "})();"])
        return _HtmlElement("script", {}, "\n".join(js_parts))
    if not ps.script:
        return _HtmlElement("script", {})
    js_parts = [
        "(function(){",
        f"  if ({ps.condition}) {{",
        f"    {ps.script}",
        "  }",
        "})();",
    ]
    return _HtmlElement("script", {}, "\n".join(js_parts))


async def generate_html(
    ctx: RenderContext,
    app_package_name: str,
    dev_mode: bool,
    prerender: bool,
    wheel_filename: str,
    pyodide_package_names: list[str] | None = None,
    wasm_local_urls: dict[str, str] | None = None,
    lockfile_url: str | None = None,
    runtime_serving: str = "cdn",
    extra_wheel_filenames: list[str] | None = None,
):
    token = _active_app_context.set(ctx)
    _set_app_instance(ctx)
    try:
        html_output, app_loader_html = await _generate_html_impl(
            ctx,
            app_package_name,
            dev_mode,
            prerender,
            wheel_filename,
            pyodide_package_names,
            wasm_local_urls,
            lockfile_url,
            runtime_serving,
            extra_wheel_filenames,
        )
        scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
        await scheduler.await_pending()
        if prerender and ctx._root is not None:
            try:
                payload_json = ctx._root._collect_transfer_data()
                data_script = f'<script type="application/json" id="__webcompy_data__">{payload_json}</script>'
                html_output = html_output.replace(
                    "</body>",
                    f"{data_script}\n{app_loader_html}</body>",
                )
            except Exception as e:
                _logger.warning("Failed to inject hydration data payload: %s", e)
                html_output = html_output.replace("</body>", f"{app_loader_html}</body>")
        else:
            html_output = html_output.replace("</body>", f"{app_loader_html}</body>")
        return html_output
    finally:
        _active_app_context.reset(token)
        _set_app_instance(None)


async def _generate_html_impl(
    ctx: RenderContext,
    app_package_name: str,
    dev_mode: bool,
    prerender: bool,
    wheel_filename: str,
    pyodide_package_names: list[str] | None = None,
    wasm_local_urls: dict[str, str] | None = None,
    lockfile_url: str | None = None,
    runtime_serving: str = "cdn",
    extra_wheel_filenames: list[str] | None = None,
):
    app = ctx._app
    base_url = ctx.config.base_url
    selector_id = ctx.config.selector.lstrip("#")
    loading_config = _resolve_loading_config(ctx.config.loading)
    app_root = (
        ctx._root
        if prerender
        else _HtmlElement(
            "div",
            {"id": selector_id, "hidden": ""},
        )
    )
    scripts_head: Scripts = []
    scripts_body: Scripts = []

    core_js_url = (
        f"{base_url}_webcompy-assets/core.js" if runtime_serving == "local" else f"{PYSCRIPT_BASE_URL}/core.js"
    )
    core_css_url = (
        f"{base_url}_webcompy-assets/core.css" if runtime_serving == "local" else f"{PYSCRIPT_BASE_URL}/core.css"
    )

    scripts_head.append(
        (
            {
                "type": "module",
                "src": core_js_url,
            },
            None,
        )
    )

    app_wheel_url = f"{base_url}_webcompy-app-package/{wheel_filename}"
    py_packages = [app_wheel_url]
    if extra_wheel_filenames:
        for name in extra_wheel_filenames:
            py_packages.insert(0, f"{base_url}_webcompy-app-package/{name}")
    for name in pyodide_package_names or []:
        if wasm_local_urls and name in wasm_local_urls:
            py_packages.append(wasm_local_urls[name])
        else:
            py_packages.append(name)
    py_config_dict: dict = {"packages": py_packages, "experimental_create_proxy": "auto"}
    if runtime_serving == "local":
        py_config_dict["interpreter"] = f"{base_url}_webcompy-assets/pyodide/pyodide.mjs"
        py_config_dict["lockFileURL"] = f"{base_url}_webcompy-assets/pyodide/pyodide-lock.json"
    elif lockfile_url is not None:
        py_config_dict["lockFileURL"] = lockfile_url
    py_config = html_module.escape(
        json.dumps(py_config_dict),
        quote=True,
    )
    py_script_lines: list[str] = []
    if ctx.config.profile:
        py_script_lines.append("import time")
        py_script_lines.append("_pyscript_ready = time.perf_counter()")
    py_script_lines.append(f"from {app_package_name}.app import app")
    if ctx.config.profile:
        py_script_lines.append('app._profile_data["pyscript_ready"] = _pyscript_ready')
    py_script_lines.append("app.run()")
    py_script = "\n".join(py_script_lines)
    app_loader_html = f'<script type="py" config="{py_config}">\n{py_script}\n</script>'

    scripts_head.extend(ctx.head["script"])
    scripts_body.extend(ctx.scripts)
    plugin_head_scripts: list[_HtmlElement] = []
    plugin_body_scripts: list[_HtmlElement] = []
    for ps in ctx.config.scripts:
        (plugin_head_scripts if ps.in_head else plugin_body_scripts).append(_render_plugin_script(ps))
    for ps in app._plugin_manager.scripts:
        (plugin_head_scripts if ps.in_head else plugin_body_scripts).append(_render_plugin_script(ps))
    if dev_mode:
        scripts_body.append(
            (
                {"type": "text/javascript"},
                " ".join(
                    (
                        f"var stream = new EventSource('{ctx.config.base_url}_webcompy_reload');",
                        "stream.addEventListener('error', (e) => window.location.reload());",
                    )
                ),
            )
        )

    assert ctx._root is not None
    head_content_html = ctx._root._head_element.get_head_content_html()
    scoped_styles_html = ctx._root._head_element.get_scoped_styles_html()

    index_css_link_html = (
        f'<link rel="stylesheet" href="{html_module.escape(base_url, quote=True)}_webcompy-ui/index.css">'
    )

    html_output = "<!doctype html>" + (
        await _HtmlElement(
            "html",
            ctx._root.html_attrs,
            _HtmlElement(
                "head",
                {},
                _HtmlElement("base", {"href": ctx.config.base_url}),
                _HtmlElement("meta", {"name": "color-scheme", "content": "light dark"}),
                _HtmlElement(
                    "link",
                    {"rel": "stylesheet", "href": f"{base_url}_webcompy-ui/index.css"},
                ),
                _HtmlElement(
                    "link",
                    {"rel": "stylesheet", "href": core_css_url},
                ),
                *_load_scripts(scripts_head),
                *plugin_head_scripts,
            ),
            _HtmlElement(
                "body",
                {},
                _Loadscreen(loading_config),
                _HtmlElement("script", {}, _loading_controller_script(loading_config)),
                app_root,
                *_load_scripts(scripts_body),
                *plugin_body_scripts,
            ),
        ).render_html()
    )

    html_output = html_output.replace("<head>", f"<head>\n{head_content_html}", 1)
    if scoped_styles_html:
        assert index_css_link_html in html_output
        html_output = html_output.replace(
            index_css_link_html,
            f"{index_css_link_html}\n{scoped_styles_html}",
            1,
        )
    return html_output, app_loader_html
