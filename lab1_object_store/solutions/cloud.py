"""
cloud.py -- Lab 1 solution.
"""
import os
import sys

# walk up from this file until a `common/` sibling turns up -- works
# whether this file stays at its committed depth (.../solutions/) or
# gets copied up to replace the stub (.../), which is how a working
# reference implementation gets exercised against the demo scripts.
# Identical in every solutions/*.py file -- no per-lab depth to tune.
_dir = os.path.dirname(os.path.abspath(__file__))
while not os.path.isdir(os.path.join(_dir, "common")):
    _dir = os.path.dirname(_dir)
sys.path.insert(0, os.path.join(_dir, "common"))
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

BUCKET_INDEX_PATH = os.path.join(METADATA_DIR, "namespace_index")


def _primary_server(cloud_name):
    first_hex_char = sha1string(cloud_name)[0]
    return h8d(first_hex_char)


def _replica_servers(cloud_name):
    """3 total copies: the primary, one same-disk neighbour, one
    cross-disk mirror -- survives losing either a single server or an
    entire physical disk."""
    primary = _primary_server(cloud_name)
    half = N_SERVERS // 2
    if disk_group(primary) == 1:
        same_disk_lo, same_disk_hi = 1, half
        cross_disk = primary + half
    else:
        same_disk_lo, same_disk_hi = half + 1, N_SERVERS
        cross_disk = primary - half
    same_disk_neighbor = leftvalue(primary, same_disk_lo, same_disk_hi)
    return [primary, same_disk_neighbor, cross_disk]


def _read_bucket_index():
    if not os.path.isfile(BUCKET_INDEX_PATH):
        return []
    with open(BUCKET_INDEX_PATH) as f:
        return [line.rstrip("\n") for line in f if line.strip()]


def _write_bucket_index(names):
    os.makedirs(METADATA_DIR, exist_ok=True)
    with open(BUCKET_INDEX_PATH, "w") as f:
        for name in names:
            f.write(name + "\n")


def cloud_upload(local_path, cloud_name):
    for server in _replica_servers(cloud_name):
        upload(local_path, server, cloud_name)

    names = _read_bucket_index()
    if cloud_name not in names:
        names.append(cloud_name)
        _write_bucket_index(names)


def cloud_download(cloud_name, local_path):
    for server in _replica_servers(cloud_name):
        if download(server, cloud_name, local_path):
            return server
    return None


def cloud_rm(cloud_name):
    deleted_from = [s for s in _replica_servers(cloud_name) if delete(s, cloud_name)]

    names = _read_bucket_index()
    if cloud_name in names:
        names.remove(cloud_name)
        _write_bucket_index(names)
    return deleted_from


def cloud_ls():
    return _read_bucket_index()
