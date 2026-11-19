"""In-memory, append-only account ledger core. Stdlib only.

Nothing is ever updated or deleted. Balances, holds and authorisation states
are derived from the history of records.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Optional, Set, Tuple

from .money import CURRENCY_DP, Amount, fmt, quantize
from .records import Accrual, AuthRecord, Capitalisation, Entry, Outcome

OVERDRAFT_FEE: Dict[str, Decimal] = {"AED": Decimal("25.00")}   # no BHD schedule defined
DAILY_INTEREST_RATE = Decimal("0.0004")                          # 0.04% per day
ZERO = Decimal("0")


class LedgerError(Exception):
    """Configuration or programming error. Business rejections are Outcomes."""


class Ledger:
    def __init__(self) -> None:
        self._ccy: Dict[str, str] = {}
        self._entries: List[Entry] = []
        self._auths: List[AuthRecord] = []
        self._accruals: List[Accrual] = []
        self._caps: List[Capitalisation] = []
        self._outcomes: List[Outcome] = []
        self._fee_keys: Set[Tuple[str, int]] = set()
        self._seq = 0

    # ----- read-only views -------------------------------------------------
    @property
    def entries(self) -> Tuple[Entry, ...]:
        return tuple(self._entries)

    @property
    def auth_records(self) -> Tuple[AuthRecord, ...]:
        return tuple(self._auths)

    @property
    def accruals(self) -> Tuple[Accrual, ...]:
        return tuple(self._accruals)

    @property
    def capitalisations(self) -> Tuple[Capitalisation, ...]:
        return tuple(self._caps)

    @property
    def outcomes(self) -> Tuple[Outcome, ...]:
        return tuple(self._outcomes)

    def currency(self, account: str) -> str:
        try:
            return self._ccy[account]
        except KeyError:
            raise LedgerError(f"unknown account {account}") from None

    # ----- internal appends ------------------------------------------------
    def _next(self) -> int:
        self._seq += 1
        return self._seq

    def _entry(self, *, event_id: str, account: str, kind: str, amount: Decimal,
               value_date: int, booked_day: int, ref: Optional[str] = None,
               note: str = "") -> Entry:
        e = Entry(seq=self._next(), event_id=event_id, account=account, kind=kind,
                  amount=amount, value_date=value_date, booked_day=booked_day,
                  ref=ref, note=note)
        self._entries.append(e)
        return e

    def _outcome(self, *, day: int, event_id: str, account: str, status: str,
                 detail: str) -> Outcome:
        o = Outcome(seq=self._next(), day=day, event_id=event_id, account=account,
                    status=status, detail=detail)
        self._outcomes.append(o)
        return o

    # ----- balances --------------------------------------------------------
    def ledger_balance(self, account: str) -> Decimal:
        """Sum of every booked entry for the account, regardless of value date."""
        return sum((e.amount for e in self._entries if e.account == account), ZERO)

    def closing_by_value_date(self, account: str, value_date: int, *,
                              exclude_fees: bool = False) -> Decimal:
        """Sum of entries with value_date <= value_date, over everything booked so far."""
        return sum((e.amount for e in self._entries
                    if e.account == account
                    and e.value_date <= value_date
                    and not (exclude_fees and e.kind == "FEE")), ZERO)

    def _latest_auths(self) -> Dict[str, AuthRecord]:
        latest: Dict[str, AuthRecord] = {}
        for r in self._auths:
            latest[r.auth_id] = r
        return latest

    def auth_state(self, auth_id: str) -> Optional[AuthRecord]:
        return self._latest_auths().get(auth_id)

    def active_holds(self, account: str) -> Decimal:
        return sum((r.hold for r in self._latest_auths().values()
                    if r.account == account and r.status == "APPROVED"), ZERO)

    def available_balance(self, account: str) -> Decimal:
        return self.ledger_balance(account) - self.active_holds(account)

    # ----- postings --------------------------------------------------------
    def open_account(self, account: str, ccy: str, opening: Amount = "0") -> None:
        if account in self._ccy:
            raise LedgerError(f"{account} already open")
        if ccy not in CURRENCY_DP:
            raise LedgerError(f"unsupported currency {ccy}")
        self._ccy[account] = ccy
        amt = quantize(opening, ccy)
        if amt != 0:
            self._entry(event_id=f"OPEN-{account}", account=account, kind="OPENING",
                        amount=amt, value_date=0, booked_day=0)

    def post_credit(self, *, event_id: str, day: int, account: str, amount: Amount,
                    value_date: int) -> Outcome:
        ccy = self.currency(account)
        amt = quantize(amount, ccy)
        if amt <= 0:
            raise LedgerError("credit must be positive")
        self._entry(event_id=event_id, account=account, kind="CREDIT", amount=amt,
                    value_date=value_date, booked_day=day)
        return self._outcome(day=day, event_id=event_id, account=account, status="POSTED",
                             detail=f"credit {fmt(amt, ccy)}, value date {value_date}")

    def post_debit(self, *, event_id: str, day: int, account: str, amount: Amount,
                   value_date: int) -> Outcome:
        """Debits post unconditionally. Only authorisations are gated."""
        ccy = self.currency(account)
        amt = quantize(amount, ccy)
        if amt <= 0:
            raise LedgerError("debit must be positive")
        self._entry(event_id=event_id, account=account, kind="DEBIT", amount=-amt,
                    value_date=value_date, booked_day=day)
        return self._outcome(day=day, event_id=event_id, account=account, status="POSTED",
                             detail=f"debit {fmt(amt, ccy)}, value date {value_date}")

    # ----- authorisations --------------------------------------------------
    def authorize(self, *, event_id: str, day: int, account: str, auth_id: str,
                  amount: Amount) -> Outcome:
        ccy = self.currency(account)
        hold = quantize(amount, ccy)
        if hold <= 0:
            raise LedgerError("hold must be positive")
        if auth_id in self._latest_auths():
            return self._outcome(day=day, event_id=event_id, account=account,
                                 status="REJECTED",
                                 detail=f"authorisation {auth_id} already exists")
        before = self.available_balance(account)
        after = before - hold
        status = "APPROVED" if after >= 0 else "DECLINED"
        self._auths.append(AuthRecord(seq=self._next(), event_id=event_id, auth_id=auth_id,
                                      account=account, status=status, hold=hold,
                                      booked_day=day))
        return self._outcome(day=day, event_id=event_id, account=account, status=status,
                             detail=(f"{auth_id}: available {fmt(before, ccy)} "
                                     f"- hold {fmt(hold, ccy)} = {fmt(after, ccy)}"))

    def settle(self, *, event_id: str, day: int, account: str, auth_id: str,
               amount: Amount, value_date: int) -> Outcome:
        ccy = self.currency(account)
        amt = quantize(amount, ccy)
        rec = self._latest_auths().get(auth_id)
        if rec is None or rec.account != account:
            return self._outcome(day=day, event_id=event_id, account=account,
                                 status="REJECTED",
                                 detail=f"no authorisation {auth_id} on {account}; no funds moved")
        if rec.status != "APPROVED":
            return self._outcome(day=day, event_id=event_id, account=account,
                                 status="REJECTED",
                                 detail=f"{auth_id} is {rec.status}; no funds moved")
        if amt > rec.hold:
            return self._outcome(day=day, event_id=event_id, account=account,
                                 status="REJECTED",
                                 detail=(f"settlement {fmt(amt, ccy)} exceeds hold "
                                         f"{fmt(rec.hold, ccy)}; no funds moved"))
        self._entry(event_id=event_id, account=account, kind="SETTLEMENT", amount=-amt,
                    value_date=value_date, booked_day=day, ref=auth_id)
        released = rec.hold - amt
        self._auths.append(AuthRecord(seq=self._next(), event_id=event_id, auth_id=auth_id,
                                      account=account, status="SETTLED", hold=rec.hold,
                                      booked_day=day,
                                      note=f"released {fmt(released, ccy)}"))
        return self._outcome(day=day, event_id=event_id, account=account, status="SETTLED",
                             detail=(f"{auth_id} settled {fmt(amt, ccy)} against hold "
                                     f"{fmt(rec.hold, ccy)}; released {fmt(released, ccy)}"))

    # ----- reversals -------------------------------------------------------
    def reverse(self, *, event_id: str, day: int, account: str,
                target_event_id: str) -> Outcome:
        ccy = self.currency(account)
        target = next((e for e in self._entries
                       if e.event_id == target_event_id and e.account == account), None)
        if target is None or target.kind not in ("CREDIT", "DEBIT", "SETTLEMENT"):
            return self._outcome(day=day, event_id=event_id, account=account,
                                 status="REJECTED",
                                 detail=f"{target_event_id} is not a reversible posting on {account}")
        if any(e.kind == "REVERSAL" and e.ref == target_event_id for e in self._entries):
            return self._outcome(day=day, event_id=event_id, account=account,
                                 status="REJECTED",
                                 detail=f"{target_event_id} is already reversed")
        self._entry(event_id=event_id, account=account, kind="REVERSAL", amount=-target.amount,
                    value_date=target.value_date, booked_day=day, ref=target_event_id)
        return self._outcome(day=day, event_id=event_id, account=account, status="REVERSED",
                             detail=(f"reversed {target_event_id} "
                                     f"({fmt(-target.amount, ccy)}), value date {target.value_date}"))

    # ----- end of day: fees and interest -----------------------------------
    def close_day(self, day: int) -> None:
        """End-of-day pass. Overdraft fees are assessed for every value date <= day
        whose closing (ex-fees) is negative and has no fee yet, so backdated
        entries can trigger fees for earlier value dates. Interest accrues on the
        closing ledger balance, positive balances only."""
        for account in self._ccy:
            self._assess_overdraft(account, day)
            self._accrue(account, day)

    def _assess_overdraft(self, account: str, day: int) -> None:
        ccy = self._ccy[account]
        for vd in range(1, day + 1):
            key = (account, vd)
            if key in self._fee_keys:
                continue
            closing = self.closing_by_value_date(account, vd, exclude_fees=True)
            if closing >= 0:
                continue
            if ccy not in OVERDRAFT_FEE:
                raise LedgerError(f"no overdraft fee defined for {ccy}")
            self._fee_keys.add(key)
            fee_id = f"FEE-{account}-VD{vd}"
            self._entry(event_id=fee_id, account=account, kind="FEE", amount=-OVERDRAFT_FEE[ccy],
                        value_date=vd, booked_day=day)
            self._outcome(day=day, event_id=fee_id, account=account, status="FEE",
                          detail=(f"overdraft fee {fmt(OVERDRAFT_FEE[ccy], ccy)} for value date "
                                  f"{vd}; closing ex-fees {fmt(closing, ccy)} < 0"))

    def _accrue(self, account: str, day: int) -> None:
        ccy = self._ccy[account]
        base = self.ledger_balance(account)
        if base <= 0:
            return
        amount = quantize(base * DAILY_INTEREST_RATE, ccy)
        self._accruals.append(Accrual(seq=self._next(), account=account, day=day,
                                      base=base, amount=amount))

    def capitalise(self, *, day: int) -> None:
        """Post one credit per account equal to the sum of its not-yet-capitalised
        rounded daily accruals. The sum is exact by construction: nothing is
        discarded and nothing is re-rounded."""
        for account, ccy in self._ccy.items():
            done = {s for c in self._caps if c.account == account for s in c.accrual_seqs}
            pending = [a for a in self._accruals if a.account == account and a.seq not in done]
            if not pending:
                continue
            total = quantize(sum((a.amount for a in pending), ZERO), ccy)
            cap_id = f"CAP-{account}-D{day}"
            if total > 0:
                self._entry(event_id=cap_id, account=account, kind="CAPITALISATION",
                            amount=total, value_date=day, booked_day=day)
            self._caps.append(Capitalisation(seq=self._next(), account=account, day=day,
                                             amount=total,
                                             accrual_seqs=tuple(a.seq for a in pending)))
            self._outcome(day=day, event_id=cap_id, account=account, status="CAPITALISED",
                          detail=f"{len(pending)} daily accruals capitalised, total {fmt(total, ccy)}")
