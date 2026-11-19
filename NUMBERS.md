# Numbers and constants

Every constant in the code, why this value, and why not half of it.

| Constant | Value | Source | Why not half |
|---|---|---|---|
| `CURRENCY_DP["AED"]` | 2 | brief | Brief fixes it. Half would be 1 decimal, which cannot hold 0.05-level accruals. |
| `CURRENCY_DP["BHD"]` | 3 | brief | Brief fixes it. |
| `OVERDRAFT_FEE["AED"]` | 25.00 | brief | Brief fixes it. |
| `OVERDRAFT_FEE["BHD"]` | not defined | my choice | Brief gives no BHD fee. Half of nothing is not defined. An overdrawn BHD account raises `LedgerError` rather than inventing a fee. No BHD account is overdrawn in the scenario. |
| `DAILY_INTEREST_RATE` | 0.0004 | brief (0.04%/day) | Half would be 0.0002, which on the scenario's largest balance (650.00) gives 0.13 instead of 0.26 on Day 3, and changes the capitalised total from 0.81 to 0.41. |
| Rounding mode | `ROUND_HALF_UP` | my choice | `ROUND_HALF_EVEN` gives the same result for every accrual here (0.186 -> 0.19, 0.156 -> 0.16, 0.26 exact), so the scenario cannot distinguish them. I chose HALF_UP because it is the rule most readers expect from "round to 2 dp". |
| Accrual base | ledger balance including fees and booked entries | my choice | Excluding fees changes the answer. Day 6 would accrue on 465.00 (0.19) instead of 390.00 (0.16), and the capitalised total would be 0.84 instead of 0.81. |
| Accrual timing | end of each booking day, on that day's balance | my choice | Accruing on the restated final balances would give Day 2 an accrual on 250 (0.10) regardless, but would change Day 5 and Day 6 bases. Point-in-time matches append-only accrual records. |
| Fee test basis | closing excluding fees | my choice | Including fees gives the same three fees here (checked by hand), but it makes fees depend on each other's order. Excluding them keeps the pass order-independent. |
| Instalment rounding | leftover minor units to earliest instalments | my choice | Splitting 10.000 BHD into three gives 3.3333... per instalment. "Half" the leftover would be 0.0005 BHD, which is not representable. The leftover is one minor unit (0.001), so it goes to instalment 1: 3.334, 3.333, 3.333. |
| Opening value date | 0 | my choice | Opening balances predate Day 1, so 0 sorts before every window day and never falls into a fee check (fee checks start at day 1). |
| First / last day | 1 / 6 | brief | Brief fixes the window. |
| Capitalisation day | 6 | brief | Brief fixes it. |
| Restatement capture day | 5 | brief criterion 1 | Brief says "evaluated at end of Day 5 and before any fee is assessed". Capturing before `close_day(5)` is the only point that satisfies both. |
| Authorisation threshold | available after hold >= 0 | brief | Brief says "at or above zero", so exactly zero is approved. Tested in `test_approved_when_available_is_exactly_zero`. |
