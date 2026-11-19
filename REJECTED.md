# Rejected criteria and abandoned approaches

## Acceptance criteria

Of the eight criteria in the brief, four are incorrect. Each refusal is below,
with the evidence from the replay.

### Verdicts

| # | Criterion (abridged) | Verdict |
|---|---|---|
| 1 | Day 2 closing at end of Day 5, before fees, is AED -370.00 | **True.** Tested. |
| 2 | E7 causes exactly one overdraft fee, on Day 2 | **False.** Refused, C2. |
| 3 | Day 4 settlement of Auth-A is accepted | **True.** Tested. |
| 4 | Settlement of an unknown auth ID is rejected, funds stay | **True.** Tested. |
| 5 | If Auth-B is approved, hold reduces available not ledger | **True** (conditional). Auth-B is declined in this replay, so the consequent is tested in unit tests. |
| 6 | After E9, all balances and fees return to pre-E7 values | **False** as written. Refused, C6. |
| 7 | Three BHD instalments of E10 are each 3.334 | **False.** Refused, C7. |
| 8 | If rounded accruals don't sum to the capitalised total, discard the remainder | **False.** Refused, C8. |

### C2: "E7 causes exactly one overdraft fee, on Day 2"

Refused. The rule says a fee is assessed on each day whose closing is negative.
E7 is booked Day 5 and debits value date 2. Recomputing each value date's closing
ex-fees gives:

- Day 2: 250.00 - 620.00 = -370.00 (negative, fee)
- Day 3: -370.00 + 400.00 = 30.00 (positive, no fee)
- Day 4: 30.00 - 185.00 = -155.00 (negative, fee)
- Day 5: -155.00 (negative, fee)

Without E7, Day 4 would be 465.00 and Day 5 would be 465.00. So Day 4 and Day 5
are negative only because of E7. E7 causes three fees, on Days 2, 4 and 5. The
criterion treats "the first fee E7 triggers" as "every fee E7 causes". The
annotated failing test is in `tests/test_acceptance.py`.

### C6: "After E9, all balances and fees return to their pre-E7 values"

Refused as written. E9 reverses E7's debit, so the ledger ex-fees returns to
465.00 (the pre-E7 figure). That part holds. But:

- Fees do not return. The three fees from C2 stay booked, totalling -75.00.
  Pre-E7 fees were zero. The brief's rules are append-only and say nothing that
  reverses a fee when its cause is reversed. Reversing fees would need an event
  the brief does not define.
- The ledger including fees is 390.00 before capitalisation, not 465.00. After
  capitalisation it is 390.81.

The corrected behaviour is tested in `test_after_e9_ledger_matches_pre_e7_only_before_fees_and_interest`.

### C7: "The three BHD instalments in E10 must each be BHD 3.334"

Refused on arithmetic. 3 x 3.334 = 10.002, not 10.000. Three equal instalments
of 10.000 BHD are not representable at 3 dp. The best exact split is 3.334,
3.333, 3.333, which sums to 10.000. Tested in `test_e10_instalments_are_3334_3333_3333`.

### C8: "If the rounded daily interest accruals do not sum to the capitalized total, the remainder is discarded"

Refused. The non-negotiable rule says the accruals must sum exactly to the
capitalised total. If they do not, something is wrong with the implementation.
Discarding a remainder would hide the inconsistency and break the rule. In this
design the sum is exact by construction: the capitalised credit is the sum of
the stored rounded accruals, so no remainder can arise. Tested in
`test_interest_sum_equals_capitalised_total_exactly`.

## Approaches considered and abandoned during design

These were considered on paper and rejected before any code was written for them.
No code was written for them, and they do not appear in the history.

- **Mutating authorisation status in place.** Simpler to read, but it breaks the
  append-only rule. Replaced by one AuthRecord per state transition, with the
  current state derived from the latest record.
- **Accruing interest on final, restated balances.** Using end-of-window balances
  would make every day's accrual depend on E7 and E9, including Days 1 to 4,
  which were already done. Replaced by point-in-time accruals.
- **Banker's rounding.** It gives the same results on this scenario. Rejected
  because HALF_UP matches the reader's expectation of "round to 2 dp".
- **Fee assessment inside `post_debit`.** Assessing the fee at the moment of the
  debit would miss the backdated effect on value dates other than the debit's.
  Replaced by the end-of-day pass, which checks every value date.
