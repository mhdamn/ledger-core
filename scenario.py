"""The event stream from the brief, as data.

`day` is the booked day. `value_date` is the value date. The stream is listed
as E1..E10; E9 is booked Day 6 and E10 Day 5, so replay groups by booked day
and keeps listed order within a day (see AMBIGUITIES.md #6).
"""
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class Event:
    event_id: str
    day: int
    kind: str                       # CREDIT | DEBIT | AUTHORIZATION | SETTLEMENT | REVERSAL
    account: str
    amount: Optional[str] = None
    value_date: Optional[int] = None
    auth_id: Optional[str] = None
    target: Optional[str] = None    # REVERSAL: event id being reversed
    instalments: int = 1


ACCOUNTS: Tuple[Tuple[str, str, str], ...] = (
    ("ACC-001", "AED", "0.00"),
    ("ACC-002", "BHD", "0.000"),
)

EVENTS: Tuple[Event, ...] = (
    Event("E1", 1, "CREDIT", "ACC-001", "1200.00", 1),
    Event("E2", 1, "DEBIT", "ACC-001", "950.00", 1),
    Event("E3", 2, "AUTHORIZATION", "ACC-001", "200.00", 2, auth_id="Auth-A"),
    Event("E4", 3, "CREDIT", "ACC-001", "400.00", 3),
    Event("E5", 4, "SETTLEMENT", "ACC-001", "185.00", 4, auth_id="Auth-A"),
    Event("E6", 4, "SETTLEMENT", "ACC-001", "180.00", 4, auth_id="Auth-Z"),
    Event("E7", 5, "DEBIT", "ACC-001", "620.00", 2),
    Event("E8", 5, "AUTHORIZATION", "ACC-001", "90.00", 5, auth_id="Auth-B"),
    Event("E9", 6, "REVERSAL", "ACC-001", target="E7", value_date=2),
    Event("E10", 5, "CREDIT", "ACC-002", "10.000", 5, instalments=3),
)
