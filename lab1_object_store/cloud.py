"""
cloud.py (Lab 1): build a distributed object store on top of cloud_lowlevel.

Implement the four functions below, in order (1.1 -> 1.2 -> 1.3). Do not
modify common/cloud_lowlevel.py: everything you need from it is already
imported for you.
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
    rightvalue,
    sha1string,
    upload,
)

# Task 1.2: the metadata directory (a real, separate location from the 8
# data servers, see METADATA_DIR) holds the namespace: every filename
# ever uploaded. cloud_ls needs a single read from here instead of asking
# all N_SERVERS servers individually.
BUCKET_INDEX_PATH = os.path.join(METADATA_DIR, "namespace_index")


def cloud_upload(local_path, cloud_name):
    """
    Task 1.1: upload `local_path` under `cloud_name`.
      - SHA-1 hash `cloud_name`, take its first hex character, and use
        h8d() to map it to one of the N_SERVERS servers. Upload there
        with upload(local_path, server, cloud_name).

    Task 1.3: come back and extend this to 3 total copies, placed so a
    single dead server AND a single dead disk both survive:
      - the primary server itself.
      - one neighbour on the SAME physical disk (disk_group() tells you
        which half of the 8 servers, 1-4 or 5-8, a server is on; use
        leftvalue/rightvalue bounded to that half).
      - the mirrored slot on the OTHER physical disk (same position,
        other half: server N <-> server N+4).

    Task 1.2: also record `cloud_name` in the namespace index (see
    cloud_ls) so it can be listed later without scanning every server.
    """
    raise NotImplementedError("cloud_upload: implement me")


def cloud_download(cloud_name, local_path):
    """
    Task 1.1: download `cloud_name` to `local_path` from its primary server.

    Task 1.3: extend this to fall back through the other 2 replica
    locations (same-disk neighbour, then cross-disk mirror) if the primary
    doesn't have (or no longer has) the file. Return as soon as one copy
    is found.
    """
    raise NotImplementedError("cloud_download: implement me")


def cloud_rm(cloud_name):
    """
    Delete `cloud_name` from every server that holds a copy of it (primary,
    and once 1.3 is done, both other replica locations too) and remove it
    from the namespace index.
    """
    raise NotImplementedError("cloud_rm: implement me")


def cloud_ls():
    """
    Task 1.2: list every uploaded filename with a single lookup, by reading
    BUCKET_INDEX_PATH (in the metadata directory) instead of calling
    list_names() on all N_SERVERS servers.
    """
    raise NotImplementedError("cloud_ls: implement me")
