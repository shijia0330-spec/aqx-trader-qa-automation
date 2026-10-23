import re

from playwright.sync_api import Page, expect


class OneClickSettings:
    """Account menu switch for One-Click Trading."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.menu_button = page.get_by_test_id("app-setting-dropdown-trigger")
        self.enabled_toggle = page.get_by_test_id("toggle-oct-checked")
        self.disabled_toggle = page.get_by_test_id("toggle-oct")
        self.terms = page.locator("#overlay-aqx-trader").filter(has_text="Terms and Conditions").last
        self.agree = self.terms.get_by_role("button", name=re.compile(r"^agree and continue$", re.I))
        self.cancel = self.terms.get_by_role("button", name=re.compile(r"^cancel$", re.I))

    def open_menu(self) -> None:
        toggle = self.enabled_toggle.or_(self.disabled_toggle)
        if not toggle.is_visible():
            self.menu_button.click()
        expect(toggle).to_be_visible()

    def close_menu(self) -> None:
        toggle = self.enabled_toggle.or_(self.disabled_toggle)
        if toggle.is_visible():
            self.menu_button.click()
        expect(toggle).to_be_hidden()

    def is_enabled(self) -> bool:
        self.open_menu()
        return self.enabled_toggle.is_visible()

    def turn_off(self) -> None:
        if self.terms.is_visible():
            self.cancel.click()
            expect(self.terms).to_be_hidden()
        self.open_menu()
        if self.enabled_toggle.is_visible():
            self.enabled_toggle.click()
        expect(self.disabled_toggle).to_be_visible()

    def turn_on(self) -> None:
        self.open_menu()
        self.disabled_toggle.click()
        expect(self.terms).to_be_visible()

    def decline(self) -> None:
        self.cancel.click()
        expect(self.terms).to_be_hidden()
        self.open_menu()
        expect(self.disabled_toggle).to_be_visible()

    def accept(self) -> None:
        self.agree.click()
        expect(self.terms).to_be_hidden()
        self.open_menu()
        expect(self.enabled_toggle).to_be_visible()

    def ensure_enabled(self) -> None:
        if self.terms.is_visible():
            self.accept()
            return
        self.open_menu()
        if self.disabled_toggle.is_visible():
            self.turn_on()
            self.accept()
