"""Cycle 10 PR2 (Phase 4 coverage) — ``browser/manager.py`` ≥80%.

``browser/manager.py`` requires ``[browser]`` optional extras
(``playwright``).  CI does NOT install playwright, so the module
ngoài rìa import-graph với mọi test khác.  Để phủ logic mà KHÔNG
buộc cài playwright vào CI, mỗi test dynamically inject ``playwright``
+ ``playwright.sync_api`` stubs vào ``sys.modules`` *trước* khi import
``vibecodekit.browser.manager`` lần đầu.

Stub thực thi 1 lớp protocol mỏng (Page / Browser / BrowserContext /
Playwright) đúng shape mà ``BrowserManager`` gọi.  Coverage báo line
được hit như khi chạy với playwright thật, nhưng test KHÔNG khởi
Chromium real.

NOTE: ``_on_console`` / ``_on_request`` / ``_on_response`` callbacks
được mark ``# pragma: no cover`` trong source vì chỉ chạy khi
playwright real bắn event — ngoài tầm với của test stub.
"""
from __future__ import annotations

import sys
import types
from typing import Any, Callable, Dict, Iterable, List, Optional

import pytest


# ---------------------------------------------------------------------------
# Stub playwright before manager imports it.
# ---------------------------------------------------------------------------

def _install_playwright_stub() -> None:
    """Inject minimal ``playwright.sync_api`` stub vào sys.modules.

    Idempotent — nếu playwright thật đã có sẵn, KHÔNG override.
    """
    if "playwright.sync_api" in sys.modules:
        return
    pw = types.ModuleType("playwright")
    sync_api = types.ModuleType("playwright.sync_api")
    sync_api.Browser = type("Browser", (), {})  # type: ignore[attr-defined]
    sync_api.BrowserContext = type("BrowserContext", (), {})  # type: ignore[attr-defined]
    sync_api.Page = type("Page", (), {})  # type: ignore[attr-defined]
    sync_api.Playwright = type("Playwright", (), {})  # type: ignore[attr-defined]
    sync_api.sync_playwright = lambda: None  # type: ignore[attr-defined]
    pw.sync_api = sync_api  # type: ignore[attr-defined]
    sys.modules["playwright"] = pw
    sys.modules["playwright.sync_api"] = sync_api


_install_playwright_stub()

from vibecodekit.browser import manager as bm  # noqa: E402


# ---------------------------------------------------------------------------
# Fakes — minimal Playwright protocol surface.
# ---------------------------------------------------------------------------

class _FakeAccessibility:
    def __init__(self, tree: Optional[Dict[str, Any]] = None) -> None:
        self._tree = tree

    def snapshot(self, interesting_only: bool = True) -> Optional[Dict[str, Any]]:
        return self._tree


class _FakePage:
    """Tiny Playwright Page double — covers the call surface in manager.py."""

    def __init__(self, url: str = "https://example.com",
                 title_value: str = "Example") -> None:
        self.url = url
        self._title = title_value
        self.accessibility = _FakeAccessibility(
            {"role": "WebArea", "name": title_value}
        )
        self._handlers: Dict[str, List[Callable[..., Any]]] = {
            "console": [], "request": [], "response": [],
        }
        self.calls: List[Dict[str, Any]] = []
        self._eval_responses: Dict[str, Any] = {}

    # Event handler registration — record callback for inspection.
    def on(self, event: str, cb: Callable[..., Any]) -> None:
        self._handlers.setdefault(event, []).append(cb)

    def title(self) -> str:
        return self._title

    def evaluate(self, expr: str, *args: Any, **kw: Any) -> Any:
        self.calls.append({"verb": "evaluate", "expr": expr})
        # Return canned values keyed by substring so multiple expr's resolve.
        # Order matters — links/forms also contain "innerText", so check
        # those more specific selectors first.
        if "scrollTo" in expr:
            return None
        if "querySelectorAll('a[href]')" in expr:
            return [{"href": "https://x", "text": "X"}]
        if "querySelectorAll('form')" in expr:
            return [{"action": "/submit", "method": "post", "fields": []}]
        if "innerText" in expr:
            return "hello world"
        return None

    def content(self) -> str:
        return "<html><body>hi</body></html>"

    def goto(self, url: str, wait_until: str = "load") -> None:
        self.calls.append({"verb": "goto", "url": url, "wait_until": wait_until})
        self.url = url

    def click(self, selector: str) -> None:
        self.calls.append({"verb": "click", "selector": selector})

    def fill(self, selector: str, value: str) -> None:
        self.calls.append({"verb": "fill", "selector": selector, "value": value})

    def select_option(self, selector: str, value: Any) -> None:
        self.calls.append({"verb": "select", "selector": selector, "value": value})

    def wait_for_selector(self, selector: str, timeout: float = 5_000) -> None:
        self.calls.append({"verb": "wait_for", "selector": selector,
                           "timeout": timeout})

    def screenshot(self, path: str, full_page: bool = True) -> None:
        self.calls.append({"verb": "screenshot", "path": path,
                           "full_page": full_page})


class _FakeContext:
    def __init__(self) -> None:
        self.cookies: List[Dict[str, Any]] = []
        self._page = _FakePage()
        self.closed = False

    def new_page(self) -> _FakePage:
        return self._page

    def add_cookies(self, cookies: Iterable[Dict[str, Any]]) -> None:
        self.cookies.extend(list(cookies))

    def close(self) -> None:
        self.closed = True


class _FakeChromium:
    def __init__(self) -> None:
        self.launched_headless: Optional[bool] = None
        self._browser: Optional["_FakeBrowser"] = None

    def launch(self, headless: bool = True) -> "_FakeBrowser":
        self.launched_headless = headless
        self._browser = _FakeBrowser()
        return self._browser


class _FakeBrowser:
    def __init__(self) -> None:
        self.contexts: List[_FakeContext] = []
        self.closed = False

    def new_context(self) -> _FakeContext:
        ctx = _FakeContext()
        self.contexts.append(ctx)
        return ctx

    def close(self) -> None:
        self.closed = True


class _FakePlaywright:
    """Playwright handle returned by ``sync_playwright().start()``."""

    def __init__(self) -> None:
        self.chromium = _FakeChromium()
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True


class _FakeSyncPlaywrightHandle:
    """Object returned by ``sync_playwright()`` (before ``.start()`` called)."""

    def __init__(self) -> None:
        self.pw = _FakePlaywright()

    def start(self) -> _FakePlaywright:
        return self.pw


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_pw(monkeypatch: pytest.MonkeyPatch) -> _FakeSyncPlaywrightHandle:
    """Patch ``manager.sync_playwright`` để trả handle giả."""
    handle = _FakeSyncPlaywrightHandle()
    monkeypatch.setattr(bm, "sync_playwright", lambda: handle)
    return handle


@pytest.fixture
def manager(fake_pw: _FakeSyncPlaywrightHandle) -> bm.BrowserManager:
    """Started BrowserManager (default tab opened)."""
    m = bm.BrowserManager(headless=True)
    m.start()
    return m


@pytest.fixture(autouse=True)
def reset_singleton() -> Iterable[None]:
    """Đảm bảo module-level singleton sạch giữa các test."""
    bm._singleton = None
    yield
    bm._singleton = None


# ---------------------------------------------------------------------------
# Module constants / dataclass
# ---------------------------------------------------------------------------

def test_buffer_constants() -> None:
    assert bm.CONSOLE_BUFFER == 200
    assert bm.NETWORK_BUFFER == 200


def test_tab_state_default_buffers_capped() -> None:
    page = _FakePage()
    ctx = _FakeContext()
    tab = bm.TabState(page=page, context=ctx)
    assert tab.console.maxlen == bm.CONSOLE_BUFFER
    assert tab.network.maxlen == bm.NETWORK_BUFFER
    assert len(tab.console) == 0
    assert len(tab.network) == 0


# ---------------------------------------------------------------------------
# BrowserManager — lifecycle (start / stop / _touch / _open_tab / _tab)
# ---------------------------------------------------------------------------

def test_start_launches_chromium_and_opens_default_tab(
    fake_pw: _FakeSyncPlaywrightHandle,
) -> None:
    m = bm.BrowserManager(headless=False)
    m.start()
    assert fake_pw.pw.chromium.launched_headless is False
    assert m._browser is fake_pw.pw.chromium._browser
    assert "default" in m._tabs
    assert m._tabs["default"].page is fake_pw.pw.chromium._browser.contexts[0]._page


def test_start_idempotent_when_already_started(manager: bm.BrowserManager) -> None:
    """Gọi start() lần 2 KHÔNG launch chromium lần nữa."""
    first_browser = manager._browser
    manager.start()
    assert manager._browser is first_browser


def test_stop_closes_contexts_and_browser(
    manager: bm.BrowserManager,
    fake_pw: _FakeSyncPlaywrightHandle,
) -> None:
    ctx = manager._tabs["default"].context
    manager.stop()
    assert ctx.closed is True  # type: ignore[attr-defined]
    assert fake_pw.pw.chromium._browser.closed is True
    assert fake_pw.pw.stopped is True
    assert manager._browser is None
    assert manager._tabs == {}


def test_stop_safe_when_not_started() -> None:
    m = bm.BrowserManager()
    # Không raise dù chưa start.
    m.stop()
    assert m._browser is None


def test_last_activity_ts_property_and_touch(
    manager: bm.BrowserManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bm.time, "time", lambda: 5_000.0)
    manager._touch()
    assert manager.last_activity_ts == 5_000.0


def test_open_tab_raises_when_browser_not_started() -> None:
    m = bm.BrowserManager()
    with pytest.raises(RuntimeError, match="browser not started"):
        m._open_tab("custom")


def test_tab_returns_active_when_no_name(manager: bm.BrowserManager) -> None:
    tab = manager._tab(None)
    assert tab is manager._tabs["default"]


def test_tab_creates_new_when_missing(manager: bm.BrowserManager) -> None:
    tab = manager._tab("brand-new")
    assert "brand-new" in manager._tabs
    assert manager._tabs["brand-new"] is tab


# ---------------------------------------------------------------------------
# BrowserManager — read verbs
# ---------------------------------------------------------------------------

def test_read_verb_text(manager: bm.BrowserManager) -> None:
    assert manager.run_read_verb("text", None, {}) == "hello world"


def test_read_verb_html(manager: bm.BrowserManager) -> None:
    assert "<html>" in manager.run_read_verb("html", None, {})


def test_read_verb_links(manager: bm.BrowserManager) -> None:
    out = manager.run_read_verb("links", None, {})
    assert isinstance(out, list)
    assert out[0]["href"] == "https://x"


def test_read_verb_forms(manager: bm.BrowserManager) -> None:
    out = manager.run_read_verb("forms", None, {})
    assert isinstance(out, list)
    assert out[0]["action"] == "/submit"


def test_read_verb_aria(manager: bm.BrowserManager) -> None:
    out = manager.run_read_verb("aria", None, {})
    assert out["role"] == "WebArea"


def test_read_verb_aria_empty_tree_returns_dict(
    manager: bm.BrowserManager,
) -> None:
    """``accessibility.snapshot`` returning None → fallback {}."""
    manager._tabs["default"].page.accessibility = _FakeAccessibility(None)
    out = manager.run_read_verb("aria", None, {})
    assert out == {}


def test_read_verb_console_returns_buffer(manager: bm.BrowserManager) -> None:
    tab = manager._tabs["default"]
    tab.console.append({"type": "log", "text": "hi", "ts": 1.0})
    assert manager.run_read_verb("console", None, {}) == [
        {"type": "log", "text": "hi", "ts": 1.0}
    ]


def test_read_verb_network_returns_buffer(manager: bm.BrowserManager) -> None:
    tab = manager._tabs["default"]
    tab.network.append({"method": "GET", "url": "/", "kind": "request"})
    assert manager.run_read_verb("network", None, {})[0]["method"] == "GET"


def test_read_verb_snapshot_returns_snapshot(
    manager: bm.BrowserManager,
) -> None:
    out = manager.run_read_verb("snapshot", None, {})
    # ``Snapshot`` is a dataclass from snapshot module.
    assert hasattr(out, "url")
    assert hasattr(out, "title")
    assert hasattr(out, "dom_hash")
    assert out.url == "https://example.com"
    assert out.title == "Example"
    assert out.text == "hello world"


def test_read_verb_tabs(manager: bm.BrowserManager) -> None:
    manager._open_tab("second")
    assert manager.run_read_verb("tabs", None, {}) == ["default", "second"]


def test_read_verb_status(manager: bm.BrowserManager) -> None:
    out = manager.run_read_verb("status", None, {})
    assert out["active"] == "default"
    assert out["tabs"] == ["default"]
    assert "last_activity_ts" in out


def test_read_verb_unknown_raises(manager: bm.BrowserManager) -> None:
    with pytest.raises(ValueError, match="unknown read verb"):
        manager.run_read_verb("hack", None, {})


def test_read_verb_uses_tab_extra(manager: bm.BrowserManager) -> None:
    """``extras['tab']`` switches active tab."""
    manager._open_tab("alt")
    out = manager.run_read_verb("tabs", None, {"tab": "alt"})
    assert "alt" in out


# ---------------------------------------------------------------------------
# BrowserManager — write verbs
# ---------------------------------------------------------------------------

def test_write_verb_goto_default_wait_until(manager: bm.BrowserManager) -> None:
    out = manager.run_write_verb("goto", "https://acme.test", {})
    assert out["url"] == "https://acme.test"
    assert out["title"] == "Example"


def test_write_verb_goto_with_wait_until(manager: bm.BrowserManager) -> None:
    manager.run_write_verb("goto", "https://x.test",
                           {"wait_until": "domcontentloaded"})
    page = manager._tabs["default"].page
    assert page.calls[-1] == {
        "verb": "goto", "url": "https://x.test",
        "wait_until": "domcontentloaded",
    }


def test_write_verb_goto_requires_url(manager: bm.BrowserManager) -> None:
    with pytest.raises(AssertionError, match="goto requires a URL"):
        manager.run_write_verb("goto", None, {})


def test_write_verb_click_uses_extras_selector(manager: bm.BrowserManager) -> None:
    out = manager.run_write_verb("click", None, {"selector": "#btn"})
    assert out == {"clicked": "#btn"}


def test_write_verb_click_falls_back_to_target(
    manager: bm.BrowserManager,
) -> None:
    out = manager.run_write_verb("click", "#btn", {})
    assert out == {"clicked": "#btn"}


def test_write_verb_fill(manager: bm.BrowserManager) -> None:
    out = manager.run_write_verb("fill", "#email", {"value": "a@b"})
    assert out == {"filled": "#email"}


def test_write_verb_select(manager: bm.BrowserManager) -> None:
    out = manager.run_write_verb("select", "#dropdown", {"value": "vn"})
    assert out == {"selected": "#dropdown", "value": "vn"}


def test_write_verb_scroll_default_y(manager: bm.BrowserManager) -> None:
    out = manager.run_write_verb("scroll", None, {})
    assert out == {"scrolled_to": [0, 600]}


def test_write_verb_scroll_with_explicit_xy(manager: bm.BrowserManager) -> None:
    out = manager.run_write_verb("scroll", None, {"x": 10, "y": 200})
    assert out == {"scrolled_to": [10, 200]}


def test_write_verb_wait_for(manager: bm.BrowserManager) -> None:
    out = manager.run_write_verb("wait_for", "#ready",
                                  {"timeout": 1_000})
    assert out == {"waited_for": "#ready"}


def test_write_verb_screenshot_default_path(
    manager: bm.BrowserManager,
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    out = manager.run_write_verb("screenshot", None, {})
    assert out["path"].endswith("vck-screenshot.png")


def test_write_verb_screenshot_explicit_path(
    manager: bm.BrowserManager,
    tmp_path: Any,
) -> None:
    target = tmp_path / "shot.png"
    out = manager.run_write_verb("screenshot", None,
                                  {"path": str(target),
                                   "full_page": False})
    assert out == {"path": str(target)}


def test_write_verb_set_cookie(manager: bm.BrowserManager) -> None:
    out = manager.run_write_verb(
        "set_cookie", None,
        {"name": "sess", "value": "abc", "domain": "x.test"},
    )
    assert out["set"] == "sess"
    ctx = manager._tabs["default"].context
    assert ctx.cookies[0]["name"] == "sess"  # type: ignore[attr-defined]


def test_write_verb_new_tab_with_explicit_name(
    manager: bm.BrowserManager,
) -> None:
    out = manager.run_write_verb("new_tab", None, {"name": "alpha"})
    assert out == {"opened": "alpha"}
    assert manager._active_tab == "alpha"
    assert "alpha" in manager._tabs


def test_write_verb_new_tab_falls_back_to_target(
    manager: bm.BrowserManager,
) -> None:
    out = manager.run_write_verb("new_tab", "beta", {})
    assert out == {"opened": "beta"}


def test_write_verb_new_tab_auto_named(manager: bm.BrowserManager) -> None:
    """Không có name + target → auto ``tab-<n>``."""
    out = manager.run_write_verb("new_tab", None, {})
    assert out["opened"].startswith("tab-")


def test_write_verb_close_tab_existing(manager: bm.BrowserManager) -> None:
    manager._open_tab("trash")
    out = manager.run_write_verb("close_tab", None, {"name": "trash"})
    assert out == {"closed": "trash"}
    assert "trash" not in manager._tabs


def test_write_verb_close_tab_missing_no_raise(
    manager: bm.BrowserManager,
) -> None:
    out = manager.run_write_verb("close_tab", None, {"name": "ghost"})
    assert out == {"closed": "ghost"}


def test_write_verb_unknown_raises(manager: bm.BrowserManager) -> None:
    with pytest.raises(ValueError, match="unknown write verb"):
        manager.run_write_verb("hack", None, {})


# ---------------------------------------------------------------------------
# Module-level get_manager / stop_manager / run_*_verb facades
# ---------------------------------------------------------------------------

def test_get_manager_creates_singleton(
    fake_pw: _FakeSyncPlaywrightHandle,
) -> None:
    m1 = bm.get_manager(headless=True)
    m2 = bm.get_manager(headless=False)  # second call returns same instance
    assert m1 is m2
    assert m1._browser is not None


def test_stop_manager_clears_singleton(
    fake_pw: _FakeSyncPlaywrightHandle,
) -> None:
    m1 = bm.get_manager()
    bm.stop_manager()
    assert bm._singleton is None
    m2 = bm.get_manager()
    assert m2 is not m1


def test_stop_manager_safe_when_no_singleton() -> None:
    bm._singleton = None
    bm.stop_manager()  # noop, không raise
    assert bm._singleton is None


def test_run_read_verb_module_facade(
    fake_pw: _FakeSyncPlaywrightHandle,
) -> None:
    out = bm.run_read_verb("text", None, {})
    assert out == "hello world"


def test_run_write_verb_module_facade(
    fake_pw: _FakeSyncPlaywrightHandle,
) -> None:
    out = bm.run_write_verb("scroll", None, {"x": 5, "y": 50})
    assert out == {"scrolled_to": [5, 50]}


# ---------------------------------------------------------------------------
# _safe context manager (helper)
# ---------------------------------------------------------------------------

def test_safe_helper_enter_returns_self() -> None:
    s = bm._safe()
    with s as inner:
        assert inner is s
