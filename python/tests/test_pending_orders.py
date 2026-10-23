from pathlib import Path

import pytest
from playwright.sync_api import expect

from aqx.config import Settings
from aqx.models import Side, format_price, parse_price
from aqx.order_tracker import OrderTracker
from aqx.pages.edit_pending_dialog import EditPendingDialog
from aqx.pages.trade_page import TradePage

POINTS_ABOVE_ASK = 200
POINTS_BELOW_BID = 200
PENDING_SEED = Path(__file__).resolve().parents[1] / ".regression" / "pending-order-id"


@pytest.mark.p0
@pytest.mark.trading
def test_buy_stop_order_is_listed_as_pending(
    trade_page: TradePage, order_tracker: OrderTracker, settings: Settings
):
    """C-06/C-08: a Buy Stop is listed pending with GTC expiry."""
    order_id = order_tracker.track_pending(
        trade_page.place_buy_stop(settings.volume, POINTS_ABOVE_ASK)
    )

    assets = trade_page.assets
    assert assets.pending_cell(order_id, "symbol") == settings.symbol
    assert assets.pending_cell(order_id, "order-type") == "BUY STOP"
    assert assets.pending_cell(order_id, "expiry") == "Good Till Canceled"
    assert order_id not in assets.open_position_ids()


@pytest.mark.p1
@pytest.mark.trading
def test_sell_stop_order_is_listed_as_pending(
    trade_page: TradePage, order_tracker: OrderTracker, settings: Settings
):
    """C-07: a Sell Stop is listed as pending and opens no position."""
    order_id = order_tracker.track_pending(
        trade_page.place_sell_stop(settings.volume, POINTS_BELOW_BID)
    )

    assets = trade_page.assets
    assert assets.pending_cell(order_id, "symbol") == settings.symbol
    assert assets.pending_cell(order_id, "order-type") == "SELL STOP"
    assert float(assets.pending_cell(order_id, "volume").split("/")[0]) == float(settings.volume)
    assert order_id not in assets.open_position_ids()


@pytest.mark.p1
@pytest.mark.trading
def test_pending_order_can_expire_on_a_specified_date(
    trade_page: TradePage, order_tracker: OrderTracker, settings: Settings
):
    """Expiry coverage: a pending order saves a specified future date."""
    panel = trade_page.order_panel
    before = trade_page.assets.settled_pending_order_ids()
    panel.open_trade_tab()
    panel.choose_side(Side.BUY)
    panel.choose_order_type("Stop")
    expiry_date = panel.choose_specified_date()
    panel.pending_price.fill(panel.price_offset(Side.BUY, POINTS_ABOVE_ASK))
    panel.volume.fill(settings.volume)
    panel.place()
    order_id = order_tracker.track_pending(
        trade_page.assets.wait_for_new_id(trade_page.assets.pending_order_ids, before)
    )

    assets = trade_page.assets
    assert assets.pending_cell(order_id, "expiry") == "Specified Date"
    assert assets.pending_cell(order_id, "expiry-date").startswith(expiry_date)
    assert order_id not in assets.open_position_ids()


@pytest.mark.p1
@pytest.mark.trading
def test_pending_order_can_expire_at_a_specified_date_and_time(
    trade_page: TradePage, order_tracker: OrderTracker, settings: Settings
):
    """Expiry coverage: a pending order saves a specified future timestamp."""
    panel = trade_page.order_panel
    before = trade_page.assets.settled_pending_order_ids()
    panel.open_trade_tab()
    panel.choose_side(Side.BUY)
    panel.choose_order_type("Stop")
    expiry_at = panel.choose_specified_date_and_time()
    panel.pending_price.fill(panel.price_offset(Side.BUY, POINTS_ABOVE_ASK))
    panel.volume.fill(settings.volume)
    panel.place()
    order_id = order_tracker.track_pending(
        trade_page.assets.wait_for_new_id(trade_page.assets.pending_order_ids, before)
    )

    assets = trade_page.assets
    assert assets.pending_cell(order_id, "expiry") == "Specified Date and Time"
    assert assets.pending_cell(order_id, "expiry-date") == expiry_at
    assert order_id not in assets.open_position_ids()


@pytest.mark.p1
@pytest.mark.trading
def test_pending_order_price_protection_and_expiry_can_be_changed(
    trade_page: TradePage, order_tracker: OrderTracker, settings: Settings
):
    """U-03: pending price, SL/TP, and expiry can be modified."""
    order_id = order_tracker.track_pending(
        trade_page.place_buy_stop(settings.volume, POINTS_ABOVE_ASK)
    )
    panel = trade_page.order_panel
    new_price = panel.price_offset(Side.BUY, points=150)
    stop = parse_price(new_price)
    assert stop is not None
    stop_loss = format_price(stop - 100 * panel.point_size(), like=new_price)
    take_profit = format_price(stop + 100 * panel.point_size(), like=new_price)

    trade_page.assets.edit_pending_order(order_id)
    dialog = EditPendingDialog(trade_page.page)
    try:
        expect(dialog.order_id).to_have_text(order_id)
        dialog.stop_loss.fill(stop_loss)
        dialog.take_profit.fill(take_profit)
        dialog.price.fill(new_price)
        dialog.price.blur()
        dialog.save()
    finally:
        dialog.dismiss()

    assets = trade_page.assets
    row = assets.pending_row(order_id)
    expect(row.get_by_test_id("asset-pending-column-entry-price")).to_have_text(new_price)
    expect(row.get_by_test_id("asset-pending-column-stop-loss")).to_have_text(stop_loss)
    expect(row.get_by_test_id("asset-pending-column-take-profit")).to_have_text(take_profit)
    assert assets.pending_cell(order_id, "order-id") == order_id
    assert parse_price(assets.pending_cell(order_id, "entry-price")) == stop
    assert parse_price(assets.pending_cell(order_id, "stop-loss")) == parse_price(stop_loss)
    assert parse_price(assets.pending_cell(order_id, "take-profit")) == parse_price(take_profit)

    assets.edit_pending_order(order_id)
    dialog = EditPendingDialog(trade_page.page)
    try:
        expect(dialog.order_id).to_have_text(order_id)
        dialog.choose_good_till_day()
        dialog.save()
    finally:
        dialog.dismiss()

    expect(assets.pending_row(order_id).get_by_test_id("asset-pending-column-expiry")).to_have_text(
        "Good Till Day"
    )
    assert assets.pending_cell(order_id, "expiry") == "Good Till Day"


def _pending_seed_id() -> str | None:
    if not PENDING_SEED.exists():
        return None
    order_id = PENDING_SEED.read_text().strip()
    return order_id or None


def _keep_pending_seed(order_id: str) -> None:
    PENDING_SEED.parent.mkdir(parents=True, exist_ok=True)
    PENDING_SEED.write_text(order_id + "\n")


@pytest.mark.p1
@pytest.mark.trading
def test_pending_order_can_be_deleted(
    trade_page: TradePage, order_tracker: OrderTracker, settings: Settings
):
    """X-01: delete a pending order and seed the next regression run."""
    assets = trade_page.assets
    seed_id = _pending_seed_id()
    if seed_id and seed_id in assets.pending_order_ids():
        order_id = order_tracker.track_pending(seed_id)
    else:
        order_id = order_tracker.track_pending(
            trade_page.place_buy_stop(settings.volume, POINTS_ABOVE_ASK)
        )

    assets.delete_pending_order(order_id)

    expect(assets.pending_row(order_id)).to_have_count(0)
    order_tracker.forget_pending(order_id)
    _keep_pending_seed(trade_page.place_buy_stop(settings.volume, POINTS_ABOVE_ASK))
