# AQX Trader QA Automation

Automated tests for the AQX Trader demo platform, written for the QA Automation Technical Assessment.

The suite covers market orders with Stop Loss and Take Profit, One-Click Trading, Stop pending orders and expiry, position management, bulk operations, trading records and notifications, and consistency of order details across records.

## Documents

- [Requirements](docs/requirements.md): the assessment brief.
- [Test cases](docs/test-cases.md): 67 test cases with priorities, traceability, coverage matrix, and open questions.
- [Environment limitations](docs/environment-limitations.md): conditional skips caused by live-market and demo-account constraints.

## Structure

| Folder | Stack | Status |
|--------|-------|--------|
| `python/` | Python, pytest, pytest-playwright | 39 tests: login, market orders with SL/TP, validation, insufficient margin, One-Click, Buy and Sell Stop, pending edit and specified expiry, position edit and partial/full close, bulk close and bulk delete, records and deals consistency, offline submit, and market closure |
| `typescript/` | TypeScript, Playwright Test | Planned |
| `docs/` | Markdown | Requirements, test cases, assumptions |

Python layout:

| Path | Purpose |
|------|---------|
| `python/aqx/pages/` | Page objects: login page, trade page, order panel, assets panel, edit dialog, notifications |
| `python/aqx/order_tracker.py` | Records orders a test creates and removes only those at teardown |
| `python/conftest.py` | Settings, session login with saved storage state, demo-account guard, trading opt-in |
| `python/tests/` | Test modules, one per feature area |

## Configuration

Copy `.env.example` to `.env` and fill in the demo account details. `.env` is ignored by git, so credentials never enter the repository.

| Variable | Default | Description |
|----------|---------|-------------|
| `AQX_BASE_URL` | `https://aqxtrader.aquariux.com` | Demo platform URL |
| `AQX_LOGIN` | | Demo account number |
| `AQX_PASSWORD` | | Demo account password |
| `AQX_SYMBOL` | `EURUSD` | Instrument used by trading tests |
| `AQX_VOLUME` | `0.01` | Order volume in lots |
| `AQX_ALLOW_TRADING` | unset | Set to `1` to run tests that place or close demo orders |

## Running the Python tests

```bash
cd python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

pytest -m "not trading"                 # login and session tests only; places no orders
AQX_ALLOW_TRADING=1 pytest -m p0        # P0 trading flows
AQX_ALLOW_TRADING=1 pytest              # full suite
AQX_ALLOW_TRADING=1 pytest -m market_closed  # run during a weekend closure
pytest --headed --slowmo 300            # watch the browser
```

On failure, Playwright keeps a trace and screenshot in `python/test-results/`. Open a trace with `playwright show-trace <file>.zip`.

## Safety design

The demo account can hold positions that were not created by the tests, so the suite is written to leave them untouched:

- Tests marked `trading` are skipped unless `AQX_ALLOW_TRADING=1` is set.
- Every trading test first checks that the account badge reads DEMO.
- A test identifies its own order by comparing order IDs before and after placing it, and teardown closes or deletes only those IDs.
- The pending-order delete test places one new Buy Stop after the delete and leaves it for the next regression round. That round deletes that order, then places another. The id is stored in `python/.regression/`, which git ignores. Other pending orders are left alone.
- Bulk Close and Bulk Delete affect every matching order on the account. Those tests read the list first and skip when an order they did not create would be removed.

One-Click Trading is enabled on the demo account. With it enabled, Buy and Close run immediately without a confirmation dialog. Tests that turn it on or off switch it off first, and each one leaves it enabled.

## Environment notes and assumptions

- Tests run against a demo account with virtual funds.
- Default instrument: EURUSD, which trades Monday to Friday. Cases marked "requires environment: market closure" can only run at the weekend.
- Closure tests verify blocked market orders, trading hours, pending-order policy, and cancellation. They skip while the instrument is open; live-execution tests skip while it is closed.
- Reopening-gap and expiry-through-reopening cases require state to persist across separate sessions and remain documented multi-session scenarios.
- Observed on the demo account:
  - Pending orders are Stop only (Buy Stop / Sell Stop); expiry times are in UTC; new pending orders default to Good Till Canceled.
  - EURUSD minimum volume is 0.01 lots (XTIUSD, the default instrument, has a 0.1 minimum).
  - Stop Loss and Take Profit must be at least 50 points from the price on new orders.
  - Buy-side messages: "Stop Loss must be less than price." and "Take Profit must be greater than price."
- Market-closure behaviour that is not yet confirmed is documented as assumptions A1–A4 in the test cases.
- Live-market and account constraints for selective bulk close and insufficient margin are documented in [Environment limitations](docs/environment-limitations.md).

### Conditional skips

- **Bulk Close Profitable/Loss Positions:** New trades normally begin at a loss because of the bid/ask spread. The tests wait for a mix of profitable and losing suite-owned positions, then skip if live prices do not create that state. AQX does not provide a test API for controlled entry prices or P/L.
- **Insufficient margin:** The demo account has approximately $1 million in free margin. EURUSD's maximum legal order is 100 lots, which requires substantially less margin. Values above 100 are rejected or capped by volume validation before margin is evaluated, so the test skips when no legal order can exceed free margin.
- A lower-balance or lower-leverage demo account, a higher-margin instrument, or a test-only balance/position fixture is required to make these scenarios deterministic. Opening many large positions merely to consume margin is intentionally avoided.

## Selectors still to verify

These were not visible during exploration and are inferred from the platform's naming pattern:

| Selector | Used for |
|----------|----------|
| Order type option labelled `Stop` | Choosing a Buy Stop order |
| `trade-input-price` | Pending order price field |
| `asset-pending-button-delete` | Delete button on a pending order row |
| Close/delete confirmation dialog | Only appears if One-Click Trading is disabled |
