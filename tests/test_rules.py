"""Unit tests for individual rules, independent of the scenario."""
import dataclasses
import unittest
from decimal import Decimal as D

from ledger import Ledger, LedgerError, quantize, split_equal


def funded(amount="100.00", ccy="AED"):
    l = Ledger()
    l.open_account("A", ccy)
    l.post_credit(event_id="fund", day=1, account="A", amount=amount, value_date=1)
    return l


class Money(unittest.TestCase):
    def test_half_up_rounding(self):
        self.assertEqual(quantize("0.125", "AED"), D("0.13"))
        self.assertEqual(quantize("0.0005", "BHD"), D("0.001"))

    def test_split_always_sums_exactly(self):
        for total in ["10.000", "0.001", "7.777", "1234.567", "0.002"]:
            parts = split_equal(total, 3, "BHD")
            self.assertEqual(sum(parts), D(total), total)

    def test_split_of_10_bhd_is_3334_3333_3333(self):
        self.assertEqual(split_equal("10.000", 3, "BHD"),
                         [D("3.334"), D("3.333"), D("3.333")])

    def test_floats_rejected(self):
        with self.assertRaises(TypeError):
            quantize(0.1, "AED")


class Authorisations(unittest.TestCase):
    def test_approved_when_available_is_exactly_zero(self):
        l = funded("200.00")
        o = l.authorize(event_id="x", day=2, account="A", auth_id="H", amount="200.00")
        self.assertEqual(o.status, "APPROVED")

    def test_declined_when_one_minor_unit_short(self):
        l = funded("200.00")
        o = l.authorize(event_id="x", day=2, account="A", auth_id="H", amount="200.01")
        self.assertEqual(o.status, "DECLINED")

    def test_approved_hold_reduces_available_not_ledger(self):
        l = funded("100.00")
        l.authorize(event_id="x", day=2, account="A", auth_id="H", amount="40.00")
        self.assertEqual(l.ledger_balance("A"), D("100.00"))
        self.assertEqual(l.available_balance("A"), D("60.00"))

    def test_settlement_above_hold_rejected_no_funds_move(self):
        l = funded("100.00")
        l.authorize(event_id="x", day=2, account="A", auth_id="H", amount="40.00")
        o = l.settle(event_id="s", day=3, account="A", auth_id="H", amount="41.00", value_date=3)
        self.assertEqual(o.status, "REJECTED")
        self.assertEqual(l.ledger_balance("A"), D("100.00"))

    def test_settlement_of_declined_auth_rejected(self):
        l = funded("10.00")
        l.authorize(event_id="x", day=2, account="A", auth_id="H", amount="50.00")
        o = l.settle(event_id="s", day=3, account="A", auth_id="H", amount="5.00", value_date=3)
        self.assertEqual(o.status, "REJECTED")

    def test_duplicate_auth_id_rejected(self):
        l = funded("100.00")
        l.authorize(event_id="x", day=2, account="A", auth_id="H", amount="10.00")
        o = l.authorize(event_id="y", day=2, account="A", auth_id="H", amount="10.00")
        self.assertEqual(o.status, "REJECTED")


class Reversals(unittest.TestCase):
    def test_reversal_twice_is_rejected(self):
        l = funded("100.00")
        l.post_debit(event_id="d", day=1, account="A", amount="30.00", value_date=1)
        self.assertEqual(l.reverse(event_id="r1", day=1, account="A", target_event_id="d").status,
                         "REVERSED")
        self.assertEqual(l.reverse(event_id="r2", day=1, account="A", target_event_id="d").status,
                         "REJECTED")
        self.assertEqual(l.ledger_balance("A"), D("100.00"))


class Fees(unittest.TestCase):
    def test_one_fee_per_value_date_even_if_day_closes_twice(self):
        l = Ledger()
        l.open_account("A", "AED")
        l.post_debit(event_id="d", day=1, account="A", amount="10.00", value_date=1)
        l.close_day(1)
        l.close_day(1)
        self.assertEqual(len([e for e in l.entries if e.kind == "FEE"]), 1)

    def test_no_fee_when_closing_is_exactly_zero(self):
        l = Ledger()
        l.open_account("A", "AED")
        l.post_credit(event_id="c", day=1, account="A", amount="10.00", value_date=1)
        l.post_debit(event_id="d", day=1, account="A", amount="10.00", value_date=1)
        l.close_day(1)
        self.assertFalse([e for e in l.entries if e.kind == "FEE"])

    def test_bhd_overdraft_has_no_fee_schedule(self):
        l = Ledger()
        l.open_account("B", "BHD")
        l.post_debit(event_id="d", day=1, account="B", amount="1.000", value_date=1)
        with self.assertRaises(LedgerError):
            l.close_day(1)


class Interest(unittest.TestCase):
    def test_positive_balance_accrues_at_0_04_percent(self):
        l = funded("1000.00")
        l.close_day(1)
        self.assertEqual(l.accruals[-1].amount, D("0.40"))

    def test_negative_balance_accrues_nothing(self):
        l = Ledger()
        l.open_account("A", "AED")
        l.post_debit(event_id="d", day=1, account="A", amount="10.00", value_date=1)
        l.close_day(1)
        self.assertEqual(l.accruals, ())

    def test_capitalised_total_equals_sum_of_rounded_accruals(self):
        l = funded("650.00")
        for day in range(1, 4):
            l.close_day(day)
        l.capitalise(day=3)
        accrued = sum(a.amount for a in l.accruals)
        self.assertEqual(l.capitalisations[-1].amount, accrued)

    def test_capitalise_is_idempotent(self):
        l = funded("650.00")
        l.close_day(1)
        l.capitalise(day=1)
        l.capitalise(day=1)
        self.assertEqual(len(l.capitalisations), 1)


class AppendOnly(unittest.TestCase):
    def test_entries_are_frozen(self):
        e = funded().entries[-1]
        with self.assertRaises(dataclasses.FrozenInstanceError):
            e.amount = D("0")

    def test_no_mutation_or_deletion_api(self):
        for name in ("delete", "update", "remove", "set_balance"):
            self.assertFalse(hasattr(Ledger, name), name)

    def test_entries_view_is_immutable_tuple(self):
        l = funded()
        self.assertIsInstance(l.entries, tuple)
        with self.assertRaises(AttributeError):
            l.entries.append(None)


if __name__ == "__main__":
    unittest.main()
