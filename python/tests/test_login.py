import re

import pytest
from playwright.sync_api import Page, expect

from aqx.config import Settings
from aqx.pages.login_page import LoginPage
from aqx.pages.trade_page import TradePage


@pytest.mark.p0
def test_valid_credentials_open_trade_page(page: Page, credentials: Settings):
    """Login: valid demo credentials open the authenticated trade page."""
    LoginPage(page).open().login(credentials.login, credentials.password)

    expect(page).to_have_url(re.compile(rf"{TradePage.PATH}$"))
    expect(TradePage(page).account_type_tag).to_have_text(re.compile("demo", re.IGNORECASE))


@pytest.mark.p1
def test_wrong_password_stays_on_login_page(page: Page, credentials: Settings):
    """Login: invalid credentials do not create an authenticated session."""
    login_page = LoginPage(page).open()
    login_page.login(credentials.login, "wrong-password-123")

    expect(page.get_by_text("Invalid credentials, please try again.")).to_be_visible()
    expect(page).to_have_url(re.compile(rf"{LoginPage.PATH}$"))
    expect(login_page.submit).to_be_visible()


@pytest.mark.p1
def test_trade_page_redirects_to_login_without_session(page: Page):
    """P-01: unauthenticated trade-page access redirects to login."""
    page.goto(TradePage.PATH)

    expect(page).to_have_url(re.compile(rf"{LoginPage.PATH}$"))
    expect(LoginPage(page).user_id).to_be_visible()
