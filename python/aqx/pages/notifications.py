from playwright.sync_api import Locator, Page, expect


class Notifications:
    def __init__(self, page: Page) -> None:
        self.toast = page.get_by_test_id("notification-box-description")
        self.bell = page.get_by_test_id("notification-selector")
        self.positions_tab = page.get_by_test_id("tab-notification-type-order")
        self.items = page.get_by_test_id("notification-list-result-item")

    def open_positions_list(self) -> None:
        self.bell.click()
        self.positions_tab.click()

    def close_list(self) -> None:
        self.bell.click()

    def for_order(self, order_id: str, title: str) -> Locator:
        return self.items.filter(has_text=title).filter(has_text=f"Order No. {order_id}")

    def text_for(self, order_id: str, title: str) -> str:
        self.open_positions_list()
        item = self.for_order(order_id, title)
        expect(item.first).to_be_visible()
        text = item.first.inner_text()
        self.close_list()
        return text
