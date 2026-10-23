import pytest

from aqx.config import Settings
from aqx.models import Side
from aqx.order_tracker import OrderTracker
from aqx.pages.trade_page import TradePage


@pytest.mark.p1
@pytest.mark.trading
def test_order_is_not_submitted_while_offline(
    trade_page: TradePage, order_tracker: OrderTracker, settings: Settings
):
    """V-15: an offline submission creates no market order."""
    page = trade_page.page
    before = trade_page.assets.open_position_ids()
    trade_page.order_panel.fill_market_order(Side.BUY, settings.volume)

    page.context.set_offline(True)
    try:
        trade_page.order_panel.place()
        page.wait_for_timeout(3_000)
    finally:
        page.context.set_offline(False)

    trade_page.open()
    page.wait_for_timeout(3_000)
    created = trade_page.assets.open_position_ids() - before
    for order_id in created:
        order_tracker.track_position(order_id)
    assert not created, f"Order was submitted while offline: {sorted(created)}"
