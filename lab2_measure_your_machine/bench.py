"""
bench.py -- Lab 2: measure your own machine.

Implement the nine TODO functions below (2.7 and 2.8 are bonus -- see
their docstrings). Each task is runnable the same way:

    python3 bench.py 2.1
    python3 bench.py 2.2
    python3 bench.py 2.3
    python3 bench.py 2.4
    python3 bench.py 2.5
    python3 bench.py 2.6
    python3 bench.py 2.7
    python3 bench.py 2.8

Keep the raw timing numbers you get -- 2.4 in particular is needed again in
Lab 3C.
"""
import argparse
import glob
import mmap
import os
import sys

DATA_SIZE = 16 * 1024 * 1024 * 1024  # 16 GiB

# On the course node, this lives on the student's own dedicated disk
# ($STEAM_BENCH_DIR) instead of the current directory -- home directories
# otherwise sit on a ~40GB root filesystem shared by every concurrent
# student, and a file this size per student would risk filling it for
# everyone. On a laptop (no $STEAM_BENCH_DIR), it's just the current
# directory -- your own disk, your own call.
WORK_DIR = os.environ.get("STEAM_BENCH_DIR") or "."
os.makedirs(WORK_DIR, exist_ok=True)
DATA_FILE = os.path.join(WORK_DIR, "bench_data.bin")

# Tasks 2.1/2.7 compare sequential vs random access using this many bytes,
# moved the SAME way both times -- kept separate from (and much smaller
# than) DATA_SIZE, which exists for other tasks' benefit. A random pass
# across the WHOLE, much bigger DATA_FILE would mean millions of real
# disk seeks once it falls out of page cache -- on a real HDD, hours
# instead of seconds. This keeps it at a fixed, safe 65536 seeks either way.
COMPARE_BYTES = 256 * 1024 * 1024

# Task 2.5 needs Lab 1's finished cloud.py and common/cloud_lowlevel.py --
# everything else in this file is plain local file I/O and doesn't.
LAB1_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lab1_object_store")
sys.path.insert(0, LAB1_DIR)
from cloud import cloud_ls, cloud_upload  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
from cloud_lowlevel import (  # noqa: E402
    N_SERVERS,
    delete,
    leftvalue,
    list_names,
    rightvalue,
    sha1string,
)

# names that don't follow the plain "one primary + 2 ring neighbours"
# placement rule -- skip these during GC, they belong to Lab 3's other
# schemes (erasure-coded chunks/parity/meta, stored checksums)
_SKIP_SUFFIXES = (".chunk0", ".chunk1", ".chunk2", ".chunk3", ".parity", ".meta", ".sha1")
NEW_RING_SIZE = 4


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
    """Given -- best-effort: ask the kernel to evict this file's cached
    pages, so the next read genuinely hits the device instead of RAM
    (with 16+ GB of RAM around, a file that was just written stays fully
    page-cached, and every read -- sequential or random -- looks equally
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


def task_2_1_sequential_vs_random():
    """
    Task 2.1: sequential vs random, same total bytes.

    The two passes use different block sizes on purpose (1 MiB
    sequential, 4 KiB random) -- that's not a loose end to fix, it's the
    realistic pairing for each pattern: streaming/bulk workloads read in
    large blocks, random/lookup-style workloads read in small ones. This
    isn't a controlled experiment isolating block size from pattern; it's
    the two of them as they actually show up together in practice.

    Call drop_cache(DATA_FILE) right before EACH pass (yes, twice -- the
    sequential pass's own read re-populates the cache for that region, so
    skipping the second call would leave the random pass reading warm
    data your first pass just cached). Otherwise you're comparing two
    RAM-speed reads, not real device behavior.

    TODO:
      1. drop_cache(DATA_FILE), then read the first COMPARE_BYTES of
         DATA_FILE sequentially in 1 MiB chunks. Time it.
      2. drop_cache(DATA_FILE) again, then read COMPARE_BYTES // 4096
         random 4 KiB chunks from DATA_FILE
         (random offset each time, via f.seek()) -- same total bytes as
         step 1, just moved differently (see the note above
         COMPARE_BYTES for why this is capped well below DATA_SIZE). Time
         it.
      3. Print both throughputs (MiB/s). Same total bytes moved either
         way -- the only difference is block size and access pattern.
    """
    raise NotImplementedError("task_2_1_sequential_vs_random: implement me")


def task_2_2_buffered_cached_direct():
    """
    Task 2.2: buffered, cached, then O_DIRECT.

    (Reminder: the "page cache" is Linux keeping recently-read/written
    disk blocks in spare RAM, so a repeat read can be served from memory
    instead of the device. O_DIRECT is the flag that opts a file out of
    that -- every read/write goes straight to the device.)

    TODO:
      1. Read DATA_FILE once with a normal buffered open() -- this is a
         "cold-ish" read (may already be page-cached from setup, note that).
      2. Read it again immediately with the same method -- this should be
         served largely from the page cache and be much faster.
      3. If `os.O_DIRECT` exists on this platform (Linux only), open the
         file with `os.open(path, os.O_RDONLY | os.O_DIRECT)` and read
         into a page-aligned buffer -- O_DIRECT rejects reads into a
         buffer that isn't aligned to the device's block size. An
         anonymous `mmap.mmap(-1, size)` region is page-aligned on every
         platform that supports O_DIRECT in the first place, so it's a
         one-line way to get an aligned buffer without ctypes; use
         `os.readv(fd, [buf])` to read into it. This bypasses the page
         cache entirely. If O_DIRECT isn't available, print that and
         skip step 3.
      4. Print all the throughputs you measured.
    """
    raise NotImplementedError("task_2_2_buffered_cached_direct: implement me")


def task_2_3_flush():
    """
    Task 2.3: write loop, with and without an explicit flush.

    TODO:
      1. Open a fresh file, write N small blocks (e.g. 2000 x 4 KiB) with
         no flush/fsync at all. Time it.
      2. Repeat, but call f.flush() + os.fsync(f.fileno()) after every
         single write. Time it.
      3. Print both times and the ratio between them.
    """
    raise NotImplementedError("task_2_3_flush: implement me")


def task_2_4_queue_depth_sweep():
    """
    Task 2.4: queue-depth sweep 1 -> 256. KEEP THE RAW PER-OP TIMINGS.

    "Queue depth" is how many I/O requests are outstanding (issued but
    not yet completed) at once. A single disk has one seek mechanism but
    can still juggle several in-flight requests, which is why throughput
    can keep rising with depth for a while -- until it can't. The "knee"
    in Lab 3C's TODO below is that turning point: the depth where more
    concurrency stops buying more throughput.

    TODO:
      1. For each depth in (1, 4, 16, 64, 256): issue a batch of random
         4 KiB reads against DATA_FILE using that many concurrent workers
         (concurrent.futures.ThreadPoolExecutor is fine here -- this is an
         approximation of true queue depth, which really needs async I/O
         (hint: think io_uring/AIO), but the throughput/latency trend it
         shows is the real thing).
      2. Record EVERY individual operation's latency, not just the mean.
      3. Print throughput and mean latency per depth.
      4. Write every (queue_depth, latency) pair to a CSV file -- Lab 3C
         needs this file to compute p50/p95/p99 and to find the "knee".
    """
    raise NotImplementedError("task_2_4_queue_depth_sweep: implement me")


def h4d(hexchar):
    """
    Task 2.5a: map a hex character '0'-'f' to a bucket 1-4 -- the same
    "ring" idea as Lab 1's h8d, just resized from 8 buckets to 4.

    (Reminder: a "ring" here just means the buckets are numbered 1..N and
    treated as wrapping around -- leftvalue/rightvalue below use that to
    find a bucket's neighbours.)

    TODO: this is a one-line change to h8d's own formula -- h8d divides by
    2 because 16 possible hex values / 8 buckets = 2 values per bucket.
    How many hex values map to each of the 4 buckets here?
    """
    raise NotImplementedError("h4d: implement me")


def _current_replica_servers(cloud_name):
    """Where `cloud_name` SHOULD live under the resized (4-server) table.
    Given -- reuses your h4d plus Lab 1's leftvalue/rightvalue, unchanged."""
    primary = h4d(sha1string(cloud_name)[0])
    return [primary, leftvalue(primary, 1, NEW_RING_SIZE), rightvalue(primary, 1, NEW_RING_SIZE)]


def _is_collectible(name):
    """Given -- True unless `name` belongs to one of Lab 3's other
    on-disk schemes (erasure-coded chunks, stored checksums), which don't
    follow this plain primary+2-neighbours placement rule and would
    otherwise look like false orphans below."""
    return not name.endswith(_SKIP_SUFFIXES)


def cloud_gc(dry_run=True):
    """
    Task 2.5b: find and (optionally) remove "orphans" -- copies sitting on
    a server that the CURRENT, resized hash table would never look at
    again. They're not corrupt or lost, just stranded: unreachable through
    normal lookups, and wasting disk until something cleans them up.

    TODO:
      1. For each of the N_SERVERS physical servers, get what's stored
         there (hint: list_names(server), same as Lab 1).
      2. Skip anything _is_collectible() says to skip.
      3. For everything else, compare the server you're scanning against
         _current_replica_servers(name) -- given, already computes the 3
         correct locations for you. Not in that list => orphan.
      4. dry_run=True (default): only build and print a report -- delete
         nothing. dry_run=False: also delete(server, name) each orphan
         (hint: same delete() you've already used in Lab 1/3).

    Print a per-server orphan count, then a total, and return the report
    as a list of (server, name) tuples.
    """
    raise NotImplementedError("cloud_gc: implement me")


def _count_copies(names):
    """Physical copies of exactly `names`, across all servers -- scoped to
    this task's own files, since the shared storage root also holds
    whatever other labs have uploaded in the same session."""
    names = set(names)
    return sum(
        1
        for server in range(1, N_SERVERS + 1)
        for name in list_names(server)
        if name in names
    )


def task_2_5_garbage_collection_after_resize():
    """
    Task 2.5: garbage collection after a resize -- implement h4d and
    cloud_gc above, then run this to see both halves of the problem:
    the resize breaking lookups, and your GC cleaning up the orphans it left.
    """
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
    """
    Task 2.6: 100 MB as 1, 100, then 10,000 files.

    Every file costs more than its bytes: an inode, a directory entry,
    permissions, timestamps -- bookkeeping the filesystem has to create,
    store and later scan through, on top of the actual data. That's the
    "metadata tax" this task measures: same total bytes, but split across
    more and more files.

    TODO:
      1. For file counts (1, 100, 10000): write the SAME total number of
         bytes (e.g. 100 MB), split evenly across that many files in a
         fresh directory.
      2. Time the writing.
      3. Then time just LISTING that directory (os.listdir()).
      4. Print write time and list time for each file count -- the data
         volume is constant; only the metadata cost changes.
    """
    raise NotImplementedError("task_2_6_small_file_tax: implement me")


def task_2_7_mmap():
    """
    Task 2.7 (bonus): mmap() -- treat the file as memory instead of a
    stream. This is the smallest possible taste of "Advanced I/O"
    (mmap/zero-copy/io_uring): mmap() maps a file directly into your
    process's own address space, so you read it by slicing/indexing a
    byte-like object -- no read(), no seek(), no syscall per access.

    TODO:
      1. drop_cache(DATA_FILE) -- same reason as Task 2.1: otherwise
         you're mapping pages already sitting in RAM, not measuring
         anything about the device.
      2. Open DATA_FILE and mmap it read-only:
         mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
      3. Repeat Task 2.1's random-access pattern EXACTLY (same
         COMPARE_BYTES // 4096 ops, same 4 KiB block size) but read each
         block by slicing the mapped object (mm[offset : offset + 4096])
         instead of f.seek() + f.read(). Time it.
      4. Print the throughput and compare it to Task 2.1's random-read
         number -- same total bytes, same pattern, different access
         mechanism.
    """
    raise NotImplementedError("task_2_7_mmap: implement me")


def task_2_8_cache_cliff():
    """
    Task 2.8 (bonus): the cache cliff. Repeat Task 2.1's sequential vs
    random comparison at several sizes -- 16 MiB, 256 MiB, 1 GiB, 16 GiB
    -- to find the point where your OWN machine's page cache stops being
    big enough to hide the difference between them. Likely homework
    rather than something to finish live -- writing 4 fresh files (up to
    16 GiB) and reading each one twice takes real wall-clock time.

    TODO: for each size in (16 MiB, 256 MiB, 1 GiB, 16 GiB):
      1. Write a FRESH file of that size in WORK_DIR (reuse
         ensure_test_file with a distinct path per size -- don't reuse
         DATA_FILE, and don't keep more than one size's file on disk at
         once, or you'll multiply Lab 2's already-sizeable footprint).
      2. Read it sequentially in 1 MiB chunks (the whole file, same idea
         as Task 2.1).
      3. Read min(size, COMPARE_BYTES) // 4096 random 4 KiB chunks --
         same total bytes as the sequential pass whenever size fits
         under COMPARE_BYTES (e.g. the 16 MiB step), otherwise capped at
         COMPARE_BYTES for the same reason Task 2.1 caps it (a real scan
         of the full 16 GiB step would mean millions of disk seeks).
      4. Print both throughputs for this size, then delete the file
         before moving to the next size.

    Question: at what size does random throughput start noticeably
    diverging from sequential? Does that line up with your machine's
    RAM?
    """
    raise NotImplementedError("task_2_8_cache_cliff: implement me")


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

# these don't touch DATA_FILE at all -- 2.5 works against the DHT
# (servers/metadata), 2.6 writes its own small_file_tax/ directory, 2.8
# writes its own differently-sized files per sweep step
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
