from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import pathlib
import sys
import types
from unittest.mock import patch

import httpx
import pytest

from webcompy.app._app import WebComPyApp
from webcompy.app._config import PluginScript, WebComPyAppConfig
from webcompy.components._generator import define_component
from webcompy.elements import html
from webcompy_cli._build import BuildArtifacts, _compute_asset_hashes, resolve_build_artifacts
from webcompy_cli.config._build_config import WebComPyBuildConfig
from webcompy_server import configure_server_context
from webcompy_testing import create_test_app, render_app_html


def _make_static_app(
    tmp_path: pathlib.Path,
    *,
    base_url: str = "/",
    head_links: list[dict[str, str]] | None = None,
    static_files: dict[str, str] | None = None,
) -> tuple[pathlib.Path, WebComPyApp, WebComPyBuildConfig]:
    pkg = tmp_path / "sample_app"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")

    static_dir = pkg / "static"
    static_dir.mkdir(exist_ok=True)
    for rel, content in (static_files or {"styles/site.css": "body { color: #111; }"}).items():
        target = static_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    @define_component()
    def SampleRoot(_):
        return html.DIV({"class": "root"}, "hello")

    SampleRoot.scoped_style = {".root": {"padding": "1rem"}}

    app = WebComPyApp(
        root_component=SampleRoot,
        config=WebComPyAppConfig(base_url=base_url),
    )
    if head_links:
        app.set_head({"link": head_links})
    configure_server_context(app)

    mod_path = pkg / "app.py"
    mod_path.write_text("app = None\n", encoding="utf-8")
    spec = importlib.util.spec_from_file_location("sample_app.app", mod_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    mod.app = app  # type: ignore[attr-defined]
    pkg_mod = types.ModuleType("sample_app")
    pkg_mod.__path__ = [str(pkg)]
    sys.modules["sample_app"] = pkg_mod
    sys.modules["sample_app.app"] = mod

    build_config = WebComPyBuildConfig(app_module=mod, dependencies=[], static_files_dir="static")
    return pkg, app, build_config


class TestGenerateHtmlAssetCacheBusting:
    def test_appends_version_to_framework_index_css_across_base_urls(self) -> None:
        @define_component()
        def CacheTestRoot(_):
            return html.DIV({}, "ok")

        for base_url, expected_prefix in [
            ("/", "/_webcompy-ui/index.css"),
            ("/myapp/", "/myapp/_webcompy-ui/index.css"),
        ]:
            app = create_test_app(root_component=CacheTestRoot, base_url=base_url)
            html_str = render_app_html(
                app,
                app_package_name="test_pkg",
                dev_mode=False,
                prerender=True,
                wheel_filename="test_pkg-0+sha.12345678-py3-none-any.whl",
                asset_hashes={"_webcompy-ui/index.css": "abcd1234"},
            )
            assert f'href="{expected_prefix}?v=abcd1234"' in html_str

    def test_scoped_styles_follow_versioned_index_css_with_escapable_base_url(self) -> None:
        @define_component()
        def StyledRoot(_):
            return html.DIV({"class": "box"}, "styled")

        StyledRoot.scoped_style = {".box": {"color": "red"}}
        app = create_test_app(root_component=StyledRoot, base_url="/a&b/")
        html_str = render_app_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=True,
            wheel_filename="test_pkg-0+sha.12345678-py3-none-any.whl",
            asset_hashes={"_webcompy-ui/index.css": "deadbeef"},
        )
        link_pos = html_str.find('href="/a&amp;b/_webcompy-ui/index.css?v=deadbeef"')
        default_pos = html_str.find('id="webcompy-component-defaults"')
        cid_pos = html_str.find('data-webcompy-cid="')
        assert link_pos != -1
        assert default_pos != -1
        assert cid_pos != -1
        assert link_pos < default_pos < cid_pos

    def test_rewrites_matching_links_and_scripts_and_preserves_exclusions(self) -> None:
        @define_component()
        def ScriptLinkRoot(_):
            return html.DIV({}, "ok")

        conditional_plugin = PluginScript(
            attrs={"src": "/js/cond.js", "defer": ""},
            condition="window.__ENABLE__ === true",
            in_head=True,
        )
        unconditional_plugin = PluginScript(
            attrs={"src": "/js/plugin.js"},
            in_head=False,
        )
        app = create_test_app(
            root_component=ScriptLinkRoot,
            base_url="/docs/",
            scripts=[conditional_plugin, unconditional_plugin],
        )
        app.set_head(
            {
                "link": [
                    {"rel": "stylesheet", "href": "/styles/site.css"},
                    {"rel": "stylesheet", "href": "/docs/_webcompy-ui/prose.css"},
                    {"rel": "stylesheet", "href": "./styles/relative.css"},
                    {"rel": "stylesheet", "href": "/styles/site.css?media=screen#top"},
                    {"rel": "stylesheet", "href": "/styles/site.css?v=manual"},
                    {"rel": "stylesheet", "href": "https://cdn.example.com/styles/site.css"},
                    {"rel": "stylesheet", "href": "//cdn.example.com/styles/site.css"},
                    {"rel": "stylesheet", "href": "data:text/css,body{}"},
                    {"rel": "stylesheet", "href": "/styles/unknown.css"},
                ],
                "script": [
                    ({"src": "/js/head.js"}, None),
                    ({"src": "https://cdn.example.com/js/head.js"}, None),
                ],
            }
        )
        app.append_script({"src": "/js/body.js"})

        hashes = {
            "_webcompy-ui/index.css": "1111aaaa",
            "_webcompy-ui/prose.css": "2222bbbb",
            "styles/site.css": "3333cccc",
            "styles/relative.css": "4444dddd",
            "js/head.js": "5555eeee",
            "js/body.js": "6666ffff",
            "js/plugin.js": "77770000",
            "js/cond.js": "88881111",
        }
        html_str = render_app_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=True,
            wheel_filename="test_pkg-0+sha.12345678-py3-none-any.whl",
            asset_hashes=hashes,
        )

        assert 'href="/docs/_webcompy-ui/index.css?v=1111aaaa"' in html_str
        assert 'href="/docs/_webcompy-ui/prose.css?v=2222bbbb"' in html_str
        assert 'href="/styles/site.css?v=3333cccc"' in html_str
        assert 'href="./styles/relative.css?v=4444dddd"' in html_str
        assert 'href="/styles/site.css?media=screen&amp;v=3333cccc#top"' in html_str
        assert 'href="/styles/site.css?v=manual"' in html_str
        assert 'href="https://cdn.example.com/styles/site.css"' in html_str
        assert 'href="//cdn.example.com/styles/site.css"' in html_str
        assert 'href="data:text/css,body{}"' in html_str
        assert 'href="/styles/unknown.css"' in html_str

        assert 'src="/js/head.js?v=5555eeee"' in html_str
        assert 'src="https://cdn.example.com/js/head.js"' in html_str
        assert 'src="/js/body.js?v=6666ffff"' in html_str
        assert 'src="/js/plugin.js?v=77770000"' in html_str
        assert '"/js/cond.js?v=88881111"' in html_str
        assert conditional_plugin.attrs["src"] == "/js/cond.js"
        assert unconditional_plugin.attrs["src"] == "/js/plugin.js"

    def test_none_asset_hashes_preserves_unversioned_urls(self) -> None:
        @define_component()
        def PlainCacheRoot(_):
            return html.DIV({}, "ok")

        app = create_test_app(root_component=PlainCacheRoot, base_url="/")
        app.set_head({"link": [{"rel": "stylesheet", "href": "/styles/site.css"}]})
        html_str = render_app_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=True,
            wheel_filename="test_pkg-0+sha.12345678-py3-none-any.whl",
            asset_hashes=None,
        )
        assert 'href="/_webcompy-ui/index.css"' in html_str
        assert 'href="/styles/site.css"' in html_str
        assert "?v=" not in html_str


class TestComputeAssetHashes:
    def test_hashes_framework_and_static_assets_and_rewrites_index_imports(self, tmp_path: pathlib.Path) -> None:
        from webcompy.ui._styles import get_styles_file, get_styles_files

        static_dir = tmp_path / "static"
        (static_dir / "styles").mkdir(parents=True)
        (static_dir / "js").mkdir(parents=True)
        (static_dir / "styles" / "site.css").write_text("body { margin: 0; }", encoding="utf-8")
        (static_dir / "js" / "helper.js").write_text("console.log(1);", encoding="utf-8")

        hashes, rewritten_index = _compute_asset_hashes(static_dir)

        expected_styles = get_styles_files()
        for name, raw in expected_styles.items():
            if name == "index.css":
                continue
            expected_digest = hashlib.sha256(raw).hexdigest()[:8]
            assert hashes[f"_webcompy-ui/{name}"] == expected_digest

        rewritten_text = rewritten_index.decode("utf-8")
        for imported in (
            "tokens.css",
            "reset.css",
            "components.css",
            "primitives.css",
            "code-block.css",
            "syntax-theme.css",
        ):
            digest = hashes[f"_webcompy-ui/{imported}"]
            assert f'./{imported}?v={digest}"' in rewritten_text

        assert hashes["_webcompy-ui/index.css"] == hashlib.sha256(rewritten_index).hexdigest()[:8]
        assert hashes["styles/site.css"] == hashlib.sha256(b"body { margin: 0; }").hexdigest()[:8]
        assert hashes["js/helper.js"] == hashlib.sha256(b"console.log(1);").hexdigest()[:8]

        raw_package_index = get_styles_file("index.css")
        assert raw_package_index is not None
        assert b"?v=" not in raw_package_index

    def test_leaf_ui_stylesheet_change_propagates_to_index_css_hash(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from webcompy.ui import _styles

        base_files = _styles.get_styles_files()
        modified_files = dict(base_files)
        modified_files["tokens.css"] = base_files["tokens.css"] + b"\n/* tweaked */\n"

        monkeypatch.setattr(_styles, "get_styles_files", lambda: base_files)
        hashes_before, index_before = _compute_asset_hashes(None)

        monkeypatch.setattr(_styles, "get_styles_files", lambda: modified_files)
        hashes_after, index_after = _compute_asset_hashes(None)

        assert hashes_after["_webcompy-ui/tokens.css"] != hashes_before["_webcompy-ui/tokens.css"]
        assert index_after != index_before
        assert hashes_after["_webcompy-ui/index.css"] != hashes_before["_webcompy-ui/index.css"]

    def test_missing_static_dir_handled_gracefully(self, tmp_path: pathlib.Path) -> None:
        hashes, rewritten_index = _compute_asset_hashes(tmp_path / "missing-static")
        assert "_webcompy-ui/index.css" in hashes
        assert b"?v=" in rewritten_index


class TestAsgiServerCacheHeadersAndAssetBusting:
    def _cleanup_modules(self) -> None:
        for name in ("sample_app.app", "sample_app"):
            sys.modules.pop(name, None)

    @pytest.mark.asyncio
    async def test_prod_mode_headers_and_busted_urls(self, tmp_path: pathlib.Path) -> None:
        try:
            pkg, app, build_config = _make_static_app(
                tmp_path,
                head_links=[
                    {"rel": "stylesheet", "href": "/styles/site.css"},
                    {"rel": "stylesheet", "href": "/_webcompy-ui/prose.css"},
                ],
                static_files={"styles/site.css": "body { color: navy; }"},
            )
            wasm_path = tmp_path / "numpy-2.0.0-cp314-cp314-pyodide_2026_0_wasm32.whl"
            wasm_path.write_bytes(b"wasm-wheel")

            asset_hashes, rewritten_index = _compute_asset_hashes(pkg / "static")
            artifacts = BuildArtifacts(
                app_version="0.1.0",
                wheel_filename="sample_app-0+sha.12345678-py3-none-any.whl",
                fw_wheel_filename="webcompy-0+sha.abcdef01-py3-none-any.whl",
                extra_wheel_filenames=["webcompy-0+sha.abcdef01-py3-none-any.whl"],
                pyodide_package_names=["numpy"],
                wasm_local_urls={"numpy": f"/_webcompy-assets/packages/{wasm_path.name}"},
                app_package_files={
                    "sample_app-0+sha.12345678-py3-none-any.whl": (b"app-wheel", "application/zip"),
                    "webcompy-0+sha.abcdef01-py3-none-any.whl": (b"fw-wheel", "application/zip"),
                },
                wasm_asset_files={wasm_path.name: wasm_path},
                asset_hashes=asset_hashes,
                framework_ui_index_css=rewritten_index,
                dev_mode=False,
            )

            with patch("webcompy_cli._server.resolve_build_artifacts", return_value=artifacts):
                from webcompy_cli._server import create_asgi_app

                serving = create_asgi_app(app, build_config, mode="prod")

            transport = httpx.ASGITransport(app=serving.asgi)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                html_res = await client.get("/")
                index_css_res = await client.get("/_webcompy-ui/index.css")
                app_whl_res = await client.get("/_webcompy-app-package/sample_app-0+sha.12345678-py3-none-any.whl")
                fw_whl_res = await client.get("/_webcompy-app-package/webcompy-0+sha.abcdef01-py3-none-any.whl")
                wasm_res = await client.get(f"/_webcompy-assets/packages/{wasm_path.name}")

            assert html_res.status_code == 200
            assert f"/_webcompy-ui/index.css?v={asset_hashes['_webcompy-ui/index.css']}" in html_res.text
            assert f"/_webcompy-ui/prose.css?v={asset_hashes['_webcompy-ui/prose.css']}" in html_res.text
            assert f"/styles/site.css?v={asset_hashes['styles/site.css']}" in html_res.text

            assert index_css_res.status_code == 200
            assert index_css_res.headers.get("cache-control") == "public, max-age=0, must-revalidate"
            assert index_css_res.content == rewritten_index
            assert "?v=" in index_css_res.text

            assert app_whl_res.status_code == 200
            assert app_whl_res.headers.get("cache-control") == "public, max-age=31536000, immutable"
            assert fw_whl_res.status_code == 200
            assert fw_whl_res.headers.get("cache-control") == "public, max-age=31536000, immutable"
            assert wasm_res.status_code == 200
            assert wasm_res.headers.get("cache-control") == "public, max-age=31536000, immutable"
        finally:
            self._cleanup_modules()

    @pytest.mark.asyncio
    async def test_dev_mode_disables_hashes_and_uses_dev_headers(self, tmp_path: pathlib.Path) -> None:
        try:
            _pkg, app, build_config = _make_static_app(
                tmp_path,
                head_links=[
                    {"rel": "stylesheet", "href": "/styles/site.css"},
                    {"rel": "stylesheet", "href": "/_webcompy-ui/prose.css"},
                ],
                static_files={"styles/site.css": "body { color: navy; }"},
            )
            wasm_path = tmp_path / "numpy-2.0.0-cp314-cp314-pyodide_2026_0_wasm32.whl"
            wasm_path.write_bytes(b"wasm-wheel")

            artifacts = BuildArtifacts(
                app_version="0.1.0",
                wheel_filename="sample_app-0+sha.12345678-py3-none-any.whl",
                fw_wheel_filename="webcompy-0+sha.abcdef01-py3-none-any.whl",
                extra_wheel_filenames=["webcompy-0+sha.abcdef01-py3-none-any.whl"],
                pyodide_package_names=["numpy"],
                wasm_local_urls={"numpy": f"/_webcompy-assets/packages/{wasm_path.name}"},
                app_package_files={
                    "sample_app-0+sha.12345678-py3-none-any.whl": (b"app-wheel", "application/zip"),
                    "webcompy-0+sha.abcdef01-py3-none-any.whl": (b"fw-wheel", "application/zip"),
                },
                wasm_asset_files={wasm_path.name: wasm_path},
                asset_hashes=None,
                framework_ui_index_css=None,
                dev_mode=True,
            )

            with patch("webcompy_cli._server.resolve_build_artifacts", return_value=artifacts):
                from webcompy_cli._server import create_asgi_app

                serving = create_asgi_app(app, build_config, mode="dev")

            transport = httpx.ASGITransport(app=serving.asgi)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                html_res = await client.get("/")
                index_css_res = await client.get("/_webcompy-ui/index.css")
                app_whl_res = await client.get("/_webcompy-app-package/sample_app-0+sha.12345678-py3-none-any.whl")
                fw_whl_res = await client.get("/_webcompy-app-package/webcompy-0+sha.abcdef01-py3-none-any.whl")
                wasm_res = await client.get(f"/_webcompy-assets/packages/{wasm_path.name}")

            assert html_res.status_code == 200
            assert 'href="/_webcompy-ui/index.css"' in html_res.text
            assert 'href="/_webcompy-ui/prose.css"' in html_res.text
            assert 'href="/styles/site.css"' in html_res.text
            assert "?v=" not in html_res.text

            assert index_css_res.status_code == 200
            assert index_css_res.headers.get("cache-control") == "no-cache, must-revalidate"
            assert "?v=" not in index_css_res.text

            assert app_whl_res.headers.get("cache-control") == "no-cache"
            assert fw_whl_res.headers.get("cache-control") == "max-age=86400, must-revalidate"
            assert wasm_res.headers.get("cache-control") == "max-age=86400, must-revalidate"
        finally:
            self._cleanup_modules()

    def test_resolve_build_artifacts_populates_hashes_only_in_prod(self, tmp_path: pathlib.Path) -> None:
        try:
            _pkg, app, build_config = _make_static_app(
                tmp_path,
                static_files={"styles/site.css": "body { color: green; }"},
            )
            with (
                patch("webcompy_cli._build.resolve_dependencies"),
                patch("webcompy_cli._build.resolve_lockfile", return_value=(None, [], [])),
                patch("webcompy_cli._build.get_bundled_deps", return_value=[]),
                patch("webcompy_cli._build.get_wasm_package_names", return_value=[]),
                patch("webcompy_cli._build.get_cdn_pure_python_package_names", return_value=[]),
            ):
                prod_artifacts = resolve_build_artifacts(app, build_config, dev_mode=False)
                dev_artifacts = resolve_build_artifacts(app, build_config, dev_mode=True)

            assert prod_artifacts.asset_hashes is not None
            assert prod_artifacts.framework_ui_index_css is not None
            assert "styles/site.css" in prod_artifacts.asset_hashes
            assert "_webcompy-ui/index.css" in prod_artifacts.asset_hashes
            assert b"?v=" in prod_artifacts.framework_ui_index_css

            assert dev_artifacts.asset_hashes is None
            assert dev_artifacts.framework_ui_index_css is None
        finally:
            self._cleanup_modules()


class TestSsgAssetCacheBusting:
    def test_generate_static_site_writes_rewritten_index_css_and_busted_html(self, tmp_path: pathlib.Path) -> None:
        try:
            _pkg, _app, build_config = _make_static_app(
                tmp_path,
                head_links=[
                    {"rel": "stylesheet", "href": "/styles/site.css"},
                    {"rel": "stylesheet", "href": "/_webcompy-ui/prose.css"},
                ],
                static_files={"styles/site.css": "body { color: teal; }"},
            )
            dist_dir = tmp_path / "dist"
            saved_argv = sys.argv
            sys.argv = ["webcompy", "generate"]
            try:
                with (
                    patch("webcompy_cli._build.resolve_dependencies"),
                    patch("webcompy_cli._build.resolve_lockfile", return_value=(None, [], [])),
                    patch("webcompy_cli._build.get_bundled_deps", return_value=[]),
                    patch("webcompy_cli._build.get_wasm_package_names", return_value=[]),
                    patch("webcompy_cli._build.get_cdn_pure_python_package_names", return_value=[]),
                    patch("webcompy_cli._generate.discover_config", return_value=build_config),
                ):
                    from webcompy_cli._generate import generate_static_site

                    build_config.dist = str(dist_dir)
                    asyncio.run(generate_static_site())
            finally:
                sys.argv = saved_argv

            emitted_index_css = (dist_dir / "_webcompy-ui" / "index.css").read_bytes()
            expected_index_hash = hashlib.sha256(emitted_index_css).hexdigest()[:8]
            expected_prose_hash = hashlib.sha256((dist_dir / "_webcompy-ui" / "prose.css").read_bytes()).hexdigest()[:8]
            expected_site_hash = hashlib.sha256(b"body { color: teal; }").hexdigest()[:8]

            assert b"?v=" in emitted_index_css
            tokens_hash = hashlib.sha256((dist_dir / "_webcompy-ui" / "tokens.css").read_bytes()).hexdigest()[:8]
            assert f'./tokens.css?v={tokens_hash}"'.encode() in emitted_index_css

            index_html = (dist_dir / "index.html").read_text(encoding="utf-8")
            assert f'href="/_webcompy-ui/index.css?v={expected_index_hash}"' in index_html
            assert f'href="/_webcompy-ui/prose.css?v={expected_prose_hash}"' in index_html
            assert f'href="/styles/site.css?v={expected_site_hash}"' in index_html
        finally:
            for name in ("sample_app.app", "sample_app"):
                sys.modules.pop(name, None)
