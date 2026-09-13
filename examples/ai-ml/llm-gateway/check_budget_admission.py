"""Offline admission-contract checks using synthetic integer cost units.

Run: python3 examples/ai-ml/llm-gateway/check_budget_admission.py

This is an in-memory model, not a gateway or durable/distributed ledger.
It assumes valid conservative price bounds. No provider, AWS or network
operation is performed. A Lock models atomic reservation on one ledger;
these tests do not verify a production database's atomicity or recovery.
"""

from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import unittest


class AdmissionDenied(Exception):
    pass


class TraceLedger:
    def __init__(self, limit):
        self.limit = limit
        self.spent = 0
        self.grants = {}
        self.events = []
        self.lock = Lock()

    def held(self):
        # Called under the lock, or after all worker threads have completed.
        return sum(g["bound"] for g in self.grants.values() if not g["settled"])

    def reserve(self, call_id, bound, expires, now):
        with self.lock:
            if type(bound) is not int or bound < 0:
                raise ValueError("The bound must be a nonnegative integer.")
            if call_id in self.grants:
                raise AdmissionDenied("A retry needs its own funded call ID.")
            if expires <= now or self.spent + self.held() + bound > self.limit:
                self.events.append(("denied", call_id))
                return False
            self.grants[call_id] = {
                "bound": bound,
                "expires": expires,
                "dispatched": False,
                "settled": False,
                "actual": None,
            }
            self.events.append(("reserved", call_id))
            return True

    def dispatch(self, call_id, now):
        with self.lock:
            grant = self.grants.get(call_id)
            if not grant or grant["dispatched"] or grant["expires"] <= now:
                raise AdmissionDenied("No unused, unexpired reservation.")
            # A real system must persist this record before the external call.
            self.events.append(("subcall_started", call_id))
            grant["dispatched"] = True
            self.events.append(("dispatch", call_id))  # No actual API call.

    def settle(self, call_id, actual):
        with self.lock:
            grant = self.grants[call_id]
            if not grant["dispatched"]:
                raise AdmissionDenied("No dispatched call to settle.")
            if type(actual) is not int or not 0 <= actual <= grant["bound"]:
                raise ValueError("The assumed price bound was not respected.")
            if grant["settled"]:
                if actual != grant["actual"]:
                    raise ValueError("Conflicting settlement requires reconciliation.")
                return
            grant["actual"] = actual
            grant["settled"] = True
            self.spent += actual
            self.events.append(("settled", call_id))
            assert self.spent + self.held() <= self.limit


class AdmissionContractTests(unittest.TestCase):
    def assert_funded_dispatches(self, ledger):
        for index, event in enumerate(ledger.events):
            if event[0] == "dispatch":
                prefix = ledger.events[:index]
                self.assertIn(("reserved", event[1]), prefix)
                self.assertIn(("subcall_started", event[1]), prefix)

    def test_unfunded_router_cannot_dispatch(self):
        ledger = TraceLedger(0)
        self.assertFalse(ledger.reserve("router", 1, expires=10, now=0))
        with self.assertRaises(AdmissionDenied):
            ledger.dispatch("router", now=0)
        self.assertEqual(ledger.spent, 0)
        self.assertFalse(any(kind == "dispatch" for kind, _ in ledger.events))

    def test_expired_allowance_blocks_auxiliary_dispatch(self):
        ledger = TraceLedger(10)
        self.assertTrue(ledger.reserve("classifier", 10, expires=1, now=0))
        with self.assertRaises(AdmissionDenied):
            ledger.dispatch("classifier", now=1)
        self.assertEqual(ledger.held(), 10)
        self.assertEqual(ledger.spent, 0)

    def test_auxiliary_cost_remains_when_main_admission_fails(self):
        ledger = TraceLedger(100)
        self.assertTrue(ledger.reserve("router", 10, expires=10, now=0))
        ledger.dispatch("router", now=0)
        ledger.settle("router", 7)
        self.assertFalse(ledger.reserve("main", 100, expires=10, now=0))
        self.assertEqual(ledger.spent, 7)
        self.assertEqual(ledger.held(), 0)
        self.assert_funded_dispatches(ledger)

    def test_concurrent_auxiliary_reservations_are_disjoint(self):
        ledger = TraceLedger(100)
        with ThreadPoolExecutor(max_workers=20) as pool:
            admitted = list(pool.map(
                lambda i: ledger.reserve(f"router-{i}", 10, expires=10, now=0),
                range(20),
            ))
        self.assertEqual(sum(admitted), 10)
        self.assertEqual(ledger.held(), 100)
        for i, permitted in enumerate(admitted):
            if permitted:
                ledger.dispatch(f"router-{i}", now=0)
                ledger.settle(f"router-{i}", 10)
        self.assertEqual(ledger.spent, 100)
        self.assert_funded_dispatches(ledger)

    def test_required_output_check_is_funded_before_generation(self):
        ledger = TraceLedger(100)
        self.assertTrue(ledger.reserve("output-check", 20, expires=10, now=0))
        self.assertTrue(ledger.reserve("main", 80, expires=10, now=0))
        ledger.dispatch("main", now=0)
        ledger.settle("main", 80)
        ledger.dispatch("output-check", now=0)
        ledger.settle("output-check", 20)
        self.assertEqual(ledger.spent, 100)
        self.assert_funded_dispatches(ledger)

    def test_expiry_does_not_refund_unknown_usage(self):
        ledger = TraceLedger(100)
        self.assertTrue(ledger.reserve("guardrail", 100, expires=1, now=0))
        ledger.dispatch("guardrail", now=0)
        self.assertFalse(ledger.reserve("retry", 1, expires=3, now=2))
        self.assertEqual(ledger.held(), 100)
        ledger.settle("guardrail", 70)  # Known usage arrives after lease expiry.
        self.assertTrue(ledger.reserve("retry", 30, expires=3, now=2))
        self.assert_funded_dispatches(ledger)

    def test_replay_does_not_dispatch_or_settle_twice(self):
        ledger = TraceLedger(10)
        self.assertTrue(ledger.reserve("embedding", 10, expires=10, now=0))
        ledger.dispatch("embedding", now=0)
        with self.assertRaises(AdmissionDenied):
            ledger.dispatch("embedding", now=0)
        ledger.settle("embedding", 6)
        ledger.settle("embedding", 6)
        self.assertEqual(ledger.spent, 6)
        self.assert_funded_dispatches(ledger)


if __name__ == "__main__":
    unittest.main()
