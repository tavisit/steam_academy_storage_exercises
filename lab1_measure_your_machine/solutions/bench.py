"""
bench.py (Lab 1): solution.

    python3 bench.py 1.1
    python3 bench.py 1.2
    python3 bench.py 1.3
    python3 bench.py 1.4
    python3 bench.py 1.5
    python3 bench.py 1.6
    python3 bench.py 1.7
"""
import argparse
import concurrent.futures
import csv
import mmap
import os
import random
import shutil
import statistics
import time

DATA_SIZE = 16 * 1024 * 1024 * 1024  # 16 GiB
WORK_DIR = os.environ.get("STEAM_SCRATCH_DIR") or "."
os.makedirs(WORK_DIR, exist_ok=True)
DATA_FILE = os.path.join(WORK_DIR, "bench_data.bin")
COMPARE_BYTES = 256 * 1024 * 1024


def ensure_test_file(path=DATA_FILE, size=DATA_SIZE):
    if os.path.exists(path) and os.path.getsize(path) >= size:
        return
    with open(path, "wb") as f:
        remaining = size
        chunk = os.urandom(1024 * 1024)
        while remaining > 0:
            f.write(chunk[: min(len(chunk), remaining)])
            remaining -= len(chunk)


def drop_cache(path):
    if not hasattr(os, "posix_fadvise"):
        return
    fd = os.open(path, os.O_RDONLY)
    try:
        os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
    finally:
        os.close(fd)


def task_1_1_sequential_vs_random():
    block_seq = 1024 * 1024
    block_rand = 4096
    file_size = os.path.getsize(DATA_FILE)
    n_ops = COMPARE_BYTES // block_rand

    drop_cache(DATA_FILE)
    t0 = time.perf_counter()
    with open(DATA_FILE, "rb") as f:
        remaining = COMPARE_BYTES
        while remaining > 0:
            chunk = f.read(min(block_seq, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
    t_seq = time.perf_counter() - t0

    drop_cache(DATA_FILE)
    rng = random.Random(42)
    t0 = time.perf_counter()
    with open(DATA_FILE, "rb") as f:
        for _ in range(n_ops):
            offset = rng.randrange(0, file_size - block_rand)
            f.seek(offset)
            f.read(block_rand)
    t_rand = time.perf_counter() - t0

    mib = COMPARE_BYTES / (1024 * 1024)
    print(f"sequential (1 MiB blocks): {t_seq:7.3f}s  ({mib / t_seq:8.1f} MiB/s)")
    print(f"random     (4 KiB blocks): {t_rand:7.3f}s  ({mib / t_rand:8.1f} MiB/s)")
    print(f"random was {t_rand / t_seq:.1f}x slower for the same total bytes.")


def task_1_2_flush():
    path = os.path.join(WORK_DIR, "bench_flush.bin")
    n_writes = 2000
    data = os.urandom(4096)

    t0 = time.perf_counter()
    with open(path, "wb") as f:
        for _ in range(n_writes):
            f.write(data)
    t_no_flush = time.perf_counter() - t0

    t0 = time.perf_counter()
    with open(path, "wb") as f:
        for _ in range(n_writes):
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
    t_flush = time.perf_counter() - t0

    os.remove(path)
    mib = (n_writes * len(data)) / (1024 * 1024)
    print(f"{n_writes} x 4 KiB writes, no flush     : {t_no_flush:7.3f}s  ({mib / t_no_flush:9.1f} MiB/s)")
    print(f"{n_writes} x 4 KiB writes, flush+fsync   : {t_flush:7.3f}s  ({mib / t_flush:9.1f} MiB/s)")
    print(f"durability tax: {t_flush / t_no_flush:.1f}x slower")


def task_1_3_queue_depth_sweep():
    block_size = 4096
    ops_per_level = 500
    levels = (1, 4, 16, 64, 256)
    csv_path = "queue_depth_timings.csv"

    file_size = os.path.getsize(DATA_FILE)
    rng = random.Random(7)
    rows = []

    def do_read(offset):
        t0 = time.perf_counter()
        with open(DATA_FILE, "rb") as f:
            f.seek(offset)
            f.read(block_size)
        return time.perf_counter() - t0

    for depth in levels:
        offsets = [rng.randrange(0, file_size - block_size) for _ in range(ops_per_level)]

        t_start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=depth) as pool:
            latencies = list(pool.map(do_read, offsets))
        wall = time.perf_counter() - t_start

        throughput = (ops_per_level * block_size) / wall / (1024 * 1024)
        for lat in latencies:
            rows.append({"queue_depth": depth, "latency_s": lat})

        print(
            f"depth={depth:>3}  throughput={throughput:8.2f} MiB/s  "
            f"mean_latency={statistics.mean(latencies) * 1000:7.3f} ms"
        )

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["queue_depth", "latency_s"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nRaw per-operation timings written to {csv_path}, keep this for Lab 3 Part 4.")


def _page_aligned_buffer(size, alignment=4096):
    # anonymous mmap regions are page-aligned on every platform that
    # supports O_DIRECT, which is exactly the platform this needs to work on
    return mmap.mmap(-1, size)


def task_1_4_buffered_cached_direct():
    block = 1024 * 1024

    t0 = time.perf_counter()
    with open(DATA_FILE, "rb", buffering=block) as f:
        while f.read(block):
            pass
    t_buffered = time.perf_counter() - t0

    t0 = time.perf_counter()
    with open(DATA_FILE, "rb", buffering=block) as f:
        while f.read(block):
            pass
    t_cached = time.perf_counter() - t0

    mib = DATA_SIZE / (1024 * 1024)
    print(f"buffered, first read : {t_buffered:7.3f}s  ({mib / t_buffered:8.1f} MiB/s)")
    print(f"buffered, second read: {t_cached:7.3f}s  ({mib / t_cached:8.1f} MiB/s)  (page cache warm)")

    if not hasattr(os, "O_DIRECT"):
        print("O_DIRECT not available on this platform (Linux-only), skipping.")
        return

    try:
        fd = os.open(DATA_FILE, os.O_RDONLY | os.O_DIRECT)
    except OSError as e:
        print(f"O_DIRECT not usable here ({e}), likely an unsupported filesystem.")
        return

    try:
        buf = _page_aligned_buffer(block)
        t0 = time.perf_counter()
        total = 0
        while True:
            n = os.readv(fd, [buf])
            if n <= 0:
                break
            total += n
        t_direct = time.perf_counter() - t0
        print(f"O_DIRECT read        : {t_direct:7.3f}s  ({total / (1024 * 1024) / t_direct:8.1f} MiB/s)  (page cache bypassed)")
    finally:
        os.close(fd)


def task_1_5_small_file_tax():
    total_mb = 100
    counts = (1, 100, 10_000)
    base_dir = os.path.join(WORK_DIR, "small_file_tax")
    total_bytes = total_mb * 1024 * 1024

    for n in counts:
        d = os.path.join(base_dir, str(n))
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d, exist_ok=True)

        size_each = total_bytes // n
        chunk = os.urandom(min(size_each, 1024 * 1024)) if size_each else b""

        t0 = time.perf_counter()
        for i in range(n):
            with open(os.path.join(d, f"f{i:06d}.bin"), "wb") as f:
                remaining = size_each
                while remaining > 0:
                    piece = chunk[: min(len(chunk), remaining)]
                    f.write(piece)
                    remaining -= len(piece)
        t_write = time.perf_counter() - t0

        t0 = time.perf_counter()
        names = os.listdir(d)
        t_list = time.perf_counter() - t0

        print(
            f"{n:>6} file(s)  write={t_write:8.3f}s  list={t_list:9.5f}s  "
            f"({len(names)} entries seen)"
        )

    shutil.rmtree(base_dir, ignore_errors=True)


def task_1_6_mmap():
    block_rand = 4096
    file_size = os.path.getsize(DATA_FILE)
    n_ops = COMPARE_BYTES // block_rand
    rng = random.Random(42)

    drop_cache(DATA_FILE)
    t0 = time.perf_counter()
    with open(DATA_FILE, "rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            for _ in range(n_ops):
                offset = rng.randrange(0, file_size - block_rand)
                mm[offset : offset + block_rand]
        finally:
            mm.close()
    t_mmap = time.perf_counter() - t0

    mib = COMPARE_BYTES / (1024 * 1024)
    print(f"mmap random access (4 KiB slices): {t_mmap:7.3f}s  ({mib / t_mmap:8.1f} MiB/s)")
    print("Compare this to Task 1.1's random read()/seek() number: same total bytes, same pattern.")


def task_1_7_cache_cliff():
    sizes = [
        ("16 MiB", 16 * 1024 * 1024),
        ("256 MiB", 256 * 1024 * 1024),
        ("1 GiB", 1024 * 1024 * 1024),
        ("16 GiB", 16 * 1024 * 1024 * 1024),
    ]
    block_seq = 1024 * 1024
    block_rand = 4096
    path = os.path.join(WORK_DIR, "cache_cliff.bin")

    for label, size in sizes:
        ensure_test_file(path, size)

        t0 = time.perf_counter()
        with open(path, "rb") as f:
            remaining = size
            while remaining > 0:
                chunk = f.read(min(block_seq, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
        t_seq = time.perf_counter() - t0

        n_ops = min(size, COMPARE_BYTES) // block_rand
        rng = random.Random(42)
        t0 = time.perf_counter()
        with open(path, "rb") as f:
            for _ in range(n_ops):
                offset = rng.randrange(0, size - block_rand)
                f.seek(offset)
                f.read(block_rand)
        t_rand = time.perf_counter() - t0

        mib_seq = size / (1024 * 1024)
        mib_rand = (n_ops * block_rand) / (1024 * 1024)
        print(
            f"{label:>8}:  sequential {mib_seq / t_seq:9.1f} MiB/s   "
            f"random {mib_rand / t_rand:9.1f} MiB/s   "
            f"ratio {(mib_seq / t_seq) / (mib_rand / t_rand):5.1f}x"
        )

        os.remove(path)


TASKS = {
    "1.1": task_1_1_sequential_vs_random,
    "1.2": task_1_2_flush,
    "1.3": task_1_3_queue_depth_sweep,
    "1.4": task_1_4_buffered_cached_direct,
    "1.5": task_1_5_small_file_tax,
    "1.6": task_1_6_mmap,
    "1.7": task_1_7_cache_cliff,
}

NO_DATA_FILE_NEEDED = {"1.5", "1.7"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", choices=sorted(TASKS), help="which task to run")
    args = parser.parse_args()

    if args.task not in NO_DATA_FILE_NEEDED:
        ensure_test_file()
    TASKS[args.task]()


if __name__ == "__main__":
    main()
