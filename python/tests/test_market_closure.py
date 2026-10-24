import re
import time

import pytest
from playwright.sync_api import expect

from aqx.config import Settings
from aqx.models import Side
from aqx.order_tracker import OrderTracker
from aqx.pages.trade_page import TradePage

CLOSED_MESSAGE = re.compile(
    r"(?:market|trading session).{0,40}closed|closed.{0,40}(?:market|trading)",
    re.IGNORECASE,
)
PENDING_POINTS = 100

pytestmark = [
    pytest.mark.p2,
    pytest.mark.trading,
    pytest.mark.market_closed,
]


def _require_closed(trade_page: TradePage, settings: Settings) -> None:
    if not trade_page.market_is_closed():
        pytest.skip(f"{settings.symbol} is open; this test requires a market closure")


def _closed_message(trade_page: TradePage):
    return trade_page.page.get_by_text(CLOSED_MESSAGE).or_(
        trade_page.notifications.toast.filter(has_text=CLOSED_MESSAGE)
    ).last


def _track_unexpected_positions(
    trade_page: TradePage,
    order_tracker: OrderTracker,
    before: set[str],
    observation_seconds: float = 3,
) -> set[str]:
    deadline = time.monotonic() + observation_seconds
    created: set[str] = set()
    while time.monotonic() < deadline:
        created |= trade_page.assets.open_position_ids() - before
        trade_page.page.wait_for_timeout(300)
    for order_id in created:
        order_tracker.track_position(order_id)
    return created


def _create_pending_during_closure(
    trade_page: TradePage,
    order_tracker: OrderTracker,
    settings: Settings,
) -> str | None:
    assets = trade_page.assets
    panel = trade_page.order_panel
    before = assets.settled_pending_order_ids()
    panel.open_trade_tab()
    panel.choose_side(Side.BUY)
    panel.choose_order_type("Stop")
    panel.pending_price.fill(panel.price_offset(Side.BUY, PENDING_POINTS))
    panel.volume.fill(settings.volume)

    if panel.submit.is_disabled():
        expect(_closed_message(trade_page)).to_be_visible()
        assert assets.pending_order_ids() == before
        return None

    panel.place()
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        created = assets.pending_order_ids() - before
        if created:
            assert len(created) == 1, f"Expected one pending order, found {sorted(created)}"
            return order_tracker.track_pending(created.pop())
        if _closed_message(trade_page).is_visible():
            assert assets.pending_order_ids() == before
            return None
        trade_page.page.wait_for_timeout(300)
    raise AssertionError("No pending order or market-closed rejection appeared within 15s")


def test_market_order_is_blocked_while_market_is_closed(
    trade_page: TradePage,
    order_tracker: OrderTracker,
    settings: Settings,
):
    """V-10: a closed market rejects a Market Buy and opens no position."""
    _require_closed(trade_page, settings)
    assets = trade_page.assets
    panel = trade_page.order_panel
    before = assets.settled_open_position_ids()
    panel.fill_market_order(Side.BUY, settings.volume)

    if panel.submit.is_disabled():
        expect(_closed_message(trade_page)).to_be_visible()
    else:
        panel.place()
        expect(_closed_message(trade_page)).to_be_visible()

    created = _track_unexpected_positions(trade_page, order_tracker, before)
    assert not created, f"Market order was accepted while closed: {sorted(created)}"


def test_market_status_and_trading_hours_are_shown_during_closure(
    trade_page: TradePage,
    settings: Settings,
):
    """L-08: closure is indicated and a weekly trading schedule is available."""
    _require_closed(trade_page, settings)
    panel = trade_page.order_panel
    panel.open_trade_tab()
    buy_sell_disabled = (
        panel.one_click_buy.is_visible()
        and panel.one_click_buy.is_disabled()
        and panel.one_click_sell.is_disabled()
    )
    submit_closed = (not panel.submit.is_enabled()) or bool(
        re.search(r"closed", panel.submit.inner_text(), re.I)
    )
    assert buy_sell_disabled or submit_closed or _closed_message(trade_page).is_visible(), (
        "Closed market has neither disabled Buy/Sell controls nor a closure message"
    )

    schedule = panel.trading_hours_text()
    assert re.search(r"GMT\s*[+-]\d{4}", schedule)
    for weekday in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday"):
        assert weekday in schedule
    assert re.search(r"\d{2}:\d{2}\s*-\s*\d{2}:\d{2}", schedule)


def test_pending_order_during_closure_is_pending_or_clearly_rejected(
    trade_page: TradePage,
    order_tracker: OrderTracker,
    settings: Settings,
):
    """C-11: broker policy either accepts a pending order or clearly rejects it."""
    _require_closed(trade_page, settings)
    order_id = _create_pending_during_closure(trade_page, order_tracker, settings)
    if order_id is None:
        return

    assets = trade_page.assets
    assert assets.pending_cell(order_id, "symbol") == settings.symbol
    assert assets.pending_cell(order_id, "order-type") == "BUY STOP"
    assert order_id not in assets.open_position_ids()


def test_pending_order_can_be_cancelled_during_closure(
    trade_page: TradePage,
    order_tracker: OrderTracker,
    settings: Settings,
):
    """X-07: an accepted pending order can be cancelled while closed."""
    _require_closed(trade_page, settings)
    order_id = _create_pending_during_closure(trade_page, order_tracker, settings)
    if order_id is None:
        pytest.skip("Broker configuration rejects pending creation while closed")

    balance_before = trade_page.account_figures()[0]
    assets = trade_page.assets
    assets.delete_pending_order(order_id)
    expect(assets.pending_row(order_id)).to_have_count(0)
    order_tracker.forget_pending(order_id)

    assert re.fullmatch(
        r"cancell?ed",
        assets.history_value(order_id, "state"),
        re.IGNORECASE,
    )
    assert trade_page.account_figures()[0] == balance_before
