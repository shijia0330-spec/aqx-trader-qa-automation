# AQX Trader Trading Functionality Test Cases

## Document Information

- Requirement source: [requirements.md](requirements.md) (QA Automation Technical Assessment)
- External references: Aquariux public articles (One-Click Trading, Bulk Close); see Platform References
- Scope: market orders with SL/TP, One-Click Trading, Stop pending orders and expiry, position management, bulk operations, trading records and notifications, cross-record consistency. Excludes deposits and withdrawals, chart analysis, and the mobile app
- Test data: demo account (virtual funds); default instrument EURUSD (FX, trades Monday to Friday). Account and password are injected through `TEST_USERNAME` and `TEST_PASSWORD`; no plaintext credentials are stored in this document
- Confirmed on the demo account: the only pending order type offered is Stop (Buy Stop / Sell Stop). Limit and Stop Limit orders are not available
- Confirmed: pending order expiry times are based on UTC
- Confirmed EURUSD volume limits: minimum 0.1 lots, maximum 100 lots (step size still open)
- Confirmed Buy-side SL/TP validation messages: `Stop Loss must be less than price.` and `Take Profit must be greater than price.`
- Confirmed One-Click Trading volume: minimum 0.1 lots; these tests use 0.1 as the One-Click volume
- Structure: standard 3 levels (feature → scenario → checkpoint)
- Open questions: 8

## Platform References

- Aquariux public articles provide the following platform facts. They are used as test references and marked "Source: Aquariux" in checkpoints:
  - One-Click Trading is available on desktop only. Users must accept the terms of use before enabling it. Once enabled, a single click on the price panel or order book opens or closes a position without a confirmation dialog.
  - Bulk Close can close all positions at once, or filter by profit or loss.
  - On desktop, SL/TP can be modified by dragging on the chart.
- The MT5 version of AQX Trader offers Stop Limit orders, but the demo account used here offers only Stop pending orders, so Stop Limit is out of scope.
- Pending order expiry options, minimum volume, and minimum stop distance are not documented publicly and are listed as open questions.

## Requirement Traceability

| Requirement | Test case IDs | Notes |
|-------------|---------------|-------|
| 1. Market orders + Stop Loss / Take Profit | F-01, C-01–C-03, V-01–V-09 | Positive path, SL/TP side validation, volume boundaries, margin, duplicate submit |
| 2. Market orders + One-Click Trading | F-03, U-01–U-02, C-04–C-05 | Terms acceptance, single-click execution, confirmation restored when disabled (Source: Aquariux) |
| 3. Pending order types and expiry | F-02, C-06–C-10, V-11–V-12, U-03, X-01 | Buy Stop and Sell Stop, expiry states, modify, delete, trigger |
| 4. View, modify, partially close, close positions | F-01, L-01, U-04–U-05, V-13–V-14, X-02 | Position fields, SL/TP modification, partial-close boundaries, full close |
| 5. Bulk close and bulk delete | X-03–X-06, L-02 | All, profitable, losing, bulk delete pending orders, empty state |
| 6. Transactions, notifications, history | L-03–L-07 | Success and failure notifications, order history, deals, empty state |
| 7. Cross-record consistency | D-01–D-03 | Order ID, price, status, P/L and balance match |
| Assumption 3. Market closure and environment limits | V-10, L-08, C-11–C-13, X-07, T-08 | Market orders blocked with a clear message; schedule shown; pending create/cancel under A1–A2; reopening gap fill (A3); expiry during closure |
| Login and session | P-01, T-07 | Unauthenticated access blocked, session timeout |
| Network errors | V-15–V-19 | Not submitted while offline; submit timeouts: accepted order discoverable, rejected order absent, no duplicate on retry, uncertain status communicated |
| Not yet specified | T-01–T-08 | Expiry, volume, stop distance, One-Click defaults, bulk failure, filters, session, market-closed messages |

## Core Flow Tests

### Flow 1: Full market order lifecycle from open to close

#### F-01 Open a market Buy with SL/TP, modify, partially close, and close <!-- P0 -->
- Logged in to the demo account, record balance B0. On the EURUSD order ticket choose Market, Buy, volume 0.20, SL = current Bid − 50 points, TP = current Ask + 50 points, and submit.
- The execution notification shows EURUSD, Buy, 0.20 and the fill price. Positions shows one new row: side Buy, volume 0.20, SL and TP equal to the submitted values.
- Modify the position's SL to current Bid − 80 points and save. The list shows the new SL.
- Partially close 0.10. The position's remaining volume is 0.10, and order history shows a new 0.10 close record.
- Close the remaining 0.10. The position disappears from Positions; account balance = B0 + the sum of realised P/L from both closes (including commission and swap).

### Flow 2: Pending order from creation to deletion

#### F-02 Create, modify, and delete a Buy Stop order <!-- P0 -->
- Logged in, on the EURUSD order ticket choose Buy Stop, price = current Ask + 100 points, volume 0.10, expiry left at the platform default, and submit.
- Pending Orders shows one new row whose type (Buy Stop), price, volume, and expiry match the submitted values. No position is opened.
- Modify the order price to current Ask + 150 points and save. The list shows the new price.
- Delete the order. It no longer appears in Pending Orders, and its status in order history is Cancelled (or the platform's equivalent).

### Flow 3: Open and close with One-Click Trading

#### F-03 Single-click execution after enabling One-Click Trading <!-- P0 -->
- Logged in on desktop, enable One-Click Trading in settings and accept the terms of use (Source: Aquariux).
- Click Buy on the EURUSD price panel. No confirmation dialog appears; one Buy position opens immediately with volume 0.1 (the One-Click volume).
- Close that position with one click. No confirmation dialog appears; the position disappears and order history shows a new close record.

## Detailed Functional Tests

### 1. Market orders and SL/TP

#### C-01 Market Buy with SL and TP executes <!-- P0 -->
- Market, Buy, EURUSD, volume 0.10, SL = Bid − 50 points, TP = Ask + 50 points; submit.
- A new Buy position opens; its open price matches the execution notification, and SL and TP match the submitted values.

#### C-02 Market Sell with SL and TP executes <!-- P0 -->
- Market, Sell, EURUSD, volume 0.10, SL = Ask + 50 points, TP = Bid − 50 points; submit.
- A new Sell position opens; its open price matches the execution notification, and SL and TP match the submitted values.

#### V-01 Buy order rejected when SL is above current Bid <!-- P1 -->
- Market, Buy, SL = current Bid + 20 points; submit.
- The order is rejected or the submit button is disabled, the message `Stop Loss must be less than price.` is shown, and no position opens.
- Boundary: on a Buy Stop at fixed price P, SL = P is rejected with the same message (the rule is strictly less than).

#### V-02 Buy order rejected when TP is below current Ask <!-- P1 -->
- Market, Buy, TP = current Ask − 20 points; submit.
- The order is rejected with the message `Take Profit must be greater than price.`, and no position opens.
- Boundary: on a Buy Stop at fixed price P, TP = P is rejected with the same message (the rule is strictly greater than).

#### V-03 Sell order rejected when SL is below current Ask <!-- P1 -->
- Market, Sell, SL = current Ask − 20 points; submit.
- The order is rejected with the Sell-side invalid SL message, and no position opens (wording pending T-03).

#### V-04 Sell order rejected when TP is above current Bid <!-- P1 -->
- Market, Sell, TP = current Bid + 20 points; submit.
- The order is rejected with the Sell-side invalid TP message, and no position opens (wording pending T-03).

#### V-05 Volume of 0 rejected <!-- P1 -->
- Market, Buy, enter volume 0; submit.
- The submit button is disabled or an invalid volume message is shown, and no position opens.

#### V-06 Minimum volume boundary <!-- P2 -->
- EURUSD minimum volume is 0.1; read step S from the instrument specification.
- Volume 0.1 − S is rejected; volumes 0.1 and 0.1 + S execute successfully (step S pending T-02).

#### V-07 Maximum volume boundary <!-- P2 -->
- EURUSD maximum volume is 100.
- Volume 100 + S is rejected with an over-limit message. Whether 100 itself executes depends on free margin and is judged by V-08 (step S pending T-02).

#### V-08 Rejected when free margin is insufficient <!-- P1 -->
- Choose a volume whose required margin exceeds the account's Free Margin and submit a Market Buy.
- The order is rejected with an insufficient margin message; balance and positions are unchanged.

#### V-09 Non-numeric or negative volume rejected <!-- P2 -->
- Enter volume `abc`, `-0.10`, and `0.1.0` in turn.
- The field rejects the input or submission shows a format error, and no order request is sent.

#### C-03 Double-clicking submit creates only one order <!-- P1 -->
- Fill a valid Market Buy ticket and double-click the submit button quickly.
- Positions shows only one new row, and the execution notification appears only once.

#### V-10 Market order rejected while market is closed <!-- P2 -->
- Submit a Market Buy on EURUSD during market closure (weekend).
- The order is not executed: it is rejected with a clear message that the market is closed, and no position opens (requires environment: market closure; exact wording pending T-08).

### 2. One-Click Trading

#### U-01 Enabling One-Click Trading requires accepting terms <!-- P1 -->
- Turn on One-Click Trading in settings; a terms of use dialog appears.
- If the terms are declined or closed, the toggle stays off; after accepting, the toggle is on (Source: Aquariux).

#### C-04 One-Click Buy executes immediately <!-- P1 -->
- With One-Click Trading on, click Buy on the EURUSD price panel.
- No confirmation dialog appears; one click opens one Buy position with volume 0.1.

#### C-05 One-Click Sell executes immediately <!-- P1 -->
- With One-Click Trading on, click Sell on the EURUSD price panel.
- No confirmation dialog appears; one Sell position opens with volume 0.1.

#### U-02 Confirmation restored after disabling One-Click Trading <!-- P1 -->
- Turn off One-Click Trading in settings, then click Buy on the price panel.
- The order ticket or a confirmation dialog opens, and no position opens before confirmation.

### 3. Pending orders (Stop) and expiry

#### C-06 Create a Buy Stop order <!-- P0 -->
- Buy Stop, price = Ask + 100 points, volume 0.10; submit.
- Pending Orders shows a new Buy Stop row with matching price and volume; no position opens.

#### C-07 Create a Sell Stop order <!-- P1 -->
- Sell Stop, price = Bid − 100 points, volume 0.10; submit.
- Pending Orders shows a new Sell Stop row with matching price and volume; no position opens.

#### V-11 Stop order rejected when price is on the wrong side <!-- P1 -->
- Submit Buy Stop at Ask − 50 points, and Sell Stop at Bid + 50 points.
- Both submissions are rejected with an invalid price message; Pending Orders has no new rows.

#### C-08 Good Till Cancelled expiry is saved <!-- P2 -->
- Create a Buy Stop order at Ask + 200 points with expiry Good Till Cancelled; submit.
- Pending Orders shows expiry GTC with no expiry time (option name pending T-01).

#### C-09 Order with a specified expiry time expires on time <!-- P1 -->
- Buy Stop, price = Ask + 200 points, expiry = current UTC time + 3 minutes; submit and record expiry time T (UTC). Pending Orders shows expiry time T in UTC.
- At T − 1 minute the order is still in Pending Orders; at T + 1 minute it has left Pending Orders and its order history status is Expired (expiry granularity pending T-01).

#### V-12 Rejected when expiry time is in the past <!-- P2 -->
- Set a Buy Stop expiry to current UTC time − 1 minute; submit.
- Submission is rejected or the date picker disallows the value; Pending Orders has no new rows.

#### U-03 Modify pending order price, SL/TP, and expiry <!-- P1 -->
- For an existing Buy Stop, change price to Ask + 150 points and change SL, TP, and expiry; save.
- Pending Orders shows all four updated values, and the order ID is unchanged.

#### X-01 Delete a pending order <!-- P1 -->
- Delete an existing pending order and confirm.
- The order leaves Pending Orders, its order history status is Cancelled, and balance is unchanged.

#### C-10 Pending order converts to a position when price is reached <!-- P2 -->
- Create a Buy Stop at price = Ask + 2 points and wait for the price to rise to it.
- When reached, the order leaves Pending Orders, Positions shows the corresponding Buy position, and order history status is Filled (requires environment: market must move to the order price).

### 4. Viewing and managing positions

#### L-01 Positions list shows all fields and updates P/L in real time <!-- P1 -->
- With an existing EURUSD Buy position, open Positions.
- The row shows symbol, side, volume, open price, current price, SL, TP, floating P/L, and open time; floating P/L changes as the current price changes.

#### U-04 Modify position SL/TP <!-- P1 -->
- For a Buy position, change SL to Bid − 80 points and TP to Ask + 80 points; save.
- The position shows the new SL and TP; order ID and volume are unchanged.

#### V-13 Rejected when position SL is modified to the wrong side <!-- P1 -->
- For a Buy position, change SL to Bid + 20 points; save.
- The change is rejected with the message `Stop Loss must be less than price.`, and the position keeps its original SL.

#### U-05 Partial close <!-- P1 -->
- Partially close 0.10 of a 0.20 position.
- Remaining volume is 0.10; order history shows a new 0.10 close record with close price and realised P/L.

#### V-14 Partial close volume boundaries <!-- P2 -->
- On a 0.30 position, enter close volumes 0.30 + S, 0.1 − S, 0.1, and finally the full remaining volume, in turn.
- 0.30 + S is rejected (more than the position); 0.1 − S is rejected (below the 0.1 minimum); 0.1 succeeds leaving 0.20; closing the remaining 0.20 equals a full close.

#### X-02 Full close <!-- P0 -->
- Close one position.
- The position leaves Positions; order history shows a new close record; the balance change equals that trade's realised P/L.

### 5. Bulk operations

#### X-03 Bulk close all positions <!-- P1 -->
- Hold 3 positions (both profitable and losing), choose close all in Bulk Close, and confirm.
- Positions is empty, and order history shows 3 new close records (Source: Aquariux).

#### X-04 Bulk close profitable positions <!-- P1 -->
- Hold both profitable and losing positions; choose close profitable in Bulk Close.
- Only positions with floating P/L > 0 at execution are closed; losing positions remain.

#### X-05 Bulk close losing positions <!-- P1 -->
- Hold both profitable and losing positions; choose close losing in Bulk Close.
- Only positions with floating P/L < 0 at execution are closed; profitable positions remain.

#### X-06 Bulk delete all pending orders <!-- P1 -->
- With 3 pending Stop orders, run bulk delete and confirm.
- Pending Orders is empty, and the 3 orders show status Cancelled in order history.

#### L-02 Bulk close with no positions shows no error <!-- P3 -->
- Open Bulk Close when the account has no positions.
- The button is disabled or a "no positions to close" message appears; the page shows no error.

### 6. Transactions, notifications, and history

#### L-03 Successful order notification shows correct details <!-- P1 -->
- Submit a Market Buy 0.10 EURUSD.
- The notification shows symbol, side, volume, fill price, and success status, matching the new position.

#### L-04 Failed order notification shows the reason <!-- P2 -->
- Trigger the insufficient-margin order from V-08.
- The notification shows failure status and reason, and no fill price.

#### L-05 Order history shows each final status <!-- P1 -->
- Complete one filled order, one deleted pending order, and one expired pending order, then open order history.
- The three records show Filled, Cancelled, and Expired, in correct time order (filter and pagination pending T-06).

#### L-06 Deals show opening and closing trades <!-- P1 -->
- Open and close one position, then open the deals/transactions view.
- It contains both the opening and closing deals, with side, volume, and price matching the order.

#### L-07 New account history shows empty state <!-- P3 -->
- Open order history and transactions on a new demo account with no trades.
- An empty-state message is shown, and the page shows no error.

### 7. Cross-record consistency

#### D-01 Same order matches across all records <!-- P0 -->
- Submit a Market Buy 0.10 EURUSD with SL/TP and record the order ID from the notification.
- Order ID, symbol, side, volume, fill price, SL, and TP are identical in the notification, Positions, order history, and transactions.

#### D-02 Close P/L matches balance change <!-- P1 -->
- Record balance B1 before closing, then close one position.
- Balance after close = B1 + that trade's realised P/L in order history (including commission and swap).

#### D-03 Deleted pending order status matches between list and history <!-- P2 -->
- After deleting a pending order, check Pending Orders and order history.
- The order ID is absent from Pending Orders and shows status Cancelled in order history.

### 8. Login and session

#### P-01 Unauthenticated access to the trading page is blocked <!-- P1 -->
- Clear browser cookies and local storage, then open the trading page URL directly.
- The page redirects to login and shows no balance, positions, or order ticket.

### 9. Network errors

#### V-15 Order is not submitted while the network is offline <!-- P1 -->
- Fill a valid Market Buy 0.10 EURUSD ticket, switch the browser offline (Playwright `context.set_offline(True)`), and click submit.
- No success notification is shown; after restoring the network and refreshing, Positions and order history contain no new order.

#### V-16 Order accepted but response times out: order is discoverable after reconnecting <!-- P1 -->
- Intercept the order request with Playwright `page.route`: forward it to the server (`route.fetch()`), then abort the response so the client times out. Submit a Market Buy 0.10 EURUSD.
- After reconnecting and refreshing, the order appears exactly once in Positions and order history, with symbol, side, and volume matching the submitted order.

#### V-17 Order not accepted: no order appears <!-- P1 -->
- Intercept the order request and abort it before it reaches the server (`route.abort()`). Submit a Market Buy 0.10 EURUSD.
- No success notification is shown; after reconnecting and refreshing, Positions and order history contain no new order.

#### V-18 Retrying after a timeout does not create a duplicate order <!-- P1 -->
- Reproduce the V-16 timeout, then click submit again with the same ticket once the network is restored.
- Positions and order history contain only the orders the user intended: the retry does not create an accidental duplicate of the timed-out order.

#### V-19 Unclear status is communicated and can be verified before retrying <!-- P2 -->
- Reproduce the V-16 timeout and observe the order ticket before retrying.
- The UI shows a message that the order status is uncertain (not a success or a plain failure) and offers a way to verify the order, such as a link to Positions or order history, before the user retries.

### 10. Market closure

Assumptions used below, to be confirmed with the product owner through T-08:
- A1: the demo broker configuration allows creating pending orders while the market is closed.
- A2: pending orders can be cancelled while the market is closed.
- A3: at reopening, a Stop order whose trigger price was crossed by the opening gap fills at the first available price, which may differ from the order price.
- A4: market-closed messages state that the market is closed; exact wording is not yet known.

#### L-08 Market status and trading hours are shown during closure <!-- P2 -->
- During EURUSD market closure, open the instrument in the price panel and its specification or trading hours.
- The instrument shows a closed status and the next opening time matches the published trading schedule; market Buy/Sell are disabled or show a market-closed message (A4).

#### C-11 Pending order can be created while the market is closed <!-- P2 -->
- During closure, create a Buy Stop at the last Ask + 100 points, volume 0.10.
- Under A1 the order appears in Pending Orders with status pending and does not fill while the market is closed. If the configuration does not allow it, the order is rejected with a clear market-closed message and Pending Orders has no new row (requires environment: market closure).

#### X-07 Pending order can be cancelled while the market is closed <!-- P2 -->
- During closure, delete an existing pending Buy Stop and confirm.
- Under A2 the order leaves Pending Orders and order history shows Cancelled; balance is unchanged (requires environment: market closure).

#### C-12 Pending orders at market reopening <!-- P2 -->
- Before the weekend close, create two Buy Stops: one 2 points above the last Ask (likely crossed by the opening gap) and one 300 points above it.
- At reopening, if the first order's price is crossed it fills at the first available price (A3), the fill price is recorded in order history and may differ from the order price, and status is Filled; the second order stays in Pending Orders (requires environment: weekend close and reopen).

#### C-13 Pending order expiring during closure does not fill at reopening <!-- P2 -->
- Before the close, create a Buy Stop with a UTC expiry time inside the closure period.
- At the expiry time the order leaves Pending Orders with status Expired, and it is not filled when the market reopens (requires environment: market closure).

### Open Question Placeholders

#### T-01 Pending order expiry options and granularity (open) <!-- P2 -->
- Check the expiry dropdown and expiry time picker.
- Confirm the options (GTC, Day, specified time, etc.) and expiry granularity. Time zone is confirmed as UTC.

#### T-02 EURUSD volume step (open) <!-- P2 -->
- Check the EURUSD instrument specification.
- Minimum 0.1 and maximum 100 are confirmed. Confirm step S, then fill in concrete values for V-06, V-07, and V-14.

#### T-03 Sell-side SL/TP messages and minimum distance (open) <!-- P2 -->
- Buy-side rule is confirmed: SL must be strictly less than price and TP strictly greater. On a Sell order, set SL below price and TP above price; on a Buy Stop at price P, set SL = P − 1 point.
- Confirm the Sell-side message wording, and whether any minimum distance applies beyond the strict rule (if SL = P − 1 point is rejected, find distance N and add N−1, N, N+1 boundaries).

#### T-04 One-Click volume setting location and default SL/TP (open) <!-- P2 -->
- Check the One-Click Trading settings.
- One-Click volume minimum 0.1 is confirmed. Confirm where the One-Click volume is changed, whether values below 0.1 are rejected there, and whether default SL/TP apply to One-Click orders.

#### T-05 Handling partial failure in bulk operations (open) <!-- P2 -->
- During bulk close, one position fails to close (for example, a closed-market instrument).
- Confirm whether the remaining positions still close and how the failure is reported.

#### T-06 Order history filters and pagination (open) <!-- P3 -->
- Check order history for date filter, symbol filter, and pagination controls.
- Confirm the supported filters and pagination, then add list query test cases.

#### T-07 Session timeout duration and expiry behaviour (open) <!-- P2 -->
- After login, stay idle until the session times out, then try to submit an order.
- Confirm the timeout duration and what the user sees when the session expires (for example, redirect to login). Order handling on submit timeouts is covered by V-16–V-19.

#### T-08 Confirm market-closure assumptions with the product owner (open) <!-- P3 -->
- Confirmed: market orders are not executed while the market is closed and a clear message is shown (V-10).
- Confirm assumptions A1–A4 in section 10: pending creation and cancellation during closure, gap fill at reopening, and the exact message wording; then finalise C-11, X-07, C-12, and L-08.

## Test Case Review Table

| ID | Name | Priority | Type | Tags |
|----|------|----------|------|------|
| F-01 | AQX Trader > Trading > Market Buy full lifecycle | P0 | smoke_sanity | market,sltp,position |
| F-02 | AQX Trader > Trading > Buy Stop create/modify/delete | P0 | smoke_sanity | pending,lifecycle |
| F-03 | AQX Trader > Trading > One-Click open and close | P0 | smoke_sanity | one-click |
| C-01 | AQX Trader > Order Ticket > Market Buy with SL/TP | P0 | functional | market,buy,sltp |
| C-02 | AQX Trader > Order Ticket > Market Sell with SL/TP | P0 | functional | market,sell,sltp |
| V-01 | AQX Trader > Order Ticket > Buy SL wrong side | P1 | boundary | validation,sltp |
| V-02 | AQX Trader > Order Ticket > Buy TP wrong side | P1 | boundary | validation,sltp |
| V-03 | AQX Trader > Order Ticket > Sell SL wrong side | P1 | boundary | validation,sltp |
| V-04 | AQX Trader > Order Ticket > Sell TP wrong side | P1 | boundary | validation,sltp |
| V-05 | AQX Trader > Order Ticket > Volume is 0 | P1 | boundary | validation,volume |
| V-06 | AQX Trader > Order Ticket > Minimum volume boundary | P2 | boundary | validation,volume |
| V-07 | AQX Trader > Order Ticket > Maximum volume boundary | P2 | boundary | validation,volume |
| V-08 | AQX Trader > Order Ticket > Insufficient margin | P1 | functional | validation,margin |
| V-09 | AQX Trader > Order Ticket > Invalid volume format | P2 | boundary | validation,volume |
| C-03 | AQX Trader > Order Ticket > Double-click creates one order | P1 | regression | idempotency |
| V-10 | AQX Trader > Order Ticket > Market closed rejects order | P2 | functional | market-closed |
| U-01 | AQX Trader > Settings > One-Click requires terms | P1 | functional | one-click,settings |
| C-04 | AQX Trader > Price Panel > One-Click Buy | P1 | functional | one-click,buy |
| C-05 | AQX Trader > Price Panel > One-Click Sell | P1 | functional | one-click,sell |
| U-02 | AQX Trader > Settings > Disabling One-Click restores confirmation | P1 | functional | one-click,settings |
| C-06 | AQX Trader > Order Ticket > Buy Stop order | P0 | functional | pending,stop |
| C-07 | AQX Trader > Order Ticket > Sell Stop order | P1 | functional | pending,stop |
| V-11 | AQX Trader > Order Ticket > Stop price wrong side | P1 | boundary | validation,pending |
| C-08 | AQX Trader > Order Ticket > GTC expiry | P2 | functional | pending,expiry |
| C-09 | AQX Trader > Pending Orders > Specified-time expiry | P1 | boundary | pending,expiry,time |
| V-12 | AQX Trader > Order Ticket > Expiry in the past | P2 | boundary | validation,expiry |
| U-03 | AQX Trader > Pending Orders > Modify pending order | P1 | functional | pending,modify |
| X-01 | AQX Trader > Pending Orders > Delete pending order | P1 | functional | pending,delete |
| C-10 | AQX Trader > Pending Orders > Converts to position on trigger | P2 | integration | pending,fill |
| L-01 | AQX Trader > Positions > Fields and live P/L | P1 | functional | position,list |
| U-04 | AQX Trader > Positions > Modify SL/TP | P1 | functional | position,modify |
| V-13 | AQX Trader > Positions > SL modified to wrong side | P1 | boundary | validation,position |
| U-05 | AQX Trader > Positions > Partial close | P1 | functional | position,partial-close |
| V-14 | AQX Trader > Positions > Partial close volume boundaries | P2 | boundary | validation,partial-close |
| X-02 | AQX Trader > Positions > Full close | P0 | functional | position,close |
| X-03 | AQX Trader > Positions > Bulk close all | P1 | functional | bulk,close |
| X-04 | AQX Trader > Positions > Bulk close profitable | P1 | functional | bulk,close,profit |
| X-05 | AQX Trader > Positions > Bulk close losing | P1 | functional | bulk,close,loss |
| X-06 | AQX Trader > Pending Orders > Bulk delete pending orders | P1 | functional | bulk,delete |
| L-02 | AQX Trader > Positions > Bulk close with no positions | P3 | functional | bulk,empty |
| L-03 | AQX Trader > Notifications > Order success notification | P1 | functional | notification |
| L-04 | AQX Trader > Notifications > Order failure notification | P2 | functional | notification,error |
| L-05 | AQX Trader > Order History > Final statuses | P1 | functional | history,status |
| L-06 | AQX Trader > Transactions > Opening and closing deals | P1 | functional | transactions |
| L-07 | AQX Trader > Order History > Empty state | P3 | functional | history,empty |
| D-01 | AQX Trader > Transactions > Order consistent across records | P0 | integration | consistency |
| D-02 | AQX Trader > Account > Close P/L matches balance | P1 | integration | consistency,balance |
| D-03 | AQX Trader > Order History > Deleted order status consistent | P2 | integration | consistency,pending |
| P-01 | AQX Trader > Login > Unauthenticated access blocked | P1 | security | auth |
| V-15 | AQX Trader > Order Ticket > Not submitted while offline | P1 | regression | network,error |
| V-16 | AQX Trader > Order Ticket > Accepted order discoverable after timeout | P1 | regression | network,timeout |
| V-17 | AQX Trader > Order Ticket > Rejected-before-server order absent | P1 | regression | network,timeout |
| V-18 | AQX Trader > Order Ticket > Retry after timeout creates no duplicate | P1 | regression | network,idempotency |
| V-19 | AQX Trader > Order Ticket > Uncertain status communicated | P2 | functional | network,ux |
| L-08 | AQX Trader > Price Panel > Market status and trading hours when closed | P2 | functional | market-closed,schedule |
| C-11 | AQX Trader > Order Ticket > Create pending order while closed | P2 | functional | market-closed,pending |
| X-07 | AQX Trader > Pending Orders > Cancel pending order while closed | P2 | functional | market-closed,pending |
| C-12 | AQX Trader > Pending Orders > Behaviour at market reopening | P2 | integration | market-closed,reopen,gap |
| C-13 | AQX Trader > Pending Orders > Expiry during closure | P2 | boundary | market-closed,expiry |
| T-01 | AQX Trader > Order Ticket > Expiry options to confirm | P2 | pending_clarification | expiry |
| T-02 | AQX Trader > Order Ticket > Volume step to confirm | P2 | pending_clarification | volume |
| T-03 | AQX Trader > Order Ticket > Sell SL/TP messages and stop distance to confirm | P2 | pending_clarification | sltp |
| T-04 | AQX Trader > Settings > One-Click volume location and SL/TP to confirm | P2 | pending_clarification | one-click |
| T-05 | AQX Trader > Positions > Bulk partial failure to confirm | P2 | pending_clarification | bulk |
| T-06 | AQX Trader > Order History > Filters and pagination to confirm | P3 | pending_clarification | history |
| T-07 | AQX Trader > Login > Session timeout to confirm | P2 | pending_clarification | session |
| T-08 | AQX Trader > Order Ticket > Market-closure assumptions to confirm | P3 | pending_clarification | market-closed |

## Coverage Matrix Self-Check

| Dimension | Triggered | Covered / Open | Notes |
|-----------|-----------|----------------|-------|
| A Data input and validation | Yes | Covered / open | V-01–V-14; volume step in T-02, Sell-side messages and stop distance in T-03 |
| B Lists and queries | Yes | Covered / open | L-01–L-07; filters and pagination in T-06 |
| C Authentication and roles | Yes | Covered / open | P-01; session timeout in T-07 |
| D Resource identifiers | Yes | Covered | D-01–D-03 checked by order ID |
| E Time and state | Yes | Covered / open | C-09 before/after expiry, V-10, V-12, C-12 reopening, C-13 expiry during closure; expiry options in T-01 |
| F Duplicates and consistency | Yes | Covered | C-03 double-click, V-18 retry after timeout, D-01–D-03 |
| G Errors and availability | Yes | Covered | V-08, L-04, V-15–V-19 |
| H API contract | No | Not applicable | No OpenAPI provided |
| I Non-functional appendix | No | Not applicable | No security or performance appendix requested |

## Open Questions

| # | Question | Related IDs |
|---|----------|-------------|
| 1 | What expiry options exist for pending orders? What is the granularity? (Time zone confirmed: UTC.) | T-01, C-08, C-09 |
| 2 | What is EURUSD's volume step? (Confirmed: minimum 0.1, maximum 100.) | T-02, V-06, V-07, V-14 |
| 3 | What are the Sell-side SL/TP messages? Is there a minimum distance beyond the strict less-than / greater-than rule? (Confirmed Buy side: SL < price, TP > price.) | T-03, V-03, V-04 |
| 4 | Where is the One-Click volume changed? Do default SL/TP apply to One-Click orders? (Confirmed: minimum volume 0.1.) | T-04, C-04, C-05 |
| 5 | If one trade fails during bulk close, do the others continue? How is it reported? | T-05 |
| 6 | What filters and pagination does order history support? | T-06, L-05 |
| 7 | How long is the session timeout, and what happens when it expires? (Submit-timeout order handling confirmed: see V-16–V-19.) | T-07 |
| 8 | Are assumptions A1–A4 correct: pending orders can be created and cancelled while closed, crossed Stop orders fill at the first available price on reopening, and what is the exact market-closed message? (Confirmed: market orders are blocked with a clear message.) | T-08, V-10, L-08, C-11, X-07, C-12 |
