"""
bench.py -- Lab 2 solution.

    python3 bench.py 2.1
    python3 bench.py 2.2
    python3 bench.py 2.3
    python3 bench.py 2.4
    python3 bench.py 2.5
    python3 bench.py 2.6
    python3 bench.py 2.7
    python3 bench.py 2.8
"""
import argparse
import concurrent.futures
import csv
import glob
import mmap
import os
import random
import shutil
import statistics
import sys
import time

DATA_SIZE = 16 * 1024 * 1024 * 1024  # 16 GiB
WORK_DIR = os.environ.get("STEAM_BENCH_DIR") or "."
os.makedirs(WORK_DIR, exist_ok=True)
DATA_FILE = os.path.join(WORK_DIR, "bench_data.bin")
COMPARE_BYTES = 256 * 1024 * 1024

# walk up from this file until a `common/` sibling turns up -- works
# whether this file stays at its committed depth (.../solutions/) or
# gets copied up to replace the stub (.../), same as every other
# solutions/*.py file
_dir = os.path.dirname(os.path.abspath(__file__))
while not os.path.isdir(os.path.join(_dir, "common")):
    _dir = os.path.dirname(_dir)
LAB1_DIR = os.path.join(_dir, "lab1_object_store")
sys.path.insert(0, LAB1_DIR)
from cloud import cloud_ls, cloud_upload  # noqa: E402

sys.path.insert(0, os.path.join(_dir, "common"))
from cloud_lowlevel import (  # noqa: E402
    N_SERVERS,
    delete,
    leftvalue,
    list_names,
    rightvalue,
    sha1string,
)

_SKIP_SUFFIXES = (".chunk0", ".chunk1", ".chunk2", ".chunk3", ".parity", ".meta", ".sha1")
NEW_RING_SIZE = 4


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


def task_2_1_sequential_vs_random():
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


def _page_aligned_buffer(size, alignment=4096):
    # anonymous mmap regions are page-aligned on every platform that
    # supports O_DIRECT, which is exactly the platform this needs to work on
    return mmap.mmap(-1, size)


def task_2_2_buffered_cached_direct():
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
        print("O_DIRECT not available on this platform (Linux-only) -- skipping.")
        return

    try:
        fd = os.open(DATA_FILE, os.O_RDONLY | os.O_DIRECT)
    except OSError as e:
        print(f"O_DIRECT not usable here ({e}) -- likely an unsupported filesystem.")
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


def task_2_3_flush():
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
    print(f"{n_writes} x 4 KiB writes, no flush     : {t_no_flush:7.3f}s")
    print(f"{n_writes} x 4 KiB writes, flush+fsync   : {t_flush:7.3f}s")
    print(f"durability tax: {t_flush / t_no_flush:.1f}x slower")


def task_2_4_queue_depth_sweep():
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
    print(f"\nRaw per-operation timings written to {csv_path} -- keep this for Lab 3C.")


def h4d(hexchar):
    return int(hexchar, 16) // 4 + 1


def _current_replica_servers(cloud_name):
    primary = h4d(sha1string(cloud_name)[0])
    return [primary, leftvalue(primary, 1, NEW_RING_SIZE), rightvalue(primary, 1, NEW_RING_SIZE)]


def _is_collectible(name):
    return not name.endswith(_SKIP_SUFFIXES)


def cloud_gc(dry_run=True):
    report = []
    per_server_counts = {}

    for server in range(1, N_SERVERS + 1):
        orphans_here = 0
        for name in list_names(server):
            if not _is_collectible(name):
                continue
            if server not in _current_replica_servers(name):
                orphans_here += 1
                report.append((server, name))
                if not dry_run:
                    delete(server, name)
        per_server_counts[server] = orphans_here

    mode = "would delete (dry run)" if dry_run else "deleted"
    for server, count in per_server_counts.items():
        print(f"server {server}: {count} orphan(s) {mode}")
    print(f"\nTotal: {len(report)} orphan(s) {'found' if dry_run else 'removed'}.")
    return report


def _count_copies(names):
    names = set(names)
    return sum(
        1
        for server in range(1, N_SERVERS + 1)
        for name in list_names(server)
        if name in names
    )


def task_2_5_garbage_collection_after_resize():
    pictures = sorted(glob.glob(os.path.join(LAB1_DIR, "pictures", "*")))[:30]
    if len(pictures) < 30:
        print("Not enough sample files -- run make_sample_files.py in lab1_object_store/ first.")
        return

    names = [os.path.basename(p) for p in pictures]
    for path, name in zip(pictures, names):
        cloud_upload(path, name)

    before = _count_copies(names)
    print(f"Uploaded {len(names)} files under the OLD 8-server hash table.")
    print(f"Physical copies of these files on disk: {before} (expected {len(names) * 3} = files x 3 replicas)\n")

    print("cloud_ls() after the 'resize' to 4 servers:")
    print(f"  {len(cloud_ls())} names still listed -- the bucket index doesn't know")
    print("  or care how many servers the hash table has.\n")

    reachable = sum(1 for name in names if name in list_names(h4d(sha1string(name)[0])))
    print(f"Reachable at their NEW-scheme (4-server) primary location: {reachable}/{len(names)}")
    print(
        "The rest still exist on disk, on whichever of the OLD 8 servers "
        "they originally hashed to -- but a lookup that trusts the new "
        "4-server hash table will never look there.\n"
    )

    print("--- dry run ---")
    cloud_gc(dry_run=True)
    after_dry_run = _count_copies(names)
    print(f"Copies of these files still on disk after dry run: {after_dry_run} (should be unchanged: {before})\n")

    print("--- actual GC ---")
    cloud_gc(dry_run=False)
    after = _count_copies(names)
    print(f"\nCopies of these files on disk after GC: {after} (removed {before - after} orphan(s))")
    print(
        "\nNote: GC only REMOVES misplaced copies, it doesn't create the "
        "correct ones -- some files may now be under-replicated at their "
        "new-scheme location. That's exactly what Lab 3B's cloud_heal is for."
    )


def task_2_6_small_file_tax():
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


def task_2_7_mmap():
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
    print("Compare this to Task 2.1's random read()/seek() number -- same total bytes, same pattern.")


def task_2_8_cache_cliff():
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
    "2.1": task_2_1_sequential_vs_random,
    "2.2": task_2_2_buffered_cached_direct,
    "2.3": task_2_3_flush,
    "2.4": task_2_4_queue_depth_sweep,
    "2.5": task_2_5_garbage_collection_after_resize,
    "2.6": task_2_6_small_file_tax,
    "2.7": task_2_7_mmap,
    "2.8": task_2_8_cache_cliff,
}

NO_DATA_FILE_NEEDED = {"2.5", "2.6", "2.8"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", choices=sorted(TASKS), help="which task to run")
    args = parser.parse_args()

    if args.task not in NO_DATA_FILE_NEEDED:
        ensure_test_file()
    TASKS[args.task]()


if __name__ == "__main__":
    main()
