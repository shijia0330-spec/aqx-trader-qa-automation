import math
import re

import pytest
from playwright.sync_api import expect

from aqx.config import Settings
from aqx.models import Side
from aqx.order_tracker import OrderTracker
from aqx.pages.trade_page import TradePage

SL_TP_POINTS = 100


@pytest.mark.p0
@pytest.mark.trading
@pytest.mark.parametrize("side", [Side.BUY, Side.SELL], ids=["buy", "sell"])
def test_market_order_with_stop_loss_and_take_profit(
    trade_page: TradePage, order_tracker: OrderTracker, settings: Settings, side: Side
):
    """C-01/C-02: Market Buy and Sell execute with valid SL and TP."""
    order_id = order_tracker.track_position(
        trade_page.place_market_order(
            side,
            settings.volume,
            stop_loss_points=SL_TP_POINTS,
            take_profit_points=SL_TP_POINTS,
        )
    )

    position = trade_page.assets.position(order_id)
    assert position.symbol == settings.symbol
    assert position.side.lower() == side.value
    assert float(position.volume) == float(settings.volume)
    assert position.stop_loss is not None and position.take_profit is not None
    if side is Side.BUY:
        assert position.stop_loss < position.entry_price < position.take_profit
    else:
        assert position.take_profit < position.entry_price < position.stop_loss


@pytest.mark.p1
@pytest.mark.trading
def test_buy_stop_loss_above_price_is_rejected(
    trade_page: TradePage, order_tracker: OrderTracker, settings: Settings
):
    """V-01: a Buy with Stop Loss above market is rejected."""
    panel = trade_page.order_panel
    before = trade_page.assets.open_position_ids()
    panel.fill_market_order(Side.BUY, settings.volume)
    panel.stop_loss_price.fill(panel.price_offset(Side.BUY, points=200))
    panel.place()

    expect(
        trade_page.page.get_by_text(
            re.compile(r"Stop Loss must be less than (?:price|Sell Price)\.")
        )
    ).to_be_visible()
    _fail_if_order_created(trade_page, order_tracker, before)


@pytest.mark.p1
@pytest.mark.trading
def test_buy_take_profit_below_price_is_rejected(
    trade_page: TradePage, order_tracker: OrderTracker, settings: Settings
):
    """V-02: a Buy with Take Profit below market is rejected."""
    panel = trade_page.order_panel
    before = trade_page.assets.open_position_ids()
    panel.fill_market_order(Side.BUY, settings.volume)
    panel.take_profit_price.fill(panel.price_offset(Side.BUY, points=-200))
    panel.place()

    expect(
        trade_page.page.get_by_text(
            re.compile(r"Take Profit must be greater than (?:price|(?:Buy|Sell) Price)\.")
        )
    ).to_be_visible()
    _fail_if_order_created(trade_page, order_tracker, before)


@pytest.mark.p1
@pytest.mark.trading
def test_zero_volume_is_rejected(trade_page: TradePage, order_tracker: OrderTracker):
    """V-05: an order with zero volume is rejected."""
    panel = trade_page.order_panel
    before = trade_page.assets.open_position_ids()
    panel.fill_market_order(Side.BUY, "0")

    message = trade_page.page.get_by_text("Please enter a valid volume.")
    if not panel.submit.is_disabled():
        panel.place()
    assert panel.submit.is_disabled() or message.is_visible()
    _fail_if_order_created(trade_page, order_tracker, before)


@pytest.mark.p1
@pytest.mark.trading
def test_order_exceeding_free_margin_is_rejected(
    trade_page: TradePage, order_tracker: OrderTracker
):
    """V-08: an otherwise legal order exceeding free margin is rejected."""
    balance_before, free_margin_text = trade_page.account_figures()
    free_margin = _money(free_margin_text)
    before = trade_page.assets.open_position_ids()
    panel = trade_page.order_panel
    panel.fill_market_order(Side.BUY, "1")
    margin_per_lot = panel.estimated_margin()
    if margin_per_lot <= 0:
        pytest.skip(f"Estimated margin for 1 lot is {margin_per_lot}; cannot size an order above free margin")

    lots = math.floor(free_margin / margin_per_lot) + 1
    panel.volume.fill(str(lots))
    maximum = trade_page.page.get_by_text(re.compile(r"Maximum volume is"))
    try:
        expect(maximum).to_be_visible(timeout=3_000)
    except AssertionError:
        over_maximum = False
    else:
        over_maximum = True

    typed = float(panel.volume.input_value())
    required_margin = panel.estimated_margin()
    legal_margin = typed * margin_per_lot
    if over_maximum or required_margin <= free_margin or legal_margin <= free_margin:
        limit = f"volume {lots} is above the maximum" if over_maximum else f"volume {typed:g} needs {required_margin:,.2f}"
        pytest.skip(
            f"Free margin is {free_margin_text} and 1 lot needs {margin_per_lot:,.2f}; "
            f"{limit}, so no accepted Market Buy can be rejected for insufficient margin"
        )

    panel.place()
    expect(trade_page.page.get_by_text(re.compile(r"Insufficient funds to open trade\.|Insufficient balance"))).to_be_visible()
    balance_after, _ = trade_page.account_figures()
    assert balance_after == balance_before
    _fail_if_order_created(trade_page, order_tracker, before)


def _money(text: str) -> float:
    match = re.search(r"([\d,]+\.\d+)", text)
    assert match, f"No amount in {text!r}"
    return float(match.group(1).replace(",", ""))


def _fail_if_order_created(trade_page: TradePage, tracker: OrderTracker, before: set[str]) -> None:
    trade_page.page.wait_for_timeout(2_000)
    created = trade_page.assets.open_position_ids() - before
    for order_id in created:
        tracker.track_position(order_id)
    assert not created, f"Invalid order was accepted: {sorted(created)}"
