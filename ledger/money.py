"""Currency precision and exact money helpers. Stdlib only."""
from decimal import ROUND_HALF_UP, Decimal
from typing import List, Union

CURRENCY_DP = {"AED": 2, "BHD": 3}

Amount = Union[str, int, Decimal]


def to_decimal(value: Amount) -> Decimal:
    if isinstance(value, float):
        raise TypeError("floats are not accepted; pass str, int or Decimal")
    return Decimal(str(value))


def unit(ccy: str) -> Decimal:
    """Smallest representable amount in the currency (0.01 AED, 0.001 BHD)."""
    return Decimal(1).scaleb(-CURRENCY_DP[ccy])


def quantize(value: Amount, ccy: str) -> Decimal:
    return to_decimal(value).quantize(unit(ccy), rounding=ROUND_HALF_UP)


def fmt(value: Amount, ccy: str) -> str:
    return f"{quantize(value, ccy):,.{CURRENCY_DP[ccy]}f}"


def split_equal(total: Amount, parts: int, ccy: str) -> List[Decimal]:
    """Split total into `parts` amounts at currency precision, summing exactly.

    Equal split is impossible when total is not divisible at minor-unit
    precision; the leftover minor units go to the earliest instalments.
    """
    total = quantize(total, ccy)
    if total <= 0 or parts < 1:
        raise ValueError("split needs a positive total and at least one part")
    u = unit(ccy)
    minor = int(total / u)
    base, extra = divmod(minor, parts)
    return [quantize(Decimal(base + (1 if i < extra else 0)) * u, ccy)
            for i in range(parts)]
