"""
cloud_ec.py -- Lab 3A (erasure coding) + Lab 3B (corruption & self-healing).

Builds directly on your Lab 1 cloud.py: cloud_check/cloud_heal operate on
files uploaded with Lab 1's replicated cloud_upload (primary + same-disk
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
    built in Lab 1's cloud_upload."""
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
# 3A -- erasure coding
# --------------------------------------------------------------------------

def cloud_ec_upload(local_path, cloud_name):
    """
    Task 3A.1: split `local_path` into 4 equal-size chunks (zero-pad the
    last one so all 4 are the same length), XOR them together to compute a
    5th parity chunk, and upload all 5 chunks to 5 different servers
    (see _ec_servers). Also store enough metadata (original file size,
    chunk size) somewhere recoverable, so cloud_ec_download can trim the
    zero-padding back off on reconstruction.

    Print the storage overhead: (5 * chunk_size) vs the original size,
    compared to what 3x replication would have cost (200%).
    """
    raise NotImplementedError("cloud_ec_upload: implement me")


def cloud_ec_download(cloud_name, local_path):
    """
    Task 3A.2/3.3/3.4: fetch whatever chunks are available.
      - If all 4 data chunks are present: concatenate and trim to the
        original size.
      - If exactly 1 data chunk is missing: reconstruct it by XOR-ing the
        3 surviving data chunks with the parity chunk.
      - If 2 or more data chunks are missing: this scheme cannot recover --
        print why and return without writing `local_path`.
    """
    raise NotImplementedError("cloud_ec_download: implement me")


# --------------------------------------------------------------------------
# 3B -- corruption & self-healing (operates on Lab 1's replicated files)
# --------------------------------------------------------------------------

def cloud_check(cloud_name):
    """
    Task 3B.1: return "OK" if all 3 replica locations
    (see _replica_servers) have the file, "DEGRADED" if some do, "LOST" if
    none do.
    """
    raise NotImplementedError("cloud_check: implement me")


def cloud_heal(cloud_name):
    """
    Task 3B.3: for a DEGRADED file, download it from whichever replica
    still has it, and re-upload it to whichever replica location(s) are
    missing it -- restoring 3 total copies. Return False if the file is
    LOST (no surviving replica to heal from).
    """
    raise NotImplementedError("cloud_heal: implement me")


def checksum_store(cloud_name, local_path):
    """
    Task 3B.4: compute a SHA-1 checksum of `local_path` and store it
    alongside the replicas (e.g. upload it as `cloud_name + '.sha1'` to
    the same servers cloud_check looks at, or just the primary -- your
    choice, as long as checksum_verify can find it again).
    """
    raise NotImplementedError("checksum_store: implement me")


def checksum_verify(cloud_name, local_path):
    """
    Task 3B.4: recompute the checksum of `local_path` (a copy you just
    downloaded) and compare it against what checksum_store saved. Return
    True/False. This is the check cloud_check does NOT do -- cloud_check
    only confirms a copy *exists*, not that its bytes are still correct.
    """
    raise NotImplementedError("checksum_verify: implement me")
