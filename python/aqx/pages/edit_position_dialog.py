from playwright.sync_api import Page


class EditPositionDialog:
    def __init__(self, page: Page) -> None:
        self.root = page.get_by_test_id("edit-confirmation-modal")
        self.stop_loss_price = self.root.get_by_test_id("trade-input-stoploss-price")
        self.take_profit_price = self.root.get_by_test_id("trade-input-takeprofit-price")
        self.update_button = self.root.get_by_test_id("edit-button-order")
        self.cancel_button = self.root.get_by_test_id("edit-button-cancel")

    def wait_until_open(self) -> None:
        self.root.wait_for()

    def set_stop_loss(self, price: str) -> None:
        self.stop_loss_price.fill(price)

    def set_take_profit(self, price: str) -> None:
        self.take_profit_price.fill(price)

    def update(self) -> None:
        self.update_button.click()

    def cancel(self) -> None:
        self.cancel_button.click()
        self.root.wait_for(state="hidden")
