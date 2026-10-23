from playwright.sync_api import Page


class LoginPage:
    PATH = "/web/login"

    def __init__(self, page: Page) -> None:
        self.page = page
        self.demo_tab = page.get_by_test_id("tab-login-account-type-demo")
        self.user_id = page.get_by_test_id("login-user-id")
        self.password = page.get_by_test_id("login-password")
        self.submit = page.get_by_test_id("login-submit")

    def open(self) -> "LoginPage":
        self.page.goto(self.PATH)
        self.user_id.wait_for()
        return self

    def login(self, user_id: str, password: str) -> None:
        if self.demo_tab.is_visible():
            self.demo_tab.click()
        self.user_id.fill(user_id)
        self.password.fill(password)
        self.submit.click()
