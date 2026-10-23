import re
import time

import pytest
from playwright.sync_api import Locator, expect

from aqx.config import Settings
from aqx.models import Side
from aqx.order_tracker import OrderTracker
from aqx.pages.assets_panel import AssetsPanel
from aqx.pages.trade_page import TradePage

MIXED_PROFIT_TIMEOUT_S = 30
STOP_DISTANCES = (300, 600, 900)


def _skip_if_listed(order_ids: set[str], reason: str) -> None:
    if order_ids:
        pytest.skip(f"{reason}: {', '.join(sorted(order_ids))}")


def _profits(assets: AssetsPanel, order_ids: set[str]) -> dict[str, float]:
    return {order_id: assets.position_profit(order_id) for order_id in order_ids}


def _ids_with_sign(profits: dict[str, float], sign: str) -> set[str]:
    if sign == "profit":
        return {order_id for order_id, profit in profits.items() if profit > 0}
    return {order_id for order_id, profit in profits.items() if profit < 0}


def _skip_if_sign(profits: dict[str, float], sign: str, reason: str) -> None:
    _skip_if_listed(_ids_with_sign(profits, sign), reason)


def _wait_for_mixed_profit(assets: AssetsPanel, order_ids: set[str]) -> dict[str, float]:
    deadline = time.monotonic() + MIXED_PROFIT_TIMEOUT_S
    profits: dict[str, float] = {}
    while time.monotonic() < deadline:
        profits = _profits(assets, order_ids)
        if _ids_with_sign(profits, "profit") and _ids_with_sign(profits, "loss"):
            return profits
        assets.page.wait_for_timeout(500)
    pytest.skip(f"Market movement did not produce both a profit and a loss: {profits}")


def _option_disabled(option: Locator) -> bool:
    return option.is_disabled() or option.get_attribute("aria-disabled") == "true"


@pytest.mark.p1
@pytest.mark.trading
def test_bulk_close_all_positions(
    trade_page: TradePage, order_tracker: OrderTracker, settings: Settings
):
    """X-03: bulk close removes every suite-created open position."""
    assets = trade_page.assets
    _skip_if_listed(
        assets.settled_open_position_ids(),
        "Bulk close all would close positions this test did not create",
    )
    created = [
        order_tracker.track_position(trade_page.place_market_order(side, settings.volume))
        for side in (Side.BUY, Side.SELL, Side.BUY)
    ]

    assets.bulk_close("all")

    assets.wait_until_ids_gone(assets.open_position_ids, set(created))
    assert assets.settled_open_position_ids() == set()
    for order_id in created:
        expect(assets.closed_position_row(order_id).first).to_be_visible()


@pytest.mark.p1
@pytest.mark.trading
def test_bulk_close_profitable_positions(
    trade_page: TradePage, order_tracker: OrderTracker, settings: Settings
):
    """X-04: bulk close profit removes only profitable positions."""
    assets = trade_page.assets
    existing = assets.settled_open_position_ids()
    _skip_if_sign(
        _profits(assets, existing),
        "profit",
        "Bulk close profitable would close positions this test did not create",
    )
    created = {
        order_tracker.track_position(trade_page.place_market_order(side, settings.volume))
        for side in (Side.BUY, Side.SELL)
    }
    profits = _wait_for_mixed_profit(assets, created)
    foreign = assets.settled_open_position_ids() - created
    _skip_if_sign(
        _profits(assets, foreign),
        "profit",
        "Bulk close profitable would close positions this test did not create",
    )
    profits = _profits(assets, created)

    assets.bulk_close("profit")

    assets.wait_until_ids_gone(assets.open_position_ids, _ids_with_sign(profits, "profit"))
    remaining = assets.settled_open_position_ids()
    assert _ids_with_sign(profits, "profit").isdisjoint(remaining)
    assert _ids_with_sign(profits, "loss") <= remaining
    assert {order_id for order_id, profit in profits.items() if profit == 0} <= remaining
    assert foreign <= remaining


@pytest.mark.p1
@pytest.mark.trading
def test_bulk_close_losing_positions(
    trade_page: TradePage, order_tracker: OrderTracker, settings: Settings
):
    """X-05: bulk close loss removes only losing positions."""
    assets = trade_page.assets
    existing = assets.settled_open_position_ids()
    _skip_if_sign(
        _profits(assets, existing),
        "loss",
        "Bulk close losing would close positions this test did not create",
    )
    created = {
        order_tracker.track_position(trade_page.place_market_order(side, settings.volume))
        for side in (Side.BUY, Side.SELL)
    }
    _wait_for_mixed_profit(assets, created)
    foreign = assets.settled_open_position_ids() - created
    _skip_if_sign(
        _profits(assets, foreign),
        "loss",
        "Bulk close losing would close positions this test did not create",
    )
    profits = _profits(assets, created)

    assets.bulk_close("loss")

    assets.wait_until_ids_gone(assets.open_position_ids, _ids_with_sign(profits, "loss"))
    remaining = assets.settled_open_position_ids()
    assert _ids_with_sign(profits, "loss").isdisjoint(remaining)
    assert _ids_with_sign(profits, "profit") <= remaining
    assert {order_id for order_id, profit in profits.items() if profit == 0} <= remaining
    assert foreign <= remaining


@pytest.mark.p1
@pytest.mark.trading
def test_bulk_delete_all_pending_orders(
    trade_page: TradePage, order_tracker: OrderTracker, settings: Settings
):
    """X-06: bulk delete removes every suite-created pending order."""
    assets = trade_page.assets
    _skip_if_listed(
        assets.settled_pending_order_ids(),
        "Bulk delete would delete pending orders this test did not create",
    )
    created = [
        order_tracker.track_pending(trade_page.place_buy_stop(settings.volume, points))
        for points in STOP_DISTANCES
    ]

    assets.bulk_delete_all_pending()

    assets.wait_until_ids_gone(assets.pending_order_ids, set(created))
    assert assets.settled_pending_order_ids() == set()
    for order_id in created:
        expect(assets.order_state(order_id)).to_have_text(re.compile(r"cancel", re.I))


@pytest.mark.p3
def test_bulk_close_with_no_positions_shows_no_error(trade_page: TradePage):
    """L-02: bulk close has a safe empty state when no positions exist."""
    assets = trade_page.assets
    _skip_if_listed(
        assets.settled_open_position_ids(),
        "Account has open positions, so the empty Bulk Close state is not available",
    )

    assets.open_positions_tab.click()
    assets.bulk_close_menu.click()
    option = assets.bulk_close_option("all")
    empty_message = trade_page.page.get_by_text(
        re.compile(r"no open positions|no positions|no order has been closed", re.I)
    )
    expect(option.or_(empty_message)).to_be_visible()
    showed_empty_state = empty_message.first.is_visible() or (
        option.is_visible() and _option_disabled(option)
    )
    assert showed_empty_state, "Bulk Close is available with no positions and no empty-state message"
    trade_page.page.keyboard.press("Escape")

    expect(trade_page.symbol_search).to_be_visible()
    assert assets.settled_open_position_ids() == set()
