import re
from datetime import date, datetime, timedelta

from playwright.sync_api import Page, expect

from aqx.models import Side, format_price, parse_price


class OrderPanel:
    """Right-hand order panel: One Click, Trade, and Specification tabs."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.one_click_tab = page.get_by_test_id("tab-one-click-trading")
        self.trade_tab = page.get_by_test_id("tab-trade")
        self.buy_side = page.get_by_test_id("trade-button-order-buy")
        self.sell_side = page.get_by_test_id("trade-button-order-sell")
        self.live_buy_price = page.get_by_test_id("trade-live-buy-price")
        self.live_sell_price = page.get_by_test_id("trade-live-sell-price")
        self.order_type = page.get_by_test_id("trade-dropdown-order-type")
        self.expiry = page.get_by_test_id("trade-dropdown-expiry")
        self.expiry_date = page.get_by_test_id("trade-input-expiry-date")
        self.expiry_time = page.get_by_test_id("trade-input-expiry-time")
        self.volume = page.get_by_test_id("trade-input-volume").first
        self.point_size_label = page.get_by_test_id("trade-one-point-equal-label")
        self.pending_price = page.locator('input[name="price"]')
        self.stop_loss_price = page.get_by_test_id("trade-input-stoploss-price").first
        self.stop_loss_points = page.get_by_test_id("trade-input-stoploss-points").first
        self.take_profit_price = page.get_by_test_id("trade-input-takeprofit-price").first
        self.take_profit_points = page.get_by_test_id("trade-input-takeprofit-points").first
        self.submit = page.get_by_test_id("trade-button-order")
        self.one_click_buy = page.get_by_test_id("trade-button-oct-order-buy")
        self.one_click_sell = page.get_by_test_id("trade-button-oct-order-sell")

    def open_trade_tab(self) -> None:
        self.trade_tab.click()
        self.order_type.wait_for()

    def open_one_click_tab(self) -> None:
        if self.one_click_buy.is_visible():
            return
        self.one_click_tab.click()
        self.one_click_buy.wait_for()

    def choose_side(self, side: Side) -> None:
        (self.buy_side if side is Side.BUY else self.sell_side).click()

    def choose_order_type(self, label: str) -> None:
        if self.order_type.inner_text().strip() == label:
            return
        self.order_type.click()
        self.page.get_by_text(re.compile(rf"^{re.escape(label)}$")).last.click()

    def choose_specified_date_and_time(self) -> str:
        """Select Specified Date and Time and a date after the one shown.

        Returns the expiry timestamp the pending list should show.
        """
        self.expiry.click()
        option = self.page.get_by_text("Specified Date and Time", exact=True).last
        expect(option).to_be_visible()
        option.click()
        expect(self.expiry_date).to_be_visible()
        shown = datetime.strptime(self.expiry_date.inner_text().strip(), "%Y-%m-%d").date()
        target = shown + timedelta(days=1)
        self.expiry_date.click()
        self._choose_calendar_day(target)
        expect(self.expiry_date).to_have_text(target.isoformat())
        clock = self.expiry_time.inner_text().strip()
        if clock.count(":") == 1:
            clock = f"{clock}:00"
        return f"{target.isoformat()} {clock}"

    def choose_specified_date(self) -> str:
        """Select Specified Date and a date after the one shown."""
        self.expiry.click()
        option = self.page.get_by_text("Specified Date", exact=True).last
        expect(option).to_be_visible()
        option.click()
        expect(self.expiry_date).to_be_visible()
        shown = datetime.strptime(self.expiry_date.inner_text().strip(), "%Y-%m-%d").date()
        target = shown + timedelta(days=1)
        self.expiry_date.click()
        self._choose_calendar_day(target)
        expect(self.expiry_date).to_have_text(target.isoformat())
        return target.isoformat()

    def _choose_calendar_day(self, target: date) -> None:
        label = target.strftime("%B %Y")
        title = self.page.get_by_role("button", name=label, exact=True)
        for _ in range(2):
            if title.count() and title.last.is_visible():
                break
            self.page.get_by_role("button", name="›", exact=True).last.click()
        expect(title.last).to_be_visible()
        popup = self.page.locator("div").filter(has=title.last).filter(has=self.page.locator("abbr")).last
        day = popup.locator("abbr").filter(has_text=re.compile(rf"^{target.day}$")).last
        day.click()

    def price_text(self, side: Side) -> str:
        locator = self.live_buy_price if side is Side.BUY else self.live_sell_price
        return locator.inner_text()

    def price(self, side: Side) -> float:
        value = parse_price(self.price_text(side))
        assert value is not None, f"No live {side.value} price shown"
        return value

    def point_size(self) -> float:
        match = re.search(r"([\d.]+)\s*$", self.point_size_label.inner_text())
        assert match, "Point size label not found in order panel"
        return float(match.group(1))

    def price_offset(self, side: Side, points: int) -> str:
        reference = self.price_text(side)
        value = self.price(side) + points * self.point_size()
        return format_price(value, like=reference)

    def fill_market_order(
        self,
        side: Side,
        volume: str,
        stop_loss_points: int | None = None,
        take_profit_points: int | None = None,
    ) -> None:
        self.open_trade_tab()
        self.choose_order_type("Market")
        self.choose_side(side)
        self.volume.fill(volume)
        if stop_loss_points is not None:
            self.stop_loss_points.fill(str(stop_loss_points))
        if take_profit_points is not None:
            self.take_profit_points.fill(str(take_profit_points))

    def estimated_margin(self) -> float:
        text = self.page.get_by_test_id("trade-details-margin-required").inner_text()
        match = re.search(r"([\d,]+\.\d+)", text)
        assert match, f"Estimated margin is not shown: {text!r}"
        return float(match.group(1).replace(",", ""))

    def place(self) -> None:
        self.submit.click()
        confirm = self.page.get_by_test_id("trade-confirmation-button-confirm")
        try:
            expect(confirm).to_be_visible(timeout=2_000)
        except AssertionError:
            return
        confirm.click()
        expect(confirm).to_be_hidden()
