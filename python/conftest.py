import re
from pathlib import Path

import pytest
from playwright.sync_api import Browser, expect

from aqx.config import Settings
from aqx.order_tracker import OrderTracker
from aqx.pages.login_page import LoginPage
from aqx.pages.trade_page import TradePage

VIEWPORT = {"width": 1600, "height": 1000}


def pytest_collection_modifyitems(config, items):
    if Settings.from_env().allow_trading:
        return
    skip_trading = pytest.mark.skip(reason="places demo orders; set AQX_ALLOW_TRADING=1 to run")
    for item in items:
        if "trading" in item.keywords:
            item.add_marker(skip_trading)


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings.from_env()


@pytest.fixture(scope="session")
def credentials(settings: Settings) -> Settings:
    if not settings.has_credentials:
        pytest.skip("AQX_LOGIN and AQX_PASSWORD are not set")
    return settings


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, settings: Settings):
    return {**browser_context_args, "base_url": settings.base_url, "viewport": VIEWPORT}


@pytest.fixture(scope="session")
def auth_state(browser: Browser, credentials: Settings, tmp_path_factory) -> Path:
    context = browser.new_context(base_url=credentials.base_url, viewport=VIEWPORT)
    page = context.new_page()
    LoginPage(page).open().login(credentials.login, credentials.password)
    page.wait_for_url(f"**{TradePage.PATH}")
    state = tmp_path_factory.mktemp("auth") / "storage_state.json"
    context.storage_state(path=state)
    context.close()
    return state


@pytest.fixture
def trade_page(new_context, auth_state: Path, settings: Settings) -> TradePage:
    context = new_context(storage_state=auth_state)
    page = TradePage(context.new_page()).open()
    expect(page.account_type_tag).to_have_text(re.compile("demo", re.IGNORECASE))
    page.select_symbol(settings.symbol)
    return page


@pytest.fixture
def order_tracker(trade_page: TradePage):
    tracker = OrderTracker(trade_page)
    yield tracker
    errors = tracker.cleanup()
    if errors:
        pytest.fail("Cleanup failed, remove these orders manually: " + "; ".join(errors))
