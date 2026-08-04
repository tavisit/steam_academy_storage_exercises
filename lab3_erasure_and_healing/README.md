# Lab 3: Erasure Coding, Corruption, and Your Own Numbers

## Background

This lab has three independent parts. Run them in order; each stands alone
if you run short on time.

- **Part 2 (Erasure Coding)** builds a second, cheaper redundancy scheme
  (erasure coding) alongside the replication you built in Lab 2.
- **Part 3 (Corruption and Self-Healing)** builds failure detection and
  self-healing on top of Lab 2's replication directly.
- **Part 4 (Re-read Your Lab 1 Numbers)** goes back to the raw numbers
  you measured in Lab 1 and asks harder questions of them.

Parts 2-3 both live in `cloud_ec.py`, which imports your finished Lab 2
`cloud.py` for its replication logic. Make sure Lab 2 is working before
you start.

## Part 1: Setup

```bash
cd lab3_erasure_and_healing
```

No new sample data needed: Parts 2-3 generate their own small test files,
and Part 4 reads back `../lab1_measure_your_machine/queue_depth_timings.csv`
from Lab 1 Task 1.3.

---

## Part 2: Erasure Coding

Up to now, redundancy has meant full copies: 3x storage for tolerating one
node loss. Erasure coding trades a little more complexity for a lot less
overhead.

### Task 3.1.1: `cloud_ec_upload`

In `cloud_ec.py`, implement `cloud_ec_upload`: split a file into 4
equal-size chunks (zero-pad the last one), compute a 5th chunk as their
byte-wise XOR, and upload all 5 to 5 different servers.

### Task 3.1.2: `cloud_ec_download`

Implement `cloud_ec_download`: fetch whatever's available and reassemble.

```bash
python3 demo_ec.py
```

Look at the overhead line it prints: **25%** for this scheme, against
**200%** for the 3x replication from Lab 2.

### Task 3.1.3: Reconstruct one lost chunk

`demo_ec.py` already deletes one chunk and re-downloads. Confirm the
recovered file is byte-identical to the original (the demo does this with
`filecmp` for you). This only works once `cloud_ec_download`
XORs the survivors against the parity chunk.

**Question 3.1.3:** You have just built the *m = 1* case of Reed–Solomon.
What does the general (m > 1) version buy you that a single XOR parity
chunk cannot?

### Task 3.1.4: Lose two chunks

`demo_ec.py`'s last section deletes a *second* chunk and tries again. It
should fail cleanly (not crash, not return corrupted data).

**Question 3.1.4:** This 4-data + 1-parity scheme tolerates exactly 1 lost
chunk. What (k, m) split would tolerate 2 simultaneous losses, and what
would that cost in overhead?

### Task 3.1.5: Replication vs Erasure Coding at Scale

Upload the 128 sample files from Lab 2 (`../lab2_object_store/pictures/`:
rerun `python3 make_sample_files.py` there if you've since deleted it)
using both Lab 2's `cloud_upload` (3x replication) and `cloud_ec_upload`
(4+1 erasure coding). Compare total bytes stored across all servers.

**Question 3.1.5:** For the *smallest* file in the set, how much of its
erasure-coded footprint is padding rather than real data? At what file
size does erasure coding stop being worth it?

---

## Part 3: Corruption and Self-Healing

This part operates on files uploaded with **Lab 2's** `cloud_upload` (3x
replication), not the erasure-coded ones from Part 2.

### Task 3.2.1: `cloud_check`

Implement `cloud_check(cloud_name)`: `"OK"` if all 3 replica locations have
the file, `"DEGRADED"` if only some do, `"LOST"` if none do.

### Task 3.2.2: Fail a node

```bash
python3 demo_healing.py
```

This uploads 20 files via Lab 2's `cloud_upload`, wipes one server, and
reports how many files are now `DEGRADED` vs `LOST`.

### Task 3.2.3: `cloud_heal`

Implement `cloud_heal(cloud_name)`: download from any surviving replica,
re-upload to whichever location(s) are missing it. `demo_healing.py` then
re-checks everything and should report all `OK` again.

**Question 3.2.3:** If you fail two servers on the *same* disk at once
(e.g. any two of servers 1-4), does `cloud_heal` recover everything? What
about failing one server from *each* disk instead? (Tie this back to
Lab 2's same-disk-neighbour-vs-cross-disk-mirror question.)

### Task 3.2.4: Now corrupt, don't delete

Implement `checksum_store` and `checksum_verify`: store a SHA-1 of a file
alongside its replicas, and later recompute it to check for a match.

```bash
python3 demo_corruption.py
```

This flips one byte directly on disk on one replica (bypassing the API
entirely, simulating silent bit rot) and then compares what `cloud_check`
reports against what `checksum_verify` reports on that same copy.

**Question 3.2.4:** `cloud_check` says `OK` on a corrupted file. Why?
What would you have to change about it to catch this, and what would that
cost?

---

## Part 4: Re-read Your Lab 1 Numbers

You measured a queue-depth sweep in Lab 1 without knowing yet why the
numbers behaved the way they did. Now you do.

### Task 3.3.1: `analyze_queue_depth.py`

Implement `load_timings()` and `summarize()`:

```bash
python3 analyze_queue_depth.py
```

This reads back every individual latency you recorded in Lab 1 Task 1.3
and computes, per queue depth: mean, p50, p95, p99 latency, and an
estimated throughput. If `matplotlib` is installed it also saves
`queue_depth_knee.png` plotting throughput and p99 latency together.

**Question 3.3.1a:** Where is the "knee", the depth where more concurrency
stops buying more throughput? How far past that point does p99 latency
keep climbing?

**Question 3.3.1b:** Was your device *busy*, or *saturated*, at your
highest queue depth? What's the difference?

## Wrapping up

Three days of exercises, three matching ideas from the lectures: erasure
coding as a cheaper alternative to full replication, self-healing as the
automated version of what you just did by hand, and percentile-based
analysis as the fix for the average lying to you. You built all three
yourself, on your own machine.
