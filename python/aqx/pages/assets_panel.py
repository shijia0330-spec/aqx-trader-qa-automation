import re
import time
from collections.abc import Callable
from typing import Literal

from playwright.sync_api import Locator, Page, TimeoutError as PlaywrightTimeoutError, expect

from aqx.models import Position, parse_price

NEW_ORDER_TIMEOUT_S = 15
BulkCloseKind = Literal["all", "profit", "loss"]
BULK_CLOSE_OPTIONS: dict[BulkCloseKind, tuple[str, str]] = {
    "all": ("dropdown-bulk-close-all", "asset-bulk-close-button-option-all"),
    "profit": ("dropdown-bulk-close-profit", "asset-bulk-close-button-option-profit"),
    "loss": ("dropdown-bulk-close-loss", "asset-bulk-close-button-option-loss"),
}
BULK_CLOSE_SUBMIT: dict[BulkCloseKind, str] = {
    "all": "bulk-close-modal-button-submit-all",
    "profit": "bulk-close-modal-button-submit-profit",
    "loss": "bulk-close-modal-button-submit-loss",
}
BULK_CLOSE_LABEL: dict[BulkCloseKind, str] = {
    "all": "All Positions",
    "profit": "Profitable Positions",
    "loss": "Loss Positions",
}


class AssetsPanel:
    """Bottom panel: Open Positions, Pending Orders, Positions History, Orders & Deals."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.open_positions_tab = page.get_by_test_id("tab-asset-order-type-open-positions")
        self.pending_orders_tab = page.get_by_test_id("tab-asset-order-type-pending-orders")
        self.positions_history_tab = page.get_by_test_id(
            "tab-asset-order-type-history-positions-history"
        )
        self.orders_and_deals_tab = page.get_by_test_id("tab-asset-order-type-history-orders-and-deals")
        self.bulk_close_menu = page.get_by_test_id("bulk-close")
        self.bulk_delete_menu = page.get_by_test_id("bulk-delete")
        self.open_rows = page.get_by_test_id("asset-open-list-item")
        self.pending_rows = page.get_by_test_id("asset-pending-list-item")
        self.history_rows = page.get_by_test_id("asset-history-position-list-item")

    def open_position_ids(self) -> set[str]:
        self.open_positions_tab.click()
        cells = self.open_rows.get_by_test_id("asset-open-column-order-id")
        return {text.strip() for text in cells.all_inner_texts()}

    def pending_order_ids(self) -> set[str]:
        self.pending_orders_tab.click()
        cells = self.pending_rows.get_by_test_id("asset-pending-column-order-id")
        return {text.strip() for text in cells.all_inner_texts()}

    def wait_for_new_id(self, read_ids: Callable[[], set[str]], before: set[str]) -> str:
        deadline = time.monotonic() + NEW_ORDER_TIMEOUT_S
        while time.monotonic() < deadline:
            new_ids = read_ids() - before
            if len(new_ids) > 1:
                raise AssertionError(f"Expected one new order, found {sorted(new_ids)}")
            if new_ids:
                return new_ids.pop()
            self.page.wait_for_timeout(500)
        raise AssertionError(f"No new order appeared within {NEW_ORDER_TIMEOUT_S}s")

    def open_row(self, order_id: str) -> Locator:
        return self.open_rows.filter(
            has=self.page.get_by_test_id("asset-open-column-order-id").filter(
                has_text=re.compile(rf"^\s*{order_id}\s*$")
            )
        )

    def pending_row(self, order_id: str) -> Locator:
        return self.pending_rows.filter(
            has=self.page.get_by_test_id("asset-pending-column-order-id").filter(
                has_text=re.compile(rf"^\s*{order_id}\s*$")
            )
        )

    def position(self, order_id: str) -> Position:
        self.open_positions_tab.click()
        row = self.open_row(order_id)

        def cell(column: str) -> str:
            return row.get_by_test_id(f"asset-open-column-{column}").inner_text().strip()

        entry = parse_price(cell("entry-price"))
        assert entry is not None, f"Position {order_id} has no entry price"
        return Position(
            order_id=order_id,
            symbol=cell("symbol"),
            side=cell("order-type"),
            volume=cell("volume"),
            entry_price=entry,
            stop_loss=parse_price(cell("stop-loss")),
            take_profit=parse_price(cell("take-profit")),
        )

    def pending_cell(self, order_id: str, column: str) -> str:
        self.pending_orders_tab.click()
        return (
            self.pending_row(order_id)
            .get_by_test_id(f"asset-pending-column-{column}")
            .inner_text()
            .strip()
        )

    def edit_pending_order(self, order_id: str) -> None:
        self.pending_orders_tab.click()
        self.pending_row(order_id).get_by_test_id("asset-open-button-edit").click()

    def edit_position(self, order_id: str) -> None:
        self.open_positions_tab.click()
        self.open_row(order_id).get_by_test_id("asset-open-button-edit").click()

    def close_position(self, order_id: str) -> None:
        self.open_positions_tab.click()
        self.open_row(order_id).get_by_test_id("asset-open-button-close").click()
        maximum = self.page.get_by_test_id("close-order-input-volume-static-max")
        try:
            expect(maximum).to_be_visible(timeout=2_000)
        except AssertionError:
            self._confirm_if_asked()
        else:
            maximum.click()
            self._submit_close_dialog()
        expect(self.open_row(order_id)).to_have_count(0, timeout=15_000)

    def partial_close_position(self, order_id: str, volume: str) -> None:
        self.open_positions_tab.click()
        self.open_row(order_id).get_by_test_id("asset-open-button-close").click()
        maximum = self.page.get_by_test_id("close-order-input-volume-static-max")
        expect(maximum).to_be_visible()
        dialog = self.page.locator("#overlay-aqx-trader").filter(
            has_text="Confirm To Close Position"
        ).last
        close_volume = dialog.locator('input[name="lotSize"]')
        close_volume.fill(volume)
        close_volume.blur()
        expect(close_volume).to_have_value(volume)
        self._submit_close_dialog()

    def delete_pending_order(self, order_id: str) -> None:
        self.pending_orders_tab.click()
        row = self.pending_row(order_id)
        row.get_by_test_id("asset-open-button-close").click()
        self._confirm_if_asked()

    def settled_open_position_ids(self) -> set[str]:
        """Open-position ids once the tab count and rendered rows agree."""
        return self._ids_matching_tab_count(
            self.open_positions_tab,
            self.open_rows.get_by_test_id("asset-open-column-order-id"),
        )

    def settled_pending_order_ids(self) -> set[str]:
        """Pending-order ids once the tab count and rendered rows agree."""
        return self._ids_matching_tab_count(
            self.pending_orders_tab,
            self.pending_rows.get_by_test_id("asset-pending-column-order-id"),
        )

    def position_profit(self, order_id: str) -> float:
        self.open_positions_tab.click()
        text = self.open_row(order_id).get_by_test_id("asset-open-column-profit").inner_text()
        value = parse_price(text.replace("+", "").replace("$", ""))
        assert value is not None, f"Position {order_id} has no profit: {text!r}"
        return value

    def bulk_close_option(self, kind: BulkCloseKind) -> Locator:
        first, second = BULK_CLOSE_OPTIONS[kind]
        return (
            self.page.get_by_test_id(first)
            .or_(self.page.get_by_test_id(second))
            .or_(self.page.get_by_text(BULK_CLOSE_LABEL[kind], exact=True))
            .last
        )

    def bulk_close(self, kind: BulkCloseKind) -> None:
        self.open_positions_tab.click()
        self.bulk_close_menu.click()
        option = self.bulk_close_option(kind)
        expect(option).to_be_visible()
        option.click()
        submit = self.page.get_by_test_id(BULK_CLOSE_SUBMIT[kind])
        expect(submit).to_be_visible()
        submit.click()

    def bulk_delete_all_pending(self) -> None:
        self.pending_orders_tab.click()
        self.bulk_delete_menu.click()
        option = self.page.get_by_test_id("asset-bulk-delete-button-option-all").or_(
            self.page.get_by_text("All Orders", exact=True)
        ).last
        expect(option).to_be_visible()
        option.click()
        dialog = self.page.locator("#overlay-aqx-trader").filter(has_text="Bulk Delete").last
        submit = self.page.get_by_test_id("bulk-delete-modal-button-submit").or_(
            dialog.get_by_role("button", name="Confirm", exact=True)
        ).last
        expect(submit).to_be_visible()
        submit.click()
        expect(dialog).to_be_hidden()

    def wait_until_ids_gone(
        self,
        read_ids: Callable[[], set[str]],
        expected_gone: set[str],
        timeout_s: float = 30,
    ) -> None:
        deadline = time.monotonic() + timeout_s
        still = expected_gone
        while time.monotonic() < deadline:
            still = read_ids() & expected_gone
            if not still:
                return
            self.page.wait_for_timeout(500)
        raise AssertionError(f"Orders still listed: {sorted(still)}")

    def closed_position_row(self, order_id: str) -> Locator:
        return self.order_history_row(order_id, closed_positions=True)

    def order_state(self, order_id: str) -> Locator:
        self.orders_and_deals_tab.click()
        row = self.history_rows.filter(
            has=self.page.get_by_test_id("asset-history-column-order-id").filter(
                has_text=re.compile(rf"^\s*{re.escape(order_id)}\s*$")
            )
        )
        return row.get_by_test_id("asset-history-column-state")

    def history_order_ids(self) -> list[str]:
        """Order IDs in the visible Orders & Deals list, top to bottom."""
        self.orders_and_deals_tab.scroll_into_view_if_needed()
        self.orders_and_deals_tab.click()
        expect(self.history_rows.first).to_be_visible()
        cells = self.history_rows.get_by_test_id("asset-history-column-order-id")
        return [text.strip() for text in cells.all_inner_texts() if text.strip()]

    def _ids_matching_tab_count(self, tab: Locator, id_cells: Locator) -> set[str]:
        tab.click()
        expect(tab).to_be_visible()
        deadline = time.monotonic() + NEW_ORDER_TIMEOUT_S
        label = ""
        ids: set[str] = set()
        previous: tuple[int, frozenset[str]] | None = None
        empty_since: float | None = None
        while time.monotonic() < deadline:
            label = " ".join(tab.inner_text().split())
            ids = {text.strip() for text in id_cells.all_inner_texts() if text.strip()}
            match = re.search(r"\((\d+)\)", label)
            current = (int(match.group(1)), frozenset(ids)) if match and int(match.group(1)) == len(ids) else None
            if current is not None and current == previous:
                if current[0] > 0:
                    return ids
                empty_since = empty_since or time.monotonic()
                if time.monotonic() - empty_since >= 2:
                    return ids
            else:
                empty_since = None
            previous = current
            self.page.wait_for_timeout(300)
        raise AssertionError(f"Order list did not match its tab count: {label!r}, read {sorted(ids)}")

    def order_history_row(self, order_id: str, *, closed_positions: bool = False) -> Locator:
        """One history row. The table does not render its rows until it is on screen."""
        tab = self.positions_history_tab if closed_positions else self.orders_and_deals_tab
        tab.scroll_into_view_if_needed()
        tab.click()
        row = self.history_rows.filter(
            has=self.page.get_by_test_id("asset-history-column-order-id").get_by_text(
                order_id, exact=True
            )
        )
        expect(row.first).to_be_visible()
        return row.first

    def history_value(self, order_id: str, column: str, *, closed_positions: bool = False) -> str:
        return (
            self.order_history_row(order_id, closed_positions=closed_positions)
            .get_by_test_id(f"asset-history-column-{column}")
            .inner_text()
            .strip()
        )

    def expanded_deal_row(self, order_id: str) -> Locator:
        parent = self.order_history_row(order_id)
        expand = parent.get_by_test_id("asset-history-position-list-item-expand")
        if expand.get_attribute("aria-label") == "Expand row":
            expand.click()
        deal = parent.locator("xpath=following-sibling::tr[1]")
        expect(deal).to_be_visible()
        return deal

    def history_row_for(self, symbol: str, entry_price: str) -> Locator:
        self.positions_history_tab.click()
        return self.history_rows.filter(has_text=symbol).filter(has_text=entry_price)

    def _confirm_if_asked(self) -> None:
        confirm = self.page.get_by_role(
            "button", name=re.compile(r"^(confirm|yes|close position|delete order)$", re.I)
        )
        try:
            confirm.first.click(timeout=2_000)
        except PlaywrightTimeoutError:
            pass

    def _submit_close_dialog(self) -> None:
        dialog = self.page.locator("#overlay-aqx-trader").filter(
            has_text="Confirm To Close Position"
        ).last
        confirm = dialog.get_by_role("button", name="Confirm", exact=True)
        expect(confirm).to_be_enabled()
        confirm.click()
        expect(dialog).to_be_hidden()
