# AQX Trader QA Automation

Automated tests for the AQX Trader demo platform, written for the QA Automation Technical Assessment.

The suite covers market orders with Stop Loss and Take Profit, One-Click Trading, Stop pending orders and expiry, position management, bulk operations, trading records and notifications, and consistency of order details across records.

## Documents

- [Requirements](docs/requirements.md): the assessment brief.
- [Test cases](docs/test-cases.md): 67 test cases with priorities, traceability, coverage matrix, and open questions.

## Planned structure

| Folder | Stack | Purpose |
|--------|-------|---------|
| `python/` | Python, pytest, pytest-playwright | UI tests for the P0 and P1 trading flows |
| `typescript/` | TypeScript, Playwright Test | UI tests for the same flows in JavaScript/TypeScript |
| `docs/` | Markdown | Requirements, test cases, assumptions |

## Configuration

Copy `.env.example` to `.env` and fill in the demo account details. `.env` is ignored by git, so credentials never enter the repository.

| Variable | Description |
|----------|-------------|
| `AQX_BASE_URL` | Demo platform URL |
| `AQX_LOGIN` | Demo account number |
| `AQX_PASSWORD` | Demo account password |

## Environment notes and assumptions

- Tests run against a demo account with virtual funds.
- Default instrument: EURUSD, which trades Monday to Friday. Cases marked "requires environment: market closure" can only run at the weekend.
- Confirmed on the demo account: pending orders are Stop only (Buy Stop / Sell Stop); expiry times are in UTC; EURUSD volume is 0.1 to 100 lots; One-Click volume is 0.1.
- Market-closure behaviour that is not yet confirmed is documented as assumptions A1–A4 in the test cases.
