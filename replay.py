"""Replays the scenario event stream and prints a per-day report.

Run:  python3 replay.py
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional

from ledger import Ledger, fmt, split_equal
from scenario import ACCOUNTS, EVENTS, Event

LAST_DAY = 6
RESTATEMENT_DAY = 5          # criterion 1 is evaluated at end of Day 5, before fees
ZERO = Decimal("0")


@dataclass
class Replay:
    ledger: Ledger
    summary: Dict[int, Dict[str, Dict[str, Decimal]]]
    restated_day2_end_day5: Optional[Decimal]


def apply(ledger: Ledger, ev: Event) -> None:
    ccy = ledger.currency(ev.account)
    if ev.kind == "CREDIT":
        if ev.instalments > 1:
            parts = split_equal(ev.amount, ev.instalments, ccy)
            for i, part in enumerate(parts, start=1):
                ledger.post_credit(event_id=f"{ev.event_id}.{i}", day=ev.day,
                                   account=ev.account, amount=part, value_date=ev.value_date)
        else:
            ledger.post_credit(event_id=ev.event_id, day=ev.day, account=ev.account,
                               amount=ev.amount, value_date=ev.value_date)
    elif ev.kind == "DEBIT":
        ledger.post_debit(event_id=ev.event_id, day=ev.day, account=ev.account,
                          amount=ev.amount, value_date=ev.value_date)
    elif ev.kind == "AUTHORIZATION":
        ledger.authorize(event_id=ev.event_id, day=ev.day, account=ev.account,
                         auth_id=ev.auth_id, amount=ev.amount)
    elif ev.kind == "SETTLEMENT":
        ledger.settle(event_id=ev.event_id, day=ev.day, account=ev.account,
                      auth_id=ev.auth_id, amount=ev.amount, value_date=ev.value_date)
    elif ev.kind == "REVERSAL":
        ledger.reverse(event_id=ev.event_id, day=ev.day, account=ev.account,
                       target_event_id=ev.target)
    else:
        raise ValueError(f"unknown event kind {ev.kind}")


def run() -> Replay:
    ledger = Ledger()
    for account, ccy, opening in ACCOUNTS:
        ledger.open_account(account, ccy, opening)

    summary: Dict[int, Dict[str, Dict[str, Decimal]]] = {}
    restated: Optional[Decimal] = None

    for day in range(1, LAST_DAY + 1):
        for ev in (e for e in EVENTS if e.day == day):
            apply(ledger, ev)
        if day == RESTATEMENT_DAY:
            restated = ledger.closing_by_value_date("ACC-001", 2)
        ledger.close_day(day)
        if day == LAST_DAY:
            ledger.capitalise(day=day)
        summary[day] = {}
        for account, _, _ in ACCOUNTS:
            summary[day][account] = {
                "ledger": ledger.ledger_balance(account),
                "holds": ledger.active_holds(account),
                "available": ledger.available_balance(account),
                "accrual": sum((a.amount for a in ledger.accruals
                                if a.account == account and a.day == day), ZERO),
            }
    return Replay(ledger=ledger, summary=summary, restated_day2_end_day5=restated)


def render(r: Replay) -> str:
    lines: List[str] = []
    outs = r.ledger.outcomes
    ccy_of = {a: c for a, c, _ in ACCOUNTS}

    def section(day_outs, title, statuses):
        rows = [o for o in day_outs if o.status in statuses]
        lines.append(f"  {title}:")
        if not rows:
            lines.append("    (none)")
        for o in rows:
            lines.append(f"    {o.event_id:<12} {o.account}  {o.status:<11} {o.detail}")

    for day in range(1, LAST_DAY + 1):
        day_outs = [o for o in outs if o.day == day]
        lines.append(f"=== Day {day} ===")
        section(day_outs, "Postings", {"POSTED", "REVERSED"})
        section(day_outs, "Fee assessments", {"FEE"})
        section(day_outs, "Authorisation states", {"APPROVED", "DECLINED", "SETTLED"})
        section(day_outs, "Errors", {"REJECTED"})
        section(day_outs, "Capitalisation", {"CAPITALISED"})
        lines.append("  Closing balances (end of day):")
        for account, ccy, _ in ACCOUNTS:
            s = r.summary[day][account]
            lines.append(f"    {account} {ccy}  ledger {fmt(s['ledger'], ccy)}  "
                         f"holds {fmt(s['holds'], ccy)}  available {fmt(s['available'], ccy)}  "
                         f"interest accrued {fmt(s['accrual'], ccy)}")
        lines.append("")

    lines.append("=== Notes ===")
    if r.restated_day2_end_day5 is not None:
        lines.append(f"  ACC-001 Day 2 closing by value date, end of Day 5, before fees: "
                     f"{fmt(r.restated_day2_end_day5, 'AED')}")
    final = r.summary[LAST_DAY]
    for account, ccy, _ in ACCOUNTS:
        lines.append(f"  Final {account}: {fmt(final[account]['ledger'], ccy)} {ccy}")
    return "\n".join(lines)


def main() -> int:
    r = run()
    print(render(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
