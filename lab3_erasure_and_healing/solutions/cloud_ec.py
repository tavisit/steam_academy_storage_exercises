"""
cloud_ec.py (Lab 3A/3B): solution.
"""
import hashlib
import os
import sys
import tempfile

# walk up from this file until a `common/` sibling turns up: works
# whether this file stays at its committed depth (.../solutions/) or
# gets copied up to replace the stub (.../), which is how a working
# reference implementation gets exercised against the demo scripts.
# Identical in every solutions/*.py file, no per-lab depth to tune.
_dir = os.path.dirname(os.path.abspath(__file__))
while not os.path.isdir(os.path.join(_dir, "common")):
    _dir = os.path.dirname(_dir)
sys.path.insert(0, os.path.join(_dir, "common"))
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
    primary = h8d(sha1string(cloud_name)[0])
    return [((primary - 1 + i) % N_SERVERS) + 1 for i in range(5)]


# --------------------------------------------------------------------------
# 3A: erasure coding
# --------------------------------------------------------------------------

def cloud_ec_upload(local_path, cloud_name):
    with open(local_path, "rb") as f:
        data = f.read()

    original_size = len(data)
    chunk_size = max(1, -(-original_size // 4))  # ceil division
    padded = data.ljust(chunk_size * 4, b"\x00")
    chunks = [padded[i * chunk_size:(i + 1) * chunk_size] for i in range(4)]

    parity_int = 0
    for c in chunks:
        parity_int ^= int.from_bytes(c, "big")
    parity = parity_int.to_bytes(chunk_size, "big")

    servers = _ec_servers(cloud_name)
    with tempfile.TemporaryDirectory() as tmp:
        for i, c in enumerate(chunks):
            p = os.path.join(tmp, f"chunk{i}")
            with open(p, "wb") as f:
                f.write(c)
            upload(p, servers[i], f"{cloud_name}.chunk{i}")

        p = os.path.join(tmp, "parity")
        with open(p, "wb") as f:
            f.write(parity)
        upload(p, servers[4], f"{cloud_name}.parity")

        meta_path = os.path.join(tmp, "meta")
        with open(meta_path, "w") as f:
            f.write(f"{original_size}\n{chunk_size}\n")
        upload(meta_path, servers[0], f"{cloud_name}.meta")

    total_stored = chunk_size * 5
    overhead_pct = (total_stored / original_size - 1) * 100 if original_size else 0.0
    print(
        f"stored {total_stored} bytes for a {original_size}-byte file "
        f"({overhead_pct:.1f}% overhead, vs 200% for 3x replication)"
    )


def cloud_ec_download(cloud_name, local_path):
    servers = _ec_servers(cloud_name)

    with tempfile.TemporaryDirectory() as tmp:
        meta_path = os.path.join(tmp, "meta")
        if not download(servers[0], f"{cloud_name}.meta", meta_path):
            print(f"EC download FAILED: no metadata found for '{cloud_name}'.")
            return False
        with open(meta_path) as f:
            original_size = int(f.readline())
            chunk_size = int(f.readline())

        chunks = [None] * 4
        for i in range(4):
            p = os.path.join(tmp, f"chunk{i}")
            if download(servers[i], f"{cloud_name}.chunk{i}", p):
                with open(p, "rb") as f:
                    chunks[i] = f.read()

        missing = [i for i, c in enumerate(chunks) if c is None]

        if len(missing) > 1:
            print(
                f"EC reconstruction FAILED: {len(missing)} data chunks missing "
                f"(chunks {missing}), a single XOR parity chunk can only "
                f"recover exactly 1 missing chunk."
            )
            return False

        if len(missing) == 1:
            parity_path = os.path.join(tmp, "parity")
            if not download(servers[4], f"{cloud_name}.parity", parity_path):
                print("EC reconstruction FAILED: parity chunk is also missing.")
                return False
            with open(parity_path, "rb") as f:
                parity = f.read()

            parity_int = int.from_bytes(parity, "big")
            for c in chunks:
                if c is not None:
                    parity_int ^= int.from_bytes(c, "big")
            chunks[missing[0]] = parity_int.to_bytes(chunk_size, "big")
            print(f"Reconstructed missing chunk {missing[0]} from parity + 3 surviving chunks.")

        full = b"".join(chunks)[:original_size]
        with open(local_path, "wb") as f:
            f.write(full)

        total_stored = chunk_size * 5
        overhead_pct = (total_stored / original_size - 1) * 100 if original_size else 0.0
        print(f"EC overhead: {overhead_pct:.1f}% (vs 200% for 3x replication)")
        return True


# --------------------------------------------------------------------------
# 3B: corruption & self-healing (operates on Lab 1's replicated files)
# --------------------------------------------------------------------------

def cloud_check(cloud_name):
    servers = _replica_servers(cloud_name)
    present = [s for s in servers if cloud_name in list_names(s)]
    if len(present) == len(servers):
        return "OK"
    if not present:
        return "LOST"
    return "DEGRADED"


def cloud_heal(cloud_name):
    servers = _replica_servers(cloud_name)
    present = [s for s in servers if cloud_name in list_names(s)]
    missing = [s for s in servers if s not in present]

    if not present:
        return False

    with tempfile.TemporaryDirectory() as tmp:
        tmp_file = os.path.join(tmp, "recovered")
        download(present[0], cloud_name, tmp_file)
        for s in missing:
            upload(tmp_file, s, cloud_name)
    return True


def checksum_store(cloud_name, local_path):
    with open(local_path, "rb") as f:
        digest = hashlib.sha1(f.read()).hexdigest()

    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "sha1")
        with open(p, "w") as f:
            f.write(digest)
        primary = _replica_servers(cloud_name)[0]
        upload(p, primary, f"{cloud_name}.sha1")
    return digest


def checksum_verify(cloud_name, local_path):
    primary = _replica_servers(cloud_name)[0]
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "sha1")
        if not download(primary, f"{cloud_name}.sha1", p):
            raise FileNotFoundError(f"no stored checksum for '{cloud_name}', call checksum_store first")
        with open(p) as f:
            expected = f.read().strip()

    with open(local_path, "rb") as f:
        actual = hashlib.sha1(f.read()).hexdigest()

    return actual == expected
