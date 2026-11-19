# Ambiguities and resolutions

Each entry: what the brief left open, what I chose, and where it is enforced.

1. **What "closing ledger balance" means.** Closing for value date d is the sum of
   all entries with value_date <= d, over everything booked so far. Resolved in
   `closing_by_value_date`. Consequence: Day 2's closing printed at end of Day 2
   is 250.00, but after E7 (booked Day 5) it is -370.00. The report shows both.

2. **Retroactive fees.** E7 is booked on Day 5 with value date Day 2. The Day 2
   closing was positive at end of Day 2, so no fee was assessed then. I chose to
   assess the fee when the closing becomes negative, booked on the day it is
   assessed, with value date = the day it applies to. Fee `FEE-ACC-001-VD2` is
   booked Day 5 with value date 2.

3. **How many fees E7 causes.** The rule is "once per day per account when that
   day's closing is negative". E7 makes value dates 2, 4 and 5 negative. So E7
   causes three fees, not one. See REJECTED.md C2.

4. **Fee check excludes fees.** Fees are excluded from the balance used to test
   for a fee. This keeps assessment order-independent. Including them gives the
   same result in this scenario, but the rule is clearer without the feedback.

5. **Fee reversal on E9.** E9 reverses E7 (the debit). It does not reverse the
   fees E7 caused. Fees are never reversed automatically. A fee reversal would
   need its own event, which the brief does not define. So fees remain after E9.
   See REJECTED.md C6.

6. **Event order.** The brief says "replayed in this order" (E1 to E10), but E9 is
   Day 6 and E10 is Day 5, so the literal order goes backwards in time. I replay
   by booked day and keep listed order within a day. The only effect is that E10
   is posted before E9. It touches ACC-002 only and accounts are independent, so
   ACC-001 results are identical either way. I checked this by reasoning, not by
   a second run.

7. **Ledger balance for an authorisation.** Available is the sum of all booked
   entries, regardless of value date, minus active holds. At E3 and E8 every
   booked entry was already value-dated on or before the event's day, so the
   choice does not change those answers.

8. **Debits are not gated.** Only authorisations are checked against available
   balance. E7 (a debit of 620.00 against a balance of 465.00) posts and overdraws
   the account. That is what produces the overdraft fees. The brief says nothing
   that would reject a debit.

9. **Settlement value date.** A settlement takes the value date from its event
   (E5 has value date 4). A settlement does not re-check available balance,
   because the hold already reserves the funds.

10. **Partial settlement.** E5 settles 185.00 against a 200.00 hold. The 15.00
    remainder is released and the hold ends. The authorisation becomes SETTLED.

11. **Settlement when no authorisation exists.** E6 names Auth-Z, which has no
    record. It is REJECTED with no ledger entry. "The funds must not leave the
    account" is met by writing no entry at all.

12. **Authorisation approval is point-in-time.** Auth-A was approved at E3 on the
    balance then (250.00). E7 later pushes Day 2 negative, but Auth-A is not
    re-evaluated. Approval is a fact about the moment it was granted.

13. **Auth-B is declined.** At E8 the ledger already includes E7, so the ledger is
    -155.00. Available is -155.00 minus the 90.00 hold, which is -245.00, so the
    hold is declined. The brief's "Auth-B is never settled" then means nothing is
    held, not that it sits open. The brief's criterion 5 is conditional on
    approval. In this replay the condition is false, so the consequence is
    tested separately in `test_rules.py`.

14. **Interest base.** The base is the full ledger balance at end of day,
    including fees, positive balances only. A zero or negative balance accrues
    nothing and no zero-accrual record is written.

15. **Interest on restated days.** Accruals are not revised after E7. An accrual
    recorded at end of Day 2 on 250.00 stays as recorded, because the record is
    immutable. Day 5 has no accrual because the balance is negative.

16. **Interest does not compound inside the window.** Capitalisation is one credit
    at end of Day 6, and no accrual is computed on it. The brief specifies one
    capitalised credit.

17. **Capitalisation amount.** The credit equals the exact sum of the stored,
    already-rounded daily accruals. Nothing is re-rounded at capitalisation, so
    the equality holds by construction. This is what the brief means by "the
    rounded daily accruals must sum exactly".

18. **BHD instalments.** 10.000 BHD cannot be three equal 3.334 amounts. The three
    instalments are 3.334, 3.333 and 3.333 (leftover minor unit to the first).
    See REJECTED.md C7.

19. **BHD fee.** The brief gives an AED fee only. An overdrawn BHD account raises
    `LedgerError` rather than inventing a fee.

20. **Rounding mode.** ROUND_HALF_UP everywhere. Not stated in the brief.

21. **Duplicate authorisation IDs.** A second authorisation with an existing ID is
    REJECTED, so an ID names one authorisation for its lifetime.

22. **Reversal scope.** Only CREDIT, DEBIT and SETTLEMENT postings can be reversed.
    A reversal cannot be reversed, and a posting can be reversed only once.

23. **Opening balances.** A non-zero opening balance is one OPENING entry with
    value date 0. The scenario's openings are 0, so no such entry is written.

24. **Report "per day" balances.** These are end-of-booking-day state, which is
    the only state that existed on that day. Restated figures are shown
    separately in the notes section.
