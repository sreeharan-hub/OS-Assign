"""Validation tests.  Run:  python -m unittest discover -s tests -v

The simulator is checked against known textbook answers *before* any experiment
is trusted.
"""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from simulator import (fifo, lru, opt, mru, random_policy, clock, dedup,  # noqa: E402
                       simulate, POLICIES)
from stackdist import stack_distances, lru_faults_from_distances  # noqa: E402
import traces  # noqa: E402

# Silberschatz, Galvin & Gagne, Operating System Concepts: 20-reference string
TEXTBOOK = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1]
# Classic Belady's-anomaly string
BELADY = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]


def rand_string(rng, length=None, pages=None):
    length = length or rng.randint(20, 60)
    pages = pages or rng.randint(3, 9)
    return [rng.randrange(pages) for _ in range(length)]


class TextbookAnswers(unittest.TestCase):
    def test_textbook_three_frames(self):
        self.assertEqual(fifo(TEXTBOOK, 3), 15)
        self.assertEqual(lru(TEXTBOOK, 3), 12)
        self.assertEqual(opt(TEXTBOOK, 3), 9)

    def test_belady_anomaly_reproduced(self):
        self.assertEqual(fifo(BELADY, 3), 9)
        self.assertEqual(fifo(BELADY, 4), 10)  # more frames, MORE faults

    def test_belady_string_lru_opt_unaffected(self):
        self.assertLessEqual(lru(BELADY, 4), lru(BELADY, 3))
        self.assertLessEqual(opt(BELADY, 4), opt(BELADY, 3))

    def test_cold_only_when_memory_covers_footprint(self):
        for pol in POLICIES:
            self.assertEqual(simulate(pol, TEXTBOOK, 8), len(set(TEXTBOOK)), pol)


class Properties(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(12345)

    def test_opt_is_lower_bound(self):
        for _ in range(300):
            s = rand_string(self.rng)
            for m in range(1, 8):
                o = opt(s, m)
                for pol in ("FIFO", "LRU", "MRU", "CLOCK"):
                    self.assertLessEqual(o, simulate(pol, s, m), (pol, m, s))
                self.assertLessEqual(o, random_policy(s, m, 1))

    def test_stack_algorithms_monotone(self):
        for _ in range(300):
            s = rand_string(self.rng)
            for m in range(1, 8):
                self.assertLessEqual(lru(s, m + 1), lru(s, m), (m, s))
                self.assertLessEqual(opt(s, m + 1), opt(s, m), (m, s))

    def test_dedup_does_not_change_faults(self):
        for _ in range(200):
            s = rand_string(self.rng, pages=4)
            d = dedup(s)
            for m in range(1, 6):
                for pol in ("FIFO", "LRU", "OPT", "MRU", "CLOCK"):
                    self.assertEqual(simulate(pol, s, m), simulate(pol, d, m), (pol, m))

    def test_random_policy_reproducible(self):
        s = rand_string(self.rng, length=200, pages=20)
        self.assertEqual(random_policy(s, 6, seed=7), random_policy(s, 6, seed=7))

    def test_clock_between_one_frame_cases(self):
        # one frame: every page change faults for every policy
        s = dedup([1, 1, 2, 3, 3, 1])
        for pol in POLICIES:
            self.assertEqual(simulate(pol, s, 1), len(s), pol)


class StackDistance(unittest.TestCase):
    def test_matches_lru_simulator(self):
        rng = random.Random(99)
        for _ in range(100):
            s = dedup(rand_string(rng, length=rng.randint(30, 120), pages=rng.randint(3, 15)))
            frames = list(range(1, 17))
            from_dist = lru_faults_from_distances(stack_distances(s), frames)
            for m in frames:
                self.assertEqual(from_dist[m], lru(s, m), (m, s))

    def test_small_example(self):
        # a b c a  -> distances: cold cold cold 3
        self.assertEqual(stack_distances(["a", "b", "c", "a"]), [0, 0, 0, 3])


class TraceGenerators(unittest.TestCase):
    def test_footprints(self):
        self.assertEqual(len(set(traces.sequential_loop())), 512)
        self.assertEqual(len(traces.sequential_loop()), 512 * 20)
        self.assertEqual(len(set(traces.uniform_random(seed=1))), 512)
        self.assertEqual(len(traces.uniform_random()), 10240)
        self.assertEqual(len(set(traces.shuffled_epochs())), 512)
        self.assertEqual(len(traces.shuffled_epochs()), 512 * 20)
        self.assertEqual(len(set(traces.bursty())), 48 + 512)
        self.assertEqual(len(traces.bursty()), 40 * (400 + 128))
        self.assertEqual(len(set(traces.forward_backward())), 256)
        self.assertEqual(len(traces.forward_backward()), 20 * 2 * 256)

    def test_matmul_shapes(self):
        a = traces.matmul_naive()
        b = traces.matmul_tiled()
        self.assertEqual(len(a), 64 ** 3 * 2 + 64 * 64)  # 528,384
        self.assertGreater(len(b), len(a))  # tiling re-touches C once per k-tile
        self.assertEqual(len(set(a)), 768)
        self.assertEqual(set(a), set(b))  # same data touched, different order

    def test_seed_determinism(self):
        for name in ("random", "shuffled", "bursty"):
            self.assertEqual(traces.build(name, seed=3), traces.build(name, seed=3))
            self.assertNotEqual(traces.build(name, seed=3), traces.build(name, seed=4))


if __name__ == "__main__":
    unittest.main()
