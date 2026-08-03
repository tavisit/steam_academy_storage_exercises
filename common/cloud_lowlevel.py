"""
cloud_lowlevel.py: low-level storage primitives (provided, fully working).

Ported from the original cloud.sh (CSC 2025). The 8 "storage servers" are
addressed by an integer 1-8. Nothing in this file needs to change; every
lab builds its cloud_upload / cloud_download / cloud_ls / cloud_rm on top
of these.
"""
import hashlib
import os
import shutil
import tempfile

N_SERVERS = 8

# This course's SSH node already provisions each student 8 real storage
# directories (server1..server8, split across their 2 physical disks) plus
# a metadata directory, and exports them as $STEAM_DIRS / $STEAM_METADATA_DIR
# in every login shell (see gitlab.cern.ch/eos/ops/user_jailing). Use that
# real infrastructure when it's present, so these exercises run against the
# SAME servers and metadata directory the rest of the course already set
# up, rather than a synthetic stand-in. Falls back to a home-relative
# synthetic layout so the same exercises still run unmodified on a
# student's own laptop.
_steam_servers_env = os.environ.get("STEAM_DIRS")
_steam_metadata_env = os.environ.get("STEAM_METADATA_DIR")

if _steam_servers_env:
    _server_dirnames = _steam_servers_env.split()
    if len(_server_dirnames) != N_SERVERS:
        raise RuntimeError(
            f"$STEAM_DIRS lists {len(_server_dirnames)} server(s), expected {N_SERVERS}"
        )
    _SERVER_DIRS = [os.path.expanduser(os.path.join("~", name)) for name in _server_dirnames]
    METADATA_DIR = _steam_metadata_env or os.path.expanduser(os.path.join("~", "metadata"))
else:
    _storage_root = os.environ.get("CLOUD_STORAGE_ROOT") or os.path.expanduser(
        os.path.join("~", "cloud-storage")
    )
    _SERVER_DIRS = [os.path.join(_storage_root, f"{n:02d}") for n in range(1, N_SERVERS + 1)]
    METADATA_DIR = os.path.join(_storage_root, "metadata")

# Every lab uses tempfile.TemporaryDirectory() for small scratch files (EC
# chunk staging, etc.). Point it at a directory under METADATA_DIR instead
# of the system default: METADATA_DIR is guaranteed writable in both
# modes above; the system /tmp is not (see steam-build-jail.sh).
_SCRATCH_DIR = os.path.join(METADATA_DIR, ".scratch")
os.makedirs(_SCRATCH_DIR, exist_ok=True)
tempfile.tempdir = _SCRATCH_DIR


def h8d(hexchar):
    """Map a hex character '0'-'f' to a server number 1-8."""
    return int(hexchar, 16) // 2 + 1


def leftvalue(value, lo=1, hi=N_SERVERS):
    """Left neighbour of `value` on the ring [lo, hi]."""
    left = value - 1
    return hi if left < lo else left


def rightvalue(value, lo=1, hi=N_SERVERS):
    """Right neighbour of `value` on the ring [lo, hi]."""
    right = value + 1
    return lo if right > hi else right


def sha1string(s):
    """SHA-1 hex digest of a string."""
    return hashlib.sha1(s.encode()).hexdigest()


def disk_group(server):
    """
    1 for the first half of servers, 2 for the second half. Mirrors the
    real per-student layout, where each student's 2 physical disks are
    split into servers 1-4 (disk A) and 5-8 (disk B). Used to keep
    replicas from all landing on the same physical disk.
    """
    return 1 if server <= N_SERVERS // 2 else 2


def pathmap(server):
    """Local directory standing in for storage server `server` (1-8)."""
    return _SERVER_DIRS[server - 1]


def sealname(name):
    """Flatten a path into a filename safe to store directly in a server dir."""
    return name.replace("/", "###")


def unsealname(name):
    """Undo sealname."""
    return name.replace("###", "/")


def reset(server):
    """Wipe a server's contents, simulates total node loss."""
    shutil.rmtree(pathmap(server), ignore_errors=True)


def upload(source_file, server, target_name):
    """Copy a local file onto `server` under `target_name`. Returns success."""
    if not os.path.isfile(source_file):
        return False
    target_dir = pathmap(server)
    os.makedirs(target_dir, exist_ok=True)
    shutil.copyfile(source_file, os.path.join(target_dir, sealname(target_name)))
    return True


def download(server, source_name, target_file):
    """Copy `source_name` off `server` to a local file. Returns success."""
    src = os.path.join(pathmap(server), sealname(source_name))
    if not os.path.isfile(src):
        return False
    parent = os.path.dirname(os.path.abspath(target_file))
    os.makedirs(parent, exist_ok=True)
    shutil.copyfile(src, target_file)
    return True


def list_names(server):
    """Names currently stored on `server`, unsealed back to their original form."""
    target_dir = pathmap(server)
    if not os.path.isdir(target_dir):
        return []
    return sorted(unsealname(name) for name in os.listdir(target_dir))


def delete(server, name):
    """Remove `name` from `server`. Returns True if it existed."""
    path = os.path.join(pathmap(server), sealname(name))
    if os.path.isfile(path):
        os.remove(path)
        return True
    return False
