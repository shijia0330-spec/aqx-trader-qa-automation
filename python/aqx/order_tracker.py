from aqx.pages.trade_page import TradePage


class OrderTracker:
    """Records orders a test creates so teardown removes only those, never pre-existing ones."""

    def __init__(self, trade_page: TradePage) -> None:
        self.trade_page = trade_page
        self.positions: list[str] = []
        self.pending_orders: list[str] = []

    def track_position(self, order_id: str) -> str:
        self.positions.append(order_id)
        return order_id

    def track_pending(self, order_id: str) -> str:
        self.pending_orders.append(order_id)
        return order_id

    def forget_position(self, order_id: str) -> None:
        self.positions.remove(order_id)

    def forget_pending(self, order_id: str) -> None:
        self.pending_orders.remove(order_id)

    def cleanup(self) -> list[str]:
        errors: list[str] = []
        assets = self.trade_page.assets
        for order_id in self.positions:
            try:
                if order_id in assets.settled_open_position_ids():
                    assets.close_position(order_id)
            except Exception as exc:
                errors.append(f"position {order_id}: {exc}")
        for order_id in self.pending_orders:
            try:
                if order_id in assets.settled_pending_order_ids():
                    assets.delete_pending_order(order_id)
            except Exception as exc:
                errors.append(f"pending order {order_id}: {exc}")
        return errors
