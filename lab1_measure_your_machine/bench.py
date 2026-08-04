"""
bench.py (Lab 1): measure your own machine.

Implement the seven TODO functions below. Each task is runnable the same way:

    python3 bench.py 1.1
    python3 bench.py 1.2
    python3 bench.py 1.3
    python3 bench.py 1.4
    python3 bench.py 1.5
    python3 bench.py 1.6
    python3 bench.py 1.7

Keep the raw timing numbers you get: 1.3 in particular is needed again in
Lab 3 Part 4.
"""
import argparse
import mmap
import os

DATA_SIZE = 16 * 1024 * 1024 * 1024  # 16 GiB

# On the course node, this lives on the student's own dedicated disk
# ($STEAM_SCRATCH_DIR) instead of the current directory. Home directories
# otherwise sit on a ~40GB root filesystem shared by every concurrent
# student, and a file this size per student would risk filling it for
# everyone. On a laptop (no $STEAM_SCRATCH_DIR), it's just the current
# directory: your own disk, your own call.
WORK_DIR = os.environ.get("STEAM_SCRATCH_DIR") or "."
os.makedirs(WORK_DIR, exist_ok=True)
DATA_FILE = os.path.join(WORK_DIR, "bench_data.bin")

# Tasks 1.1/1.6 compare sequential vs random access using this many bytes,
# kept separate from (and much smaller than) DATA_SIZE, which exists for
# other tasks' benefit. A random pass across the WHOLE, much bigger
# DATA_FILE would mean millions of real disk seeks once it falls out of
# page cache: on a real HDD, hours instead of seconds. This keeps it at a
# fixed, safe 65536 seeks either way.
COMPARE_BYTES = 256 * 1024 * 1024


def ensure_test_file(path=DATA_FILE, size=DATA_SIZE):
    """Creates the shared test file if it doesn't already exist."""
    if os.path.exists(path) and os.path.getsize(path) >= size:
        return
    with open(path, "wb") as f:
        remaining = size
        chunk = os.urandom(1024 * 1024)
        while remaining > 0:
            f.write(chunk[: min(len(chunk), remaining)])
            remaining -= len(chunk)


def drop_cache(path):
    """Given: best-effort, asks the kernel to evict this file's cached
    pages, so the next read genuinely hits the device instead of RAM
    (with 16+ GB of RAM around, a file that was just written stays fully
    page-cached, and every read, sequential or random, looks equally
    fast). Unprivileged and Linux-only (posix_fadvise); silently a no-op
    on macOS/Windows, where you'll want to interpret your numbers with
    that in mind."""
    if not hasattr(os, "posix_fadvise"):
        return
    fd = os.open(path, os.O_RDONLY)
    try:
        os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
    finally:
        os.close(fd)


def task_1_1_sequential_vs_random():
    """
    Task 1.1: sequential vs random, same total bytes.

    The two passes use different block sizes on purpose (1 MiB
    sequential, 4 KiB random). That's not a loose end to fix, it's the
    realistic pairing for each pattern: streaming/bulk workloads read in
    large blocks, random/lookup-style workloads read in small ones. This
    isn't a controlled experiment isolating block size from pattern; it's
    the two of them as they actually show up together in practice.

    Call drop_cache(DATA_FILE) right before EACH pass (yes, twice: the
    sequential pass's own read re-populates the cache for that region, so
    skipping the second call would leave the random pass reading warm
    data your first pass just cached). Otherwise you're comparing two
    RAM-speed reads, not real device behavior.

    TODO:
      1. drop_cache(DATA_FILE), then read the first COMPARE_BYTES of
         DATA_FILE sequentially in 1 MiB chunks. Time it.
      2. drop_cache(DATA_FILE) again, then read COMPARE_BYTES // 4096
         random 4 KiB chunks from DATA_FILE
         (random offset each time, via f.seek()), same total bytes as
         step 1, just moved differently (see the note above
         COMPARE_BYTES for why this is capped well below DATA_SIZE). Time
         it.
      3. Print both throughputs (MiB/s). Same total bytes moved either
         way; the only difference is block size and access pattern.
    """
    raise NotImplementedError("task_1_1_sequential_vs_random: implement me")


def task_1_2_flush():
    """
    Task 1.2: write loop, with and without an explicit flush.

    TODO:
      1. Open a fresh file, write N small blocks (e.g. 2000 x 4 KiB) with
         no flush/fsync at all. Time it.
      2. Repeat, but call f.flush() + os.fsync(f.fileno()) after every
         single write. Time it.
      3. Print both times and the ratio between them.
    """
    raise NotImplementedError("task_1_2_flush: implement me")


def task_1_3_queue_depth_sweep():
    """
    Task 1.3: queue-depth sweep 1 to 256. KEEP THE RAW PER-OP TIMINGS.

    "Queue depth" is how many I/O requests are outstanding (issued but
    not yet completed) at once. A single disk has one seek mechanism but
    can still juggle several in-flight requests, which is why throughput
    can keep rising with depth for a while, until it can't. The "knee" in
    Lab 3 Part 4's TODO below is that turning point: the depth where more
    concurrency stops buying more throughput.

    TODO:
      1. For each depth in (1, 4, 16, 64, 256): issue a batch of random
         4 KiB reads against DATA_FILE using that many concurrent workers
         (concurrent.futures.ThreadPoolExecutor is fine here: this is an
         approximation of true queue depth, which really needs async I/O
         (hint: think io_uring/AIO), but the throughput/latency trend it
         shows is the real thing).
      2. Record EVERY individual operation's latency, not just the mean.
      3. Print throughput and mean latency per depth.
      4. Write every (queue_depth, latency) pair to a CSV file. Lab 3
         Part 4 needs this file to compute p50/p95/p99 and to find the
         "knee".
    """
    raise NotImplementedError("task_1_3_queue_depth_sweep: implement me")


def task_1_4_buffered_cached_direct():
    """
    Task 1.4: buffered, cached, then O_DIRECT.

    (Reminder: the "page cache" is Linux keeping recently-read/written
    disk blocks in spare RAM, so a repeat read can be served from memory
    instead of the device. O_DIRECT is the flag that opts a file out of
    that: every read/write goes straight to the device.)

    TODO:
      1. Read DATA_FILE once with a normal buffered open(). This is a
         "cold-ish" read (may already be page-cached from setup, note that).
      2. Read it again immediately with the same method. This should be
         served largely from the page cache and be much faster.
      3. If `os.O_DIRECT` exists on this platform (Linux only), open the
         file with `os.open(path, os.O_RDONLY | os.O_DIRECT)` and read
         into a page-aligned buffer: O_DIRECT rejects reads into a
         buffer that isn't aligned to the device's block size. An
         anonymous `mmap.mmap(-1, size)` region is page-aligned on every
         platform that supports O_DIRECT in the first place, so it's a
         one-line way to get an aligned buffer without ctypes; use
         `os.readv(fd, [buf])` to read into it. This bypasses the page
         cache entirely. If O_DIRECT isn't available, print that and
         skip step 3.
      4. Print all the throughputs you measured.
    """
    raise NotImplementedError("task_1_4_buffered_cached_direct: implement me")


def task_1_5_small_file_tax():
    """
    Task 1.5: 100 MB as 1, 100, then 10,000 files.

    Every file costs more than its bytes: an inode, a directory entry,
    permissions, timestamps, bookkeeping the filesystem has to create,
    store and later scan through, on top of the actual data. That's the
    "metadata tax" this task measures: same total bytes, but split across
    more and more files.

    TODO:
      1. For file counts (1, 100, 10000): write the SAME total number of
         bytes (e.g. 100 MB), split evenly across that many files in a
         fresh directory.
      2. Time the writing.
      3. Then time just LISTING that directory (os.listdir()).
      4. Print write time and list time for each file count. The data
         volume is constant; only the metadata cost changes.
    """
    raise NotImplementedError("task_1_5_small_file_tax: implement me")


def task_1_6_mmap():
    """
    Task 1.6: mmap(), treat the file as memory instead of a
    stream. This is the smallest possible taste of "Advanced I/O"
    (mmap/zero-copy/io_uring): mmap() maps a file directly into your
    process's own address space, so you read it by slicing/indexing a
    byte-like object, no read(), no seek(), no syscall per access.

    TODO:
      1. drop_cache(DATA_FILE), same reason as Task 1.1: otherwise
         you're mapping pages already sitting in RAM, not measuring
         anything about the device.
      2. Open DATA_FILE and mmap it read-only:
         mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
      3. Repeat Task 1.1's random-access pattern EXACTLY (same
         COMPARE_BYTES // 4096 ops, same 4 KiB block size) but read each
         block by slicing the mapped object (mm[offset : offset + 4096])
         instead of f.seek() + f.read(). Time it.
      4. Print the throughput and compare it to Task 1.1's random-read
         number: same total bytes, same pattern, different access
         mechanism.
    """
    raise NotImplementedError("task_1_6_mmap: implement me")


def task_1_7_cache_cliff():
    """
    Task 1.7: the cache cliff. Repeat Task 1.1's sequential vs
    random comparison at several sizes (16 MiB, 256 MiB, 1 GiB, 16 GiB)
    to find the point where your OWN machine's page cache stops being
    big enough to hide the difference between them. Writing 4 fresh
    files (up to 16 GiB) and reading each one twice takes real
    wall-clock time, budget for that.

    TODO: for each size in (16 MiB, 256 MiB, 1 GiB, 16 GiB):
      1. Write a FRESH file of that size in WORK_DIR (reuse
         ensure_test_file with a distinct path per size; don't reuse
         DATA_FILE, and don't keep more than one size's file on disk at
         once, or you'll multiply Lab 1's already-sizeable footprint).
      2. Read it sequentially in 1 MiB chunks (the whole file, same idea
         as Task 1.1).
      3. Read min(size, COMPARE_BYTES) // 4096 random 4 KiB chunks: same
         total bytes as the sequential pass whenever size fits under
         COMPARE_BYTES (e.g. the 16 MiB step), otherwise capped at
         COMPARE_BYTES for the same reason Task 1.1 caps it (a real scan
         of the full 16 GiB step would mean millions of disk seeks).
      4. Print both throughputs for this size, then delete the file
         before moving to the next size.

    Question: at what size does random throughput start noticeably
    diverging from sequential? Does that line up with your machine's
    RAM?
    """
    raise NotImplementedError("task_1_7_cache_cliff: implement me")


TASKS = {
    "1.1": task_1_1_sequential_vs_random,
    "1.2": task_1_2_flush,
    "1.3": task_1_3_queue_depth_sweep,
    "1.4": task_1_4_buffered_cached_direct,
    "1.5": task_1_5_small_file_tax,
    "1.6": task_1_6_mmap,
    "1.7": task_1_7_cache_cliff,
}

# these don't touch DATA_FILE at all: 1.5 writes its own small_file_tax/
# directory, 1.7 writes its own differently-sized files per sweep step
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
