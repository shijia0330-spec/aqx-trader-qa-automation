# AQX Demo Environment Limitations

This document explains environment-dependent tests that may be skipped when their required state cannot be created safely on the AQX demo platform.

## Market closure

The `market_closed` tests run only when the selected instrument is closed. They verify that:

- Market orders are blocked without creating a position.
- Closed Buy/Sell controls or a clear closure message is shown with trading hours.
- A pending order is either accepted under the broker configuration or clearly rejected.
- An accepted pending order can be cancelled and is recorded as cancelled.

These tests skip while the market is open. Conversely, tests that require live execution skip when the selected instrument is closed.

The reopening-gap and expiry-through-reopening cases span separate market sessions. They remain documented in `docs/test-cases.md` as C-12 and C-13 and require a persisted two-phase setup before they can be safely automated.

## Selective bulk close by profit or loss

The suite includes tests for:

- Bulk Close Profitable Positions
- Bulk Close Loss Positions

These tests require at least one profitable position and one losing position so they can verify both the selected positions and those that must remain open.

New market positions normally start at a small loss because of the bid/ask spread. The suite opens opposing positions and waits up to 30 seconds for live prices to produce mixed profit and loss. If that does not happen, the tests skip instead of failing.

The tests cannot create this state deterministically because:

- AQX market orders execute at live prices.
- Profit and loss depend on unpredictable market movement.
- The demo platform exposes no test-only endpoint for setting entry prices or unrealised P/L.
- Mocking displayed P/L would not verify the server-side bulk filter.
- Keeping unknown positions for later runs could close orders not owned by the current test.

Bulk Close All, Bulk Delete All, and the empty bulk-close state remain deterministic and are tested normally.

### Future deterministic setup

If AQX provides a test-only fixture API, it should create suite-owned positions with:

- A requested symbol, side, volume, and controlled entry price
- One positive and one negative unrealised P/L
- Returned position IDs for safe cleanup
- Isolation to a dedicated demo account

The selective bulk tests can then replace their market-movement precondition with that fixture.

## Insufficient-margin rejection

The insufficient-margin test needs a valid order whose required margin is greater than the account's free margin.

The dedicated demo account has approximately one million dollars of virtual free margin. EURUSD allows at most 100 lots, and that maximum legal order requires substantially less margin than the account has available.

Entering more than 100 lots does not test insufficient margin: volume validation rejects or caps the value before the server evaluates margin. Submitting such an order could also create an unintended large position if the client clamps it.

The test therefore calculates the required volume and skips safely when no legal order can exceed free margin. A lower-balance account or a test-only balance/margin fixture is required to exercise this rejection deterministically.

## How to interpret these skips

These skips indicate that a required environment precondition was unavailable. They are not treated as product passes or failures. The skip reason includes the observed account or position values so the result can be reviewed.
