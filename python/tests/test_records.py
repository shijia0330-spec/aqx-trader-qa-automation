import re
from decimal import Decimal

import pytest
from playwright.sync_api import expect

from aqx.config import Settings
from aqx.models import Side
from aqx.order_tracker import OrderTracker
from aqx.pages.trade_page import TradePage

SL_TP_POINTS = 100
ORDER_VOLUME = "0.10"
PENDING_POINTS = 200
EXPIRY_MINUTES = 3


def _amount(text: str) -> Decimal:
    cleaned = text.strip().replace(",", "").replace("$", "").replace("+", "")
    if cleaned in ("", "--"):
        return Decimal("0")
    return Decimal(cleaned)


def _lots(text: str) -> float:
    return float(text.split("/")[0].strip())


@pytest.mark.p0
@pytest.mark.trading
def test_order_matches_across_notification_position_and_history(
    trade_page: TradePage, order_tracker: OrderTracker, settings: Settings
):
    """D-01: one order has consistent details across all trading records."""
    order_id = order_tracker.track_position(
        trade_page.place_market_order(
            Side.BUY,
            ORDER_VOLUME,
            stop_loss_points=SL_TP_POINTS,
            take_profit_points=SL_TP_POINTS,
        )
    )
    position = trade_page.assets.position(order_id)
    notification = trade_page.notifications.text_for(order_id, "Position Created")

    assert settings.symbol in notification
    assert f"Order No. {order_id}" in notification
    assert re.search(r"\bBUY\b", notification)
    assert _lots(re.search(r"([\d.]+)\s+volume", notification).group(1)) == float(ORDER_VOLUME)
    filled_at = float(re.search(r"at\s+([\d.]+)", notification).group(1))

    assert position.symbol == settings.symbol
    assert position.side.lower() == Side.BUY.value
    assert float(position.volume) == float(ORDER_VOLUME)
    assert position.entry_price == filled_at
    assert position.stop_loss is not None and position.take_profit is not None

    assets = trade_page.assets
    assert assets.history_value(order_id, "symbol") == position.symbol
    assert assets.history_value(order_id, "order-type").lower() == Side.BUY.value
    assert _lots(assets.history_value(order_id, "volume")) == float(ORDER_VOLUME)
    assert float(assets.history_value(order_id, "entry-price")) == position.entry_price
    assert float(assets.history_value(order_id, "stop-loss")) == position.stop_loss
    assert float(assets.history_value(order_id, "take-profit")) == position.take_profit


@pytest.mark.p1
@pytest.mark.trading
def test_deals_show_opening_and_closing_trades(
    trade_page: TradePage, order_tracker: OrderTracker, settings: Settings
):
    """L-06: Deals contains matching opening and closing trades."""
    assets = trade_page.assets
    order_id = order_tracker.track_position(
        trade_page.place_market_order(Side.BUY, settings.volume)
    )
    position = assets.position(order_id)

    assets.close_position(order_id)
    expect(assets.open_row(order_id)).to_have_count(0)
    order_tracker.forget_position(order_id)

    open_row = assets.order_history_row(order_id)
    close_row = open_row.locator("xpath=preceding-sibling::tr[1]")
    expect(close_row).to_be_visible()
    expect(close_row.get_by_test_id("asset-history-position-list-item-expand")).to_be_visible()
    expected_volume = f"{float(settings.volume):g}"
    expect(close_row.get_by_test_id("asset-history-column-order-type")).to_have_text("Sell")
    expect(close_row.get_by_test_id("asset-history-column-volume")).to_have_text(
        f"{expected_volume} / {expected_volume}"
    )
    close_id = close_row.get_by_test_id("asset-history-column-order-id").inner_text().strip()
    assert close_id != order_id

    close_row = assets.order_history_row(close_id)
    assert open_row.get_by_test_id("asset-history-column-order-type").inner_text().lower() == "buy"
    assert close_row.get_by_test_id("asset-history-column-order-type").inner_text().lower() == "sell"
    assert _lots(open_row.get_by_test_id("asset-history-column-volume").inner_text()) == float(
        settings.volume
    )
    assert _lots(close_row.get_by_test_id("asset-history-column-volume").inner_text()) == float(
        settings.volume
    )
    assert float(open_row.get_by_test_id("asset-history-column-entry-price").inner_text()) == (
        position.entry_price
    )
    order_close_price = float(
        close_row.get_by_test_id("asset-history-column-entry-price").inner_text()
    )
    assert open_row.get_by_test_id("asset-history-column-state").inner_text().upper() == "FILLED"
    assert close_row.get_by_test_id("asset-history-column-state").inner_text().upper() == "FILLED"

    opening_deal = assets.expanded_deal_row(order_id)
    closing_deal = assets.expanded_deal_row(close_id)
    assert opening_deal.get_by_test_id("asset-history-column-order-type").inner_text() == "In"
    assert closing_deal.get_by_test_id("asset-history-column-order-type").inner_text() == "Out"
    assert float(opening_deal.get_by_test_id("asset-history-column-volume").inner_text()) == float(
        settings.volume
    )
    assert float(closing_deal.get_by_test_id("asset-history-column-volume").inner_text()) == float(
        settings.volume
    )
    close_price = float(assets.history_value(order_id, "close-price", closed_positions=True))
    assert order_close_price == close_price


@pytest.mark.p1
@pytest.mark.trading
def test_close_profit_matches_balance_change(
    trade_page: TradePage, order_tracker: OrderTracker, settings: Settings
):
    """D-02: realised P/L, commission, and swap reconcile to balance."""
    # Commission on the history row includes the opening charge, so read the balance first.
    balance_before = _amount(trade_page.account_figures()[0])
    order_id = order_tracker.track_position(trade_page.place_market_order(Side.BUY, settings.volume))

    trade_page.assets.close_position(order_id)
    expect(trade_page.assets.open_row(order_id)).to_have_count(0)
    order_tracker.forget_position(order_id)

    assets = trade_page.assets
    realised = sum(
        _amount(assets.history_value(order_id, column, closed_positions=True))
        for column in ("profit", "commission", "swap")
    )
    balance_after = _amount(trade_page.account_figures()[0])
    assert balance_after == balance_before + realised


@pytest.mark.p1
@pytest.mark.trading
def test_order_history_shows_filled_cancelled_and_expired_statuses(
    trade_page: TradePage, order_tracker: OrderTracker, settings: Settings
):
    """L-05: order history records Filled, Cancelled, and Expired statuses."""
    assets = trade_page.assets
    filled_id = order_tracker.track_position(trade_page.place_market_order(Side.BUY, settings.volume))
    assets.close_position(filled_id)
    expect(assets.open_row(filled_id)).to_have_count(0)
    order_tracker.forget_position(filled_id)
    expect(assets.order_state(filled_id)).to_have_text(re.compile(r"filled", re.I))

    cancelled_id = order_tracker.track_pending(
        trade_page.place_buy_stop(settings.volume, PENDING_POINTS)
    )
    assets.delete_pending_order(cancelled_id)
    expect(assets.pending_row(cancelled_id)).to_have_count(0)
    order_tracker.forget_pending(cancelled_id)
    expect(assets.order_state(cancelled_id)).to_have_text(re.compile(r"cancell?ed", re.I))

    panel = trade_page.order_panel
    before = assets.settled_pending_order_ids()
    panel.open_trade_tab()
    panel.choose_side(Side.BUY)
    panel.choose_order_type("Stop")
    expiry_at = panel.choose_specified_date_and_time_after(EXPIRY_MINUTES)
    panel.pending_price.fill(panel.price_offset(Side.BUY, PENDING_POINTS))
    panel.volume.fill(settings.volume)
    panel.place()
    expired_id = order_tracker.track_pending(
        assets.wait_for_new_id(assets.pending_order_ids, before)
    )
    assert assets.pending_cell(expired_id, "expiry") == "Specified Date and Time"
    assert assets.pending_cell(expired_id, "expiry-date") == expiry_at

    assets.wait_until_ids_gone(
        assets.pending_order_ids,
        {expired_id},
        timeout_s=EXPIRY_MINUTES * 60 + 90,
    )
    order_tracker.forget_pending(expired_id)
    expect(assets.order_state(expired_id)).to_have_text(re.compile(r"expired", re.I))

    history_ids = assets.history_order_ids()
    assert filled_id in history_ids, f"Filled order {filled_id} missing from history"
    assert cancelled_id in history_ids, f"Cancelled order {cancelled_id} missing from history"
    assert expired_id in history_ids, f"Expired order {expired_id} missing from history"
    assert history_ids.index(expired_id) < history_ids.index(cancelled_id) < history_ids.index(
        filled_id
    ), f"History is not newest-first: {history_ids[:12]}"


@pytest.mark.p2
@pytest.mark.trading
def test_deleted_pending_order_is_cancelled_in_history(
    trade_page: TradePage, order_tracker: OrderTracker, settings: Settings
):
    """D-03: a deleted pending order is recorded as cancelled."""
    order_id = order_tracker.track_pending(trade_page.place_buy_stop(settings.volume, points_above_ask=200))
    trade_page.assets.delete_pending_order(order_id)

    expect(trade_page.assets.pending_row(order_id)).to_have_count(0)
    order_tracker.forget_pending(order_id)
    state = trade_page.assets.history_value(order_id, "state")
    assert re.fullmatch(r"cancell?ed", state, re.IGNORECASE)
