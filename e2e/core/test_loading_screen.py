import json
import os
import socket
import subprocess
import time
import urllib.request
from pathlib import Path

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

PROJECT_ROOT = Path(__file__).parent.parent.parent
E2E_DIR = Path(__file__).parent

_KNOWN_LABELS = {
    "Preparing Python runtime…",
    "Downloading Python runtime…",
    "Installing packages…",
    "Runtime ready…",
    "Starting app…",
}


def _free_port():
    s = socket.socket()
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _throttle(page, latency_ms, throughput):
    cdp = page.context.new_cdp_session(page)
    cdp.send("Network.enable")
    cdp.send("Network.clearBrowserCache")
    cdp.send(
        "Network.emulateNetworkConditions",
        {
            "offline": False,
            "latency": latency_ms,
            "downloadThroughput": throughput,
            "uploadThroughput": throughput,
        },
    )


@pytest.fixture()
def loading_server_factory(serving_mode):
    if serving_mode == "static":
        pytest.skip("Custom loading config variants run only against the prod server")
    created = []

    def _spawn(loading_dict):
        port = _free_port()
        env = os.environ.copy()
        env["PYTHONPATH"] = str(E2E_DIR) + os.pathsep + env.get("PYTHONPATH", "")
        env["LOADING_JSON"] = json.dumps(loading_dict)
        tmp_dir = Path(os.environ.get("E2E_TMP_DIR", str(PROJECT_ROOT / ".tmp")))
        tmp_dir.mkdir(parents=True, exist_ok=True)
        log_file = (tmp_dir / f"loading-{port}.log").open("w")
        proc = subprocess.Popen(
            [
                "uv",
                "run",
                "--project",
                str(PROJECT_ROOT),
                "python",
                "-m",
                "webcompy",
                "start",
                "--config",
                "loading_config",
                "--port",
                str(port),
            ],
            cwd=str(E2E_DIR),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            env=env,
        )
        created.append((proc, log_file))
        base_url = f"http://localhost:{port}/"
        for _ in range(120):
            try:
                urllib.request.urlopen(base_url, timeout=5)
                break
            except Exception:
                if proc.poll() is not None:
                    pytest.fail(f"Loading server exited prematurely:\n{log_file.name}")
                time.sleep(1)
        else:
            pytest.fail(f"Loading server did not start within 120 seconds:\n{log_file.name}")
        return base_url

    yield _spawn

    for proc, log_file in created:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        log_file.close()


def test_fade_class_present_before_removal(page, server_url):
    page.add_init_script(
        """
        new MutationObserver(function (mutations) {
            for (var m of mutations) {
                if (m.type === 'attributes' && m.attributeName === 'class') {
                    var el = m.target;
                    if (el.id === 'webcompy-loading' && el.classList.contains('wc-fading')) {
                        window.__wcFadingSeen = true;
                    }
                }
            }
        }).observe(document, {subtree: true, attributes: true});
        """
    )
    page.goto(server_url)
    page.wait_for_selector("#webcompy-loading", state="hidden")
    assert page.evaluate("window.__wcFadingSeen === true")


def test_staged_status_during_boot(page, server_url):
    page.add_init_script(
        """
        window.__wcLabels = [];
        new MutationObserver(function () {
            var el = document.querySelector('[data-wc-status]');
            if (el && el.textContent && window.__wcLabels.indexOf(el.textContent) === -1) {
                window.__wcLabels.push(el.textContent);
            }
        }).observe(document, {subtree: true, childList: true, characterData: true});
        """
    )
    page.goto(server_url, wait_until="domcontentloaded")
    _throttle(page, 1500, 700 * 1024)
    page.reload(wait_until="domcontentloaded")
    page.wait_for_selector("#webcompy-loading", state="hidden", timeout=120000)
    labels = page.evaluate("window.__wcLabels")
    assert len(labels) >= 2, f"Expected at least 2 distinct stage labels, got {labels}"
    assert set(labels) <= _KNOWN_LABELS, f"Unexpected labels observed: {set(labels) - _KNOWN_LABELS}"


def test_watchdog_timeout_message(page, loading_server_factory):
    url = loading_server_factory({"timeout_seconds": 2})
    page.goto(url, wait_until="domcontentloaded")
    _throttle(page, 8000, 1000 * 1024)
    page.reload(wait_until="domcontentloaded")
    expect(page.locator("[data-wc-timeout]")).to_be_visible(timeout=20000)


def test_dormant_treatment_during_boot(page, server_url):
    page.goto(server_url, wait_until="domcontentloaded")
    _throttle(page, 1500, 700 * 1024)
    page.reload(wait_until="domcontentloaded")
    page.wait_for_function(
        "() => parseFloat(getComputedStyle(document.querySelector('#webcompy-app')).opacity) < 1",
        timeout=15000,
    )
    page.wait_for_selector("#webcompy-loading", state="hidden", timeout=120000)
    assert page.evaluate("getComputedStyle(document.querySelector('#webcompy-app')).opacity") == "1"


def test_block_policy_intercepts_clicks(page, server_url):
    page.goto(server_url, wait_until="domcontentloaded")
    _throttle(page, 1500, 700 * 1024)
    page.reload(wait_until="domcontentloaded")
    link = page.locator("[data-testid='nav-reactive']")
    link.wait_for(state="visible")
    box = link.bounding_box()
    assert box is not None
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.wait_for_timeout(1000)
    assert page.url.rstrip("/") == server_url.rstrip("/")


def test_inert_attribute_during_boot(page, loading_server_factory):
    url = loading_server_factory({"mode": "content", "interaction": "inert"})
    page.goto(url, wait_until="domcontentloaded")
    _throttle(page, 1500, 700 * 1024)
    page.reload(wait_until="domcontentloaded")
    page.wait_for_function(
        "() => document.querySelector('#webcompy-app').hasAttribute('inert')",
        timeout=15000,
    )
    assert page.evaluate("document.querySelector('#webcompy-app').getAttribute('aria-busy') === 'true'")
    page.wait_for_selector("#webcompy-loading", state="hidden", timeout=120000)
    assert page.evaluate("!document.querySelector('#webcompy-app').hasAttribute('inert')")
    assert page.evaluate("!document.querySelector('#webcompy-app').hasAttribute('aria-busy')")


def test_passthrough_allows_navigation(page, loading_server_factory):
    url = loading_server_factory({"mode": "content", "interaction": "passthrough"})
    page.goto(url, wait_until="domcontentloaded")
    _throttle(page, 1500, 700 * 1024)
    page.reload(wait_until="domcontentloaded")
    link = page.locator("[data-testid='nav-link']")
    link.wait_for(state="visible")
    box = link.bounding_box()
    assert box is not None
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.wait_for_url("**/other", timeout=30000)


def test_splash_preset_drives_status(page, loading_server_factory):
    url = loading_server_factory({"template": "splash"})
    page.goto(url, wait_until="domcontentloaded")
    _throttle(page, 1500, 700 * 1024)
    page.reload(wait_until="domcontentloaded")
    expect(page.locator(".wc-splash")).to_be_visible()
    expect(page.locator("[data-wc-status]")).to_have_text("Preparing Python runtime…", timeout=15000)


def test_custom_template_hooks_driven(page, loading_server_factory):
    template = '<div id="webcompy-loading" data-wc-fade="250"><div class="my-custom-splash" data-wc-status></div></div>'
    url = loading_server_factory({"template": template})
    page.goto(url, wait_until="domcontentloaded")
    _throttle(page, 1500, 700 * 1024)
    page.reload(wait_until="domcontentloaded")
    expect(page.locator("#webcompy-loading")).to_have_attribute("role", "status")
    expect(page.locator(".my-custom-splash")).to_be_visible()
    expect(page.locator(".my-custom-splash")).to_have_text("Preparing Python runtime…", timeout=15000)
    page.wait_for_selector("#webcompy-loading", state="hidden", timeout=120000)


def test_bar_trickles_during_download(page, server_url):
    page.goto(server_url, wait_until="domcontentloaded")
    _throttle(page, 1500, 700 * 1024)
    page.reload(wait_until="domcontentloaded")
    page.wait_for_function(
        "() => {"
        "var el = document.querySelector('[data-wc-status]');"
        "return el && el.textContent === 'Downloading Python runtime…';"
        "}",
        timeout=30000,
    )

    def _bar_progress():
        return page.evaluate(
            "() => parseFloat(document.querySelector('[data-wc-bar]').style.getPropertyValue('--wc-progress'))"
        )

    page.wait_for_function(
        "() => parseFloat(document.querySelector('[data-wc-bar]').style.getPropertyValue('--wc-progress')) > 0.36",
        timeout=30000,
    )
    first = _bar_progress()
    page.wait_for_timeout(3000)
    second = _bar_progress()
    label = page.evaluate("() => document.querySelector('[data-wc-status]').textContent")
    assert label == "Downloading Python runtime…", f"Stage changed during sampling: {label}"
    assert second > first, f"Bar did not trickle during download: {first} -> {second}"
    assert second < 0.60, f"Bar exceeded the download stage ceiling: {second}"


def test_custom_template_passthrough_allows_navigation(page, loading_server_factory):
    template = '<div id="webcompy-loading"><span data-wc-status></span></div>'
    url = loading_server_factory({"mode": "content", "interaction": "passthrough", "template": template})
    page.goto(url, wait_until="domcontentloaded")
    _throttle(page, 1500, 700 * 1024)
    page.reload(wait_until="domcontentloaded")
    link = page.locator("[data-testid='nav-link']")
    link.wait_for(state="visible")
    box = link.bounding_box()
    assert box is not None
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.wait_for_url("**/other", timeout=30000)
