"""Acceptance tests against the replayed event stream.

Each acceptance criterion from the brief is either asserted here (if true) or
asserted in its corrected form (if false). See REJECTED.md for the refusals.
"""
import unittest
from decimal import Decimal as D

from replay import run


class Acceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = run()
        cls.l = cls.r.ledger

    def outcome(self, event_id):
        matches = [o for o in self.l.outcomes if o.event_id == event_id]
        self.assertEqual(len(matches), 1, event_id)
        return matches[0]

    # Criterion 1 (TRUE)
    def test_day2_closing_end_day5_before_fees_is_minus_370(self):
        self.assertEqual(self.r.restated_day2_end_day5, D("-370.00"))

    # Criterion 3 (TRUE)
    def test_day4_settlement_of_auth_a_is_accepted(self):
        self.assertEqual(self.outcome("E5").status, "SETTLED")

    # Criterion 4 (TRUE)
    def test_settlement_of_unknown_auth_rejected_and_funds_stay(self):
        self.assertEqual(self.outcome("E6").status, "REJECTED")
        self.assertFalse([e for e in self.l.entries if e.event_id == "E6"])
        self.assertEqual(self.r.summary[4]["ACC-001"]["ledger"], D("465.00"))

    # Criterion 5 (TRUE, conditional; Auth-B is declined in this replay so the
    # hold path is exercised in test_rules.py::test_approved_hold_reduces_available_not_ledger)
    def test_auth_b_declined_so_no_hold_is_active(self):
        self.assertEqual(self.outcome("E8").status, "DECLINED")
        self.assertEqual(self.l.active_holds("ACC-001"), D("0.00"))

    # Criterion 6 (FALSE, corrected form): balances return, fees do not
    def test_after_e9_ledger_matches_pre_e7_only_before_fees_and_interest(self):
        pre_e7_ledger = self.r.summary[4]["ACC-001"]["ledger"]         # 465.00
        fees = sum(e.amount for e in self.l.entries if e.kind == "FEE")
        self.assertEqual(pre_e7_ledger, D("465.00"))
        self.assertEqual(fees, D("-75.00"))                            # fees do not return
        self.assertEqual(self.r.summary[6]["ACC-001"]["ledger"], D("390.81"))

    # Criterion 7 (FALSE, corrected form): 10.000 cannot be three equal 3.334s
    def test_e10_instalments_are_3334_3333_3333(self):
        amts = [e.amount for e in self.l.entries if e.event_id.startswith("E10.")]
        self.assertEqual(amts, [D("3.334"), D("3.333"), D("3.333")])
        self.assertEqual(sum(amts), D("10.000"))

    # Criterion 8 (FALSE, corrected form): remainder is never discarded
    def test_interest_sum_equals_capitalised_total_exactly(self):
        accrued = sum(a.amount for a in self.l.accruals if a.account == "ACC-001")
        capitalised = [c.amount for c in self.l.capitalisations if c.account == "ACC-001"]
        self.assertEqual(accrued, D("0.81"))
        self.assertEqual(capitalised, [D("0.81")])
        self.assertEqual(self.r.summary[6]["ACC-001"]["accrual"], D("0.16"))

    def test_bhd_interest_sums_exactly(self):
        accrued = sum(a.amount for a in self.l.accruals if a.account == "ACC-002")
        self.assertEqual(accrued, D("0.008"))
        self.assertEqual(self.l.capitalisations[-1].amount, D("0.008"))

    def test_final_balances(self):
        self.assertEqual(self.r.summary[6]["ACC-001"]["ledger"], D("390.81"))
        self.assertEqual(self.r.summary[6]["ACC-002"]["ledger"], D("10.008"))

    # Criterion 2 (FALSE). Expected to FAIL against this design. Kept as an
    # expected failure so the suite is green while the defect is on record.
    @unittest.expectedFailure
    def test_e7_causes_exactly_one_overdraft_fee_on_day2(self):
        """ANNOTATED FAILING TEST. Against this design it fails with
        `3 != 1`.

        What it reveals: the fee rule is per (account, value date), checked at
        every end-of-day pass against the closing ex-fees. E7 (booked Day 5,
        value date 2) pushes three value dates below zero: 2 (-370.00),
        4 (-155.00) and 5 (-155.00). Without E7 the Day 4 closing is 465.00.
        So E7 causes three fees, on Day 2, Day 4 and Day 5, not one. The
        criterion treats 'the first fee E7 triggers' as 'every fee E7 causes'.
        Refused in REJECTED.md, item C2.
        """
        fees = [e for e in self.l.entries if e.kind == "FEE"]
        self.assertEqual(len(fees), 1)
        self.assertEqual(fees[0].value_date, 2)


if __name__ == "__main__":
    unittest.main()
