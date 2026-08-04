"""
cloud.py (Lab 2): build a distributed object store on top of cloud_lowlevel.

Implement the six functions below, in order (2.1 -> 2.2 -> 2.3 -> 2.4). Do
not modify common/cloud_lowlevel.py: everything you need from it is
already imported for you.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
from cloud_lowlevel import (  # noqa: E402
    METADATA_DIR,
    N_SERVERS,
    delete,
    disk_group,
    download,
    h8d,
    leftvalue,
    list_names,
    rightvalue,
    sha1string,
    upload,
)

# Task 2.2: the metadata directory (a real, separate location from the 8
# data servers, see METADATA_DIR) holds the namespace: every filename
# ever uploaded. cloud_ls needs a single read from here instead of asking
# all N_SERVERS servers individually.
BUCKET_INDEX_PATH = os.path.join(METADATA_DIR, "namespace_index")


def cloud_upload(local_path, cloud_name):
    """
    Task 2.1: upload `local_path` under `cloud_name`.
      - SHA-1 hash `cloud_name`, take its first hex character, and use
        h8d() to map it to one of the N_SERVERS servers. Upload there
        with upload(local_path, server, cloud_name).

    Task 2.3: come back and extend this to 3 total copies, placed so a
    single dead server AND a single dead disk both survive:
      - the primary server itself.
      - one neighbour on the SAME physical disk (disk_group() tells you
        which half of the 8 servers, 1-4 or 5-8, a server is on; use
        leftvalue/rightvalue bounded to that half).
      - the mirrored slot on the OTHER physical disk (same position,
        other half: server N <-> server N+4).

    Task 2.2: also record `cloud_name` in the namespace index (see
    cloud_ls) so it can be listed later without scanning every server.
    """
    raise NotImplementedError("cloud_upload: implement me")


def cloud_download(cloud_name, local_path):
    """
    Task 2.1: download `cloud_name` to `local_path` from its primary server.

    Task 2.3: extend this to fall back through the other 2 replica
    locations (same-disk neighbour, then cross-disk mirror) if the primary
    doesn't have (or no longer has) the file. Return as soon as one copy
    is found.
    """
    raise NotImplementedError("cloud_download: implement me")


def cloud_rm(cloud_name):
    """
    Delete `cloud_name` from every server that holds a copy of it (primary,
    and once 2.3 is done, both other replica locations too) and remove it
    from the namespace index.
    """
    raise NotImplementedError("cloud_rm: implement me")


def cloud_ls():
    """
    Task 2.2: list every uploaded filename with a single lookup, by reading
    BUCKET_INDEX_PATH (in the metadata directory) instead of calling
    list_names() on all N_SERVERS servers.
    """
    raise NotImplementedError("cloud_ls: implement me")


# names that don't follow the plain "one primary + 2 ring neighbours"
# placement rule: skip these during GC, they belong to Lab 3's other
# schemes (erasure-coded chunks/parity/meta, stored checksums)
_SKIP_SUFFIXES = (".chunk0", ".chunk1", ".chunk2", ".chunk3", ".parity", ".meta", ".sha1")
NEW_RING_SIZE = 4


def h4d(hexchar):
    """
    Task 2.4a: map a hex character '0'-'f' to a bucket 1-4, the same
    "ring" idea as h8d above, just resized from 8 buckets to 4.

    (Reminder: a "ring" here just means the buckets are numbered 1..N and
    treated as wrapping around; leftvalue/rightvalue below use that to
    find a bucket's neighbours.)

    TODO: this is a one-line change to h8d's own formula. h8d divides by
    2 because 16 possible hex values / 8 buckets = 2 values per bucket.
    How many hex values map to each of the 4 buckets here?
    """
    raise NotImplementedError("h4d: implement me")


def _current_replica_servers(cloud_name):
    """Where `cloud_name` SHOULD live under the resized (4-server) table.
    Given: reuses your h4d plus leftvalue/rightvalue, unchanged."""
    primary = h4d(sha1string(cloud_name)[0])
    return [primary, leftvalue(primary, 1, NEW_RING_SIZE), rightvalue(primary, 1, NEW_RING_SIZE)]


def _is_collectible(name):
    """Given: True unless `name` belongs to one of Lab 3's other
    on-disk schemes (erasure-coded chunks, stored checksums), which don't
    follow this plain primary+2-neighbours placement rule and would
    otherwise look like false orphans below."""
    return not name.endswith(_SKIP_SUFFIXES)


def cloud_gc(dry_run=True):
    """
    Task 2.4b: find and (optionally) remove "orphans", copies sitting on
    a server that the CURRENT, resized hash table would never look at
    again. They're not corrupt or lost, just stranded: unreachable
    through normal lookups, and wasting disk until something cleans them up.

    TODO:
      1. For each of the N_SERVERS physical servers, get what's stored
         there (hint: list_names(server), same as you used elsewhere).
      2. Skip anything _is_collectible() says to skip.
      3. For everything else, compare the server you're scanning against
         _current_replica_servers(name), given, already computes the 3
         correct locations for you. Not in that list means orphan.
      4. dry_run=True (default): only build and print a report, delete
         nothing. dry_run=False: also delete(server, name) each orphan.

    Print a per-server orphan count, then a total, and return the report
    as a list of (server, name) tuples.
    """
    raise NotImplementedError("cloud_gc: implement me")
