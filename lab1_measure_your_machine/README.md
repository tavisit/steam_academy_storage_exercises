# Lab 1: Measure Your Own Machine

## Background

Everything under a single `read()` call is something you can measure on
your own laptop with nothing but Python's standard library: sequential
vs random access, the page cache, direct I/O, the cost of a flush, queue
depth and the metadata tax of many small files. This lab has you watch
every one of those layers yourself, with no framework in the way.

**Keep every number you print.** Task 1.3's raw timings are used again in
Lab 3 Part 4, on Day 2.

**Timing note:** most tasks finish in well under a second. A few don't:

- **Task 1.1**'s random-read pass (256 MiB in 4 KiB chunks, forced cold)
pays a real seek cost on all 65536 reads and is the longest task in this
lab (measured ~6 minutes on the course node's disks; likely a few
seconds on a laptop SSD)
- **Task 1.2** forces 2000 real disk syncs (measured ~90 seconds on the
course node's spinning disks; likely a few seconds on a laptop SSD
- **Task 1.4** reads the whole 16 GiB file up to 3 times over (cold pass
and the `O_DIRECT` pass can each take over a minute on a spinning disk,
up to several minutes if the operation is done by multiple processes),
- **Task 1.7** writes up to 16 GiB four times over (measured ~2
minutes solo on the course node, but this one varies a lot more than
the others: if many students reach it around the same time, the last
(16 GiB) step alone can take anywhere from a few seconds to several
minutes, since it depends on how much of the *shared* page cache
happens to be free right then, not just your own file size). None of
these are stuck if they take that long: that wait *is* the thing being
measured.

## Part 1: Setup

```bash
cd lab1_measure_your_machine
```

Nothing to generate up front: `bench.py` creates its own 16 GiB test
file (`bench_data.bin`) the first time it needs one. On the course node
this lands on your own dedicated disk (`$STEAM_SCRATCH_DIR`), not your
home directory, so it's safe regardless of how many other students are
running the same task at once. On a laptop it's just the current
directory, so make sure you have ~16 GB free, or override `DATA_SIZE` in
`bench.py` if you don't.

This one-time write takes a few seconds on a fast SSD, up to 30-60
seconds on a spinning disk. It only happens once (whichever task you
run first creates it; every task after reuses the same file).

## Part 2: Task 1.1: Sequential vs Random

Implement `task_1_1_sequential_vs_random` in `bench.py`: read
`COMPARE_BYTES` of the test file sequentially in 1 MiB chunks, then read
the same total number of bytes again as random 4 KiB chunks at random
offsets. Time both.

`COMPARE_BYTES` (256 MiB) is fixed, independent of `DATA_SIZE` (16 GiB),
since a random scan across the whole 16 GiB file would mean millions of
real disk seeks if it isn't page-cached, which can mean hours instead of
seconds on a real disk. 256 MiB keeps that at a safe, fixed 65536 seeks
either way.

The two passes also use different block sizes on purpose (1 MiB vs
4 KiB). That's not a loose end, it mirrors how each pattern is
actually used in practice: streaming/bulk workloads read in large
blocks, random/lookup-style workloads read in small ones.

Call the given `drop_cache(DATA_FILE)` right before **each** pass. With
16+ GB of RAM around, a file you just wrote stays fully page-cached, and
every read, sequential or random, looks equally fast (RAM speed, not
disk speed). `drop_cache` evicts it first, so you're actually measuring
the device.

```bash
python3 bench.py 1.1
```

**Record:**

| access pattern | time (s) | throughput (MiB/s) |
|---|---:|---:|
| sequential, 1 MiB blocks | | |
| random, 4 KiB blocks | | |

**Question 1.1:** Same total bytes moved either way. Where does the
difference come from?

## Part 3: Task 1.2: The Cost of a Flush

Implement `task_1_2_flush`: write 2000 small (4 KiB) blocks with no
flush at all, then repeat calling `f.flush()` + `os.fsync()` after every
single write.

```bash
python3 bench.py 1.2
```

The flush+fsync half forces 2000 real disk syncs, one per write.
Measured ~90 seconds on the course node's spinning disks (likely a few
seconds on a laptop SSD). If it seems to hang, it isn't; that wait *is*
the durability tax the question below asks about.

**Question 1.2:** What real-world guarantee do you get from `fsync()`
that you don't get from a plain `write()`? When would you pay this cost
on purpose?

## Part 4: Task 1.3: Queue-Depth Sweep (keep the raw data!)

Implement `task_1_3_queue_depth_sweep`: for queue depths 1, 4, 16, 64, 256,
issue that many concurrent random 4 KiB reads (a thread pool is a fine
stand-in for true async I/O here) and record **every individual
operation's latency**, not just the mean.

```bash
python3 bench.py 1.3
```

This writes `queue_depth_timings.csv`. **Do not delete this file**, Lab
3 Part 4 reads it back.

**Question 1.3:** At what depth does throughput stop improving? What
happens to latency at that same point?

## Part 5: Task 1.4: Buffered, Cached, `O_DIRECT`

Implement `task_1_4_buffered_cached_direct`: read the test file once
(buffered `open()`), read it again immediately (should hit the page
cache), then, if `os.O_DIRECT` exists on your platform, read it a third
time bypassing the page cache entirely.

```bash
python3 bench.py 1.4
```

Each pass reads the whole 16 GiB file. The first (cold) and third
(`O_DIRECT`, which always bypasses cache) passes can each take over a
minute on a spinning disk. The second (warm) pass should be much
faster, which is the point.

If your OS doesn't support `O_DIRECT` (macOS, Windows), the script will
say so and skip that measurement. That's expected, not a bug.

**Question 1.4:** Why is the *second* buffered read faster than the
first, even though it's the exact same file and the exact same code?

## Part 6: Task 1.5: The Small-File Tax

Implement `task_1_5_small_file_tax`: write the same 100 MB total as 1
file, then as 100 files, then as 10,000 files, timing the writes and then
timing just listing the directory back.

```bash
python3 bench.py 1.5
```

**Record:**

| file count | write time (s) | list time (s) |
|---:|---:|---:|
| 1 | | |
| 100 | | |
| 10,000 | | |

**Question 1.5:** The data volume was identical in all three rows. What
was actually getting more expensive as the file count grew?

## Part 7: Task 1.6: `mmap`

Everything so far has read the file through `read()`/`seek()`. `mmap()`
takes a different approach entirely: it maps the file directly into your
process's own address space, so you access it by slicing/indexing a
byte-like object instead, with no `read()`, no `seek()`, no syscall per
access. This is the smallest possible taste of "Advanced I/O"
(mmap/zero-copy/io_uring).

Implement `task_1_6_mmap`: repeat Task 1.1's random-access pattern
exactly (same total bytes, `COMPARE_BYTES // 4096` ops, same 4 KiB
blocks), but read each block by slicing a read-only `mmap.mmap(...)` of
`DATA_FILE` instead of `f.seek()` + `f.read()`.

```bash
python3 bench.py 1.6
```

**Question 1.6:** Compare this throughput to Task 1.1's random-read
number. Same total bytes, same access pattern. Where would you expect
any difference to come from?

## Part 8: Task 1.7: The Cache Cliff

A single fixed `DATA_SIZE` only tells you one point on a curve. This
task sweeps it: repeat Task 1.1's sequential-vs-random comparison at
16 MiB, 256 MiB, 1 GiB and 16 GiB, to find where *your own machine's*
page cache stops being big enough to hide the difference between them.
Writing up to 16 GiB four times over adds up: measured ~2 minutes total
on the course node, budget for that.

**On the course node specifically**, each account is capped at 24 GiB of
memory. By this point `DATA_FILE` (16 GiB, from earlier tasks) is
usually still fully cached, so the 16 GiB step here needs another
~16 GiB on top of that, more than the cap allows. That means you'll
likely see a real cliff at the 16 GiB step even on your own, solo,
rather than needing to rely on other students' concurrent load for it.

Implement `task_1_7_cache_cliff`: for each size, write a fresh file (in
`WORK_DIR`, one at a time, deleting each before moving to the next size),
then measure sequential throughput and a random-access throughput over
`min(size, COMPARE_BYTES)` bytes: the full size at the smallest step
(16 MiB, under `COMPARE_BYTES` already), capped at `COMPARE_BYTES` from
256 MiB upward, for the same reason Task 1.1 caps it.

```bash
python3 bench.py 1.7
```

**Question 1.7:** At what size does random throughput start noticeably
diverging from sequential? Does that line up with how much RAM your
machine has?

## Wrapping up

You now have raw, uncurated timing data sitting in `queue_depth_timings.csv`.
Don't touch it. Lab 3 Part 4 is where you come back and ask harder
questions of the exact same numbers.
