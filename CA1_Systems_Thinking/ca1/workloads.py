"""CA-1: synthetic ML-like workloads (seeded, standard library only)."""
import random


def epoch_scan(pages, epochs):
    """Every epoch reads the whole dataset in the same sequential order."""
    return [p for _ in range(epochs) for p in range(pages)]


def shuffled_epoch(pages, epochs, seed=1):
    """Every epoch reads the whole dataset in a new random order (typical SGD data loader)."""
    rng, out = random.Random(seed), []
    for _ in range(epochs):
        perm = list(range(pages))
        rng.shuffle(perm)
        out += perm
    return out


def sharded_epoch(pages, epochs, shard, passes, seed=1):
    """Dataset split into shards that fit in RAM. Shards are visited in random order;
    each shard is read `passes` times (shuffled inside the shard) before moving on."""
    rng, out = random.Random(seed), []
    shards = [list(range(s, min(s + shard, pages))) for s in range(0, pages, shard)]
    for _ in range(epochs):
        rng.shuffle(shards)
        for sh in shards:
            for _ in range(passes):
                perm = sh[:]
                rng.shuffle(perm)
                out += perm
    return out


def hot_plus_stream(pages, hot, epochs, hot_share=0.5, seed=1):
    """Model weights / embeddings (a small hot set touched constantly) + a data stream."""
    rng, out = random.Random(seed), []
    stream = [p for _ in range(epochs) for p in range(hot, pages)]
    for p in stream:
        out.append(p)
        while rng.random() < hot_share:
            out.append(rng.randrange(hot))
    return out


def uniform_random(w, length, seed=1):
    """A process that touches w pages uniformly at random (used by the thrashing model)."""
    rng = random.Random(seed)
    return [rng.randrange(w) for _ in range(length)]
