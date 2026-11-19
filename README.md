# ledger-core

An in-memory, append-only account ledger core. Standard library only (Python 3.9+).
No web layer, no persistence, no UI, no database.

## Run the suite

    python3 -m unittest discover -s tests -v

Expected last line: `OK (expected failures=1)`.

The one expected failure is deliberate. It encodes acceptance criterion 2 from
the brief ("E7 causes exactly one overdraft fee, on Day 2"), which this design
does not satisfy. The test is annotated in `tests/test_acceptance.py`, and the
refusal is documented in `REJECTED.md` (item C2). If that test ever passes
unexpectedly, unittest reports it as an unexpected success and the suite fails.

## Run the replay

    python3 replay.py

It replays the ten-event stream from `scenario.py` (Day 1 to Day 6) and prints,
per day:

- **Postings**: every ledger entry booked that day (POSTED / REVERSED).
- **Fee assessments**: overdraft fees booked that day, with the value date they
  apply to and the closing balance that triggered them.
- **Authorisation states**: APPROVED, DECLINED or SETTLED, with the arithmetic
  shown (available, hold, result).
- **Errors**: REJECTED events, with the reason and confirmation that no funds moved.
- **Capitalisation**: Day 6 only.
- **Closing balances**: ledger, holds, available and interest accrued, per account.

The final notes print two numbers that need care to read correctly:

- `Day 2 closing by value date, end of Day 5, before fees: -370.00`. This is
  the Day 2 closing restated after E7 was booked. The "Closing balances" line
  for Day 2 shows 250.00 because E7 had not been booked yet on Day 2.
- `Final ACC-001: 390.81 AED`, `Final ACC-002: 10.008 BHD`.

## Layout

    ledger/money.py     currency precision, half-up rounding, exact equal split
    ledger/records.py   frozen dataclasses: Entry, AuthRecord, Accrual, Capitalisation, Outcome
    ledger/core.py      the Ledger: postings, holds, settlement, reversal, fees, interest
    scenario.py         the event stream and account setup, as data
    replay.py           runs the stream and renders the per-day report
    tests/              unit tests (test_rules.py) and acceptance tests (test_acceptance.py)

## Design in brief

- Every record is a frozen dataclass appended to a list. There is no update or
  delete method. Current states (authorisation status, balances) are derived.
- Balances are sums over entries. Ledger balance is all booked entries.
  Closing balance for a value date is entries with value_date <= that date.
- Authorisations are approved only if available (ledger minus active holds)
  stays >= 0 after the hold. Debits post unconditionally.
- Overdraft fees are checked in an end-of-day pass for every value date up to
  that day. This is how a backdated entry can trigger fees for earlier value dates.
- Interest accrues daily on positive ledger balances and is capitalised once at
  the end of Day 6 as the exact sum of the rounded daily accruals.

See `NUMBERS.md` for constants, `AMBIGUITIES.md` for every interpretation
choice, `REJECTED.md` for refused criteria and abandoned approaches, and
`WORKLOG.md` for the build log.
