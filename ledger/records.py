"""Immutable record types. Every record is written once and never changed."""
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Tuple


@dataclass(frozen=True)
class Entry:
    """A ledger posting. amount is signed: + increases the ledger balance."""
    seq: int
    event_id: str
    account: str
    kind: str            # OPENING | CREDIT | DEBIT | SETTLEMENT | REVERSAL | FEE | CAPITALISATION
    amount: Decimal
    value_date: int
    booked_day: int
    ref: Optional[str] = None
    note: str = ""


@dataclass(frozen=True)
class AuthRecord:
    """One state transition of an authorisation. Current state = latest record."""
    seq: int
    event_id: str
    auth_id: str
    account: str
    status: str          # APPROVED | DECLINED | SETTLED
    hold: Decimal
    booked_day: int
    note: str = ""


@dataclass(frozen=True)
class Accrual:
    seq: int
    account: str
    day: int
    base: Decimal        # closing ledger balance the accrual was computed on
    amount: Decimal      # rounded to account precision


@dataclass(frozen=True)
class Capitalisation:
    seq: int
    account: str
    day: int
    amount: Decimal
    accrual_seqs: Tuple[int, ...]


@dataclass(frozen=True)
class Outcome:
    """Result of handling one event (or one system action such as a fee)."""
    seq: int
    day: int
    event_id: str
    account: str
    status: str          # POSTED | REVERSED | APPROVED | DECLINED | SETTLED | REJECTED | FEE | CAPITALISED
    detail: str
