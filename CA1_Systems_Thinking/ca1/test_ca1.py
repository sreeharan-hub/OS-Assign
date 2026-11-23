import unittest, random
from policies import fifo, lru, mru, opt, effective_access_time
from workloads import epoch_scan, shuffled_epoch, sharded_epoch, hot_plus_stream
from working_set import wss_series

TEXTBOOK = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1]


class T(unittest.TestCase):
    def test_textbook(self):
        self.assertEqual((fifo(TEXTBOOK, 3), lru(TEXTBOOK, 3), opt(TEXTBOOK, 3)), (15, 12, 9))

    def test_belady(self):
        s = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]
        self.assertEqual((fifo(s, 3), fifo(s, 4)), (9, 10))

    def test_opt_is_lower_bound(self):
        rng = random.Random(5)
        for _ in range(200):
            s = [rng.randrange(8) for _ in range(60)]
            f = rng.randint(1, 6)
            o = opt(s, f)
            self.assertLessEqual(o, min(fifo(s, f), lru(s, f), mru(s, f)))

    def test_cyclic_scan(self):
        s = epoch_scan(10, 5)
        self.assertEqual(lru(s, 9), 50)      # LRU/FIFO fault on every reference
        self.assertEqual(fifo(s, 9), 50)
        self.assertLess(mru(s, 9), 50)

    def test_everything_fits(self):
        s = shuffled_epoch(50, 4)
        for f in (fifo, lru, opt):
            self.assertEqual(f(s, 50), 50)    # only compulsory faults

    def test_sharding_reduces_faults(self):
        a = lru(shuffled_epoch(400, 12), 250)   # same total references (12 passes)
        b = lru(sharded_epoch(400, 4, 200, 3), 250)
        self.assertLess(b, a)

    def test_wss(self):
        self.assertEqual(max(wss_series(epoch_scan(100, 3), 30)), 30)

    def test_eat(self):
        self.assertAlmostEqual(effective_access_time(0.0), 200.0)
        self.assertGreater(effective_access_time(1e-3), 8000)

    def test_bad_frames(self):
        with self.assertRaises(ValueError):
            lru([1], 0)


if __name__ == "__main__":
    unittest.main()
