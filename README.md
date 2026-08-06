# CERN STEAM Academy STORAGE Exercises

Exercises used for the Storage classes for the STEAM Academy CERN 2026.

Three labs, each following its matching lecture block. Every lab is
Python 3, so it runs the same on macOS, Windows and Linux.

## Origin

These exercises are a Python port and extension of Andreas Joachim
Peters' **CSC 2025 Cloud Storage exercises**
(<https://apeters.web.cern.ch/csc2025/html/CLOUD.html>), which were
originally a bash script (`cloud.sh`) built around SHA-1 hashing, path
mapping, and a handful of local directories standing in for storage
servers. Lab 2 here follows that original design closely (DHT, namespace,
replication), extended with a garbage-collection-after-resize task; Lab
3's erasure coding and self-healing extend it further with material from
the CSC 2025 "New Storage Exercises" ideas built on top of the same
primitives.

## Getting started

1. Get your account username and temporary password from the speakers.
2. SSH in and change your password when prompted (first login forces this):
   ```bash
   ssh <username>@steam-storage.cern.ch
   ```
3. Clone this repo into your home directory on the node:
   ```bash
   git clone https://github.com/tavisit/steam_academy_storage_exercises.git
   cd steam_academy_storage_exercises
   ```
4. Start with [`lab1_measure_your_machine/`](lab1_measure_your_machine/) (its `README.md` is the exercise). See [Order](#order) below for the rest.

You don't need root, sudo, or anything outside this repo and your own home
directory: everything a lab needs (your 8 storage servers, your metadata
directory) is already there waiting for you.

## Layout

```
common/                    low-level primitives shared by every lab (given, don't edit)
lab1_measure_your_machine/ Lab 1: sequential/random, flush, queue depth, page cache/O_DIRECT, small-file tax
lab2_object_store/         Lab 2: DHT, namespace, replication, resize/GC
lab3_erasure_and_healing/  Lab 3: erasure coding (Part 2), self-healing (Part 3), re-reading Lab 1's data (Part 4)
```

Each lab directory has:
- `README.md`: the instructions for that lab (GitHub renders it automatically when you open the folder).
- One or more stub `.py` files with `TODO`s and `raise NotImplementedError(...)` markers to fill in.
- `demo_*.py` scripts (given, working) that exercise your implementation and print what to look for.
- `solutions/`: a fully-working reference implementation of every stub, mirroring the directory it belongs to.

## Running a lab

```bash
cd lab2_object_store
python3 make_sample_files.py
# ... implement cloud.py ...
python3 demo_distribution.py
```

### Where the "8 servers" actually live

On this course's node, your shell already has `$STEAM_DIRS` (your real
`server1`..`server8` directories), `$STEAM_METADATA_DIR` (your real
`metadata` directory), and `$STEAM_SCRATCH_DIR` (a scratch directory for
Lab 1's large throwaway test files) exported. `common/cloud_lowlevel.py`
and `lab1_measure_your_machine/bench.py` detect these automatically and
use them, so every lab runs against your actual provisioned storage,
backed by your 2 real dedicated physical disks (not the shared root
filesystem your home directory otherwise sits on).

Running the same exercises anywhere else (your own laptop) falls back to a
synthetic layout under `~/cloud-storage` instead: no account, no SSH,
nothing else to set up:

```bash
git clone https://github.com/tavisit/steam_academy_storage_exercises.git
cd steam_academy_storage_exercises
```

then follow [Order](#order) below exactly as on the course node. Override
the synthetic storage location with `$CLOUD_STORAGE_ROOT` if you want. To
reset between attempts:

```bash
rm -rf ~/cloud-storage        # laptop / fallback mode only
```

**Disk space:** roughly 16 GB total, almost all of it Lab 1's own fixed
16 GiB test file (`bench_data.bin`, deleted or not as you like once
you're done with that lab; on the course node it's on your own
dedicated disk regardless). Lab 1's Task 1.7 sweep additionally
needs up to 16 GiB of headroom for its own largest step, one size at a
time (it deletes each size's file before moving to the next). Everything
else (the repo itself, Lab 2/3's synthetic 8-server storage) adds up to
well under 100 MB. On a laptop, make sure you have ~16 GB free, or lower
`DATA_SIZE` in `lab1_measure_your_machine/bench.py`.

On the course node, resetting means clearing out whichever of your
`server1`..`server8` / `metadata` directories the lab wrote to. Don't
`rm -rf` those directories themselves (they're bind-mounted to your real
disks), just their contents. You own them, so no root needed:

```bash
rm -rf ~/server{1,2,3,4,5,6,7,8}/* ~/metadata/*
```

## Order

1. [`lab1_measure_your_machine/`](lab1_measure_your_machine/)
2. [`lab2_object_store/`](lab2_object_store/)
3. [`lab3_erasure_and_healing/`](lab3_erasure_and_healing/): builds directly on Lab 2's `cloud.py` and Lab 1's `queue_depth_timings.csv`
