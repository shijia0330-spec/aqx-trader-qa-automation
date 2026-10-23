import pytest
from playwright.sync_api import expect

from aqx.config import Settings
from aqx.models import Side
from aqx.order_tracker import OrderTracker
from aqx.pages.one_click_settings import OneClickSettings
from aqx.pages.trade_page import TradePage

ONE_CLICK_VOLUME = "0.1"


@pytest.mark.p1
@pytest.mark.trading
def test_enabling_one_click_requires_accepting_terms(trade_page: TradePage):
    """U-01: One-Click remains disabled until its terms are accepted."""
    one_click = OneClickSettings(trade_page.page)
    try:
        one_click.turn_off()

        one_click.turn_on()
        one_click.decline()
        assert not one_click.is_enabled()

        one_click.turn_on()
        one_click.accept()
        assert one_click.is_enabled()
    finally:
        one_click.ensure_enabled()


@pytest.mark.p0
@pytest.mark.trading
def test_one_click_buy_opens_and_closes_without_confirmation(
    trade_page: TradePage, order_tracker: OrderTracker, settings: Settings
):
    """F-03: One-Click opens and closes a position without confirmation."""
    one_click = OneClickSettings(trade_page.page)
    confirmation = trade_page.page.get_by_test_id("trade-confirmation-modal")
    try:
        one_click.turn_off()
        one_click.turn_on()
        one_click.accept()
        one_click.close_menu()

        panel = trade_page.order_panel
        panel.open_one_click_tab()
        panel.volume.fill(ONE_CLICK_VOLUME)
        before = trade_page.assets.open_position_ids()
        panel.one_click_buy.click()
        expect(confirmation).to_be_hidden()

        order_id = order_tracker.track_position(
            trade_page.assets.wait_for_new_id(trade_page.assets.open_position_ids, before)
        )
        position = trade_page.assets.position(order_id)
        assert position.symbol == settings.symbol
        assert position.side.lower() == Side.BUY.value
        assert float(position.volume) == float(ONE_CLICK_VOLUME)

        entry_text = (
            trade_page.assets.open_row(order_id)
            .get_by_test_id("asset-open-column-entry-price")
            .inner_text()
            .strip()
        )
        trade_page.assets.open_positions_tab.click()
        trade_page.assets.open_row(order_id).get_by_test_id("asset-open-button-close").click()
        expect(confirmation).to_be_hidden()
        expect(trade_page.assets.open_row(order_id)).to_have_count(0)
        order_tracker.forget_position(order_id)

        expect(trade_page.assets.history_row_for(position.symbol, entry_text).first).to_be_visible()
    finally:
        one_click.ensure_enabled()
        one_click.close_menu()


@pytest.mark.p1
@pytest.mark.trading
def test_buy_asks_for_confirmation_when_one_click_is_off(
    trade_page: TradePage, order_tracker: OrderTracker
):
    """U-02: disabling One-Click restores confirmation before execution."""
    one_click = OneClickSettings(trade_page.page)
    try:
        one_click.turn_off()
        one_click.close_menu()

        before = trade_page.assets.open_position_ids()
        panel = trade_page.order_panel
        panel.buy_side.click()

        ticket_or_confirmation = panel.order_type.or_(
            trade_page.page.get_by_test_id("trade-confirmation-modal")
        )
        expect(ticket_or_confirmation).to_be_visible()
        expect(panel.submit).to_be_visible()
        created = trade_page.assets.open_position_ids() - before
        for order_id in created:
            order_tracker.track_position(order_id)
        assert not created, f"Buy opened a position before confirmation: {sorted(created)}"
    finally:
        one_click.ensure_enabled()
        one_click.close_menu()


@pytest.mark.p1
@pytest.mark.trading
@pytest.mark.parametrize("side", [Side.BUY, Side.SELL], ids=["buy", "sell"])
def test_one_click_order_opens_position_immediately(
    trade_page: TradePage, order_tracker: OrderTracker, settings: Settings, side: Side
):
    """C-04/C-05: One-Click Buy and Sell execute immediately."""
    order_id = order_tracker.track_position(trade_page.place_one_click_order(side, settings.volume))

    position = trade_page.assets.position(order_id)
    assert position.symbol == settings.symbol
    assert position.side.lower() == side.value
    assert float(position.volume) == float(settings.volume)
