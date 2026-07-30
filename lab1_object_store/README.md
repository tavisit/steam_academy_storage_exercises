# Lab 1: Build a Distributed Object Store

*60 minutes · after Storage Foundations*

## Background

A "cloud storage" system is just three ideas stacked on top of each other:
an object store (key → blob), a namespace on top of it (so listing your
files doesn't mean asking every server), and redundancy (so one dead server
doesn't lose data). In this lab you build all three, in that order, on top
of eight storage servers and a metadata directory.

On this course's node, those aren't simulated — they're the real
`server1`..`server8` and `metadata` directories already sitting in your
home directory (`$STEAM_SERVERS` / `$STEAM_METADATA`, exported by your
shell), backed by your 2 real physical disks. Running the same exercises
on your own laptop instead falls back to a synthetic stand-in under
`~/cloud-storage` automatically — nothing in your code needs to know or
care which mode it's running in.

Everything low-level (hashing, path mapping, raw upload/download/list/delete
against a single server) is already implemented for you in
`../common/cloud_lowlevel.py`. You will not need to change it — only read
it to see what's available.

## Part 1: Setup

Generate the 128 sample files every task in this lab uploads:

```bash
cd lab1_object_store
python3 make_sample_files.py
```

## Part 2: Task 1.1 — A Distributed Hash Table (DHT)

Open `cloud.py`. Implement `cloud_upload` and `cloud_download` so that a
file is placed on exactly one server, chosen like this:

1. SHA-1 hash the file's cloud name (`sha1string`).
2. Take the first hex character of the digest.
3. Map it to a server 1–8 with `h8d`.
4. Upload to that server with the provided `upload()` primitive.

`cloud_download` is the mirror image: hash the name the same way, then
`download()` from that server.

Once both are implemented, upload every sample file and look at how they
land:

```bash
python3 demo_distribution.py
```

**Record the per-server counts here** (do this now, right after Task 1.1
— Task 1.3 adds replication, which will roughly triple every count if
you re-run this demo later):

| server | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| files | | | | | | | | |

**Question 1.1** — SHA-1 is supposed to be uniform. Is the distribution you
just measured actually even? If not, is that a bug in your code, or exactly
what you'd expect from hashing only 128 items into 8 buckets?

## Part 3: Task 1.2 — Bucket / Namespace

Right now, listing every uploaded file would mean asking all 8 servers.
Implement `cloud_ls` instead to use the **metadata directory**
(`METADATA_DIR` in `cloud.py`, imported from `cloud_lowlevel`) — a location
genuinely separate from the 8 data servers, exactly like a real system's
namespace/metadata service. Write a single index file there
(`BUCKET_INDEX_PATH`) listing every name ever uploaded. Update
`cloud_upload` (and `cloud_rm`, once you get to it) to keep that index in
sync.

Compare your single-lookup listing against a brute-force scan of all 8
servers:

```bash
python3 demo_bucket.py
```

It should report a **match** between `cloud_ls()` and the brute-force scan,
with `cloud_ls()` needing 1 lookup instead of 8.

**Question 1.2** — You gained one lookup instead of eight. What did you
lose? (Hint: none of the 8 data servers holds anything special anymore —
but is that true of the metadata directory too? What happens to every
single upload/list/delete if it's slow, full, or down?)

## Part 4: Task 1.3 — Redundancy

A single primary server is a single point of failure — and on this node,
servers 1-4 sit on one physical disk and 5-8 on the other, so "one dead
server" and "one dead disk" are both real failure modes to plan for.
Extend `cloud_upload` to write 3 total copies, placed so either failure
survives:

1. the primary server itself.
2. one neighbour on the **same** disk as the primary (`disk_group` tells
   you which half — 1-4 or 5-8 — a server belongs to; use
   `leftvalue`/`rightvalue` bounded to that half).
3. the mirrored slot on the **other** disk (server *N* ↔ server *N* + 4).

Extend `cloud_download` to try the primary first, then the same-disk
neighbour, then the cross-disk mirror, returning as soon as one succeeds.
Extend `cloud_rm` to delete from all three.

Confirm a file survives losing its primary server:

```bash
python3 demo_redundancy.py
```

It should upload a file, report its primary server, wipe that server
entirely, and still recover the file from a replica.

(If you re-run `demo_distribution.py` now out of curiosity, every
server's count will jump to roughly 3x what you recorded above --
`list_names()` counts every copy it finds, primary or not. That's
expected, not a bug -- you just tripled how many copies of each file
exist.)

**Question 1.3** — Should `cloud_download` always prefer the primary
replica, or pick one of the three at random? Argue both sides.

**Question 1.4** — Of your 2 non-primary copies, one is same-disk and one
is cross-disk. Which one actually protects you against a whole-disk
failure? What's the same-disk copy still buying you, then, if the
cross-disk one already covers the worse failure?

## Wrapping up

By the end of this lab your `cloud.py` has independently reinvented a
metadata service (the namespace index) and a replication scheme (the
three-way, disk-aware mirror). Keep your working `cloud.py` — Lab 3 builds
directly on top of it.
