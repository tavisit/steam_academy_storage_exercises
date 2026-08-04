"""
cloud_ec.py (Lab 3 Part 2, erasure coding; Part 3, corruption & self-healing).

Builds directly on your Lab 2 cloud.py: cloud_check/cloud_heal operate on
files uploaded with Lab 2's replicated cloud_upload (primary + same-disk
neighbour + cross-disk mirror). Erasure coding is a separate, independent
scheme on the same 8 servers.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
from cloud_lowlevel import (  # noqa: E402
    N_SERVERS,
    delete,
    disk_group,
    download,
    h8d,
    leftvalue,
    list_names,
    pathmap,
    rightvalue,
    sealname,
    sha1string,
    upload,
)


def _replica_servers(cloud_name):
    """Same primary + same-disk neighbour + cross-disk mirror formula you
    built in Lab 2's cloud_upload."""
    primary = h8d(sha1string(cloud_name)[0])
    half = N_SERVERS // 2
    if disk_group(primary) == 1:
        same_disk_lo, same_disk_hi = 1, half
        cross_disk = primary + half
    else:
        same_disk_lo, same_disk_hi = half + 1, N_SERVERS
        cross_disk = primary - half
    same_disk_neighbor = leftvalue(primary, same_disk_lo, same_disk_hi)
    return [primary, same_disk_neighbor, cross_disk]


def _ec_servers(cloud_name):
    """5 servers, starting at the file's hash-derived primary, walking the ring."""
    primary = h8d(sha1string(cloud_name)[0])
    return [((primary - 1 + i) % N_SERVERS) + 1 for i in range(5)]


# --------------------------------------------------------------------------
# Part 2: erasure coding
# --------------------------------------------------------------------------

def cloud_ec_upload(local_path, cloud_name):
    """
    Task 3.1.1: split `local_path` into 4 equal-size chunks (zero-pad the
    last one so all 4 are the same length), XOR them together to compute a
    5th parity chunk, and upload all 5 chunks to 5 different servers
    (see _ec_servers). Also store enough metadata (original file size,
    chunk size) somewhere recoverable, so cloud_ec_download can trim the
    zero-padding back off on reconstruction.

    TODO, using `data` and `original_size` above:
      1. Compute `chunk_size` as `original_size` divided by 4, rounded
         UP (so the last chunk still fits even when original_size isn't
         a clean multiple of 4). Pad `data` on the right with zero bytes
         up to `chunk_size * 4`, then slice it into 4 equal pieces.
      2. XOR the 4 chunks together, byte-for-byte, to get a 5th parity
         chunk of the same `chunk_size` (hint: int.from_bytes each
         chunk, XOR the integers, then int.to_bytes back).
      3. Get your 5 target servers from _ec_servers(cloud_name). Upload
         each of the 4 data chunks and the parity chunk to one server
         each, naming them e.g. f"{cloud_name}.chunk0" .. "chunk3" and
         f"{cloud_name}.parity" (upload() takes a local file, so write
         each chunk to a temp file first -- tempfile.TemporaryDirectory
         is convenient here). Also upload a small metadata file (e.g.
         f"{cloud_name}.meta") containing `original_size` and
         `chunk_size`, so cloud_ec_download can trim padding later.
      4. Print the storage overhead: (5 * chunk_size) vs original_size,
         compared to what 3x replication would have cost (200%).
    """
    with open(local_path, "rb") as f:
        data = f.read()
    original_size = len(data)

    raise NotImplementedError("cloud_ec_upload: implement me")


def cloud_ec_download(cloud_name, local_path):
    """
    Task 3.1.2/3.1.3/3.1.4: fetch whatever chunks are available.
      - If all 4 data chunks are present: concatenate and trim to the
        original size.
      - If exactly 1 data chunk is missing: reconstruct it by XOR-ing the
        3 surviving data chunks with the parity chunk.
      - If 2 or more data chunks are missing: this scheme cannot recover.
        Print why and return without writing `local_path`.

    TODO, using `servers` above:
      1. Download the metadata file (servers[0], f"{cloud_name}.meta")
         to get back `original_size` and `chunk_size`. If it's missing,
         print why and return False.
      2. Try to download each of the 4 data chunks
         (servers[0..3], f"{cloud_name}.chunk0".."chunk3"), keeping
         track of which indices actually came back (a list of 4 slots,
         some possibly None, works well).
      3. If more than 1 is missing: print which chunk indices are
         missing and that a single parity chunk can't recover more than
         1, then return False.
      4. If exactly 1 is missing: download the parity chunk
         (servers[4], f"{cloud_name}.parity"). XOR it together with the
         3 surviving data chunks (same XOR trick as upload) to
         reconstruct the missing one.
      5. Concatenate all 4 data chunks in order, trim to `original_size`
         (this removes the zero-padding from upload), write the result
         to `local_path`, print the overhead percentage again, and
         return True.
    """
    servers = _ec_servers(cloud_name)

    raise NotImplementedError("cloud_ec_download: implement me")


# --------------------------------------------------------------------------
# Part 3: corruption & self-healing (operates on Lab 2's replicated files)
# --------------------------------------------------------------------------

def cloud_check(cloud_name):
    """
    Task 3.2.1: return "OK" if all 3 replica locations
    (see _replica_servers) have the file, "DEGRADED" if some do, "LOST" if
    none do.

    TODO, using `servers` above: for each server in `servers`, check
    whether `cloud_name` is in list_names(server). Count how many say
    yes. All of them -> "OK". None of them -> "LOST". Anything in
    between -> "DEGRADED".
    """
    servers = _replica_servers(cloud_name)

    raise NotImplementedError("cloud_check: implement me")


def cloud_heal(cloud_name):
    """
    Task 3.2.3: for a DEGRADED file, download it from whichever replica
    still has it, and re-upload it to whichever replica location(s) are
    missing it, restoring 3 total copies. Return False if the file is
    LOST (no surviving replica to heal from).

    TODO, using `servers` above:
      1. Split `servers` into those that currently have the file and
         those that don't (list_names(server) again).
      2. If none have it, return False.
      3. Otherwise, download it once from any server that has it (a
         temp file works well here), then upload that copy to each
         server that was missing it. Return True.
    """
    servers = _replica_servers(cloud_name)

    raise NotImplementedError("cloud_heal: implement me")


def checksum_store(cloud_name, local_path):
    """
    Task 3.2.4: compute a SHA-1 checksum of `local_path` and store it
    alongside the replicas (e.g. upload it as `cloud_name + '.sha1'` to
    the same servers cloud_check looks at, or just the primary, your
    choice, as long as checksum_verify can find it again).

    TODO, using `primary` above: read `local_path`'s bytes, run them
    through hashlib.sha1(...).hexdigest() to get `digest`, write
    `digest` to a temp file and upload() it to `primary` as
    f"{cloud_name}.sha1". Return `digest`.
    """
    primary = _replica_servers(cloud_name)[0]

    raise NotImplementedError("checksum_store: implement me")


def checksum_verify(cloud_name, local_path):
    """
    Task 3.2.4: recompute the checksum of `local_path` (a copy you just
    downloaded) and compare it against what checksum_store saved. Return
    True/False. This is the check cloud_check does NOT do: cloud_check
    only confirms a copy *exists*, not that its bytes are still correct.

    TODO, using `primary` above: download(primary, f"{cloud_name}.sha1",
    ...) to get the checksum `checksum_store` saved (if it's missing,
    that means checksum_store was never called -- raise
    FileNotFoundError). Recompute local_path's SHA-1 the same way
    checksum_store did, and return whether the two hex digests match.
    """
    primary = _replica_servers(cloud_name)[0]

    raise NotImplementedError("checksum_verify: implement me")
