from playwright.sync_api import Page, expect


class EditPendingDialog:
    """Edit form for an existing pending order."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.root = (
            page.locator("div")
            .filter(has=page.get_by_test_id("edit-order-id-value"))
            .filter(has=page.get_by_test_id("edit-button-order"))
            .last
        )
        self.order_id = page.get_by_test_id("edit-order-id-value")
        self.price = self.root.locator('input[name="price"]')
        self.stop_loss = self.root.get_by_test_id("trade-input-stoploss-price")
        self.take_profit = self.root.get_by_test_id("trade-input-takeprofit-price")
        self.expiry = page.get_by_test_id("edit-dropdown-expiry")
        self.confirm = page.get_by_test_id("edit-button-order")
        self.cancel = page.get_by_test_id("edit-button-cancel")
        self.confirmation_confirm = page.get_by_test_id("trade-confirmation-button-confirm")
        self.confirmation_close = page.get_by_test_id("trade-confirmation-button-close")

    def choose_good_till_day(self) -> None:
        self.expiry.click()
        option = self.page.get_by_text("Good Till Day", exact=True).last
        expect(option).to_be_visible()
        option.click()
        expect(self.expiry).to_have_text("Good Till Day")

    def dismiss(self) -> None:
        if self.confirmation_close.is_visible():
            self.confirmation_close.click()
            expect(self.confirmation_close).to_be_hidden()
        if self.cancel.is_visible():
            self.cancel.click()
            expect(self.cancel).to_be_hidden()

    def save(self) -> None:
        self.confirm.click()
        try:
            expect(self.confirmation_confirm).to_be_visible(timeout=2_000)
        except AssertionError:
            pass
        else:
            self.confirmation_confirm.click()
            expect(self.confirmation_confirm).to_be_hidden()
        expect(self.confirm).to_be_hidden()
