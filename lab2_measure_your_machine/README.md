# Lab 2: Measure Your Own Machine

*60 minutes · after Hardware, Linux I/O, Advanced I/O*

## Background

Everything under a single `read()` call — sequential vs random access,
the page cache, direct I/O, the cost of a flush, queue depth, and the
metadata tax of many small files — is something you can measure on your
own laptop with nothing but Python's standard library. This lab has you
watch every one of those layers yourself, with no framework in the way.

**Keep every number you print.** Task 2.4's raw timings are used again in
Lab 3C, on Day 2.

**Timing note:** most tasks finish in well under a second. A few don't --
**Task 2.2** reads the whole 16 GiB file up to 3 times over (cold pass
and the `O_DIRECT` pass can each take over a minute on a spinning disk),
**Task 2.3** forces 2000 real disk syncs (measured ~90 seconds on the
course node's spinning disks; likely a few seconds on a laptop SSD), and
**Task 2.8** (bonus) writes up to 16 GiB four times over (measured ~2
minutes on the course node). None of these are stuck if they take that
long -- that wait *is* the thing being measured.

## Part 1: Setup

```bash
cd lab2_measure_your_machine
```

Nothing to generate up front — `bench.py` creates its own 16 GiB test
file (`bench_data.bin`) the first time it needs one. On the course node
this lands on your own dedicated disk (`$STEAM_BENCH_DIR`), not your
home directory, so it's safe regardless of how many other students are
running the same task at once. On a laptop it's just the current
directory — make sure you have ~16 GB free, or override `DATA_SIZE` in
`bench.py` if you don't.

This one-time write takes a few seconds on a fast SSD, up to 30-60
seconds on a spinning disk -- it only happens once (whichever task you
run first creates it; every task after reuses the same file).

## Part 2: Task 2.1 — Sequential vs Random

Implement `task_2_1_sequential_vs_random` in `bench.py`: read
`COMPARE_BYTES` of the test file sequentially in 1 MiB chunks, then read
the same total number of bytes again as random 4 KiB chunks at random
offsets. Time both.

`COMPARE_BYTES` (256 MiB) is fixed, independent of `DATA_SIZE` (16 GiB) --
a random scan across the whole 16 GiB file would mean millions of real
disk seeks if it isn't page-cached, which can mean hours instead of
seconds on a real disk. 256 MiB keeps that at a safe, fixed 65536 seeks
either way.

The two passes also use different block sizes on purpose (1 MiB vs
4 KiB) -- that's not a loose end, it mirrors how each pattern is
actually used in practice: streaming/bulk workloads read in large
blocks, random/lookup-style workloads read in small ones.

Call the given `drop_cache(DATA_FILE)` right before **each** pass. With
16+ GB of RAM around, a file you just wrote stays fully page-cached, and
every read -- sequential or random -- looks equally fast (RAM speed, not
disk speed). `drop_cache` evicts it first, so you're actually measuring
the device.

```bash
python3 bench.py 2.1
```

**Record:**

| access pattern | time (s) | throughput (MiB/s) |
|---|---:|---:|
| sequential, 1 MiB blocks | | |
| random, 4 KiB blocks | | |

**Question 2.1** — Same total bytes moved either way. Where does the
difference come from?

## Part 3: Task 2.2 — Buffered, Cached, `O_DIRECT`

Implement `task_2_2_buffered_cached_direct`: read the test file once
(buffered `open()`), read it again immediately (should hit the page
cache), then — if `os.O_DIRECT` exists on your platform — read it a third
time bypassing the page cache entirely.

```bash
python3 bench.py 2.2
```

Each pass reads the whole 16 GiB file. The first (cold) and third
(`O_DIRECT`, which always bypasses cache) passes can each take over a
minute on a spinning disk -- the second (warm) pass should be much
faster, which is the point.

If your OS doesn't support `O_DIRECT` (macOS, Windows), the script will
say so and skip that measurement — that's expected, not a bug.

**Question 2.2** — Why is the *second* buffered read faster than the
first, even though it's the exact same file and the exact same code?

## Part 4: Task 2.3 — The Cost of a Flush

Implement `task_2_3_flush`: write 2000 small (4 KiB) blocks with no
flush at all, then repeat calling `f.flush()` + `os.fsync()` after every
single write.

```bash
python3 bench.py 2.3
```

The flush+fsync half forces 2000 real disk syncs, one per write --
measured ~90 seconds on the course node's spinning disks (likely a few
seconds on a laptop SSD). If it seems to hang, it isn't; that wait *is*
the durability tax the question below asks about.

**Question 2.3** — What real-world guarantee do you get from `fsync()`
that you don't get from a plain `write()`? When would you pay this cost
on purpose?

## Part 5: Task 2.4 — Queue-Depth Sweep (keep the raw data!)

Implement `task_2_4_queue_depth_sweep`: for queue depths 1, 4, 16, 64, 256,
issue that many concurrent random 4 KiB reads (a thread pool is a fine
stand-in for true async I/O here) and record **every individual
operation's latency**, not just the mean.

```bash
python3 bench.py 2.4
```

This writes `queue_depth_timings.csv` — **do not delete this file**, Lab
3C reads it back.

**Question 2.4** — At what depth does throughput stop improving? What
happens to latency at that same point?

## Part 6: Task 2.5 — Garbage Collection After a Resize

Needs Lab 1's `cloud.py` finished first -- this task uploads through it.

Real distributed hash tables get resized — servers get added or removed.
When that happens without also moving data, some copies end up sitting on
servers that are no longer "correct" for their key: not discoverable
through the new placement logic, and not cleaned up either.

In `bench.py`, implement:

- `h4d(hexchar)` — maps a hex character to a bucket **1–4**, the same way
  `h8d` maps to 1–8.
- `cloud_gc(dry_run=True)` — walks every one of the 8 physical servers,
  recomputes each stored file's correct location under the *current*
  (4-server) hash table, and reports any copy sitting somewhere it no
  longer belongs. With `dry_run=False`, it also deletes those orphans.

```bash
python3 bench.py 2.5
```

Like every other task in this lab, this is one command -- it first shows
the resize problem (`cloud_ls()` still lists every name, but most are no
longer reachable at the location a 4-server hash function would compute
for them), then a dry run that reports orphans without changing anything,
then an actual GC pass that removes them and reduces the total number of
physical copies on disk.

**Question 2.5a** — Why implement the dry-run report *before* the
destructive version, rather than the other way around? What would a bug
in `h4d` do to a destructive-only `cloud_gc`?

**Question 2.5b** — The task notes that `cloud_gc` only *removes*
misplaced copies — it doesn't *create* the correct ones. After GC, could
some files now be under-replicated at their new-scheme location? What
already-built tool from Lab 3 fixes that?

**Question 2.5c** — What could go wrong if `cloud_gc` ran
*concurrently* with a client still uploading or downloading a file?

## Part 7: Task 2.6 — The Small-File Tax

Implement `task_2_6_small_file_tax`: write the same 100 MB total as 1
file, then as 100 files, then as 10,000 files, timing the writes and then
timing just listing the directory back.

```bash
python3 bench.py 2.6
```

**Record:**

| file count | write time (s) | list time (s) |
|---:|---:|---:|
| 1 | | |
| 100 | | |
| 10,000 | | |

**Question 2.6** — The data volume was identical in all three rows. What
was actually getting more expensive as the file count grew?

## Part 8: Task 2.7 (bonus) — `mmap`

Everything so far has read the file through `read()`/`seek()`. `mmap()`
takes a different approach entirely: it maps the file directly into your
process's own address space, so you access it by slicing/indexing a
byte-like object instead — no `read()`, no `seek()`, no syscall per
access. This is the smallest possible taste of "Advanced I/O"
(mmap/zero-copy/io_uring) — likely homework rather than something to
finish live.

Implement `task_2_7_mmap`: repeat Task 2.1's random-access pattern
exactly (same total bytes, `COMPARE_BYTES // 4096` ops, same 4 KiB
blocks), but read each block by slicing a read-only `mmap.mmap(...)` of
`DATA_FILE` instead of `f.seek()` + `f.read()`.

```bash
python3 bench.py 2.7
```

**Question 2.7** — Compare this throughput to Task 2.1's random-read
number. Same total bytes, same access pattern — where would you expect
any difference to come from?

## Part 9: Task 2.8 (bonus) — The Cache Cliff

A single fixed `DATA_SIZE` only tells you one point on a curve. This
task sweeps it: repeat Task 2.1's sequential-vs-random comparison at
16 MiB, 256 MiB, 1 GiB, and 16 GiB, to find where *your own machine's*
page cache stops being big enough to hide the difference between them.
Also likely homework — writing up to 16 GiB four times over adds up:
measured ~2 minutes total on the course node.

Implement `task_2_8_cache_cliff`: for each size, write a fresh file (in
`WORK_DIR`, one at a time — delete each before moving to the next size),
then measure sequential throughput and a random-access throughput over
`min(size, COMPARE_BYTES)` bytes -- the full size at the smallest step
(16 MiB, under `COMPARE_BYTES` already), capped at `COMPARE_BYTES` from
256 MiB upward, for the same reason Task 2.1 caps it.

```bash
python3 bench.py 2.8
```

**Question 2.8** — At what size does random throughput start noticeably
diverging from sequential? Does that line up with how much RAM your
machine has?

## Wrapping up

You now have raw, uncurated timing data sitting in `queue_depth_timings.csv`.
Don't touch it — Lab 3C is where you come back and ask harder questions of
the exact same numbers.
