import re

import pytest
from playwright.sync_api import expect

from aqx.config import Settings
from aqx.models import Side, format_price
from aqx.order_tracker import OrderTracker
from aqx.pages.one_click_settings import OneClickSettings
from aqx.pages.trade_page import TradePage

OFFSET_POINTS = 150
PARTIAL_OPEN_VOLUME = "0.20"
PARTIAL_CLOSE_VOLUME = "0.10"


@pytest.fixture
def open_buy_position(trade_page: TradePage, order_tracker: OrderTracker, settings: Settings) -> str:
    return order_tracker.track_position(trade_page.place_market_order(Side.BUY, settings.volume))


@pytest.mark.p1
@pytest.mark.trading
def test_modify_stop_loss_and_take_profit(trade_page: TradePage, open_buy_position: str):
    """U-04: an open position saves modified Stop Loss and Take Profit."""
    reference = trade_page.order_panel.price_text(Side.SELL)
    point = trade_page.order_panel.point_size()
    entry = trade_page.assets.position(open_buy_position).entry_price
    new_sl = format_price(entry - OFFSET_POINTS * point, like=reference)
    new_tp = format_price(entry + OFFSET_POINTS * point, like=reference)

    trade_page.assets.edit_position(open_buy_position)
    dialog = trade_page.edit_dialog
    dialog.wait_until_open()
    dialog.set_stop_loss(new_sl)
    dialog.set_take_profit(new_tp)
    dialog.update()

    expect(dialog.root).to_be_hidden()
    row = trade_page.assets.open_row(open_buy_position)
    expect(row.get_by_test_id("asset-open-column-stop-loss")).to_have_text(new_sl)
    expect(row.get_by_test_id("asset-open-column-take-profit")).to_have_text(new_tp)
    position = trade_page.assets.position(open_buy_position)
    assert position.stop_loss == float(new_sl)
    assert position.take_profit == float(new_tp)


@pytest.mark.p1
@pytest.mark.trading
def test_modify_stop_loss_to_wrong_side_is_rejected(trade_page: TradePage, open_buy_position: str):
    """V-13: an invalid position Stop Loss modification is rejected."""
    original = trade_page.assets.position(open_buy_position)
    invalid_sl = trade_page.order_panel.price_offset(Side.SELL, points=OFFSET_POINTS)

    trade_page.assets.edit_position(open_buy_position)
    dialog = trade_page.edit_dialog
    dialog.wait_until_open()
    try:
        dialog.set_stop_loss(invalid_sl)
        dialog.update()
        expect(
            trade_page.page.get_by_text(
                re.compile(r"Stop Loss must be less than (?:price|Sell Price)\.")
            )
        ).to_be_visible()
    finally:
        if dialog.root.is_visible():
            dialog.cancel()
    assert trade_page.assets.position(open_buy_position).stop_loss == original.stop_loss


@pytest.mark.p0
@pytest.mark.trading
def test_position_can_be_partially_closed(
    trade_page: TradePage, order_tracker: OrderTracker
):
    """U-05: partially close 0.10 of a 0.20 position."""
    one_click = OneClickSettings(trade_page.page)
    try:
        one_click.turn_off()
        one_click.close_menu()
        order_id = order_tracker.track_position(
            trade_page.place_market_order(Side.BUY, PARTIAL_OPEN_VOLUME)
        )

        assets = trade_page.assets
        assets.partial_close_position(order_id, PARTIAL_CLOSE_VOLUME)

        volume = assets.open_row(order_id).get_by_test_id("asset-open-column-volume")
        expect(volume).to_have_text(str(float(PARTIAL_CLOSE_VOLUME)))
        history_volume = assets.history_value(order_id, "volume", closed_positions=True)
        assert float(history_volume.split("/")[0].strip()) == float(PARTIAL_CLOSE_VOLUME)
    finally:
        one_click.ensure_enabled()
        one_click.close_menu()


@pytest.mark.p0
@pytest.mark.trading
def test_close_position_is_recorded_in_notifications_and_history(
    trade_page: TradePage, order_tracker: OrderTracker, open_buy_position: str
):
    """X-02/L-03: full close appears in notifications and history."""
    position = trade_page.assets.position(open_buy_position)
    entry_text = trade_page.assets.open_row(open_buy_position).get_by_test_id(
        "asset-open-column-entry-price"
    ).inner_text().strip()

    trade_page.assets.close_position(open_buy_position)

    expect(trade_page.assets.open_row(open_buy_position)).to_have_count(0)
    order_tracker.forget_position(open_buy_position)

    notifications = trade_page.notifications
    notifications.open_positions_list()
    expect(notifications.for_order(open_buy_position, "Position Created")).to_have_count(1)
    expect(notifications.for_order(open_buy_position, "Position Closed")).to_have_count(1)
    notifications.close_list()

    expect(trade_page.assets.history_row_for(position.symbol, entry_text).first).to_be_visible()
