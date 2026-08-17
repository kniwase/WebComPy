from __future__ import annotations

import html as html_module
import json
import re
from logging import getLogger
from pathlib import Path
from typing import TYPE_CHECKING, TypeAlias, cast

from webcompy.app._config import _LOADING_DEFAULTS, PluginScript
from webcompy.components._component import Component, _active_app_context, _set_app_instance
from webcompy.di import inject
from webcompy.elements.typealias import ElementChildren
from webcompy.elements.types import Element
from webcompy.elements.types._base import ElementWithChildren
from webcompy.exception import WebComPyException
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
    def __init__(self, mode: str, structure: str, loading: dict) -> None:
        delay_ms = loading["reveal_delay_ms"]
        fade_ms = loading["fade_out_ms"]
        children: list[ElementChildren] = []
        if structure == "bar":
            children.append(
                _HtmlElement(
                    "div",
                    {"class": "wc-bar"},
                    _HtmlElement("div", {"class": "wc-bar-fill", "data-wc-bar": ""}),
                )
            )
        elif structure == "splash":
            children.append(
                _HtmlElement(
                    "div",
                    {"class": "wc-splash"},
                    _HtmlElement("div", {"class": "wc-splash-logo", "aria-hidden": "true"}),
                )
            )
        else:
            children.append(_HtmlElement("div", {"class": "wc-loader"}))
        if loading["stages"]:
            children.append(
                _HtmlElement(
                    "div",
                    {"class": "wc-status"},
                    _HtmlElement("span", {"data-wc-status": ""}),
                    _HtmlElement(
                        "span",
                        {"class": "wc-substatus", "data-wc-substatus": "", "aria-hidden": "true"},
                    ),
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
        attrs: dict[str, str] = {
            "id": "webcompy-loading",
            "role": "status",
            "data-wc-mode": mode,
            "data-wc-fade": str(fade_ms),
            "style": f"--wc-delay:{delay_ms}ms;--wc-fade:{fade_ms}ms",
        }
        if mode == "content":
            attrs["data-wc-interaction"] = loading["interaction"]
        super().__init__("div", attrs, *children)


_LOADING_BASE_CSS = (
    "#webcompy-loading{position:fixed;inset:0;display:flex;flex-direction:column;align-items:center;"
    "justify-content:center;gap:16px;background:var(--wc-backdrop, rgba(0, 0, 0, 0.15));z-index:9999;} "
    "#webcompy-loading[data-wc-mode='content']{background:transparent;} "
    "#webcompy-loading[data-wc-mode='content'][data-wc-interaction='passthrough']{pointer-events:none;} "
    "#webcompy-loading [hidden]{display:none;} "
    ".wc-bar{position:fixed;top:0;left:0;right:0;height:3px;opacity:0;"
    "animation:wc-reveal 0.01s linear var(--wc-delay, 350ms) forwards;} "
    ".wc-bar-fill{height:100%;background:var(--wc-accent, var(--color-accent, light-dark(#1d4ed8, #7dd3fc)));"
    "transform:scaleX(var(--wc-progress, 0));transform-origin:left top;transition:transform 0.2s ease;} "
    "#webcompy-loading[data-wc-complete] .wc-bar-fill{transform:scaleX(1);} "
    ".wc-loader{opacity:0;width:40px;height:40px;border:3px solid;"
    "border-color:var(--wc-ring, var(--color-border, light-dark(#d3d3d3, #4b5563)));"
    "border-top-color:var(--wc-accent, var(--color-accent, light-dark(#87ceeb, #7dd3fc)));"
    "border-radius:50%;animation:wc-spin 0.8s linear infinite, "
    "wc-reveal 0.01s linear var(--wc-delay, 350ms) forwards;} "
    ".wc-splash{display:flex;flex-direction:column;align-items:center;gap:8px;opacity:0;"
    "animation:wc-reveal 0.01s linear var(--wc-delay, 350ms) forwards;} "
    ".wc-splash-logo{width:48px;height:48px;border-radius:12px;"
    "background:var(--color-bg-elevated, light-dark(#e5e7eb, #374151));} "
    ".wc-status{opacity:0;animation:wc-reveal 0.01s linear var(--wc-delay, 350ms) forwards;"
    "text-align:center;color:var(--wc-fg, var(--color-fg, light-dark(#333333, #cccccc)));font-family:system-ui, sans-serif;"
    "font-size:14px;min-height:1.5em;} "
    "#webcompy-loading[data-wc-mode='content'] .wc-status{position:fixed;left:16px;bottom:16px;text-align:left;} "
    ".wc-substatus{display:block;font-size:12px;opacity:0.7;} "
    ".wc-timeout{color:var(--wc-fg, var(--color-fg, light-dark(#333333, #cccccc)));font-family:system-ui, sans-serif;"
    "font-size:14px;pointer-events:auto;} "
    ".wc-reload{background:none;border:none;padding:0;color:var(--wc-accent, var(--color-accent, light-dark(#1d4ed8, #7dd3fc)));"
    "text-decoration:underline;cursor:pointer;font:inherit;} "
    "html[data-theme='dark'] .wc-loader{--wc-ring:#4b5563;--wc-accent:#7dd3fc;} "
    "html[data-theme='dark'] .wc-status{--wc-fg:#cccccc;} "
    "html[data-theme='dark'] .wc-timeout{--wc-fg:#cccccc;} "
    "html[data-theme='dark'] .wc-reload{--wc-accent:#7dd3fc;} "
    "html[data-theme='dark'] #webcompy-loading[data-wc-mode='overlay']{background:rgba(0, 0, 0, 0.35);} "
    "@keyframes wc-spin{0%{transform:rotate(0deg);}100%{transform:rotate(360deg);}} "
    "@keyframes wc-reveal{to{opacity:1;}} "
    "@keyframes wc-dormant-in{to{opacity:var(--wc-dormant-opacity, 0.9);"
    "filter:saturate(var(--wc-dormant-saturation, 0.85));}} "
    "body.wc-booting #webcompy-app{animation:wc-dormant-in 0.01s linear var(--wc-delay, 350ms) forwards;} "
    "body:is(.wc-booting, .wc-waking) #webcompy-app{transition:opacity 0.3s ease, filter 0.3s ease;} "
    "body.wc-waking #webcompy-app{animation:none;opacity:1;filter:none;} "
    "#webcompy-loading.wc-fading{opacity:0 !important;transition:opacity var(--wc-fade, 250ms) ease;} "
    "@media (prefers-reduced-motion: reduce){"
    ".wc-loader{animation:wc-reveal 0.01s linear var(--wc-delay, 350ms) forwards;}"
    ".wc-status{animation:wc-reveal 0.01s linear var(--wc-delay, 350ms) forwards;}"
    ".wc-bar-fill{transition:none;}"
    "body:is(.wc-booting, .wc-waking) #webcompy-app{transition:none;}"
    "#webcompy-loading.wc-fading{transition:none;}}"
)


def _loading_base_css(loading: dict, selector: str) -> str:
    return (
        _LOADING_BASE_CSS.replace("var(--wc-delay, 350ms)", f"var(--wc-delay, {loading['reveal_delay_ms']}ms)")
        .replace("var(--wc-fade, 250ms)", f"var(--wc-fade, {loading['fade_out_ms']}ms)")
        .replace("#webcompy-app", selector)
    )


_LOADING_STRUCTURES = {"overlay": "spinner", "bar": "bar", "splash": "splash"}

_LOADING_TEMPLATE_HOOKS = ("data-wc-status", "data-wc-substatus", "data-wc-bar", "data-wc-timeout", "data-wc-reload")

_LOADING_TEMPLATE_MARKER = '<div id="webcompy-loading" data-wc-template-marker=""></div>'


def _loading_structure(loading: dict, mode: str) -> str:
    template = loading["template"]
    if template in _LOADING_STRUCTURES:
        return _LOADING_STRUCTURES[template]
    return "bar" if mode == "content" else "spinner"


def _resolve_loading_template(template: str | None, app_package_path: Path | None) -> str | None:
    if template is None or template in _LOADING_STRUCTURES:
        return None
    if template.lstrip().startswith("<"):
        return template
    base = app_package_path or Path.cwd()
    path = base / template
    if not path.is_file():
        raise WebComPyException(f"Loading template file not found: {path}")
    return path.read_text(encoding="utf-8")


def _validate_loading_template(template_html: str) -> None:
    matches = re.findall(r'id\s*=\s*["\']webcompy-loading["\']', template_html)
    if len(matches) != 1:
        raise WebComPyException(
            f'Custom loading template must contain exactly one element with id="webcompy-loading", found {len(matches)}'
        )
    if not any(hook in template_html for hook in _LOADING_TEMPLATE_HOOKS):
        _logger.warning("Custom loading template contains no documented hooks; progress plumbing will not drive it")


def _find_tag_end(html: str, start: int) -> int:
    quote: str | None = None
    for i in range(start, len(html)):
        char = html[i]
        if quote is not None:
            if char == quote:
                quote = None
        elif char in ('"', "'"):
            quote = char
        elif char == ">":
            return i
    return -1


def _inject_loading_template_attrs(template_html: str, loading: dict, mode: str) -> str:
    match = re.search(r'id\s*=\s*["\']webcompy-loading["\']', template_html)
    if match is None:
        raise WebComPyException('Custom loading template must contain exactly one element with id="webcompy-loading"')
    tag_end = _find_tag_end(template_html, match.end())
    if tag_end == -1:
        raise WebComPyException("Custom loading template contains an unclosed #webcompy-loading tag")
    tag = template_html[:tag_end]
    injections: list[str] = []
    if not re.search(r"role\s*=", tag):
        injections.append('role="status"')
    if "data-wc-mode" not in tag:
        injections.append(f'data-wc-mode="{mode}"')
    if mode == "content" and "data-wc-interaction" not in tag:
        injections.append(f'data-wc-interaction="{loading["interaction"]}"')
    if "data-wc-fade" not in tag:
        injections.append(f'data-wc-fade="{loading["fade_out_ms"]}"')
    if "style" not in tag:
        injections.append(f'style="--wc-delay:{loading["reveal_delay_ms"]}ms;--wc-fade:{loading["fade_out_ms"]}ms"')
    if not injections:
        return template_html
    return template_html[: match.end()] + " " + " ".join(injections) + template_html[match.end() :]


def _resolve_loading_config(config: dict | None) -> dict:
    merged = dict(_LOADING_DEFAULTS)
    if config:
        merged.update(config)
    merged["messages"] = dict(merged["messages"])
    return merged


def _resolve_loading_mode(loading: dict, prerender: bool) -> str:
    if loading["mode"] == "auto":
        return "content" if prerender else "overlay"
    return loading["mode"]


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
  if (root.hasAttribute("data-wc-fade")) {
    root.style.setProperty("--wc-fade", root.getAttribute("data-wc-fade") + "ms");
  }
  var CONFIG = __WC_CONFIG__;
  var STAGES = __WC_STAGES__;
  var CEILINGS = __WC_CEILINGS__;
  var FIXED_CEILING = 97;
  var statusEl = root.querySelector("[data-wc-status]");
  var substatusEl = root.querySelector("[data-wc-substatus]");
  var barEl = root.querySelector("[data-wc-bar]");
  var timeoutEl = root.querySelector("[data-wc-timeout]");
  var reloadEl = root.querySelector("[data-wc-reload]");
  if (timeoutEl) timeoutEl.hidden = true;
  var STAGE_KEYS = Object.keys(CEILINGS);
  var ceiling = CONFIG.stages ? CEILINGS.runtime_prepare : FIXED_CEILING;
  var progress = 0;
  var start = Date.now();
  var watchdog = null;
  var showSub = false;
  var reducedMotion = !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);

  function setStage(key) {
    var index = STAGE_KEYS.indexOf(key);
    if (index > 0) setBar(CEILINGS[STAGE_KEYS[index - 1]]);
    ceiling = CEILINGS[key];
    showSub = key === "packages";
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
      if (timeoutEl && timeoutEl.hidden && !root.hasAttribute("data-wc-complete")) timeoutEl.hidden = false;
    }, CONFIG.timeoutSeconds * 1000);
  }

  function onProgress(e) {
    var detail = e.detail;
    if (typeof detail !== "string") return;
    if (CONFIG.stages) {
      for (var i = 0; i < STAGES.length; i++) {
        if (STAGES[i][0] === detail) {
          setStage(STAGES[i][1]);
          resetWatchdog();
          return;
        }
      }
      if (showSub) setSub(detail);
    }
    resetWatchdog();
  }

  function onReady() {
    setStage("app_start");
    resetWatchdog();
  }

  if (CONFIG.stages) {
    window.addEventListener("py:progress", onProgress);
    window.addEventListener("py:ready", onReady);
  } else {
    window.addEventListener("py:progress", resetWatchdog);
    window.addEventListener("py:ready", resetWatchdog);
  }

  if (reloadEl) {
    reloadEl.addEventListener("click", function () {
      window.location.reload();
    });
  }

  function applyMountState() {
    if (!CONFIG.selector) return;
    var mount = document.querySelector(CONFIG.selector);
    if (!mount) return;
    mount.setAttribute("aria-busy", "true");
    if (CONFIG.interaction === "inert") mount.setAttribute("inert", "");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", applyMountState);
  } else {
    applyMountState();
  }

  function trickle() {
    if (root.hasAttribute("data-wc-complete") || !root.isConnected || reducedMotion) return;
    var elapsed = (Date.now() - start) / 1000;
    var target = ceiling * (2 / Math.PI) * Math.atan(elapsed / 6);
    setBar(target);
    requestAnimationFrame(trickle);
  }

  resetWatchdog();
  if (CONFIG.stages) setStage("runtime_prepare");
  trickle();
})();"""


def _loading_controller_script(loading: dict, mode: str, selector: str) -> str:
    messages = dict(_LOADING_DEFAULT_MESSAGES)
    if loading["stages"]:
        messages.update(loading.get("messages") or {})
    config: dict = {
        "stages": loading["stages"],
        "timeoutSeconds": loading["timeout_seconds"],
        "selector": selector,
    }
    if mode == "content":
        config["interaction"] = loading["interaction"]
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
    app_package_path: Path | None = None,
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
            app_package_path,
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
    app_package_path: Path | None = None,
):
    app = ctx._app
    base_url = ctx.config.base_url
    selector_id = ctx.config.selector.lstrip("#")
    loading_config = _resolve_loading_config(ctx.config.loading)
    loading_mode = _resolve_loading_mode(loading_config, prerender)
    body_attrs: dict[str, str] = {}
    if loading_mode == "content" and loading_config["dormant"]:
        body_attrs["class"] = "wc-booting"
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

    custom_template = _resolve_loading_template(loading_config["template"], app_package_path)
    if custom_template is not None:
        _validate_loading_template(custom_template)
        custom_template = _inject_loading_template_attrs(custom_template, loading_config, loading_mode)
        loading_body: list[ElementChildren] = [
            _HtmlElement("style", {}, _loading_base_css(loading_config, ctx.config.selector)),
            _HtmlElement("div", {"id": "webcompy-loading", "data-wc-template-marker": ""}),
        ]
    else:
        loading_body = [
            _HtmlElement("style", {}, _loading_base_css(loading_config, ctx.config.selector)),
            _Loadscreen(
                loading_mode,
                _loading_structure(loading_config, loading_mode),
                loading_config,
            ),
        ]

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
                body_attrs,
                *loading_body,
                _HtmlElement(
                    "script",
                    {},
                    _loading_controller_script(loading_config, loading_mode, ctx.config.selector),
                ),
                app_root,
                *_load_scripts(scripts_body),
                *plugin_body_scripts,
            ),
        ).render_html()
    )

    if custom_template is not None:
        if _LOADING_TEMPLATE_MARKER not in html_output:
            raise WebComPyException(
                "Failed to inject custom loading template: contract marker not found in generated HTML"
            )
        html_output = html_output.replace(_LOADING_TEMPLATE_MARKER, custom_template)

    html_output = html_output.replace("<head>", f"<head>\n{head_content_html}", 1)
    if scoped_styles_html:
        assert index_css_link_html in html_output
        html_output = html_output.replace(
            index_css_link_html,
            f"{index_css_link_html}\n{scoped_styles_html}",
            1,
        )
    return html_output, app_loader_html
