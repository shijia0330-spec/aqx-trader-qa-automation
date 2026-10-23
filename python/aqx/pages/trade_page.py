from playwright.sync_api import Page, expect

from aqx.models import Side
from aqx.pages.assets_panel import AssetsPanel
from aqx.pages.edit_position_dialog import EditPositionDialog
from aqx.pages.notifications import Notifications
from aqx.pages.order_panel import OrderPanel


class TradePage:
    PATH = "/web/trade"

    def __init__(self, page: Page) -> None:
        self.page = page
        self.account_type_tag = page.get_by_test_id("account-type-tag")
        self.symbol_search = page.get_by_test_id("symbol-input-search")
        self.symbol_overview = page.get_by_test_id("symbol-overview-id")
        self.order_panel = OrderPanel(page)
        self.assets = AssetsPanel(page)
        self.edit_dialog = EditPositionDialog(page)
        self.notifications = Notifications(page)

    def open(self) -> "TradePage":
        self.page.goto(self.PATH)
        expect(self.symbol_search).to_be_visible()
        return self

    def select_symbol(self, symbol: str) -> None:
        self.symbol_search.fill(symbol)
        self.page.get_by_text(symbol, exact=True).first.click()
        expect(self.symbol_overview).to_contain_text(symbol)

    def account_figures(self) -> tuple[str, str]:
        """Open the account menu and return (balance, free margin) as displayed."""
        self.page.get_by_test_id("account-info").click()
        free_margin = self.page.get_by_test_id("account-info-free-margin-value")
        balance = self.page.get_by_test_id("account-info-balance-value")
        expect(free_margin).to_be_visible()
        expect(balance).to_be_visible()
        figures = (balance.inner_text().strip(), free_margin.inner_text().strip())
        self.page.get_by_test_id("account-info").click()
        expect(free_margin).to_be_hidden()
        return figures

    def place_market_order(
        self,
        side: Side,
        volume: str,
        stop_loss_points: int | None = None,
        take_profit_points: int | None = None,
    ) -> str:
        before = self.assets.settled_open_position_ids()
        self.order_panel.fill_market_order(side, volume, stop_loss_points, take_profit_points)
        self.order_panel.place()
        return self.assets.wait_for_new_id(self.assets.open_position_ids, before)

    def place_one_click_order(self, side: Side, volume: str) -> str:
        before = self.assets.settled_open_position_ids()
        panel = self.order_panel
        panel.open_one_click_tab()
        panel.volume.fill(volume)
        (panel.one_click_buy if side is Side.BUY else panel.one_click_sell).click()
        return self.assets.wait_for_new_id(self.assets.open_position_ids, before)

    def place_buy_stop(self, volume: str, points_above_ask: int) -> str:
        return self._place_stop(Side.BUY, volume, points_above_ask)

    def place_sell_stop(self, volume: str, points_below_bid: int) -> str:
        return self._place_stop(Side.SELL, volume, -points_below_bid)

    def _place_stop(self, side: Side, volume: str, points: int) -> str:
        before = self.assets.settled_pending_order_ids()
        panel = self.order_panel
        panel.open_trade_tab()
        panel.choose_side(side)
        panel.choose_order_type("Stop")
        panel.pending_price.fill(panel.price_offset(side, points))
        panel.volume.fill(volume)
        panel.place()
        return self.assets.wait_for_new_id(self.assets.pending_order_ids, before)
