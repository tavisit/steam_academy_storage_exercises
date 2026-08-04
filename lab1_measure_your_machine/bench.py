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

    TODO, using the variables below:
      1. drop_cache(DATA_FILE). Open DATA_FILE for reading, start a
         timer, and read forward through it in `block_seq`-sized chunks
         until you've read COMPARE_BYTES total (the last chunk may be
         smaller than block_seq if it doesn't divide evenly). Stop the
         timer -> t_seq.
      2. drop_cache(DATA_FILE) again. Open DATA_FILE for reading, start
         a timer, and repeat `n_ops` times: pick a random offset between
         0 and `file_size - block_rand`, seek there, read `block_rand`
         bytes. Stop the timer -> t_rand.
      3. Compute each pass's throughput: COMPARE_BYTES in MiB, divided
         by its own time. Print both throughputs (MiB/s) and how many
         times slower random was. Same total bytes moved either way;
         the only difference is block size and access pattern.
    """
    block_seq = 1024 * 1024
    block_rand = 4096
    file_size = os.path.getsize(DATA_FILE)
    n_ops = COMPARE_BYTES // block_rand

    raise NotImplementedError("task_1_1_sequential_vs_random: implement me")


def task_1_2_flush():
    """
    Task 1.2: write loop, with and without an explicit flush.

    TODO, using the variables below:
      1. Open `path` for writing, start a timer, and write `data` to it
         `n_writes` times back to back, no flush/fsync at all. Stop the
         timer -> t_no_flush.
      2. Open `path` for writing again (overwriting it), start a timer,
         and write `data` `n_writes` times again, but call f.flush()
         then os.fsync(f.fileno()) after EVERY single write. Stop the
         timer -> t_flush.
      3. Delete `path`. Compute each pass's throughput: (n_writes *
         len(data)) in MiB, divided by its own time. Print both times,
         both throughputs, and t_flush / t_no_flush as the "durability
         tax".
    """
    path = os.path.join(WORK_DIR, "bench_flush.bin")
    n_writes = 2000
    data = os.urandom(4096)

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

    TODO, using the variables below:
      1. For each depth in `levels`:
         a. Pick `ops_per_level` random offsets into DATA_FILE, each
            between 0 and `file_size - block_size`.
         b. Using a thread pool of `depth` workers
            (concurrent.futures.ThreadPoolExecutor is fine here: an
            approximation of true queue depth, which really needs async
            I/O -- hint: think io_uring/AIO -- but the throughput/latency
            trend it shows is the real thing), issue one `block_size`
            read at each offset, up to `depth` running concurrently.
            Record the wall-clock start and end of the WHOLE batch (for
            throughput), and the individual duration of EACH read (for
            latency) -- keep every one of those, not just their average.
         c. Compute this depth's throughput: (ops_per_level * block_size)
            in MiB, divided by the batch's wall-clock time. Compute the
            mean of the per-op latencies. Print depth, throughput, mean
            latency.
      2. After the loop, write every (depth, latency) pair you collected
         across ALL depths to `csv_path`, one row per individual
         operation, with a header row. Lab 3 Part 4 needs this exact
         file to compute p50/p95/p99 and find the "knee".
    """
    block_size = 4096
    ops_per_level = 500
    levels = (1, 4, 16, 64, 256)
    csv_path = "queue_depth_timings.csv"
    file_size = os.path.getsize(DATA_FILE)

    raise NotImplementedError("task_1_3_queue_depth_sweep: implement me")


def task_1_4_buffered_cached_direct():
    """
    Task 1.4: buffered, cached, then O_DIRECT.

    (Reminder: the "page cache" is Linux keeping recently-read/written
    disk blocks in spare RAM, so a repeat read can be served from memory
    instead of the device. O_DIRECT is the flag that opts a file out of
    that: every read/write goes straight to the device.)

    TODO, using `block` below:
      1. Open DATA_FILE with a normal buffered open(), start a timer,
         and read it from start to end in `block`-sized chunks until
         exhausted. Stop the timer -> t_buffered. This is a "cold-ish"
         read (may already be page-cached from setup, note that).
      2. Repeat step 1 immediately: same file, same method, fresh timer
         -> t_cached. This should be noticeably faster: the page cache
         is doing the work now.
      3. If `os.O_DIRECT` exists on this platform (Linux only): open the
         file with `os.open(path, os.O_RDONLY | os.O_DIRECT)`, allocate
         a page-aligned buffer (O_DIRECT rejects reads into a buffer
         that isn't aligned to the device's block size; an anonymous
         `mmap.mmap(-1, block)` region is page-aligned on every platform
         that supports O_DIRECT in the first place, so it's a one-line
         way to get one without ctypes), start a timer, and read the
         whole file into that buffer via `os.readv(fd, [buf])` in a loop
         until a read returns 0. Stop the timer -> t_direct. This
         bypasses the page cache entirely. If O_DIRECT isn't available,
         print that and skip this step.
      4. Print all the throughputs you measured (DATA_SIZE in MiB
         divided by each time).
    """
    block = 1024 * 1024

    raise NotImplementedError("task_1_4_buffered_cached_direct: implement me")


def task_1_5_small_file_tax():
    """
    Task 1.5: 100 MB as 1, 100, then 10,000 files.

    Every file costs more than its bytes: an inode, a directory entry,
    permissions, timestamps, bookkeeping the filesystem has to create,
    store and later scan through, on top of the actual data. That's the
    "metadata tax" this task measures: same total bytes, but split across
    more and more files.

    TODO, using the variables below, for each count in `counts`:
      1. Make a fresh subdirectory of `base_dir` (one per count works
         well, e.g. named after the count itself), and compute
         `size_each = total_bytes // count`.
      2. Start a timer and write `count` files into that directory, each
         holding `size_each` bytes (content doesn't matter, os.urandom
         is fine). Stop the timer -> write time.
      3. Start a timer and call os.listdir() on that directory. Stop the
         timer -> list time.
      4. Print the count, write time, and list time. The data volume is
         constant across all three counts; only the metadata cost
         changes.
    """
    total_mb = 100
    counts = (1, 100, 10_000)
    base_dir = os.path.join(WORK_DIR, "small_file_tax")
    total_bytes = total_mb * 1024 * 1024

    raise NotImplementedError("task_1_5_small_file_tax: implement me")


def task_1_6_mmap():
    """
    Task 1.6: mmap(), treat the file as memory instead of a
    stream. This is the smallest possible taste of "Advanced I/O"
    (mmap/zero-copy/io_uring): mmap() maps a file directly into your
    process's own address space, so you read it by slicing/indexing a
    byte-like object, no read(), no seek(), no syscall per access.

    TODO, using the variables below:
      1. drop_cache(DATA_FILE), same reason as Task 1.1: otherwise
         you're mapping pages already sitting in RAM, not measuring
         anything about the device.
      2. Open DATA_FILE and mmap it read-only:
         mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
      3. Start a timer and repeat `n_ops` times: pick a random offset
         between 0 and `file_size - block_rand` (same pattern as Task
         1.1's random pass), and read that slice via
         mm[offset : offset + block_rand] instead of f.seek() +
         f.read(). Stop the timer.
      4. Print the throughput (COMPARE_BYTES in MiB divided by the
         time) and compare it to Task 1.1's random-read number: same
         total bytes, same pattern, different access mechanism.
    """
    block_rand = 4096
    file_size = os.path.getsize(DATA_FILE)
    n_ops = COMPARE_BYTES // block_rand

    raise NotImplementedError("task_1_6_mmap: implement me")


def task_1_7_cache_cliff():
    """
    Task 1.7: the cache cliff. Repeat Task 1.1's sequential vs
    random comparison at several sizes (16 MiB, 256 MiB, 1 GiB, 16 GiB)
    to find the point where your OWN machine's page cache stops being
    big enough to hide the difference between them. Writing 4 fresh
    files (up to 16 GiB) and reading each one twice takes real
    wall-clock time, budget for that.

    TODO, using the variables below, for each (label, size) in `sizes`:
      1. Call ensure_test_file(path, size) to write a FRESH file of
         exactly `size` bytes at `path` (don't reuse DATA_FILE, and
         don't keep more than one size's file on disk at once, or
         you'll multiply Lab 1's already-sizeable footprint).
      2. Start a timer and read the whole file sequentially in
         `block_seq`-sized chunks (same idea as Task 1.1). Stop the
         timer -> t_seq.
      3. Compute `n_ops = min(size, COMPARE_BYTES) // block_rand`: same
         total bytes as the sequential pass whenever size fits under
         COMPARE_BYTES (e.g. the 16 MiB step), otherwise capped at
         COMPARE_BYTES for the same reason Task 1.1 caps it (a real scan
         of the full 16 GiB step would mean millions of disk seeks).
         Start a timer and read `n_ops` random `block_rand`-byte chunks
         at random offsets into the file. Stop the timer -> t_rand.
      4. Print `label`, both throughputs, and their ratio, then delete
         `path` before moving to the next size.

    Question: at what size does random throughput start noticeably
    diverging from sequential? Does that line up with your machine's
    RAM?
    """
    sizes = [
        ("16 MiB", 16 * 1024 * 1024),
        ("256 MiB", 256 * 1024 * 1024),
        ("1 GiB", 1024 * 1024 * 1024),
        ("16 GiB", 16 * 1024 * 1024 * 1024),
    ]
    block_seq = 1024 * 1024
    block_rand = 4096
    path = os.path.join(WORK_DIR, "cache_cliff.bin")

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
