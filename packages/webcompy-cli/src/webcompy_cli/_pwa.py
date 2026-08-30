"""Build-time Progressive Web App generation: manifest serialization, precache enumeration, and worker emission.

The framework owns the Service Worker implementation as a vanilla JS
template embedded in this module; the effective PWA configuration is
serialized into it at build time so the worker operates offline from its
first install without fetching any runtime configuration.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys
from dataclasses import asdict
from typing import TYPE_CHECKING

from webcompy.exception import WebComPyException

if TYPE_CHECKING:
    from webcompy_cli._build import BuildArtifacts
    from webcompy_cli.config._pwa_config import PWAConfig

MANIFEST_FILENAME = "manifest.webmanifest"
SW_FILENAME = "sw.js"
PWA_OUTPUT_NAMES = frozenset({MANIFEST_FILENAME, SW_FILENAME})
MANIFEST_MEDIA_TYPE = "application/manifest+json"
SW_MEDIA_TYPE = "application/javascript"
RUNTIME_ASSET_PREFIX = "_webcompy-assets/"

_DEFAULT_OFFLINE_HTML = (
    '<!doctype html><html><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width, initial-scale=1">'
    "<title>Offline</title>"
    "<style>body{font-family:system-ui,sans-serif;text-align:center;padding:15vmin 24px;color:#333}</style>"
    "</head><body><main><h1>You're offline</h1>"
    "<p>This page is not available without a network connection.</p>"
    "</main></body></html>"
)

_SW_TEMPLATE = """const CONFIG = __WC_PWA_CONFIG__;
const PREFIX = "webcompy-pwa-";
const PRECACHE_NAME = PREFIX + "v-" + CONFIG.version;
const SCOPE_PATH = self.location.pathname.replace(/[^/]*$/, "");
const cachedAt = new Map();

function resolveUrl(url) {
  return new URL(url, self.location.href);
}

function scopeRelative(pathname) {
  return pathname.indexOf(SCOPE_PATH) === 0 ? "/" + pathname.slice(SCOPE_PATH.length) : pathname;
}

function ruleCacheName(index) {
  return PREFIX + "r" + index + "-" + CONFIG.version;
}

function globToRegex(glob) {
  var source = "";
  for (var i = 0; i < glob.length; i++) {
    var char = glob[i];
    if (char === "*") {
      if (glob[i + 1] === "*") {
        source += ".*";
        i++;
      } else {
        source += "[^/]*";
      }
    } else if ("\\\\.[]{}()+-?^$|".indexOf(char) !== -1) {
      source += "\\\\" + char;
    } else {
      source += char;
    }
  }
  return new RegExp("^" + source + "$");
}

function matchRule(url) {
  var rules = CONFIG.runtime || [];
  var pathname = scopeRelative(url.pathname);
  for (var i = 0; i < rules.length; i++) {
    var pattern = rules[i].pattern;
    var matched = pattern.indexOf("*") !== -1
      ? globToRegex(pattern).test(pathname)
      : pathname.indexOf(pattern) === 0;
    if (matched) {
      var rule = {};
      for (var key in rules[i]) rule[key] = rules[i][key];
      rule.cacheName = ruleCacheName(i);
      return rule;
    }
  }
  return null;
}

function isFresh(request, rule) {
  if (!rule.maxAge) return true;
  var stored = cachedAt.get(request.url);
  if (stored === undefined) return true;
  return Date.now() - stored <= rule.maxAge * 1000;
}

async function trimCache(cache, rule) {
  if (!rule.maxEntries) return;
  var keys = await cache.keys();
  if (keys.length <= rule.maxEntries) return;
  var excess = keys.slice(0, keys.length - rule.maxEntries);
  for (var entry of excess) {
    cachedAt.delete(entry.url);
    await cache.delete(entry);
  }
}

async function store(cache, request, response, rule) {
  if (response && response.ok) {
    await cache.put(request, response.clone());
    cachedAt.set(request.url, Date.now());
    await trimCache(cache, rule);
  }
}

async function cacheFirst(request, rule) {
  var cache = await caches.open(rule.cacheName);
  var hit = await cache.match(request);
  if (hit && isFresh(request, rule)) return hit;
  try {
    var fresh = await fetch(request);
    await store(cache, request, fresh, rule);
    return fresh;
  } catch (err) {
    if (hit) return hit;
    throw err;
  }
}

async function networkFirst(request, rule) {
  var cache = await caches.open(rule.cacheName);
  try {
    var fresh = await fetch(request);
    await store(cache, request, fresh, rule);
    return fresh;
  } catch (err) {
    var hit = await cache.match(request);
    if (hit) return hit;
    throw err;
  }
}

async function staleWhileRevalidate(request, rule) {
  var cache = await caches.open(rule.cacheName);
  var hit = await cache.match(request);
  var update = fetch(request)
    .then(function (fresh) {
      return store(cache, request, fresh, rule).then(function () {
        return fresh;
      });
    })
    .catch(function () {
      return null;
    });
  if (hit && isFresh(request, rule)) return hit;
  var fresh = await update;
  if (fresh) return fresh;
  if (hit) return hit;
  return fetch(request);
}

function hasFileExtension(pathname) {
  return pathname.lastIndexOf(".") > pathname.lastIndexOf("/");
}

async function navigationMatch(request) {
  var hit = await caches.match(request, { ignoreSearch: true });
  if (hit) return hit;
  var pathname = new URL(request.url).pathname;
  if (hasFileExtension(pathname)) return undefined;
  return caches.match(pathname.replace(/\\/?$/, "/index.html"));
}

async function offlineResponse() {
  if (CONFIG.fallback) {
    var hit = await caches.match(CONFIG.fallback);
    if (hit) return hit;
  }
  return new Response(CONFIG.offlineHtml, {
    status: 200,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "X-WebComPy-Offline": "fallback",
    },
  });
}

async function handleRequest(request, url) {
  if (request.mode === "navigate") {
    var cached = await navigationMatch(request);
    if (cached) return cached;
    try {
      return await fetch(request);
    } catch (err) {
      return offlineResponse();
    }
  }
  var rule = matchRule(url);
  if (!rule) return fetch(request);
  if (rule.strategy === "network-first") return networkFirst(request, rule);
  if (rule.strategy === "stale-while-revalidate") return staleWhileRevalidate(request, rule);
  return cacheFirst(request, rule);
}

async function precacheEntry(cache, entry) {
  var target = resolveUrl(entry);
  var init = target.origin === self.location.origin ? undefined : { mode: "no-cors" };
  var response = await fetch(new Request(target.href, init));
  if (response.ok || response.type === "opaque") {
    await cache.put(target.href, response);
    return;
  }
  throw new Error("HTTP " + response.status);
}

async function installPrecache() {
  var cache = await caches.open(PRECACHE_NAME);
  var entries = (CONFIG.precache || []).map(function (entry) {
    return precacheEntry(cache, entry).catch(function (err) {
      console.warn("[webcompy-pwa] precache failed:", entry, err);
    });
  });
  await Promise.all(entries);
}

self.addEventListener("install", function (event) {
  event.waitUntil(installPrecache().then(function () {
    return self.skipWaiting();
  }));
});

self.addEventListener("activate", function (event) {
  var keep = [PRECACHE_NAME];
  var rules = CONFIG.runtime || [];
  for (var i = 0; i < rules.length; i++) keep.push(ruleCacheName(i));
  event.waitUntil(
    caches.keys().then(function (names) {
      return Promise.all(names.filter(function (name) {
        return name.indexOf(PREFIX) === 0 && keep.indexOf(name) === -1;
      }).map(function (name) {
        return caches.delete(name);
      }));
    }).then(function () {
      return self.clients.claim();
    })
  );
});

self.addEventListener("fetch", function (event) {
  var request = event.request;
  if (request.method !== "GET") return;
  var url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  event.respondWith(handleRequest(request, url));
});"""


def serialize_manifest(pwa: PWAConfig, base_url: str) -> str:
    """Serialize the PWA manifest configuration to Web App Manifest JSON.

    Args:
        pwa: PWA configuration whose ``manifest`` is serialized.
        base_url: Application base URL (normalized with surrounding
            slashes) used for ``start_url`` and ``scope`` defaults.

    Returns:
        The ``manifest.webmanifest`` document as a JSON string.

    Raises:
        WebComPyException: If no manifest is configured.

    """
    manifest = pwa.manifest
    if manifest is None:
        raise WebComPyException("serialize_manifest requires PWAConfig.manifest to be set")
    data: dict = {
        "name": manifest.name,
        "start_url": base_url if manifest.start_url is None else manifest.start_url,
        "scope": base_url if manifest.scope is None else manifest.scope,
        "display": manifest.display,
    }
    if manifest.short_name is not None:
        data["short_name"] = manifest.short_name
    if manifest.theme_color is not None:
        data["theme_color"] = manifest.theme_color
    if manifest.background_color is not None:
        data["background_color"] = manifest.background_color
    if manifest.icons:
        data["icons"] = [
            {key: value for key, value in asdict(icon).items() if value is not None} for icon in manifest.icons
        ]
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def runtime_entry_urls(cdn_lockfile_url: str | None) -> list[str]:
    """List the known CDN entry URLs of the Python runtime for precaching.

    Args:
        cdn_lockfile_url: URL of the Pyodide lock file when the runtime is
            served from a CDN, or ``None`` when unavailable.

    Returns:
        Absolute URLs of the PyScript core files and the lock file.

    """
    from webcompy_server._html import PYSCRIPT_BASE_URL

    urls = [f"{PYSCRIPT_BASE_URL}/core.js", f"{PYSCRIPT_BASE_URL}/core.css"]
    if cdn_lockfile_url:
        urls.append(cdn_lockfile_url)
    return urls


def _clean_page_url(rel: str) -> str | None:
    if rel == "index.html":
        return "./"
    if rel.endswith("/index.html"):
        return rel[: -len("index.html")]
    return None


def build_precache_entries(
    pwa: PWAConfig,
    *,
    dist_dir: pathlib.Path | None = None,
    runtime_asset_files: dict[str, pathlib.Path] | None = None,
    cdn_runtime_urls: list[str] | None = None,
) -> list[str]:
    """Resolve the precache URL list for a PWA-enabled build or server start.

    With ``precache="none"`` the result is empty and the output directory
    is not enumerated. With ``"auto"`` and a ``dist_dir``, build output is
    enumerated as scope-relative paths, each generated page additionally
    contributes its clean URL, and the PWA output files are excluded.
    Runtime files are excluded regardless of serving mode unless
    ``precache_runtime`` is enabled, in which case the included set is
    extended with the local runtime URLs and/or the given CDN runtime
    entry URLs and a size warning is logged to stderr.

    Args:
        pwa: Validated PWA configuration.
        dist_dir: SSG output directory to enumerate, or ``None`` for
            dynamic server mode (no pages to precache).
        runtime_asset_files: Mapping of runtime asset paths (relative to
            the ``_webcompy-assets/`` prefix) to on-disk source paths, for
            local runtime serving.
        cdn_runtime_urls: Absolute CDN entry URLs for runtime precaching
            when the runtime is served from a CDN.

    Returns:
        Sorted precache entries (scope-relative paths and absolute URLs).

    """
    if pwa.precache == "none":
        return []

    runtime_rels = frozenset(f"{RUNTIME_ASSET_PREFIX}{rel}" for rel in runtime_asset_files or {})
    entries: set[str] = set()

    if dist_dir is not None:
        for path in dist_dir.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(dist_dir).as_posix()
            if rel in PWA_OUTPUT_NAMES or (rel in runtime_rels and not pwa.precache_runtime):
                continue
            entries.add(rel)
            clean = _clean_page_url(rel)
            if clean is not None:
                entries.add(clean)

    if pwa.precache_runtime:
        entries.update(runtime_rels)
        if cdn_runtime_urls:
            entries.update(cdn_runtime_urls)
        if runtime_asset_files:
            total = sum(p.stat().st_size for p in runtime_asset_files.values() if p.is_file())
            print(
                f"Warning: precache_runtime enabled: the Python runtime "
                f"({total / 1_000_000:.1f} MB) will be precached to device storage.",
                file=sys.stderr,
                flush=True,
            )
        elif cdn_runtime_urls:
            print(
                "Warning: precache_runtime enabled with a CDN runtime: only runtime "
                "entry files are precached; offline startup is not guaranteed.",
                file=sys.stderr,
                flush=True,
            )

    if pwa.fallback_path is not None:
        entries.add(pwa.fallback_path)

    return sorted(entries)


def precache_entries_for_artifacts(
    pwa: PWAConfig, artifacts: BuildArtifacts, *, dist_dir: pathlib.Path | None = None
) -> list[str]:
    """Derive precache entries from resolved build artifacts.

    Args:
        pwa: Validated PWA configuration.
        artifacts: Resolved build artifacts describing runtime serving.
        dist_dir: SSG output directory to enumerate, or ``None`` for
            dynamic server mode.

    Returns:
        Sorted precache entries.

    """
    runtime_asset_files = artifacts.runtime_asset_files
    cdn_runtime_urls = None
    if pwa.precache_runtime and not runtime_asset_files:
        cdn_runtime_urls = runtime_entry_urls(artifacts.lockfile_url)
    return build_precache_entries(
        pwa,
        dist_dir=dist_dir,
        runtime_asset_files=runtime_asset_files,
        cdn_runtime_urls=cdn_runtime_urls,
    )


def _normalize_pattern(pattern: str) -> str:
    if pattern.startswith("/"):
        return pattern
    return "/" + pattern


def generate_sw(pwa: PWAConfig, app_version: str, precache_entries: list[str]) -> str:
    """Generate the framework-owned Service Worker with the build config embedded.

    Runtime rule patterns are normalized to start with a slash so patterns
    written without the leading slash match the scope-relative request
    paths the worker compares against.

    Args:
        pwa: Validated PWA configuration.
        app_version: Application build version embedded in cache names.
        precache_entries: Precache manifest entries.

    Returns:
        The complete ``sw.js`` source with the serialized configuration.

    """
    rules: list[dict] = []
    for rule in pwa.runtime:
        entry: dict = {"pattern": _normalize_pattern(rule.pattern), "strategy": rule.strategy}
        if rule.max_entries is not None:
            entry["maxEntries"] = rule.max_entries
        if rule.max_age is not None:
            entry["maxAge"] = rule.max_age
        rules.append(entry)
    config: dict = {
        "precache": precache_entries,
        "runtime": rules,
        "fallback": pwa.fallback_path,
        "offlineHtml": _DEFAULT_OFFLINE_HTML,
    }
    digest = hashlib.sha256(json.dumps(config, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:12]
    config["version"] = f"{app_version}-{digest}"
    payload = json.dumps(config, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return _SW_TEMPLATE.replace("__WC_PWA_CONFIG__", payload)
