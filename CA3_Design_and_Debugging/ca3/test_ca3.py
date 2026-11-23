"""CA-3 regression suite.  Run:  python -m unittest discover -s ca3 -p "test_ca3.py" -v"""
import random
import sys
import unittest
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parent.parent / "src")]
import bugs  # noqa: E402
import simulator as S  # noqa: E402

T = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1]
CAN = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]


class TestProvidedDefect(unittest.TestCase):
    def test_defect_reproduced(self):
        self.assertEqual(bugs.lru_defective(T, 3), 15)       # wrong: this is the FIFO answer
        self.assertEqual(bugs.fifo_reference(T, 3), 15)

    def test_defective_equals_fifo_everywhere(self):
        r = random.Random(3)
        for _ in range(300):
            t = [r.randrange(9) for _ in range(r.randrange(0, 50))]
            for k in (1, 2, 4, 7):
                self.assertEqual(bugs.lru_defective(t, k), bugs.fifo_reference(t, k))


class TestFinalImplementation(unittest.TestCase):
    def test_textbook(self):
        self.assertEqual(bugs.lru_final(T, 3), 12)

    def test_all_fixes_agree_with_oracle(self):
        r = random.Random(5)
        for _ in range(300):
            t = [r.randrange(12) for _ in range(r.randrange(0, 70))]
            for k in (1, 2, 3, 5, 8):
                want = bugs.lru_reference(t, k)
                for fn in bugs.FIXES.values():
                    self.assertEqual(fn(t, k), want)
                self.assertEqual(bugs.lru_final(t, k), want)
                self.assertEqual(S.lru(t, k), want)

    def test_no_belady_anomaly(self):
        self.assertEqual([bugs.lru_final(CAN, k) for k in range(1, 8)], [12, 12, 10, 8, 5, 5, 5])
        self.assertEqual([bugs.fifo_reference(CAN, k) for k in range(1, 8)], [12, 12, 9, 10, 5, 5, 5])

    def test_cyclic_loop_always_faults(self):
        for k in (2, 3, 8):
            self.assertEqual(bugs.lru_final(list(range(k + 1)) * 5, k), (k + 1) * 5)

    def test_invalid_input_and_recovery(self):
        for bad in (0, -3, 2.5, None):
            with self.assertRaises(ValueError):
                bugs.lru_final(T, bad)
        self.assertEqual(bugs.lru_final(T, 3), 12)            # no state leaks after a failed call


class TestFaultInjection(unittest.TestCase):
    def test_every_mutant_is_caught_by_the_oracle(self):
        r = random.Random(9)
        sample = [[r.randrange(12) for _ in range(r.randrange(10, 60))] for _ in range(100)]
        for name, fn in bugs.mutants.items():
            caught = any(fn(t, k) != bugs.lru_reference(t, k) for t in sample for k in (1, 2, 3, 5, 8))
            self.assertTrue(caught, f"{name} survived the differential test")


if __name__ == "__main__":
    unittest.main()
